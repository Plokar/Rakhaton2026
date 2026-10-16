# MDT Copilot — myšlenková mapa projektu

> Přehled celého projektu na jednom místě: zadání z prezentace, poznámky z konzultace se zadavateli, požadavky lékaře z [docs/POZADAVKY_LEKARE.md](docs/POZADAVKY_LEKARE.md), architektura z [ARCHITEKTURA.md](ARCHITEKTURA.md) a stav z [PROGRESS.md](PROGRESS.md). Stav odpovídá pátku 16. 10. večer.
>
> Značky: _(poznámka)_ = zaznělo na konzultaci se zadavateli · ⚠️ **mezera** = v návrhu zatím chybí.

**MDT Copilot** je AI asistent pro onkologické konzilium. Z dat pacienta za pár sekund připraví podklad pro každého člena komise a zapíše rozhodnutí jako oficiální záznam ve FHIR.

**Zlaté pravidlo:** AI připravuje, shrnuje, upozorňuje a navrhuje. Rozhoduje vždy lékař.

## V kostce: vstupy → MDT Copilot → výstupy

Zjednodušený pohled, stejný graf jako záložka „Přehled“ v artefaktu. Čte se shora dolů, výstupy odpovídají blokům A · B · B2 · C ze zadání.

```mermaid
flowchart TB
  subgraph VSTUPY["① VSTUPY"]
    direction LR
    I1["<b>Data pacienta</b><br/>zprávy, krev a markery,<br/>popisy CT/MRI, léky, výkony,<br/>dotazník PROMs 2× v čase"]
    I2["<b>Nominace pacienta</b><br/>kdo ho posílá<br/>a s jakou otázkou,<br/>předchozí MDT"]
    I3["<b>Postupy a studie</b><br/>výtahy z guidelines<br/>s číslovanými pasážemi,<br/>6 klinických studií"]
    I4["<b>Od předsedy</b><br/>sekce, pořadí,<br/>přítomné role, detail;<br/>bonus: přepis diskuse"]
  end

  CP[["<b>② MDT COPILOT</b><br/>spojí data v IRIS → vytáhne podstatné s citací<br/>→ zkontroluje rozpory a chybějící údaje → připraví podklad"]]

  subgraph NAVRH["③ AI NÁVRH PODKLADU · za pár sekund"]
    direction LR
    A["<b>A · Souhrn do 30 s</b><br/>diagnóza, TNM,<br/>ECOG lékař vs. pacient,<br/>otázka komise"]
    B["<b>B · Pohled každé role</b><br/>chirurg: kandidát na operaci?<br/>onkolog, radiolog,<br/>patolog, pacient"]
    B2["<b>B2 · Podpora rozhodování</b><br/>možnosti léčby s citací,<br/>vhodné studie,<br/>otázky k diskusi"]
    RF["<b>Varovné signály</b><br/>rozpory mezi zdroji,<br/>chybějící údaje,<br/>předchozí operace"]
  end

  GATE(["✓ ④ Komise rozhodne, předseda potvrdí"])

  subgraph ZAZNAM["⑤ OFICIÁLNÍ ZÁZNAM · C · Závěr a akční plán"]
    direction LR
    R1["<b>Rozhodnutí</b><br/>co se udělá a proč"]
    R2["<b>Úkoly</b><br/>odpovědný, termín,<br/>opětovné posouzení"]
    R3["<b>Zápis do IRIS</b><br/>FHIR, přítomní,<br/>kdo potvrdil a z čeho"]
    R4["<b>Export</b><br/>PDF a HL7 FHIR"]
  end

  VSTUPY --> CP --> NAVRH --> GATE --> ZAZNAM

  style NAVRH stroke-dasharray: 6 4
  style GATE stroke:#2F7A4E,stroke-width:2px
  style ZAZNAM stroke:#2F7A4E,stroke-width:2px
```

