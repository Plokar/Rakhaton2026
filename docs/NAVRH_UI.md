# Návrh UI v2: kalendář zasedání, jednání komise a detail pacienta

> **Stav:** implementováno ve větvi `t-516-ui-v2` (T-516, T-517, T-519–T-522) · návrh @Jarda+claude, implementace @Maty+claude · So 17. 10. 2026. Otevřené otázky Q1–Q7 jsou rozhodnuté ([§14](#14-otevřené-otázky)), API změny (T-518) čekají na API lane; UI do té doby skládá data z existujících endpointů.
>
> - **Navazuje na:** T-512 (admin okno a úzký panel `/projector`, větev `t-512-admin-board-overview`, čeká na review) a T-514 (přihlašovací stránka, v `master`).
> - **Zdroj pravdy pro požadavky** zůstává [ARCHITEKTURA.md](../ARCHITEKTURA.md) a [POZADAVKY_LEKARE.md](POZADAVKY_LEKARE.md). Tento dokument řeší jen podobu a chování UI.
> - **Metoda:** skilly `impeccable` (critique, shape, craft-floor), `shadcn`, `vercel-react-best-practices` a `web-design-guidelines`. Audit stojí na snímcích reálné aplikace (backend + IRIS, demo účet předsedy) a na mechanickém skenu kódu.

---

## 0. Shrnutí

**Proč:** komise má na pacienta 2–5 minut a lékař se musí zorientovat do 30 sekund. Dnešní UI tomu brání:

- podklad případu je dlouhý ~15 000 px (16 obrazovek);
- karta pacienta v agendě má ~380 px výšky a pět akcí;
- vzhled působí jako šablona: verzálkové popisky, monospace „štítky“, ikony v barevných čtvercích, karty v kartách.

**Co se mění:**

1. **Přehled = kalendář zasedání.** Týdenní mřížka, každé políčko je jedno zasedání se svými pacienty. Pacienty jde přetahovat mezi zasedáními (drag & drop s alternativou z klávesnice a z menu). Plus v pravém horním rohu políčka zařadí pacienta. Klik na pacienta otevře boční panel s rychlým přehledem.
2. **Jednání komise** (`/dashboard/mdt/[id]`) má vlevo úzký seznam pacientů a vpravo **30s rychlý přehled** (stejný obsah jako panel projektoru z T-512). Mezi pacienty se přepíná šipkami, okno projektoru jede synchronně a z přehledu se jde do detailu.
3. **Detail pacienta** (`/dashboard/cases/[id]`) má pevnou hlavičku a navigaci po sekcích. Nahoře je rychlý přehled, ostatní je sbalené. Varovné signály jsou kompaktní seznam místo 11 velkých karet a časová osa je jen jedna.
4. **Shell:**
   - sidebar postavený na komponentě `Sidebar` ze shadcn s rychlými odkazy na nejbližší zasedání a bez „Dev služeb“;
   - avatar vpravo nahoře otevře menu s Nastavením a Odhlášením;
   - pryč je tlačítko Swagger UI.
5. **Dashboard** bez karty „Úkoly po termínu“ a bez ukázkového banneru. Úkoly zůstávají v sidebaru.
6. **Vizuální jazyk** podle přihlašovací stránky (T-514): tiché plochy, hustota v řádcích místo karet, barva jen pro význam a písmo od 13 px.

**Požadavky ze zadání (17. 10.) → kde jsou řešené:**

| Požadavek | Sekce |
|---|---|
| Odebrat dev služby a tlačítko Swagger UI | [§5](#5-shell-sidebar-a-horní-lišta) |
| Avatar „P“ vpravo nahoře → menu Nastavení a Odhlásit | [§5.2](#52-horní-lišta-a-uživatelské-menu) |
| Z dashboardu pryč „Úkoly po termínu“ | [§6](#6-přehled--kalendář-zasedání) |
| Zasedání jako kalendářová mřížka, políčko = zasedání, pacienti v něm | [§6.1](#61-mřížka) |
| Drag & drop pacienta mezi zasedáními | [§6.3](#63-přesun-pacienta-drag--drop) |
| Klik na pacienta → detail s AI obsahem | [§6.4](#64-rychlý-přehled-v-bočním-panelu), [§8](#8-detail-pacienta) |
| Plus v pravém horním rohu zasedání → zařadit pacienta | [§6.5](#65-zařazení-pacienta-z-kalendáře) |
| Lepší sidebar | [§5.1](#51-sidebar) |
| Zasedání: pacienti + 30s rychlý přehled + proklik na detail | [§7](#7-jednání-komise) |
| Méně „AI-generated“ feel | [§1.3](#13-proč-to-působí-generovaně), [§3](#3-vizuální-jazyk) |
| Moderní knihovny Next.js a React | [§11](#11-knihovny) |

---

## 1. Výchozí stav (audit)

### 1.1 Obrazovky dnes

| Routa | Komponenta | Co dělá | Hlavní problém |
|---|---|---|---|
| `/dashboard` | `app/dashboard/page.tsx` | nadpis, banner „Ukázkový 30s podklad P03“, karta 4 nejbližších zasedání, karta „Úkoly po termínu“ (vždy prázdná) | nic z toho nepomáhá připravit zasedání; zasedání jsou seznam bez pacientů (jen ID) |
| `/dashboard/mdt` | `app/dashboard/mdt/page.tsx` + `SessionCard` | seznam zasedání | stejná karta jako na dashboardu, bez času v kontextu týdne |
| `/dashboard/mdt/[id]` | `AgendaItem` (`components/mdt/sessions.tsx`) | agenda: karta na pacienta | ~380 px na pacienta, vnořené boxy (diagnóza / ECOG / záměr / otázka), 5 akcí a select „Přesunout na board…“ |
| `/dashboard/cases/[id]` | `CaseBriefScreen` → `BriefView` | celý podklad | **14 924 px** u P02, dvě časové osy (AI + IRIS), 11 varovných signálů jako velké karty |
| shell | `components/layout/DashboardLayout.tsx` | sidebar, horní lišta | „Dev služby“ a Swagger v UI, avatar vpravo bez akce, uživatelské menu schované dole v sidebaru, každá stránka si layout montuje sama (sidebar se při navigaci přemontuje) |

### 1.2 Kritika podle Nielsenových heuristik

Hodnoceno nad snímky reálné aplikace (1440 × 900, demo účet předsedy, backend + IRIS) a nad kódem. 0 = chybí, 4 = výborné.

| # | Heuristika | Skóre | Klíčové zjištění |
|---|---|---|---|
| 1 | Viditelnost stavu systému | 2 | připravenost a stav případu jsou drobné štítky; po „Přesunout“ chybí potvrzení a vrácení |
| 2 | Shoda se světem lékaře | 3 | jazyk komise sedí (ECOG, C/P, MKN-10), ale „30s Rychlý náhled“, „Úzké okno“ a „Nastavit podklad“ jsou interní pojmy týmu |
| 3 | Kontrola a svoboda | 2 | přesun mezi boardy nejde vrátit; smazání boardu přes `window.confirm` |
| 4 | Konzistence | 2 | uživatelské menu je dole v sidebaru, avatar nahoře bez akce; pacient vypadá jinak v kartě zasedání, v agendě a v podkladu; mono písmo pro kódy i čísla; tlačítka a odkazy s vlastními třídami místo `Button` |
| 5 | Prevence chyb | 2 | přesun jde i na uzavřený board (backend to nekontroluje) |
| 6 | Rozpoznání místo vybavování | 2 | v agendě není vidět, který pacient je na řadě; mezi agendou a podkladem se ztrácí kontext |
| 7 | Flexibilita a efektivita | 1 | kromě Ctrl+K žádné klávesové zkratky; během jednání se mezi pacienty nedá rychle přepínat |
| 8 | Estetika a minimalismus | 1 | karta v kartě, 11 velkých karet varování, verzálkové popisky nad každým údajem |
| 9 | Zotavení z chyb | 2 | chyby jsou texty z API (anglicky, nebo „HTTP Error 500“) bez dalšího kroku |
| 10 | Nápověda | 2 | vysvětlivky barev jsou jen u semaforu; legenda zkratek chybí |
| | **Celkem** | **19/40** | **slabé**, funkčně bohaté, ale pro 2–5 min na pacienta příliš rozvláčné |

**Kognitivní zátěž** (impeccable checklist, 8 bodů): **6 bodů nesplněno**, tedy vysoká zátěž. Splněné je seskupení souvisejících údajů a částečně hierarchie v hlavičce podkladu. Nesplněné: jedno zaměření (agenda soupeří s pěti akcemi), členění po ≤ 4 položkách (11 varování naráz), jedna věc v daný okamžik, ≤ 4 volby v rozhodovacím bodě, práce bez paměti z předchozí obrazovky (agenda → podklad ztrácí kontext) a postupné odkrývání (podklad je celý rozbalený).

### 1.3 Proč to působí „generovaně“

Mechanický sken `components/mdt`, `app/dashboard` a `components/layout`:

| Vzor | Počet | Proč vadí |
|---|---|---|
| písmo 9–11 px (`text-[9px]` … `text-[11px]`) | **90×** | na projektoru nečitelné; komise sleduje jedno plátno |
| `font-mono` | **53×** ve 21 souborech | monospace jako „technický kostým“ pro ID, MKN a čísla; v klinické dokumentaci působí cize |
| `rounded-xl border` / `rounded-2xl border` | **47×** | všechno je orámovaná karta, často karta v kartě |
| verzálkové popisky (`uppercase tracking-…`) | **30×** | „kicker“ nad každým údajem (craft-floor ho zakazuje) |
| `font-extrabold` / `font-black` | **22×** | křik místo hierarchie; vedle sebe tři úrovně tučnosti |
| ikony v barevném čtverci (`h-11 w-11 rounded-xl bg-primary/10`) | dashboard, `SessionCard`, prázdné stavy | šablonová „ikonová dlaždice“, nenese informaci |

Detektor `impeccable detect` našel jen 4 barevné levé pruhy (`CaseHeader`, `sessions`). Ty jsou záměrné (D-017: AI, závažnost, hlavní otázka).

Zásadní nekonzistence: **AI je označená tyrkysově (`teal-700`), stejnou barvou jako primární akce (`--primary: #0f766e`).** POZADAVKY §3.4 přitom chce pro AI fialovou, aby se nepletla s ničím jiným. Viz otevřená otázka [Q1](#14-otevřené-otázky).

### 1.4 Co funguje a zůstane

- **Citace a zdroje:** `CitationChip` + `SourceDrawer` (FR-R3) a čísla citací v pořadí podkladu.
- **Semafor:** `CompatibilityLight` (✓ ! ✕ ? + text, D-015), barvy odborností z `roles.ts` (D-017), `AiBlock` s označením „AI návrh“ (logika zůstává, mění se barva, Q1).
- **Formulář zařazení:** `IntakeForm` (Doplnit / Přeskočit, varování, D-019), `BoardDialog`, `JobProgress`.
- **Z T-512:**
  - `ProjectorPanel` a `key-facts.ts`, tedy 30s přehled: kolečka normality jen z referenčních mezí a pravidel, všechny postupy se semaforem, otázka a MKN-10 dole;
  - synchronizace oken přes BroadcastChannel.
- **Z T-514:** vizuální jazyk loginu (MedTeam, tiché plochy, štítky odborností u rolí).

---

## 2. Principy návrhu

1. **Jedna obrazovka, jedna práce** (impeccable: režim *Operate*):
   - kalendář = plánování;
   - jednání = projednat pacienta;
   - detail = dohledat a ověřit.
2. **30 sekund na orientaci.** Rychlý přehled má všude stejné pořadí a stejné zkratky: v jednání, v bočním panelu, na projektoru i nahoře v detailu. Lékař se ho naučí jednou.
3. **Postupné odkrývání:** kalendář → rychlý přehled (panel) → detail (stránka). Každá úroveň má odkaz o úroveň hlouběji a nikdy nevynucuje víc.
4. **Barva jen pro význam:**
   - semafor (soulad postupu);
   - normalita hodnot (stejná paleta a tvary ikon);
   - odbornost (štítek);
   - AI (vlastní barva, Q1).
   Primární tyrkysová patří jen primární akci, výběru a focusu. Barva nikdy nenese informaci sama, vždy je u ní tvar ikony nebo text (POZADAVKY §3.4).
5. **Řádky místo karet.** Kartou je jen samostatný objekt (zasedání v kalendáři, panel). Pacient je řádek, údaj je dvojice zkratka–hodnota. Nikdy karta v kartě.
6. **Klávesnice a projektor:**
   - písmo nejméně 13 px (v jednání 14–15 px, na projektoru 15–18 px);
   - zkratky pro vše, co se během jednání opakuje;
   - kontrast AA i v tmavém režimu („Projektor“).
7. **Pravidla obsahu z AGENTS.md platí beze změny:**
   - AI je vždy označená a každé tvrzení má citaci;
   - nikdy „doporučujeme“;
   - hlavička bez jména a RČ (D-018);
   - semafor počítá jen kód (D-015);
   - nic se neztratí (D-019).

---

## 3. Vizuální jazyk

Tokeny v `src/app/globals.css` zůstávají (stejné názvy jako shadcn), mění se jejich použití.

### 3.1 Typografie

Jedna rodina: **Inter** (už načtená přes `next/font`). Váhy 400 / 500 / 600, **bez 700–900**. Žádné verzálky ani prostrkání.

| Role | Velikost / řádek | Váha | Kde |
|---|---|---|---|
| Titulek stránky | 24 / 32 | 600 | „Zasedání“, název boardu |
| Nadpis sekce | 16 / 24 | 600 | „Klíčové údaje“, „Léčebné postupy“ |
| Text | 14 / 20 | 400 | výchozí |
| Hustý text a meta | 13 / 18 | 400–500 | řádky pacientů, čas, počet |
| Popisek (minimum) | 12 / 16 | 500 | jen legendy a nápovědy, nikdy klinický údaj |
| Číslo v hlavičce | 28 / 32 | 600 | PS, C/P |

- Čísla a data mají `tabular-nums`, aby nevyskakovala ve sloupcích.
- **Monospace se nepoužívá.** MKN-10, ID pacienta a citace jsou běžné písmo; kódy dostanou `translate="no"`.

### 3.2 Barvy

| Token / systém | Použití | Poznámka |
|---|---|---|
| `--background`, `--card`, `--muted` | tři plochy: stránka, panel, zvýraznění řádku | žádné další odstíny šedi |
| `--border` | jediná tloušťka 1 px | oddělovač místo rámečku, kde stačí |
| `--primary` (tyrkysová) | primární tlačítko, vybraný řádek, focus, dnešní den | nic jiného |
| Semafor (`CompatibilityLight`) | soulad postupu | zelená / oranžová / červená / šedá + ✓ ! ✕ ? + text |
| Normalita (`key-facts`) | hodnoty pacienta | stejné odstíny, tvary ikon `CircleCheck` / `CircleAlert` / `OctagonAlert` / `CircleDot` / `CircleDashed` |
| Odbornost (`roles.ts`) | štítek role | beze změny |
| AI | levý pruh a štítek „AI návrh“ | **návrh: fialová** (`violet-600` / `violet-400` v tmavém režimu), aby se nepletla s `--primary` (Q1) |

### 3.3 Prostor, tvary, pohyb

- **Mřížka:** 4 px. Rytmus 4 / 8 / 12 / 16 / 24 / 32. Nad nadpisem víc místa než pod ním.
- **Zaoblení:**
  - 8 px: ovládací prvky a čipy;
  - 12 px: dlaždice zasedání a panely;
  - 16 px nepoužíváme.
- **Stíny** jen pro vrstvy nad obsahem (menu, boční panel, tažený čip). Měkké, s posunem: `0 12px 32px -12px rgb(15 23 42 / .25)`.
- **Ikony:** lucide, 16 px, tah 1.75, bez barevných dlaždic. Ikona jen tam, kde nese funkci nebo stav.
- **Pohyb:**
  - 150–200 ms ease-out;
  - jediný „autorský“ pohyb je přesun čipu pacienta do jiného zasedání (layout animace);
  - `prefers-reduced-motion` vypíná vše kromě změny stavu.

---

## 4. Informační architektura a routy

Společný shell bude **`app/dashboard/layout.tsx`** místo `<DashboardLayout>` v každé stránce. Sidebar se při navigaci nepřemontuje a drží stav (sbalení, scroll). Stav obrazovek (týden, vybraný pacient) je v URL přes `nuqs`, takže jde sdílet odkazem a funguje tlačítko Zpět.

| Routa | Obrazovka | Změna |
|---|---|---|
| `/dashboard` | **Kalendář zasedání** (`?tyden=2026-W43&pacient=12`) | nová (§6) |
| `/dashboard/mdt` | seznam zasedání (filtr komise, minulá) | zjednodušení: řádky místo karet |
| `/dashboard/mdt/[id]` | **Jednání komise** (`?pacient=12`) | nová podoba (§7) |
| `/dashboard/mdt/[id]/add` | zařazení pacienta | zůstává jako záloha; hlavní cesta je boční panel z kalendáře (§6.5) |
| `/dashboard/mdt/[id]/setup` | konfigurátor podkladu | beze změny |
| `/dashboard/cases/[id]` | **Detail pacienta** | nová podoba (§8) |
| `/dashboard/cases/[id]/record` | závěr komise | beze změny |
| `/dashboard/tasks` | úkoly | jen v sidebaru (s počtem), z dashboardu pryč |
| `/dashboard/settings` | nastavení | odkaz z uživatelského menu |
| `/projector` | okno projektoru | z T-512, beze změny |
| `/brief/[id]` | úzké okno podkladu | beze změny |

---

## 5. Shell: sidebar a horní lišta

```
┌──────────────────────┬────────────────────────────────────────────────────────────────────┐
│ ◉ MedTeam        ⟨⟨  │ Přehled › Mamární komise › P05          [⌕ Hledat pacienta… Ctrl K]  ◐  (P)│
│                      ├────────────────────────────────────────────────────────────────────┤
│ ▣ Přehled            │                                                                    │
│ ▤ Zasedání           │                         obsah stránky                              │
│ ☑ Úkoly           3  │                                                                    │
│                      │                                                                    │
│ Nejbližší zasedání   │                                                                    │
│ St 21. 10.           │                                                                    │
│  14:00 GIT        1  │                                                                    │
│  14:00 Hrudní     1  │                                                                    │
│  14:00 Mamární    3  │                                                                    │
│                      │                                                                    │
│                      │                                                                    │
│                      │                                                                    │
│ ⎚ Okno pro projektor │                                                                    │
└──────────────────────┴────────────────────────────────────────────────────────────────────┘
```

### 5.1 Sidebar

Postavený na komponentě `Sidebar` ze shadcn (`collapsible="icon"`, Ctrl+B, stav v cookie).

- **Hlavička:** logo MedTeam (jako login a admin okno).
- **Navigace:** Přehled · Zasedání · Úkoly. U Úkolů je počet otevřených úkolů po termínu (`GET /api/mdt/tasks/?status=requested`, filtr termínu na klientu).
- **„Nejbližší zasedání“:** 5 nadcházejících boardů seskupených podle dne, s časem, zkráceným názvem a počtem pacientů. Aktivní board je zvýrazněný. Proklik vede do Jednání. Tohle je hlavní přidaná funkce: předseda se dostane k zasedání jedním klikem z jakékoli obrazovky.
- **Patička:** akce „Okno pro projektor“ otevře `/projector` (T-512).
- **Pryč:** „Dev služby“ (Swagger, Django Admin, Mailhog, Traefik). Odkazy na ně patří do README a `dev.ps1`, ne do aplikace pro lékaře. Pryč je i uživatelský blok v patičce, menu je jen jedno (vpravo nahoře).
- **Úzký režim:** ikony s tooltipem. Seznam zasedání se schová a místo něj je ikona kalendáře s počtem dnešních boardů.
- **Mobil:** sidebar jako `Sheet` z levé strany.

### 5.2 Horní lišta a uživatelské menu

- **Vlevo** drobečková navigace (Přehled › board › pacient). Vždy je jasné, kde jsem a kam se vrátit.
- **Uprostřed** vyhledávání `Ctrl K` (`Command` ze shadcn místo dnešní `command-palette.tsx`):
  - pacienti (ID, diagnóza, board);
  - zasedání;
  - akce: „Přesunout P03 na…“, „Otevřít okno projektoru“, „Tmavý režim“.
- **Vpravo** přepínač tmavého režimu (týmový název „Projektor“, teď jako ikona s tooltipem) a **avatar s iniciálou**. Ten je tlačítko (`DropdownMenu` ze shadcn) a menu obsahuje:
  - jméno, roli a odbornost (`meLabel`), např. „Předseda komise · klinický onkolog“;
  - Nastavení (`/dashboard/settings`);
  - Klávesové zkratky (dialog se seznamem, §7.3);
  - oddělovač, pak **Odhlásit se**.
- **Pryč:** tlačítko „Swagger UI“.

---

## 6. Přehled = kalendář zasedání

Komise zasedají podle odborností jednou týdně a v jednom dni jich bývá víc. V datech je 21. 10. ve 14:00 GIT, Hrudní i Mamární komise najednou. Mřížka má proto **sloupce = pracovní dny** a **v buňce dne pod sebou dlaždice zasedání**. Každá dlaždice je jedno „políčko“ ze zadání.

### 6.1 Mřížka

```
Zasedání                          ‹  Týden 43 · 19.–23. 10. 2026  ›   Dnes   [Komise ▾]  [+ Nový board]
┌──────────────┬──────────────┬──────────────────────────────┬──────────────┬──────────────┐
│ Po 19. 10.   │ Út 20. 10.   │ St 21. 10.                   │ Čt 22. 10.   │ Pá 23. 10.   │
├──────────────┼──────────────┼──────────────────────────────┼──────────────┼──────────────┤
│              │              │┌────────────────────────────┐│              │              │
│              │              ││ GIT – kolorektální       + ││              │              │
│              │              ││ 14:00 · 1 pacient          ││              │              │
│              │              ││ ⋮ P03 M 67  C18.7          ││              │              │
│              │              │└────────────────────────────┘│              │              │
│              │              │                              │              │              │
│              │              │┌────────────────────────────┐│              │              │
│              │              ││ Hrudní – plíce           + ││              │              │
│              │              ││ 14:00 · 1 pacient          ││              │              │
│              │              ││ ⋮ P04 M 70  C34.1          ││              │              │
│              │              │└────────────────────────────┘│              │              │
│              │              │                              │              │              │
│              │              │┌────────────────────────────┐│              │              │
│              │              ││ Mamární komise           + ││              │              │
│              │              ││ 14:00 · 3 pacienti         ││              │              │
│              │              ││ ⋮ P01 Ž 63  C50.4   ◔ 75 % ││              │              │
│              │              ││ ⋮ P05 Ž 68  C50.4   ◔ 81 % ││              │              │
│              │              ││ ⋮ P06 Ž 76  C50.4   ◔ 85 % ││              │              │
│              │              │└────────────────────────────┘│              │              │
└──────────────┴──────────────┴──────────────────────────────┴──────────────┴──────────────┘
```

- **Rozsah:**
  - výchozí jsou **2 týdny** (aktuální a příští), protože nominace se připravují s předstihem;
  - navigace ‹ › a „Dnes“, týden v URL (`?tyden=2026-W43`);
  - víkend se zobrazí, jen když na něj připadá zasedání;
  - minulé dny jsou ztlumené a jejich boardy jen ke čtení.
- **Filtr komise** (multi-select podle názvu, později podle sady guidelines) pro nemocnice s mnoha komisemi.
- **Dnešní sloupec** má tyrkysový nadpis dne, nic víc.
- **Prázdný den** zobrazí jen jemný text „Bez zasedání“. Předseda na něj může kliknout a založit board s předvyplněným datem (`BoardDialog`).

### 6.2 Dlaždice zasedání a čip pacienta

**Dlaždice** (12 px zaoblení, `--card`, 1px okraj):

- **Řádek 1:** název komise (max. 2 řádky, zkrácení s tooltipem) a **„+“ v pravém horním rohu**. „+“ je ikonové tlačítko s `aria-label="Zařadit pacienta na …"` a vidí ho předseda a lékař (`can.generateBrief`).
- **Řádek 2:** čas (`tabular-nums`), počet pacientů a stav. Stav je text a tečka jen u „probíhá“ a „uzavřeno“, „plánováno“ je výchozí a nezobrazuje se.
- **Tělo:** seznam čipů pacientů v pořadí agendy. Víc než 6 pacientů → 5 čipů a odkaz „+ 3 další“ do Jednání.
- **Klik na název** otevře Jednání komise (§7).
- **Uzavřený board:** ztlumený, bez „+“ a nepřijímá přetažení.

**Čip pacienta** (řádek 36 px, bez rámečku, oddělený mezerou):

```
⋮⋮ P05 · Ž · 68    C50.4          ◔ 81 %
```

- `⋮⋮` je úchyt viditelný při najetí myší (celý čip je tažitelný myší, úchyt je vodítko pro oko).
- `P05 · Ž · 68` je zkrácená hlavička (D-018: bez jména a RČ).
- `C50.4` je MKN-10 hlavní diagnózy (`translate="no"`).
- `◔ 81 %` je připravenost (T-303, `ReadinessBadge` zmenšený na ikonu a číslo). Pod 70 % oranžově s ikonou `CircleAlert`.
- Případ, který potřebuje doplnění (`returned`), má ikonu `Undo2` a text v tooltipu.
- Kontextové menu (pravé tlačítko nebo tlačítko `⋯` při najetí):
  - Rychlý přehled;
  - Otevřít detail;
  - **Přesunout na… ▸** (seznam otevřených boardů);
  - Okno pro projektor.

### 6.3 Přesun pacienta (drag & drop)

Knihovna `@dnd-kit/core` + `@dnd-kit/sortable` (§11).

- **Kdo smí:** předseda kterýkoli případ, zadávající lékař jen svůj (`can.editCase`, odpovídá `_require_case_edit` v backendu). Ostatním se čip nedá chytit (kurzor `default`) a menu „Přesunout“ chybí.
- **Kam:** jen otevřené boardy (`planned`, `in_progress`) mimo výchozí. Při tažení:
  - **povolené** dlaždice dostanou tyrkysový okraj a text „Přesunout sem“;
  - **nepovolené** (uzavřené, minulé) jsou ztlumené s ikonou zákazu;
  - zdrojová pozice drží zástupný řádek, aby se mřížka nehýbala.
- **Klávesnice (povinné, web-design-guidelines):**
  1. Tab na čip.
  2. **Mezerník** = zvednout.
  3. **← →** = den, **↑ ↓** = board v dni.
  4. **Mezerník** = položit, **Esc** = zrušit.
- **Čtečky:** dnd-kit `announcements` česky, např. „P05 zvednut z Mamární komise 21. 10.“, „nad GIT – kolorektální, úterý 21. 10.“, „P05 přesunut na GIT – kolorektální“.
- **Dotyk:** aktivace po podržení 250 ms (`TouchSensor`). Na šířce pod 1024 px se drag vypíná a zůstává „Přesunout na…“ v menu.
- **Po puštění:**
  1. Čip se okamžitě přesune (optimistická aktualizace, layout animace 180 ms).
  2. Odejde `PATCH /api/mdt/cases/{id}/ { session }`.
  3. Toast (sonner): „P05 přesunut na GIT – kolorektální · st 21. 10. 14:00“ s akcí **Vrátit** (8 s). Vrácení je stejný PATCH zpět.
  4. **Chyba:** čip se vrátí na původní místo a toast ukáže důvod česky („Board je uzavřený“, „Tento případ může přesunout jen předseda nebo zadávající lékař“, „Server neodpovídá, zkuste to znovu“).
- **Dopad do IRIS:** přesun mezi daty přepíše termín v `Task.restriction.period.start` (T-501). Je vratný, proto bez potvrzovacího dialogu a s „Vrátit“ (impeccable: modal není první volba).

### 6.4 Rychlý přehled v bočním panelu

Klik na čip otevře **`Sheet` vpravo (440 px)** s komponentou **`CaseQuickView`**, tedy obsahem `ProjectorPanel` z T-512:

- hlavička `P05 · žena · 68 let`, PS lékař / pacient, C/P;
- anamnéza (AI, citace);
- klíčové údaje podle diagnózy s kolečky normality;
- všechny léčebné postupy se semaforem;
- dole otázka pro MDT a MKN-10.

Patička panelu: **Otevřít detail** (primární) · Otevřít jednání · Okno pro projektor. Panel je v URL (`?pacient=12`): odkaz jde poslat kolegovi a Zpět panel zavře. Kalendář pod panelem zůstává, takže kontext se neztrácí.

### 6.5 Zařazení pacienta z kalendáře

„+“ na dlaždici otevře `Sheet` **„Zařadit pacienta – Mamární komise, st 21. 10.“**:

1. **Výběr pacienta:** vyhledávací seznam z `GET /api/patients/` (ID, věk, pohlaví, diagnóza, otázka z nominace). Pacient, který už na boardu je, je označený a nedá se vybrat znovu.
2. **Formulář:** stávající `IntakeForm` (předvyplnění z IRIS, Doplnit / Přeskočit, varování „Beru na vědomí“, ECOG + C/P, checkbox snímku). Otázku pro MDT nejde přeskočit (OBC-1.1).
3. **Hotovo:** panel se zavře, čip se objeví v dlaždici a toast „P02 zařazen na Mamární komisi“.

Stránka `/dashboard/mdt/[id]/add` zůstává pro přímé odkazy a pro mobil.

### 6.6 Úzké obrazovky

Pod 1024 px se mřížka mění na **seznam po dnech** (nadpis dne → dlaždice pod sebou → čipy). Drag & drop je vypnutý, přesun jde přes menu. Kalendář nikdy nevytvoří vodorovné rolování stránky (FR-U2).

---

## 7. Jednání komise

`/dashboard/mdt/[id]`. Komise má 2–5 minut na pacienta. Obrazovka proto odpovídá na tři otázky, a to v tomto pořadí: **kdo je teď na řadě, o čem rozhodujeme a co tomu brání.**

```
┌ Mamární komise · st 21. 10. 14:00 ────────────────────────────────────────────────────────────────────────┐
│ ← Přehled             1 / 3 projednáno · 09:41               ⎚ Projektor   ⚙ Podklad   ✎ Board   [+ Zařadit] │
├────────────────────────────┬──────────────────────────────────────────────────────────────────────────────┤
│ 1  P01 · Ž · 63     ✓      │ P05 · žena · 68 let                                     PS 1 · pac. 1 │ C/P │
│    C50.4 · ◔ 75 %   04:12  │ C50.4 · HR+/HER2-low · M1 (játra, skelet, uzliny)       ⚠ 8 varování   │  P  │
│ 2  P05 · Ž · 68     ▶ 03:05│ ◀ Předchozí [↑]            [Otevřít detail D]   [Závěr Z]          Další ▶ [↓] │
│    C50.4 · ◔ 81 %          ├─────────────────────────────────────┬────────────────────────────────────────┤
│ 3  P06 · Ž · 76            │ Klíčové údaje                       │ Léčebné postupy (11)                   │
│    C50.4 · ◔ 85 %          │ ⬣ Třezalka × PARPi  interakce       │ PARP inhibitor (RKT-06)       ! pozor  │
│                            │ ⬣ Hb  92 g/l, opakovaně < 80        │   Hb 92 g/l, zbývá dávka 200 mg  [4]   │
│                            │ ⓘ gBRCA  nevyšetřeno                │ Endokrinní léčba ± CDK4/6     ! pozor  │
│                            │ ⓘ ESR1  chybí (NGS)                 │   interakce s třezalkou          [6]   │
│                            │ ⓘ Zobrazení  83 dní (limit 42)      │ Chemoterapie                  ! pozor  │
│                            │ ⊙ ER 100 % · PR 10 % · HER2 1+      │   zobrazení 83 dní          OBC-1.2    │
│                            │ ✓ laboratoř v normě (n)  ▸          │ Zoledronát / denosumab        ✓        │
│                            │ Anamnéza (AI)  ▸                    │ T-DXd                         ? nelze  │
│                            │                                     │ … (výřez: dalších 6× „nelze posoudit“) │
│                            ├─────────────────────────────────────┴────────────────────────────────────────┤
│                            │ Pokračovat ve studijní léčbě ve 2. redukci dávky, nebo léčbu změnit? …   C50.4 │
└────────────────────────────┴──────────────────────────────────────────────────────────────────────────────┘
```

### 7.1 Rozvržení

- **Levý pruh agendy** (280 px, `react-resizable-panels` 240–360 px):
  - řádky v pořadí agendy: číslo, `P05 · Ž · 68`, MKN, připravenost a stav;
  - **projednáno** = `CircleCheck` + ztlumení, **právě na řadě** = výběr a ikona `Play`;
  - čas strávený u pacienta (`tabular-nums`), viz 7.4;
  - dole souhrn „2 / 3 projednáno · 09:41 celkem“.
- **Hlavní plocha = `CaseQuickView` v širokém rozvržení**, tedy obsah panelu projektoru ve dvou sloupcích:
  - **hlavička** přes celou šířku: identita, diagnóza + TNM, PS lékař / pacient (rozdíl ≥ 1 oranžově, OBC-1.3), C/P a počet varování;
  - **vlevo** klíčové údaje podle diagnózy (abnormální a chybějící nahoře, normální laboratoř sbalená pod „laboratoř (6) ▸“) a pod tím sbalená anamnéza (AI);
  - **vpravo** všechny léčebné postupy se semaforem a rozhodujícím pravidlem (bez „doporučujeme“). Pořadí je z katalogu (backend), ne podle barvy, aby řazení nepůsobilo jako doporučení. Postupy „nelze posoudit“ zůstávají na svém místě jako kompaktní jednořádkové řádky a jsou **vždy viditelné** (AGENTS.md: zobrazit všechny možnosti). U P05 je to 7 z 11;
  - **dole přilepený pás:** otázka pro MDT velkým tučným písmem a MKN-10. Je to kotva celé diskuse, proto je vidět pořád.
- **Akční lišta pod hlavičkou:** Předchozí · **Otevřít detail** · Závěr komise · Další. Lišta obsahuje jen akce pro pacienta, akce boardu jsou v hlavičce stránky.
- **Okno projektoru:** výběr pacienta se rovnou publikuje do `/projector` (BroadcastChannel z T-512). Kdo vede jednání, ovládá plátno z vlastního notebooku.

### 7.2 Proklik do detailu

„Otevřít detail“ (nebo `D`) otevře `/dashboard/cases/[id]` ve stejné záložce s návratem „← Jednání“. Kdo chce mít oboje, použije `Ctrl` + klik. Detail na stejném místě nabízí „Zpět k jednání“ a šipky Předchozí / Další, takže jde projet celou agendu i v detailu.

### 7.3 Klávesové zkratky

Platí v Jednání. Vypsané jsou v dialogu „Klávesové zkratky“ v uživatelském menu (`?`).

| Klávesa | Akce |
|---|---|
| `↓` / `J` | další pacient |
| `↑` / `K` | předchozí pacient |
| `D` | otevřít detail |
| `Z` | závěr komise |
| `P` | otevřít nebo zaostřit okno projektoru |
| `H` | označit jako projednané (předseda, `PATCH status: in_discussion → decided`) |
| `Ctrl K` | vyhledávání a akce |
| `?` | nápověda ke zkratkám |

### 7.4 Čas na pacienta

U pacienta na řadě běží čas (začne s výběrem). Po 5 minutách číslo zoranžoví, nic nepípá ani nebliká. Slouží předsedovi k řízení jednání, ne k hodnocení. Čas je jen v paměti prohlížeče (`sessionStorage`), neukládá se do IRIS. Jestli ho chceme, je otevřená otázka Q4.

### 7.5 Stavy

| Stav | Co uvidí lékař |
|---|---|
| Podklad ještě nevznikl | rychlý přehled z intake a laboratoře (nepotřebuje AI) + tlačítko „Vytvořit podklad“ (předseda a lékař, `JobProgress`) |
| Chybí data | kolečka „chybí“ (`CircleDashed`) s pravidlem, které údaj vyžaduje (`required_by`) |
| Případ vrácen k doplnění | pruh nad hlavičkou „Vráceno k doplnění: …“ s odkazem na formulář |
| Prázdná agenda | prázdný stav s „+ Zařadit pacienta“ (předseda a lékař) |
| Úzká obrazovka | agenda jako výběr nahoře, přehled na celou šířku, stejné zkratky |

---

## 8. Detail pacienta

`/dashboard/cases/[id]`. Cíl: **první obrazovka odpoví za 30 s** (je to rychlý přehled) a vše ostatní je o krok dál a sbalené.

```
┌ ← Jednání · Mamární komise ───────────────────────────────────────────────────────────────────────────────┐
│ P05 · žena · 68 let   C50.4 · HR+/HER2-low · M1   PS 1 · pac. 1   P   ⚠ 8   ◀ ▶   [⎚ Projektor] [Závěr]    │
├────────────────┬──────────────────────────────────────────────────────────────────────────────────────────┤
│ Rychlý přehled │ Rychlý přehled                                                                           │
│ Varování     8 │   (CaseQuickView, široké rozvržení jako v Jednání)                                       │
│ Souhrn a osa   │                                                                                          │
│ Anamnéza       │ Varovné signály (8)   [vše · vysoká 2 · střední 6]                                       │
│ Odbornosti     │   ⬣ vysoká   Léková interakce: třezalka × studijní PARPi   [5] P05-doc03#4 · RF-MED  ▸   │
│  Onkolog       │   ⬣ vysoká   Opakovaně Hb < 80 g/l (naposledy 92)          [2] [3] · RF-LAB          ▸   │
│  Radiolog      │   ⓘ střední  Zobrazení starší než 6 týdnů (83 dní)        [7] · OBC-1.2             ▸   │
│  Patolog       │   ⓘ střední  Chybí výsledek: ESR1 (tkáň, NGS)              PRS-1.3                   ▸   │
│ Léčba a studie │   … 4 další                                                                              │
│ Hlas pacienta  │                                                                                          │
│ Otázky         │ Souhrn a časová osa   [AI shrnutí | Události z IRIS]                                     │
└────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Přilepená hlavička** (kompaktní `CaseHeader`, jeden řádek):
  - identita, diagnóza + TNM, PS lékař / pacient, C/P, počet varování;
  - šipky na předchozího a dalšího pacienta boardu, Okno pro projektor, Závěr komise.
- **Navigace po sekcích** vlevo (xl ≥ 1280 px). Zvýrazňuje sekci, ve které právě jsem, a ukazuje počty. Pod 1280 px jsou to vodorovné záložky pod hlavičkou (dnešní řada odkazů zůstane, jen přilepená).
- **Pořadí a výchozí stav sekcí:**
  1. **Rychlý přehled:** otevřený, stejná komponenta jako v Jednání.
  2. **Varovné signály:** otevřené, **kompaktní seznam**. Řádek = závažnost (ikona + text), název, citace faktu, pasáž pravidla. Rozbalení ukáže popis a „Porovnat oba zdroje vedle sebe“. Filtr podle závažnosti. Odkliknutá varování zůstávají ztlumená s „Bere na vědomí: MUDr. …“ (D-019).
  3. **Souhrn a časová osa:** sbalené. **Jedna** osa s přepínačem „AI shrnutí / Události z IRIS“ místo dnešních dvou pod sebou.
  4. **Anamnéza:** sbalená. AI blok s citacemi, přepínač doslovně / shrnutí (T-507).
  5. **Odbornosti:** sbalené. Každá role jako řádek se štítkem odbornosti, rozbalení ukáže posouzení, údaje podle diagnózy a trendy (`TrendChart`).
  6. **Léčba a studie:** sbalené. Tabulka „postup · semafor · rozhodující pravidlo · kdo se vyjadřuje“ + screening studií po kritériích.
  7. **Hlas pacienta, Otázky k diskusi:** sbalené.
- **Zdroj citace** se otevírá v `Sheet` vpravo (dnešní `SourceDrawer` na shadcn). Obsah stránky se neposouvá.
- **Výsledek:** výchozí výška stránky ≤ 3 obrazovky místo 16. Celý obsah zůstává dostupný a nic se neskrývá natrvalo (D-019).

---

## 9. Komponenty

| Komponenta | Nová / změna | Základ | Kde |
|---|---|---|---|
| `AppSidebar` | nová (nahradí sidebar v `DashboardLayout`) | shadcn `sidebar` | `components/layout/` |
| `UserMenu` | nová | shadcn `dropdown-menu` + `avatar` | horní lišta |
| `CommandMenu` | náhrada `ui/command-palette.tsx` | shadcn `command` (cmdk) | horní lišta |
| `Breadcrumbs` | nová | shadcn `breadcrumb` | horní lišta |
| `WeekCalendar` | nová | CSS grid + `date-fns` | `/dashboard` |
| `SessionTile` | nová (nahradí `SessionCard`) | droppable (`@dnd-kit/core`) | kalendář |
| `PatientChip` | nová | draggable + shadcn `context-menu` / `dropdown-menu` | kalendář |
| `CaseQuickView` | z `ProjectorPanel` (T-512) | `key-facts.ts`, `CompatibilityLight` | panel, Jednání, detail, `/projector` |
| `QuickViewSheet` | nová | shadcn `sheet` | kalendář |
| `AddPatientSheet` | nová | shadcn `sheet` + stávající `IntakeForm` | kalendář |
| `MeetingRail` | nová (nahradí `AgendaItem`) | `react-resizable-panels` přes shadcn `resizable` | Jednání |
| `MeetingToolbar` | nová | shadcn `button`, `kbd` | Jednání |
| `CaseHeaderCompact` | změna `CaseHeader` | | detail |
| `SectionNav` | nová | `IntersectionObserver` | detail |
| `RedFlagList` | změna (nahradí `RedFlagCard` v seznamu) | shadcn `collapsible` | detail |
| `TreatmentTable` | změna `TreatmentOptions` | | detail |
| `StatusIcon` | nová, sdílená | lucide (sada tvarů z `key-facts`) | všude |
| `Toaster` | nová | shadcn `sonner` | root layout |

**Odchází:** `SessionCard` s ikonovou dlaždicí, velká karta `AgendaItem`, banner „Ukázkový 30s podklad“ (demo P03 zůstává dostupné přes `/dashboard/cases/demo` a vyhledávání), „Dev služby“, vlastní `ui/dropdown.tsx` a `ui/dialog.tsx` (nahradí je shadcn s fokusem a `role="dialog"`).

---

## 10. Data a API

### 10.1 Co už existuje

| Potřeba | Endpoint | Poznámka |
|---|---|---|
| zasedání | `GET /api/mdt/sessions/` | vrací u pacientů jen ID (`patients: ["P03"]`) |
| agenda boardu | `GET /api/mdt/sessions/{id}/` | `cases[]` s hlavičkou pacienta z IRIS |
| přesun pacienta | `PATCH /api/mdt/cases/{id}/ { session }` | práva: předseda / zadávající lékař; zapisuje termín do IRIS |
| stav případu | `PATCH /api/mdt/cases/{id}/ { status }` | jen předseda |
| rychlý přehled | `getIntake(pid)`, `getObservations(pid)`, `getCompatibility(cid)`, `getBrief(cid)` | všechny souběžně (T-512) |
| připravenost | `GET /api/mdt/cases/{id}/readiness/` | jeden dotaz na případ |
| pacienti k zařazení | `GET /api/patients/` | |

### 10.2 Návrh změn API (API lane, @Seb)

**⚠️ KONTRAKT:** změna patří nejdřív do ARCH §6.3 a §8 (AGENTS.md).

1. **`GET /api/mdt/sessions/?from=2026-10-20&to=2026-11-02&expand=cases`** vrátí zasedání v rozsahu s `cases: MdtCaseSummary[]`:
   ```ts
   interface MdtCaseSummary {
     id: number; order: number; status: MdtCase['status'];
     patient_id: string; display_name: string; diagnosis: { icd10: string; text: string } | null;
     ecog: number | null; intent: 'C' | 'P' | null;
     readiness: number | null;   // skóre 0–1 z T-303, null = nespočteno
   }
   ```
   Bez rozšíření musí kalendář udělat jeden dotaz na každé zasedání a jeden na každou připravenost. Při 4 boardech je to snesitelné (záložní řešení pro první verzi), při desítkách ne.
2. **Kontrola cílového boardu při přesunu:** `PATCH … { session }` na `closed` board vrátí **409** s českou zprávou. Dnes ho backend přijme.
3. **(Volitelně) pořadí v agendě:** `order` zapisovatelné, aby šlo přetahovat i uvnitř boardu. Dnes je `order` jen pro čtení.

### 10.3 Datová vrstva na klientu

Vychází ze skillu `vercel-react-best-practices`: žádné řetězení dotazů, sdílená cache a optimistické změny.

- **TanStack Query** místo `useApiData`, postupně:
  - **klíče:** `['sessions', from, to]`, `['session', id]`, `['case', id, 'brief' | 'compatibility']`, `['patient', pid, 'intake' | 'observations']`;
  - **jedna cache:** sidebar („Nejbližší zasedání“), kalendář i Jednání čtou stejná data, takže se nic nenačítá dvakrát;
  - **`useMoveCase`:** `onMutate` udělá snímek a přesune čip, `onError` vrátí stav a zobrazí toast, `onSettled` invaliduje `sessions` a oba dotčené boardy;
  - **čerstvost:** `staleTime` 30 s a `refetchOnWindowFocus`. Na stejné boardy se dívá víc lékařů najednou.
- **Předběžné načtení:** najetí myší na čip načte rychlý přehled dopředu (`queryClient.prefetchQuery`, pravidlo `bundle-preload`), takže panel se otevře bez čekání.
- **URL stav:** `nuqs` (`?tyden=`, `?pacient=`), adaptér `NuqsAdapter` pro App Router v `app/dashboard/layout.tsx`.
- **Rozdělení kódu:** drag & drop a kalendář přes `next/dynamic` jen na `/dashboard` (pravidlo `bundle-dynamic-imports`).

---

## 11. Knihovny

Verze ověřené v npm registru 17. 10. 2026. Všechny podporují React 19.

| Balíček | Verze | K čemu | Proč tento |
|---|---|---|---|
| `shadcn` (CLI) + `@base-ui/react` | 4.22.0 / 1.9.0 | primitiva: `sidebar`, `dropdown-menu`, `sheet`, `command`, `tooltip`, `hover-card`, `resizable`, `sonner`, `kbd`, `empty`, `item`, `breadcrumb`, `collapsible`, `context-menu` | zdrojový kód zůstává v repu; tokeny už máme se stejnými názvy; přístupnost (fokus, ARIA, klávesnice) zdarma; v4 má Base UI jako výchozí základ (Radix jako varianta, Q2) |
| `@dnd-kit/core` + `@dnd-kit/utilities` | 6.3.1 / 3.2.2 | přesun pacientů mezi zasedáními | zralé API, senzory pro klávesnici a dotyk, oznámení pro čtečky; `sortable` zatím není potřeba (Q6); nový `@dnd-kit/react` 0.5.1 je zatím před 1.0 |
| `@tanstack/react-query` | 5.104.3 | serverová data, cache, optimistické přesuny s návratem | odstraní duplicitní dotazy mezi sidebarem, kalendářem a Jednáním |
| `nuqs` | 2.10.2 | stav v URL (týden, pacient) | typované parametry, adaptér pro Next App Router, funguje Zpět a sdílení odkazu |
| `sonner` | 2.0.8 | toasty s akcí „Vrátit“ | shadcn ho používá; přístupné `aria-live` |
| `date-fns` + `date-fns/locale/cs` | 4.4.0 | týdny (ISO), dny v mřížce, české názvy dnů | výpočty dat; formát pro zobrazení dál přes `Intl` |
| `react-resizable-panels` | 4.14.5 | šířka pruhu agendy v Jednání | základ shadcn `resizable`; klávesnicí ovladatelné |
| `motion` | 13.5.1 | layout animace přesunu čipu („Přesunout na…“, „Vrátit“) | `LazyMotion` + `domMax` jen na kalendáři, `MotionConfig reducedMotion="user"`; 14.3.0 vyšla 15. 10., proto starší stabilní verze |
| `react-hotkeys-hook` | 5.3.3 | zkratky v Jednání (↑↓ J K D Z P H) | `ignoreEventWhen` vypne zkratky, když je otevřené menu, dialog nebo zdroj citace |

**Zvažováno a zamítnuto:**

- **FullCalendar, react-big-calendar:** časová osa po hodinách, těžké a nehodí se pro dlaždice zasedání s pacienty.
- **`vaul`:** poslední vydání 2024.
- **Tremor:** poslední vydání 2025.
- **Magic UI:** efekty pro marketing.
- **`@tanstack/react-virtual`:** desítky položek virtualizaci nepotřebují.
- **SWR:** TanStack Query umí optimistické mutace s rollbackem lépe.

**Zavedení shadcn (rozhoduje UI lane @Mira):**

1. `npx shadcn@latest init --base base` ve `WEB_Template/frontend`.
2. Tokeny v `globals.css` sloučit ručně: názvy už sedí, hodnoty zůstávají naše.
3. Komponenty, které už existují pod stejným jménem (`button`, `card`, `dialog`, `input`, `tabs`, `badge`, `avatar`, `skeleton`), přidávat **jen s `--dry-run` a `--diff`** a přepisovat po jedné. Nové (`sidebar`, `sheet`, `dropdown-menu`…) přidat rovnou.
4. Skill `shadcn` je v `.claude/skills/` a jeho blok „V MDT Copilot“ hlídá D-017 a lane.

---

## 12. Přístupnost, projektor, výkon

- **Písmo:** min. 13 px v aplikaci a 15 px v Jednání (hlavní plocha). Otázka pro MDT 18–20 px.
- **Kontrast AA** ve světlém i tmavém režimu, ověřený na projektoru (T-310). Kolečka a semafor mají vždy tvar ikony a text.
- **Klávesnice:** viditelný focus (`focus-visible:ring`) všude. Drag & drop má klávesovou alternativu i alternativu „Přesunout na…“ z menu. Zkratky v Jednání (§7.3).
- **Čtečky:** oznámení přesunu (`aria-live`), dialogy a panely s titulkem (`SheetTitle`, `DialogTitle`), ikonová tlačítka s `aria-label` („Zařadit pacienta na Mamární komisi“).
- **Pohyb:** do 200 ms, `prefers-reduced-motion` vypíná animace přesunu i panelů.
- **Výkon:**
  - **rychlý přehled:** dotazy jdou souběžně a načítají se dopředu při najetí myší;
  - **kód:** kalendář a drag & drop se načítají jen na `/dashboard`;
  - **vykreslování:** dlaždice a čipy memoizované, takže tažení nepřekresluje celou mřížku.
- **Úzké okno (FR-U2):** od 360 px bez vodorovného rolování. Kalendář se mění na seznam, Jednání na výběr + přehled.

---

## 13. Plán implementace

Na pitch (So 13:00) a finále (Ne 14:00). Úkoly jsou návrh. Do PROGRESS §4 se zapíšou po odsouhlasení UI lane.

| ID | Úkol | Lane | Závisí na | DoD |
|---|---|---|---|---|
| T-516 | **Shell:** `app/dashboard/layout.tsx`, `shadcn init` (Base UI), `AppSidebar` s „Nejbližší zasedání“, `UserMenu` (Nastavení, Klávesové zkratky, Odhlásit), drobečky, bez Dev služeb a Swaggeru, `Toaster` | UI | rozhodnutí Q2 | navigace bez přemontování; avatar otevře menu; lint + build |
| T-517 | **Datová vrstva:** TanStack Query provider + hooky (`useSessions`, `useSession`, `useMoveCase` s rollbackem), `NuqsAdapter` | UI | T-516 | sidebar a kalendář sdílí cache; přesun jde vrátit |
| T-518 | **API:** `sessions?from&to&expand=cases` (`MdtCaseSummary` + readiness), 409 při přesunu na uzavřený board | API | — | ⚠️ KONTRAKT v ARCH §6.3/§8; testy |
| T-519 | **Kalendář** na `/dashboard`: `WeekCalendar`, `SessionTile` s „+“, `PatientChip`, drag & drop (myš, klávesnice, dotyk) + „Přesunout na…“, `QuickViewSheet`, `AddPatientSheet`; pryč „Úkoly po termínu“ a banner | UI | T-512 (merge), T-517; T-518 volitelně | P05 jde přetáhnout z Mamární na GIT a zpět přes „Vrátit“; klávesnicí stejně; 390 px bez vodorovného rolování |
| T-520 | **Jednání komise:** `MeetingRail`, `CaseQuickView` široký, zkratky, čas na pacienta, synchronizace s `/projector` | UI | T-512, T-517 | průchod 3 pacienty jen klávesnicí; projektor se přepíná sám |
| T-521 | **Detail pacienta:** přilepená hlavička, `SectionNav`, rychlý přehled nahoře, `RedFlagList`, jedna časová osa, sbalené sekce, zdroj v `Sheet` | UI | T-512 | P02 má výchozí výšku ≤ 3 obrazovky; nic z podkladu nezmizí (D-019) |
| T-522 | **Vizuální jazyk:** typografie (bez 700–900 a verzálek, min. 13 px), bez `font-mono`, AI barva podle Q1, sjednocení tlačítek; audit `impeccable detect` + web-design-guidelines | UI | T-516 | sken: 0× `text-[9–11px]` v klinickém obsahu, 0× `font-mono`, 0× `uppercase` |

**Pořadí do pitche:** T-516 → T-517 → T-519 (záložní data bez T-518) → T-520. T-521 a T-522 do finále.

**Stav (So 17. 10.):** T-516, T-517, T-519, T-520, T-521 a T-522 hotové ve větvi `t-516-ui-v2`; T-518 (API) volné. Ověřeno nad mock API se syntetickými daty (dataset + dev ground truth): přesun myší, klávesnicí a přes menu včetně „Vrátit“, průchod agendou zkratkami, synchronizace projektoru, šířky 390 / 1024 / 1440 px bez vodorovného posouvání, světlý i tmavý režim. Sken: 0× `text-[9–11px]`, `font-mono`, `uppercase` a `font-bold/extrabold` v klinickém UI; `impeccable detect` hlásí jen záměrné pruhy AI / závažnosti (D-017). Detail P03 má výchozí výšku ~3 obrazovky (dřív 16).

---

## 14. Otevřené otázky

| # | Otázka | Rozhodnutí (So 17. 10., UI lane) |
|---|---|---|
| Q1 | Barva AI: dnes tyrkysová jako primární akce, POZADAVKY §3.4 chtějí fialovou | **fialová**, token `--ai` (`#7c3aed`, v tmavém režimu `#a78bfa`) v `AiBlock`, `AiTag`, závěru komise i potvrzení |
| Q2 | shadcn nad Base UI, nebo nad Radix? | **Base UI** (`components/shadcn`, kompozice přes `render`) |
| Q3 | Rozsah kalendáře: 1 týden, 2 týdny, měsíc? | **2 týdny** pod sebou, posun po týdnu, „Dnes“ vrací na aktuální týden |
| Q4 | Čas na pacienta v Jednání: zobrazovat? | **ano**, v pruhu agendy, po 5 min oranžově, jen `sessionStorage`, do IRIS nic |
| Q5 | Značka: MedTeam (login, admin okno) vs. MDT Copilot (sidebar, metadata) | **MedTeam** všude (titulek, manifest, sidebar), „MDT Copilot“ v popisu produktu |
| Q6 | Přetahování i uvnitř boardu (pořadí agendy)? | **později** (chce zapisovatelné `order`, T-518 bod 3) |
| Q7 | Potvrzovat přesun mezi daty (zápis do IRIS)? | **nepotvrzovat**, toast s „Vrátit“ 8 s; přesun na uzavřený nebo minulý board UI nepustí (backend 409 zatím nemá) |
