# MedTeam · MDT Copilot: filmový scénář

> Dvě videa do prezentace na **Rakathon 2026** (výzva Asseco CE „MDT Copilot“ + cena InterSystems).
> Postup a stav práce: [video_progress_file.md](video_progress_file.md). Projekt Remotion je v této složce (`src/`).

| | Film A · **HOOK** | Film B · **PRŮCHOD** |
|---|---|---|
| Kde | 1. slide, než kdokoli promluví | uprostřed prezentace, místo živého dema |
| Délka | **30 s** (900 snímků @ 30 fps) | **1:30** (2 700 snímků @ 30 fps) |
| Úkol | nastavit energii: problém, zlom, řešení, značka | ukázat aplikaci tak, aby ji řečník mohl živě komentovat |
| Zvuk | trailerová hudba + SFX + volitelný voice-over | tichý podkres (verze i bez hudby), žádný voice-over |
| Kompozice Remotion | `MedTeamHook` | `MedTeamWalkthrough` |

---

## 1. Kontext: proč to celé existuje

- **Rakathon 2026** je „největší AI hackathon proti rakovině na světě“ (Praha, Brno, Ostrava, 16.–18. 10. 2026, FN Motol a Homolka + 2. LF UK).
- **Výzva Asseco CE: MDT Copilot.** Webový AI kopilot pro multidisciplinární onkologickou komisi, který propojí zprávy a dotazníky pacienta, připraví souhrny podle odborností a upozorní na nesrovnalosti. Platí zásady: „Každé tvrzení musí mít dohledatelný zdroj“ a rozhoduje vždy lékař.
- **Cena InterSystems:** nejlepší využití InterSystems (IRIS for Health, HL7 FHIR, interoperabilita).
- **Naše odpověď: MedTeam.** Aplikace čte data jen z IRIS FHIR, ke každému tvrzení AI dává klikací citaci a chybějící údaj hlásí jako „chybí“, nikdy si ho nedomýšlí. Semafor léčby počítají pravidla, ne AI. Potvrzený závěr komise se zapisuje zpět do IRIS (`Composition`, `CarePlan`, `Provenance`).

**Myšlenka obou filmů v jedné větě:** *Komise má pět minut na pacienta, kterého často vidí poprvé. MedTeam z chaosu let zpráv udělá jeden ověřitelný pohled a rozhodnutí nechá lékaři.*

---

## 2. Vizuální jazyk (odvozený z produktu)

Pravidlo skillu video-shotcraft: film nesmí mít vlastní „reklamní kůži“, vizuální jazyk vyrůstá z aplikace. Tokeny jsou převzaté z `WEB_Template/frontend/src/app/globals.css` (tmavý režim = režim projektoru) a z loga.

| Token | Hodnota | Použití ve filmu |
|---|---|---|
| Pozadí | `#0b1118` → hlubší `#05080c` | prostor, ve kterém UI levituje |
| Plocha | `#111a24`, okraj `#263547` | karty dokumentů, panely |
| Primární tyrkys | `#2dd4bf` | EKG linka, světlo, citace, zvýraznění |
| AI fialová | `#a78bfa` | jen u AI textu („AI návrh“), nikdy jinde |
| Semafor | jantar `#fbbf24` · červená `#f87171` · šedá `#94a3b8` · zelená `#34d399` | štítky „pozor / vylučuje / nelze posoudit / nevylučuje“ |
| Logo | kříž `#c8102e`, bublina `#17375e`, vlna a „Team“ `#3fb4c0` | finální značka |
| Písmo | **Inter** (produkt), wordmark **Montserrat 800** (logo) | titulky Inter 700–800 se staženým prokladem |

**Styl pohybu (preset „profesionální důvěra × klidná péče“):** hlavní časování ~24 f, náběhy `bezier(0.16, 1, 0.3, 1)`, bez pružení u textu. Pruží jen dopady (karty, razítko, kříž loga). Kamera je 2.5D bez třesu (pravidlo Q3), s rozmazáním pohybu jen v rychlých přeletech.

**Filmová vrstva:** jemné filmové zrno, vinětace a u hooku letterbox 2,39 : 1, který se při logu otevře do plného obrazu. Světlo je „tyrkysové světlo v temném sále“: UI září, okolí je ve tmě.