> **Nominace ≠ složení komise.** Nominace je žádanka na projednání *pacienta* (`ServiceRequest`: kdo posílá, otázka typu „lze operovat?“). Kdo sedí u stolu, vybírá předseda v nastavení (FR-R1, `roles_present`) a do výstupu se zapíše jako `CareTeam`. Jestli operovat, ozařovat nebo léčit léky, je **výstup**: Copilot navrhne posouzení každé role a možnosti léčby, komise rozhodne.

## Jak do sebe projekt zapadá

Shora dolů: proč to stavíme, co Copilot připraví (bloky A · B · B2 · C ze zadání), na čem to stojí a podle čeho nás hodnotí. Vstupy a výstupy jsou v grafu výše.

```mermaid
flowchart TB
  P["<b>PROČ</b><br/>3–5 min na pacienta<br/>data roztroušená v dokumentech<br/>volný text v eZdraví, chybí hlas pacienta"]

  subgraph PODKLAD["CO COPILOT PŘIPRAVÍ"]
    direction LR
    A["<b>A · Souhrn</b><br/>orientace do 30 s<br/>diagnóza, TNM, ECOG<br/>otázka komise"]
    B["<b>B · Pohled rolí</b><br/>chirurg, onkolog, radiolog,<br/>patolog, radiační onkolog, pacient<br/>+ posouzení: je kandidát?"]
    B2["<b>B2 · Podpora rozhodování</b><br/>možnosti léčby s citací<br/>vhodné studie<br/>otázky k diskusi"]
    C["<b>C · Závěr</b><br/>rozhodnutí a úkoly<br/>potvrzení předsedou<br/>zápis do FHIR, export"]
    A --> B --> B2 --> C
  end

  subgraph PILIRE["NA ČEM TO STOJÍ"]
    direction LR
    D["<b>Důvěra v AI</b><br/>citace u každého tvrzení<br/>red flags, údaj chybí<br/>rozhoduje člověk"]
    T["<b>Technologie</b><br/>Next.js a Django<br/>IRIS FHIR + Vector Search<br/>Gemini"]
    S["<b>Standardy</b><br/>FHIR R4, mCODE, ECCDM<br/>MKN-10, LOINC, SNOMED CT"]
  end

  H["<b>HODNOCENÍ</b><br/>UX 30 % · AI 20 % · nastavitelnost 20 %<br/>standardy 15 % · proces 15 %<br/>pitch So 13:00"]

  P --> PODKLAD
  PODKLAD -. stojí na .-> PILIRE
  PILIRE ~~~ H
```

---

## Kontext: proč, pro koho, s čím

### Problém

- Na jednoho pacienta zbývá 3–5 minut, rozhodnutí musí padnout v řádu minut _(poznámka)_.
- Data jsou v oddělených dokumentech: zprávy, PACS, předchozí vyšetření. Z nich je potřeba vytáhnout to nejdůležitější _(poznámka)_.
- Nálezy v eZdraví jsou volný text, nic se nesčítá samo.
- Chybí hlas pacienta: dotazník PROMs není s komisí propojený.
- Špatně zvolené pořadí léčby se těžko napravuje.

### Kdo sedí u stolu

Každá role chce vidět něco jiného _(poznámka)_. Složení komise Copilot negeneruje: přítomné role vybere předseda v nastavení a Copilot pro každou z nich připraví pohled a posouzení.

| Role | Co potřebuje vidět |
|---|---|
| Předseda | vybere přítomné role, nastaví podklad, potvrdí závěr |
| Chirurg | lze operovat, rozsah TNM, předchozí operace _(poznámka)_ |
| Klinický onkolog | biomarkery, linie léčby, nežádoucí účinky |
| Radiolog | vývoj nálezů v čase, RECIST 1.1 |
| Patolog | histologie, grade, ICD-O-3 |
| Radiační onkolog | předchozí ozařování, oblasti, dávky |
| Pacient | trend PROMs, symptomy, preference |
| Pneumolog, kardiolog | podle diagnózy: spirometrie a operabilita plic, LVEF při anti-HER2 léčbě |

**Role v aplikaci** (požadavek lékaře, D-014):

- předseda = administrátor: boardy, termíny, nastavení podkladu, potvrzení závěru;
- zadávající lékař: zařadí a přesouvá své pacienty;
- prohlížející: člen komise.

### Vstupní data

Smyšlená data od Asseco, **dataset v1.1 už dorazil a je ve formátu FHIR R4**. Podrobně v [DATASET.md](DATASET.md). *(aktualizováno Pá 16:20)*

- **6 pacientů** (4× prs, 1× kolorektum, 1× plíce), každý jako FHIR Bundle se 142–215 resources.
- eZdraví: zprávy (`DocumentReference`), patologie a zobrazení (`DiagnosticReport`), laboratoř s trendy markerů, ECOG, biomarkery, TNM (`Observation`), léky, výkony.
- PROMs: vlastní dotazník `MDT-PROMS-1` (ne EORTC, kvůli licenci), 2 vyplnění v čase; otázka `samostatnost` = ECOG podle pacienta.
- Nominace pacienta (žádanka na projednání, ne složení komise): `ServiceRequest` s žadatelem, otázkou pro komisi a požadovaným zaměřením MDT + `Task` s datem zasedání. Předchozí MDT jako `Composition` + `CarePlan` + `CareTeam` (kdo tehdy seděl u stolu).
- Guidelines: 4 výtahy (KRC, PRS, PLI, OBC) se 42 číslovanými pasážemi + 6 smyšlených studií (`RKT-01…06`).
- Schválně vložené chyby a mezery ano. **Ground truth zatím ne** (až po odevzdání), máme vlastní hypotézy (DATASET §9).
- Bonus přepis diskuse v datasetu **není**. Nahrajeme vlastní a přepíšeme ho Gemini.
- PACS: dataset má jen textové popisy s rozměry lézí, žádné DICOM. Snímky jsou mimo rozsah _(poznámka)_ ✅ potvrzeno datasetem

### Proces komise

Copilot má pokrýt všechny 3 fáze.

1. **Před:** lékař nominuje pacienta s otázkou (`ServiceRequest`), kontrola úplnosti, agenda, předseda vybere přítomné role.
2. **Během:** přepínání pacientů, prezentační režim na projektor, AI zapisovatel převede přepis na draft závěru.
3. **Po:** úkoly s termíny, kontrola plnění, opětovné posouzení.

### Hodnocení

| Kritérium | Váha |
|---|---|
| Klinická hodnota a UX | 30 % |
| Spolehlivost AI | 20 % |
| Nastavitelnost | 20 % |
| Data a standardy | 15 % |
| Proces a zodpovědná AI | 15 % |
| Bonusy (kvalita, ne počet) | +10 % |

- Finále: 5 minut, jeden pacient, celý cyklus komise živě.
- Výzva InterSystems: 1. místo 1 500 EUR, kombinovatelná s MDT Copilot.

### Plán a stav

- Kód je zatím čistý template (Hackathon OS), MDT moduly neexistují.
- Z 68 úkolů v PROGRESS.md jsou hotové T-007 (dataset) a T-500 (požadavky lékaře), T-008 je škrtnutý. Owneři lanes: Seb (INFRA + API), Maty (DATA), Jarda (AI), Mira (UI + PITCH).
- Práce běží ve sprintech = milnících M0–M4. Pravidla pro víc lidí, strojů a agentů jsou v PROGRESS §1.
- Kritická cesta: `T-002` → `T-003` → `T-006` → `T-101` → `T-105` → `T-106` → `T-108` (T-008 „pacient 0“ nahrazen datasetem, dev pacient je P03).
- Sprinty startují Pá 19:00. Milníky: M0 co nejdřív · M1 Pá 23:00 · M2 So 04:00 · M3 So 09:00 · freeze So 10:00 · odevzdání zatím neřešíme · pitch 13:00.
- Vyřešeno: dataset ✅ (Q1), LLM = Google AI Studio / Gemini ✅ (Q2), backend na VPS ✅ (Q3), dataset smí do gitu ✅ (Q5), start sprintů Pá 19:00 ✅ (Q10), owneři lanes ✅ (Q11).
- Otevřené: zapnout placený tier Gemini (Q9), připomínky onkologů k prahům (Q6), oficiální ground truth (Q8), CRLF na Windows (Q12).