**Data ve filmu:** všechna data jsou fiktivní (dataset hackathonu v1.1, pacient **P03**). Ve filmu nejsou žádná jména ani rodná čísla, hlavička je ve tvaru `P03 · muž · 67 let`, stejně jako v aplikaci (D-018).

---

## 3. Zvuk

### 3.1 Hudba

| Film | Skladba | Licence | Úsek |
|---|---|---|---|
| A | **„We Will Get It“**, Eugenio Mininni (Mixkit #598) | Mixkit Stock Music Free License: komerčně zdarma, bez uvedení autora | od **41,92 s**, takže hudební „drop“ v 52,92 s padne přesně na **f330 (11,0 s)** |
| B | **„Vastness“**, Andrew Ev (Mixkit #184), ambient, 78 BPM, stálá energie | Mixkit Free License | od začátku, hlasitost 0,18 (pod živý hlas) |

Naměřené údery skladby 598 po dropu (čas v hooku): **f330** drop · f399 · f423 · f518 · f610 · f704 · f773 · f797 · f892. Na tyto snímky jsou navázané předěly scén.

Obě videa se renderují ve dvou verzích, **s hudbou** a **bez hudby** (SFX zůstávají). Hudbu tak jde vyměnit, například za vlastní skladbu podle promptů v §7.

### 3.2 Zvukové efekty (SFX)

Knihovna skillu video-shotcraft (`assets/audio/sfx`, Mixkit SFX Free License). Slovník trailerového filmu: **whoosh** = pohyb kamery, **impact** = dopad, **riser** = gradace, **sparkle** = světlo, **heartbeat / clock** = napětí. Žádné „herní“ zvuky (pravidlo S1). Konkrétní mapa SFX je v tabulkách scén níže a v kódu (`SFX_A`, `SFX_B`).

### 3.3 Voice-over (jen film A, volitelný)

Hook funguje i bez hlasu, protože všechny věty běží jako titulky. Když dodáš nahrávky, ulož je do `public/audio/vo/` pod názvy z tabulky. Remotion je najde sám a v jejich průběhu hudbu ztlumí (ducking na 55 %).

| Soubor | Kdy (s) | Text (český, klidný hluboký hlas, ne „reklamní“) | Max. délka |
|---|---|---|---|
| `A_01.mp3` | 0,6 | „Pět specialistů. Pět minut. Jeden pacient.“ | 3,0 s |
| `A_02.mp3` | 4,2 | „A za ním roky zpráv, nálezů… a rozporů.“ | 4,5 s |
| `A_03.mp3` | 11,6 | „MedTeam připraví celý případ za pár sekund.“ | 3,0 s |
| `A_04.mp3` | 15,0 | „Každé tvrzení má zdroj. Každý rozpor je na očích.“ | 4,0 s |
| `A_05.mp3` | 20,4 | „Semafor léčby počítají pravidla. Ne AI.“ | 2,8 s |
| `A_06.mp3` | 23,5 | „Rozhoduje vždy lékař.“ | 1,8 s |
| `A_07.mp3` | 26,6 | „MedTeam. Copilot onkologické komise.“ | 2,6 s |

Režijní poznámka k hlasu: mluvit pomalu, s pauzou po každé tečce, a poslední slovo věty nezvedat. Věta A_06 je emoční vrchol, proto ji říct tišeji, ne hlasitěji.

---

## 4. Film A · HOOK „Pět minut“ (30 s)

**Dramaturgie: tři dějství za 30 sekund.**
1. **Tlak** (0–11 s): tep, čas a lavina textu. Divák má pocítit, co komise zažívá.
2. **Zlom a řád** (11–26 s): na hudební drop se chaos stáhne do jednoho světelného bodu a z něj vyroste úzký panel MedTeam. Každá další scéna přidá jeden důkaz důvěry: zdroj, semafor, lékař.
3. **Značka** (26–30 s): logo s pulzující vlnou hlasu, které na plátně zůstane stát, když řečník začne mluvit.

Vizuální motiv, který drží film pohromadě, je **tyrkysová EKG linka** z loga (vlna v bublině). V první scéně je tepem pacienta, ve čtvrté se z ní stane linka, která nakreslí panel, a na konci se vrátí jako vlna v logu.

| # | Snímky (čas) | Scéna | Obraz a pohyb | Titulek | SFX | Recept skillu |
|---|---|---|---|---|---|---|
| A1 | 0–105 (0,0–3,5 s) | **Tep** | Tma a letterbox. Tenká tyrkysová EKG linka se kreslí zleva, na každém kmitu bliká světlo. Tři slova přicházejí po jednom, každé na úder srdce. | „Pět specialistů.“ → „Pět minut.“ → „Jeden pacient.“ | heartbeat f8, f40, f72 | `chart-live-moves` (oscilloscope) + `blur-slide` |
| A2 | 105–300 (3,5–10 s) | **Lavina** | Úryvky skutečných (fiktivních) zpráv P03 letí z hloubky prostorem ke kameře a zrychlují (hloubkový tunel). Vpravo nahoře odpočet `05:00 → 04:54`. V polovině se proti sobě zastaví dva rozpory, které se zvýrazní červeně: „ECOG 0 · lékař“ ↔ „ECOG 1 · pacient“ a „neuropatie G1“ ↔ „padají mi věci z ruky“. | „Roky historie. Volný text.“ → „Rozpory.“ | clock tick každou s, syntetický riser f196→322 (whoosh v 5 s a úder v 7 s odebrány na přání) | `flying-words` (tunel, stopy pohybu) |
| A3 | 300–330 (10–11 s) | **Nádech** | Vše zamrzne, odbarví se a během 18 f se stáhne do jednoho bodu uprostřed. Pak 6 f tmy, v níž zůstane jen tyrkysový bod. | – | reverse whoosh, ticho (hudba sama klesá) | `trailer-grammar` (černý takt ticha) |
| A4 | 330–420 (11–14 s) | **Zážeh** | **DROP.** Bod exploduje do EKG linky, která přejede obraz a za sebou „nakreslí“ úzký panel MedTeam (reálný snímek okna projektoru P03). Panel vystoupá z hloubky a kamera ho obkrouží z boku (rotY 28° → 8°). | „MedTeam připraví celý případ.“ | impact-epic-trailer f330, whoosh-big f336, sparkle f399 | `spotlight-hero-card` (reflektor, světlo, beam) |
| A5 | 420–600 (14–20 s) | **Důkaz** | Kamera najede na panel: hlavička `P03 · muž · 67 let` (f423), pak PS **0** vs **pac. 1** a jantarový puls varování. Citační čip se rozzáří a světelný oblouk ho spojí s plovoucí kartou zdroje `P03-img03 · CT … hrudník nebyl požadován` (f518). | „Každé tvrzení má zdroj.“ → „Každý rozpor na očích.“ | click f423, data-scan f470, light-sweep f518 | `glow-flyline` (flyline-arc) + `scanline-annotate-focus` |
| A6 | 600–700 (20–23,3 s) | **Semafor** | Tři řádky léčebných možností se snesou shora a zapadnou do panelu, každý na úder hudby: Resekce jaterních metastáz → **pozor** · Anti-EGFR (KRAS G12D) → **vylučuje** · Imunoterapie → **nelze posoudit**. | „Semafor počítají pravidla. Ne AI.“ | impact krátký ×3 (f610, f633, f656) | `row-embed` |
| A7 | 700–775 (23,3–25,8 s) | **Lékař** | Detail tlačítka **Potvrdit**: kurzor ho stiskne (f704) a přes obraz dopadne razítko „Potvrzeno · zapsáno do InterSystems IRIS · FHIR R4 · Provenance“. | „Rozhoduje vždy lékař.“ | click-camera + impact f704 („switch“ přesunut ke kříži v A8) | `slam-entrance-moves` (score-slam) |
| A8 | 775–900 (25,8–30 s) | **Značka** | Vše zmizí do tmy. Červený kříž složí dvě ramena (f773), bublina vyskočí (f797) a pět pruhů vlny pulzuje v rytmu, zatímco se maskou odhalí „MedTeam“. Letterbox se otevře. Pod logem běží „MDT Copilot · podklady pro onkologickou komisi“, dole drobně „Rakathon 2026 · Asseco CE × InterSystems IRIS for Health“. Od f820 vše stojí (hold ≥ 1 s, pravidlo R1). | logo | impact-movie-epic (vrchol ~f773), **switch (lock-digital) f781 = dosednutí kříže**, sparkle f797, hudba se do f900 stáhne | `ui-to-brand-morph` + `logo-shrink-wordmark-lockup` |

**Energetická křivka:** nízká (A1) → stoupající (A2) → nula (A3) → **vrchol** (A4) → střední (A5) → rytmická (A6) → emoční (A7) → **vrchol a klid** (A8). Plošné údery na celý obraz jsou jen tři: f330, f704 a f773 (pravidlo R4, max. 3).

---

## 5. Film B · PRŮCHOD v2 „Jeden pacient, jedno jednání“ (1:30)

> v2 podle zpětné vazby (17. 10.): logo se stejnou animací a zvukem jako v hooku, přirozený klik myší, žádné prodlevy,
> skutečné přechody aplikace (menu, boční panel, dialog, posun stránky), **kamera sleduje myš**, zajímavější funkce
> (chat, okno projektoru na míru, otázka nad případem), srozumitelnější projektor, na konci QR kód.

**Princip: jeden souvislý záběr.** Žádné střihy mezi kapitolami. Myš otevírá menu, panely a stránky stejně jako v aplikaci.

**Gramatika kamery (v2.1, zpětná vazba 18. 10.).** Každý okamžik je právě jeden ze tří typů, nikdy jejich mix:
- **navigace:** kamera sleduje myš až do kliknutí;
- **čtení:** kamera stojí na zvýrazněné části 2,5–3,5 s, myš zmizí a reflektor se rozsvítí až po zastavení kamery;
- **akce v dialogu** (oko, přetažení): kamera stojí, hýbe se jen myš.

Pružina kamery je pomalá (ω 0,12), náklon minimální. Na kapitolu připadají nejvýš dvě zvýraznění. Závěr trvá 5,5 s, logo a QR se objeví současně.
Řečník mluví živě, proto video nemá voice-over. Štítek kapitoly vlevo dole mu slouží jako tahák.

Logika příběhu je **den předsedy komise s pacientem P03**:
- **příprava** (01–04): orientace, podklad podle odbornosti, dotaz, okno pro projektor;
- **jednání** (05–07): plátno, zdroj tvrzení, chat;
- **výstup** (08–09): zápis a nemocniční databáze.

Každá scéna odpovídá na jednu otázku lékaře.

| # | Čas | Kapitola | Co chceme říct (selling point) | Jak to ukážeme | Napojení dál | Řečník (~2,5 slova/s) |
|---|---|---|---|---|---|---|
| — | 0:00–0:04 | logo | značka | stejná animace a zvuk jako v hooku: dopad kříže, cvaknutí, bublina, vlna, wordmark | logo se rozplyne do kalendáře | „Ukážu vám jedno jednání komise.“ |
| 01 | 0:04–0:14 | Rychlý přehled za 30 sekund | Lékař, který pacienta vidí poprvé, se zorientuje za 30 s, bez jména a RČ. | kalendář → najetí na P03 → „⋯“ → menu → **Rychlý přehled** → boční panel vyjede, kamera přiblíží PS 0 vs pac. 1 a 13 varování | klik na **Otevřít detail** v panelu | „U pacienta P03 otevřu rychlý přehled: diagnóza, TNM, výkonnostní stav podle lékaře i pacienta a 13 varování. Bez jména a rodného čísla.“ |
| 02 | 0:14–0:24 | Podklad podle odbornosti | Každý specialista má nahoře to, o čem rozhoduje on (souhrn podle odborností ze zadání). | navigace sekcí **Pro vás** → plynulý posun → co je doložené, co je jen zmínka (MMR) a co chybí (DPD) → postupy s odkazem na guidelines | posun dolů k dotazu | „Onkolog vidí údaje pro své rozhodnutí: doložené, jen zmíněné a chybějící. A postupy, ke kterým se vyjadřuje, s odkazem na guidelines.“ |
| 03 | 0:24–0:33 | Otázka nad případem | Zeptám se vlastními slovy; odpověď je jen z dat pacienta a každá věta má citaci. | klik na navrženou otázku → AI hledá → odpověď (fialově „AI návrh“): poslední oxaliplatina 7. 9. s redukcí na 75 % a neuropatie G1, citace a % shody | rychlý posun nahoru, **← Jednání** | „Na cokoli se zeptám. Odpověď je jen z dat pacienta v nemocniční databázi, každá věta s citací. Nic se neukládá.“ |
| 04 | 0:33–0:42 | Okno pro projektor na míru | Zadávající lékař sám připraví, co komise uvidí na plátně. | jednání → **Upravit okno pro projektor** → dialog → oko skryje Hmotnost a Screening HBV → **přetažení** MMR/MSI nahoru → náhled vpravo se přeskládá („Pořadí zadávajícího lékaře“) → Uložit | klik na **Projektor** | „Před jednáním si zadávající lékař upraví okno pro projektor: nepotřebné skryje, důležité přetáhne nahoru. Vpravo vidí výsledek.“ |
| 05 | 0:42–0:50 | Jednání a plátno v sále | Předseda řídí z notebooku, plátno se přepne samo. Panel stojí vedle snímků z PACS. | obraz se zmenší do **notebooku předsedy**, vpravo se rozsvítí **plátno v zasedačce**: snímky z PACS a vedle panel MedTeam s úpravou ze 04, spojení „přepíná se samo“ | kamera se ponoří zpět do notebooku | „Na jednání řídí předseda z notebooku a plátno se přepíná samo. Panel stojí vedle snímků z PACS.“ |
| 06 | 0:50–0:58 | Každé tvrzení se zdrojem | Odkud to víme? Jedním klikem původní věta. | klik na citaci u PNP → vyjede zdroj P03-neuro01 → zvýrazní se „Neuropatie dle pacienta přetrvává“ | klávesa **Esc**, **Chat** | „Klik na citaci a vidím původní zprávu. Lékař hodnotí neuropatii jako stupeň 1, pacient popisuje víc.“ |
| 07 | 0:58–1:06 | Chat komise u pacienta | Komise si píše přímo u pacienta, i kolegové mimo sál. Zprávy mají štítek pacienta. | chat vyjede zprava (chirurg k FLR, radiolog k CT hrudníku, onkolog k MMR), přijde nová zpráva radiologa se štítkem **P03** | **Nahrávat diskusi** | „Komise má vlastní chat a každá zpráva nese štítek pacienta. Radiolog potvrdí, že CT hrudníku objednal.“ |
| 08 | 1:06–1:15 | AI zapisovatel | Z diskuse vznikne návrh závěru. AI text je vždy odlišený. | nahrávání a živá vlna → klávesa **Z** → Závěr komise s fialovými bloky „AI návrh“ | posun nahoru | „Diskusi nahrajeme, Whisper ji přepíše a AI připraví návrh závěru. Fialové je vždy to, co napsala AI.“ |
| 09 | 1:15–1:24 | Zápis do nemocnice (IRIS) | Oficiální je to až po potvrzení předsedou. Pak jednou transakcí do InterSystems IRIS (FHIR) a export. | potvrzený závěr se rozsvítí, štítek IRIS · FHIR R4, najetí na Export PDF a FHIR Bundle a na shrnutí pro pacienta | rozplynutí do loga | „Po potvrzení předsedou se závěr jednou transakcí zapíše do InterSystems IRIS for Health. Export do PDF nebo FHIR je na jeden klik.“ |
| — | 1:24–1:30 | logo + QR | vyzkoušejte si to | stejná animace loga jako v hooku, „AI předkládá. Lékař rozhoduje.“, **QR kód** na medteam.nervelabs.co.uk | — | „Vyzkoušejte si to sami, odkaz je v QR kódu.“ |

**Zvuk filmu B:** přirozený klik myší (Mixkit „Mouse click close“ a „Clear mouse clicks“, střídají se), tiché přechody,
jemné cvaknutí zprávy v chatu a u loga stejné SFX jako v hooku. Podkres „Vastness“ hraje na 0,16 a je i verze bez hudby.

**Poctivost dat:** všechno jsou snímky skutečné aplikace (živá doména, syntetický pacient P03). Výjimky jsou dvě:
- zprávy v chatu jsou nahrazené jen v prohlížeči (na živé instanci byly testovací zprávy týmu);
- stav „nahrává se“ a vlna jsou dokreslené.

Nic se při snímání neuložilo.

## 6. Technika

```powershell
cd video
npm install
npm run capture          # snímky pro hook → public/textures (Playwright, tmavý režim, 2×)
node scripts/capture2.mjs  # snímky interakcí pro průchod v2 → public/textures/v2 + layout2.json
node scripts/stills.mjs MedTeamWalkthrough 0.5 300 800  # rychlé kontrolní snímky (jeden bundle)
npm run dev              # Remotion Studio: náhled a ladění
npx remotion render src/index.ts MedTeamHook out/medteam-hook.mp4
npx remotion render src/index.ts MedTeamWalkthrough out/medteam-walkthrough.mp4
npx remotion render src/index.ts MedTeamHook out/medteam-hook-nobgm.mp4 --props=props-nobgm.json
```

- 1920 × 1080, 30 fps, H.264. Do PowerPointu vložit jako video a nastavit „Spustit automaticky“. U hooku navíc „Skrýt při nepřehrávání“ nevypínat, ať logo na konci zůstane stát.
- **Voice-over:** soubory podle tabulky v §3.3 do `public/audio/vo/` a pak znovu renderovat. Nic dalšího se nemění.
- **Výměna hudby:** `public/audio/music-hook.mp3`, offset `HOOK_MUSIC_OFFSET` v `src/hook/timeline.ts`.
- Projekt je deterministický: žádné `Math.random` ani `Date.now`, takže každý render dá stejný výsledek.

---

## 7. Prompty pro vlastní hudbu (Suno / Udio / Stable Audio)

**Hook (30 s):**
> Cinematic hybrid trailer cue, exactly 30 seconds, 76 BPM half-time feel. 0–10 s: tense low drone, a solitary heartbeat kick, ticking clock texture, rising string ostinato and a reverse-swell riser building tension. 10–11 s: one full second of near silence (suck-out). 11 s: massive orchestral-electronic impact with sub-bass boom, then hopeful, determined theme: warm low strings, pulsing synth arpeggio, taiko and big toms hitting every bar, brass swell. 25.8 s: final huge hit and a sustained shimmering chord that decays to silence by 30 s. Mood: humane, hopeful, high-stakes medical technology, not aggressive, no vocals. Style: Hans Zimmer meets Apple keynote.

**Průchod (90 s, podkres pod živý hlas):**
> Minimal ambient electronic underscore for a product walkthrough, 90 seconds, 80 BPM, steady and unobtrusive so a presenter can speak over it. Soft felt piano motifs, warm analog pads, gentle sub pulse, light glitchy percussion, no drops, no melody leads in the 1–4 kHz speech range, no vocals. Calm, trustworthy, clinical-clean, subtle optimism. Seamless loopable ending.

---

## 8. Použité nástroje a zdroje

- **Skill [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft)** (Apache-2.0): 124 receptů záběrů, PageCam (2.5D kamera nad snímkem), pravidla estetiky (R/Q/S/C/P), knihovna SFX. Použité recepty jsou uvedené ve sloupci „Recept skillu“.
- **Oficiální [Remotion Agent Skills](https://www.remotion.dev/docs/ai/skills)** (`remotion-dev/skills`): osvědčené postupy pro Remotion.
- **Remotion 4.0.532**, React 19, `@remotion/media` (zvuk), písma Inter a Montserrat lokálně v `public/fonts` (OFL, render nezávisí na síti), Playwright (snímání aplikace).
- QR kód: `public/qr.svg` (segno, oprava chyb H, uprostřed malý kříž).
- Hudba a SFX: **[Mixkit](https://mixkit.co/license/)** (bezplatná licence pro komerční užití, bez uvedení autora).
- Data: syntetický dataset hackathonu (Asseco CE v1.1), pacient P03, bez osobních údajů.

---

## 9. Poznámky a vědomé odchylky

- **Logo v tmavé variantě:** „Med“ je bílé místo navy a bublina má tyrkysový obrys, jinak by na černém pozadí filmu zmizely. Kříž, vlna a „Team“ mají barvy originálu.
- **Nesrovnalost v datech P03** (pro datovou lane, DATASET.md §9): v klíčových údajích je „RAS bez mutace (wild-type)“ (`P03-bm02`), ale léčebný postup anti-EGFR je vyloučený kvůli „KRAS mutace c.35G>A G12D“. Hook ukazuje řádek anti-EGFR tak, jak ho zobrazuje aplikace.
- **Úpravy zvuku podle zpětné vazby (17. 10.):** odebrán whoosh v 0:05 a úder v 0:07, „switch“ přesunut z razítka (23,5 s) na dosednutí kříže loga (26,0 s).
- **Riser, obrácený whoosh a sub** jsou syntetické (`scripts/synth_sfx.py`, deterministické), ostatní SFX a hudba jsou z Mixkitu.