---

## Řešení: co stavíme

### Požadavky lékaře (Pá večer)

Poznámky lékaře, který by aplikaci používal, sladěné se zadáním. Detail je v [docs/POZADAVKY_LEKARE.md](docs/POZADAVKY_LEKARE.md).

- **Role:** předseda (administrátor), zadávající lékař, prohlížející.
- **Boardy = zasedání:** předseda zakládá a mění termíny, lékař přesouvá své pacienty.
- **Zařazení pacienta:**
  - formulář předvyplněný z IRIS, Doplnit / Přeskočit;
  - varování: chybí, mimo normu, rozpor, nejistota AI;
  - ECOG + **C/P** a připomínka „snímek mladší než 3 měsíce“.
- **Hlavička:** `P03 · muž · 67 let` místo RČ, diagnóza + TNM, otázka, velké ECOG lékaře a vedle ECOG pacienta, velké C/P.
- **Úzké okno:** jeden sloupec, sekce odborností s barvou, výchozí obsah nastaví předseda.
- **Semafor u postupů léčby:** soulad se stavem pacienta (např. špatná spirometrie vylučuje odebrání plíce). Počítají ho pravidla, ne AI.
- **Bonusy:** Lung-RADS / Fleischner s kontrolou použitelnosti, vstup přes PDF nebo vložený text.

### Podklad A · B · B2 · C

- **A Souhrn do 30 s:** diagnóza, TNM, ECOG lékař vs. pacient, časová osa, otázka komise _(poznámka)_.
- **B Pohled každé přítomné role**, povinně aspoň 3.
- **B2 Podpora rozhodování:**
  - možnosti léčby z guidelines s citací, AI nevybírá;
  - screening studií: splňuje / nesplňuje / nelze určit;
  - dvě až tři otázky k diskusi.
- **C Závěr:** rozhodnutí, zdůvodnění, úkoly, export PDF a FHIR _(poznámka)_.

### Match pro roli

Je pacient pro tuhle roli kandidát? Nápad z konzultace _(poznámka)_.

- Pro každou roli předběžné posouzení: kandidát / ne / podmíněně / chybí data.
- Chirurg: resekabilita, ECOG, komorbidity, předchozí operace.
- Vyhodnotit po kritériích s citací, stejně jako screening studií.
- Verdikt je jen podklad, potvrzuje ho lékař dané role.
- Návrh postupu operace jde do B2 jako jedna z možností _(poznámka)_.
- ✅ Doplněno: požadavek FR-B7 a typ `RoleAssessment` v kontraktu (ARCHITEKTURA §8.2), verdikt `candidate` / `conditional` / `not_candidate` / `insufficient_data`.

### Kontrola dat a varování

Warning systém _(poznámka)_.

- Red flags: rozpor mezi zdroji, závažnost, citace obou zdrojů.
- Pravidla red flags jsou v ARCHITEKTURA §5.4. Prahy jsou převzaté z guidelines datasetu (OBC-1.2 staging ≤ 6 týdnů, OBC-1.3 rozdíl ECOG ≥ 1…).
- Readiness: checklist OBC-1.1, zastaralý staging, chybějící povinné biomarkery.
- Grounding validátor: sedí citace, čísla, data a vektorová podobnost tvrzení se zdrojem (IRIS).
- „Údaj chybí v podkladech“ místo hádání.
- Varování „už operován“, implantáty, alergie _(poznámka)_ ✅ pravidlo `RF-PRIOR-PROC` + hlavička (FR-A4). Výkony a implantáty jsou v `Procedure`, alergie jen v PROMs a textu (T-312).
- Přiřazení dokumentu ke správnému pacientovi a roli _(poznámka)_ 🟨 pravidlo `RF-IDENTITY` (strana těla, pohlaví, věk, datum), úkol T-312.

### Guidelines a studie

- Výběr guidelines podle MKN-10: C50 → PRS, C18–C20 → KRC, C34 → PLI, OBC vždy.
- Postupy se liší podle diagnózy i země _(poznámka)_ 🟨 `MDT.GuidelineChunk` má sloupce `Source` a `Region`. Dataset obsahuje jen jeden zdroj (výtah inspirovaný ESMO a národními standardy, CZ).
- Kombinované choroby (diabetes + rakovina) mění kritéria studií _(poznámka)_ ✅ komorbidity jsou v datasetu (`Condition` „komorbidita“) a vstupují do screeningu a posouzení rolí. Příklad: P02 DM + dexametazon → OBC-3.1.
- Studie jako `ResearchStudy` + kritéria inclusion / exclusion.
- Kandidát do studie se zapíše jen po potvrzení komisí.

### Důvěra v AI

Čtyři pravidla zadání a jak je plníme:

| Pravidlo | Jak |
|---|---|
| Nastavitelnost | předseda nakliká sekce, pořadí, role, detail, presety |
| Varovné signály | red flags se závažností a citací obou zdrojů |
| Dohledatelnost | každé tvrzení má Evidence ID a zdroj na jeden klik |
| Člověk rozhoduje | AI text má štítek „AI návrh“, potvrzení podepíše lékař |

- Pipeline: ingest → kontext → generace → validace → review → zápis.
- Pseudonymizace před LLM, zpracování v EU, žádné PII v logu.
- Eval proti ground truth dá čísla do pitche.

### Architektura

- Next.js 16 na Vercelu: jen UI, žádné klíče.
- Django 4.2 + DRF na VPS: orchestrace AI, pravidla, FHIR.
- IRIS for Health: FHIR R4 jako nemocniční databáze.
- IRIS Vector Search: RAG vždy s filtrem na pacienta.
- PostgreSQL: jen uživatelé, drafty, presety, logy.
- Generování jako job + polling, cíl pod 20 s.
- LLM, embeddingy i přepis audia: Google AI Studio / Gemini, placený tier (`D-008`) ✅

### Standardy a FHIR

- Vstup: `Patient`, `Condition`, `Observation`, `DiagnosticReport`, `DocumentReference`…
- Zápis do IRIS ve stejném tvaru jako předchozí MDT v datasetu: `Composition`, `CarePlan`, `CareTeam` (přítomní), `Task`, `DetectedIssue`, `Provenance` _(poznámka: výstup ve FHIRu)_.
- Kódy: MKN-10, ICD-O-3, LOINC, SNOMED CT, ATC.
- Bonus: profily mCODE / ECCDM v exportu, `$validate` v IRIS.
- Komorbidity a alergie v datovém modelu ✅ ARCHITEKTURA §4.3: komorbidity = `Condition` „komorbidita“, alergie = PROMs + text (resource `AllergyIntolerance` v datasetu není).

---

## Poznámky z konzultace vs. návrh

| Poznámka z konzultace | Kde je v návrhu | Stav a co doplnit |
|---|---|---|
| Krátká doba, rozhodnutí za 3–5 minut, přehledná appka | §1.1, souhrn do 30 s (FR-A1), `CaseHeader`, UX principy §7.3 | ✅ pokryto |
| Oddělené dokumenty, PACS, předchozí vyšetření → vytáhnout to nejdůležitější | Blok A, `context_builder` §5.1 | 🟨 částečně: PACS jen jako textové popisy (`DiagnosticReport`). V pitchi říct, že obrazová data DICOM jsou mimo rozsah prototypu. |
| Různé role v týmu (chirurg atd.) | Blok B, FR-B1 až B6, `RoleTabs` | ✅ pokryto |
| Operoval / neoperoval, „match“ pacienta pro roli | FR-B7, `RoleAssessment` v §8.2, úkol T-201 | ✅ doplněno *(Pá 16:20)*: kritéria splněno / nesplněno / neznámo s citací + verdikt kandidát / podmíněně / ne / chybí data. Jen podklad. Zapsáno jako `⚠️ KONTRAKT` v Deníku. |
| Přiřazování dokumentace | Ingest se zachovanými ID z datasetu (§4.4), pravidlo `RF-IDENTITY` (§5.4) | 🟨 navrženo, implementace T-312: kontrola strany těla, pohlaví, věku a data. Dataset má každý dokument s `subject` = pacient. Zařazení k roli podle oddělení (`category.text`, např. RDG, PAT-B). |
| Chyby v datech, musíme mít kontrolu | Red flags §5.4 (18 pravidel včetně `RF-DATAQUALITY`), readiness (BON-1), grounding §5.3, hypotézy v DATASET §9 | ✅ navrženo: pravidla mají prahy z guidelines datasetu. Ruční průzkum našel desítky nesrovnalostí pro vývoj a eval. |
| Klinické postupy jiné pro diagnózu a zemi | `MDT.GuidelineChunk` se sloupci `GuidelineSet`, `Source`, `Region`, `IcdPrefixes` (§4.5) | 🟨 dataset má jen jeden zdroj (výtah inspirovaný ESMO a národními standardy). Struktura na více zdrojů a regionů je připravená, v B2 se ukazuje ID pasáže. |
| Návrh řešení pro operaci | B2 `treatment_options` (§5.5) | ✅ pokryto, jako možnost s citací, nikdy „doporučujeme“ |
| Data z klinických studií, kombinované choroby (diabetes + rakovina) | Screening studií FR-D2 (`RKT-01…06`, `MDT.TrialCriterion`), komorbidity v hlavičce (FR-A4) | ✅ komorbidity jsou v datasetu jako `Condition` „komorbidita“ a vstupují do screeningu i posouzení rolí. |
| Warning: defekty, jestli už byl operovaný | Pohled chirurga (FR-B1), pravidlo `RF-PRIOR-PROC`, hlavička `alerts` (FR-A4) | ✅ navrženo, implementace T-312: předchozí výkony a implantáty z `Procedure` (port, stent, operace), alergie z PROMs a textu. `AllergyIntolerance` dataset nemá. |
| Výstup ve FHIRu | Zápis do IRIS (§4.3 výstupy), export document Bundle (FR-C4) | ✅ pokryto |

---

## Co z toho plyne

### Doplnit do ARCHITEKTURA.md

Stav k Pá 16:20:

- ✅ §8: `RoleAssessment` + společný typ `Criterion`, zapsáno jako změna kontraktu.
- ✅ §4.3: komorbidity (`Condition`), alergie (PROMs + text), implantáty a výkony (`Procedure`).
- ✅ §5.4: `RF-IDENTITY`, `RF-PRIOR-PROC`, `RF-DATAQUALITY`.
- ✅ §4.5: `Source` a `Region` u guidelines.
- ✅ Požadavky lékaře: FR-U1, FR-U2, FR-P4, FR-B8, FR-D4, FR-D5, FR-A5, FR-R5, BON-6, BON-7, D-014 až D-020, kontrakty §8.6 *(Pá večer)*.

### Rozjet práci

- ✅ Lanes rozdělené (Seb (INFRA + API), Maty (DATA), Jarda (AI), Mira (UI + PITCH)), sprinty od Pá 19:00. Teď zabrat úkoly M0, zatím jsou všechny volné. Pravidla pro sprinty a paralelní práci jsou v PROGRESS §1.
- ✅ Dataset je k dispozici (Q1), viz [DATASET.md](DATASET.md).
- ✅ LLM = Gemini (Q2). Zbývá zapnout placený tier v Google AI Studio (Q9).
- Zeptat se mentorů na národní postupy a na prahy red flags (Q6). Zatím je bereme z guidelines OBC v datasetu.

---

Zdroje: `WEB_Template/MDT_Copilot_zadani_upravené_2026_v02.pptx` (13 slidů vč. poznámek řečníka), [ARCHITEKTURA.md](ARCHITEKTURA.md), [PROGRESS.md](PROGRESS.md), [AGENTS.md](AGENTS.md), `WEB_Template/` (backend a frontend), poznámky z konzultace se zadavateli.
