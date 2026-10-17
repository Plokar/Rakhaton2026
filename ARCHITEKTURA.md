# MDT Copilot — technická specifikace a architektura

> **Rakathon 2026** · Praha 16.–18. 10. 2026 · zadání **Asseco Central Europe** (MDT Copilot) + souběžná výzva **InterSystems** („Best Use of InterSystems Technology for AI and Interoperability“)
>
> Tento dokument je **jediný zdroj pravdy** pro architekturu, požadavky a datové kontrakty.
>
> - Dataset (struktura, FHIR, ingest, ID, vložené nesrovnalosti): [DATASET.md](DATASET.md)
> - Úkoly a stav: [PROGRESS.md](PROGRESS.md)
> - Pravidla pro AI agenty: [AGENTS.md](AGENTS.md)
> - Přehled a poznámky z konzultace: [MYSLENKOVA_MAPA.md](MYSLENKOVA_MAPA.md)
> - Požadavky lékaře (detail obrazovek, katalog pravidel semaforu, škály, zkratky): [docs/POZADAVKY_LEKARE.md](docs/POZADAVKY_LEKARE.md)
>
> Změnu kontraktu ([§8](#8-datové-kontrakty-fe--be)) nebo API ([§6.3](#63-rest-api)) udělej **nejdřív tady**, ve stejném PR jako kód, a zapiš ji do Deníku v PROGRESS.md.

---

## 0. TL;DR

- **Co stavíme:** webovou aplikaci, která z dat onkologického pacienta během pár sekund připraví podklad pro multidisciplinární komisi (MDT). Podklad má čtyři bloky: **A** souhrn, **B** pohledy odborníků, **B2** podpora rozhodování a **C** závěr a akční plán. Každé tvrzení AI má klikací citaci zdroje, AI hlásí rozpory (red flags) a **rozhoduje vždy lékař** (human-in-the-loop).
- **Stack:**
  - **Next.js 16** na **Vercelu** (`WEB_Template/frontend`);
  - **Django 5.2 + DRF** na **VPS** (`WEB_Template/backend`) v Dockeru s Traefikem;
  - vedle běží **InterSystems IRIS for Health** jako **nemocniční databáze** (FHIR R4 server + Vector Search);
  - PostgreSQL drží jen stav aplikace.
- **AI:** **Google AI Studio (Gemini API, placený tier)**: LLM, embeddingy i přepis audia ([§5.7](#57-model-a-ochrana-údajů)).
- **Data:** dataset od Asseco **už je FHIR R4**:
  - 6 pacientů, 1 091 resources;
  - 42 číslovaných pasáží guidelines;
  - 6 fiktivních studií.

  Ingest = sanitizace + převod `collection` na `transaction` do IRIS ([DATASET.md](DATASET.md)).
- **Totální integrace IRIS/FHIR:**
  - všechna klinická data jsou FHIR resources v IRIS a aplikace je za běhu čte **jen odtud**;
  - IRIS Vector Search slouží k výběru a ověřování citací;
  - potvrzený závěr komise se **zapisuje zpět do IRIS** ve stejné struktuře, jakou mají předchozí záznamy MDT v datasetu (`Composition` „Záznam MDT“ + `CarePlan` + `CareTeam`), doplněné o `Task`, `DetectedIssue` a `Provenance`;
  - export je FHIR document Bundle a PDF.
- **Harmonogram:** [§1.9](#19-harmonogram). Odevzdání zatím neřešíme (rozhodnutí týmu).
- **Požadavky lékaře** (budoucího uživatele, [§1.10](#110-požadavky-budoucího-uživatele-lékaře)):
  - role předseda (administrátor) / zadávající lékař / prohlížející;
  - boardy = zasedání, pacient se do boardu zařazuje formulářem s kontrolou úplnosti a varováními;
  - úzké rozložení do jednoho sloupce se sekcemi odborností;
  - u léčebných postupů semafor souladu se stavem pacienta (počítají ho pravidla, ne AI).

---

## 1. Zadání v kostce

Výtah ze zadání `docs/zadani/MDT_Copilot_zadani_upravené_2026_v02.pptx`, včetně poznámek řečníka.

### 1.1 Kontext

- **MDT** (multidisciplinární tým, v ČR „indikační onkologická komise“ / onkologické konzilium) je pravidelná porada lékařů různých oborů. Ti společně rozhodnou, jak léčit konkrétního pacienta s nádorem: operací, léky, ozařováním, nebo jejich kombinací. Žádný obor nevidí celý obraz a špatně zvolené pořadí léčby se těžko napravuje.
- **Role u stolu:** klinický onkolog (chemo-, imuno- a cílená léčba), chirurg (operabilita), radiační onkolog (radioterapie), radiolog (CT, MRI, PET-CT) a patolog (typ nádoru z biopsie).
- **Problém:**
  - na jednoho pacienta zbývají **3–5 minut** a za tu dobu se musí všichni zorientovat v často mnohaleté historii;
  - lékaři dohledávají informace **ručně**, protože nálezy v eZdraví jsou **volný text** bez struktury;
  - chybí **hlas pacienta**: dotazník (PROMs) zpravidla není s komisí propojený.
- **MDT je proces ve 3 fázích:**
  1. **před zasedáním:** lékař nominuje pacienta s konkrétní otázkou a kontroluje se úplnost podkladů;
  2. **během:** diskuse a rozhodnutí;
  3. **po zasedání:** úkoly, kontrola a opětovné posouzení.

  Copilot má podpořit **všechny tři fáze**, ne jen přípravu podkladu.

### 1.2 Mise a zlaté pravidlo

> Postavte funkční prototyp webové aplikace, která s pomocí AI spojí data pacienta, za pár sekund připraví přehledný podklad pro každého člena komise a na konci zapíše její rozhodnutí jako oficiální záznam.
>
> **Zlaté pravidlo:** AI připravuje, shrnuje, upozorňuje a navrhuje. **Rozhodují vždy lékaři** (human-in-the-loop). Žádný výstup AI se nestane oficiálním záznamem bez potvrzení lékařem a obsah od AI musí být **vizuálně odlišen**.

### 1.3 Čtyři bloky podkladu

| Blok | Název | Obsah | Poznámka ze zadání |
|---|---|---|---|
| **A** | Souhrn případu | „Executive summary“ pro orientaci **do 30 s**: diagnóza a hlavní otázka pro komisi, kondice **ECOG 0–4 podle lékaře i podle pacienta**, časová osa nemoci a léčby | Výrazný rozdíl mezi ECOG od lékaře a od pacienta je **varovný signál** |
| **B** | Pohled odborníků | Každý vidí, co potřebuje, **min. 3 role**. Chirurg: lze operovat, rozsah (TNM). Onkolog: biomarkery, dosavadní léky, nežádoucí účinky. Radiolog, patolog, pohled pacienta | povinně min. 3 role |
| **B2** | Podpora rozhodování | **AI předkládá, nevybírá.** Možnosti léčby z doporučených postupů **s citací**, vhodnost pro klinické studie, 2–3 klíčové otázky k diskusi | povinné minimum: možnosti z dodaných guidelines + screening studií |
| **C** | Závěr a akční plán | Oficiální záznam komise: rozhodnutí se zdůvodněním, úkoly, termíny, kontrola, **export (PDF / HL7 FHIR)** | |

Pojmy:

- **ECOG:** jak pacient zvládá běžné činnosti (0 = bez omezení, 4 = upoután na lůžko).
- **TNM:** T velikost nádoru, N uzliny, M vzdálené metastázy.
- **Biomarker:** vlastnost nádoru, podle které se vybírá lék (HER2, MSI, KRAS, PD-L1…).
- **RECIST 1.1:** pravidla měření odpovědi nádoru na snímcích.

### 1.4 Čtyři pravidla řešení

1. **Nastavitelnost:** předseda komise si „naklikne“, které sekce chce, v jakém pořadí, kdo je přítomen a jak podrobně.
2. **Varovné signály (red flags):** AI hledá rozpory mezi zdroji. Příklad: krevní testy ukazují pokles hemoglobinu a pacient v dotazníku hlásí extrémní únavu. **Každý red flag má závažnost a citaci obou zdrojů.**
3. **Dohledatelnost:** u každého tvrzení AI lze kliknout na zdroj. Když údaj chybí, AI to řekne a nehádá (nehalucinuje). Technicky jde o grounding: AI pracuje jen s daty pacienta a dodanými dokumenty.
4. **Člověk rozhoduje:** nic se nestane oficiálním záznamem bez potvrzení lékařem. Text od AI je vizuálně odlišený.

### 1.5 Dodaná data: dataset v1.1

Podrobně v **[DATASET.md](DATASET.md)**. Shrnutí:

- **6 fiktivních pacientů** (P01–P06):
  - 4× karcinom prsu (HR+/HER2-low, HER2+);
  - 1× kolorektum s jaterními metastázami;
  - 1× NSCLC st. III.

  Každý je **FHIR R4 Bundle** se 142–215 resources: nominace (`ServiceRequest` + `Task`), předchozí záznam MDT (`Composition` + `CarePlan` + `CareTeam`), zprávy (`DocumentReference`), patologie a zobrazení (`DiagnosticReport` + `ImagingStudy`), laboratoř s trendy markerů, ECOG lékaře, biomarkery, TNM, toxicita (`Observation`), medikace (`MedicationRequest` / `MedicationAdministration`), výkony (`Procedure`) a **2× PROMs** (`QuestionnaireResponse`).
- **PROMs:** vlastní dotazník `MDT-PROMS-1` (symptomy 0–10, **`samostatnost` = ECOG podle pacienta**, chůze, hmotnost, nové obtíže, léky navíc, preference).
- **Guidelines:** 4 výtahy (KRC, PRS, PLI, OBC) s **42 číslovanými pasážemi** (`KRC-2.4`). Pasáže OBC jsou zároveň konvence hackathonu pro prahy (staging ≤ 6 týdnů, rozdíl ECOG ≥ 1…).
- **Studie:** 6 fiktivních (`RKT-01`…`RKT-06`) jako `ResearchStudy` + `Group` s kritérii `Z1…` / `V1…`.
- **Vložené nesrovnalosti a mezery** jsou součást úlohy. Pracovní hypotézy týmu jsou v [DATASET.md §9](DATASET.md#9-vložené-nesrovnalosti--pracovní-hypotézy-týmu).
- **Chybí:**
  - **ground truth** (organizátor ho zveřejní po odevzdání);
  - **přepis diskuse MDT** (bonus, obstaráme si ho sami);
  - snímky DICOM (jen textové popisy, PACS je mimo rozsah).

### 1.6 Standardy

- **HL7 FHIR R4:** `Condition` (diagnóza a rozsah), `Observation` (biomarkery, kondice, dotazník), `CarePlan` + `Task` (rozhodnutí a úkoly), `Provenance` (odkud tvrzení je a kdo ho potvrdil).
- **Onkologické modely:**
  - **mCODE** (minimální onkologická sada ve FHIR, USA);
  - **HL7 Europe Common Cancer Model** (ECCDM, 1.0.0-ballot), mapuje se na FHIR i na OMOP;
  - **IPS** (International Patient Summary);
  - kontext **EHDS**.
- **Číselníky:** MKN-10 / ICD-O-3 (diagnózy, morfologie), LOINC (laboratoř, typy dokumentů, ECOG), SNOMED CT (klinické pojmy), ATC (léky). Dataset používá MKN-10, ICD-O-3, LOINC, ATC, DICOM a lokální číselníky `rakathon.example.org`.
- Mapování exportu na FHIR R4 / mCODE je v zadání **bonus**.

### 1.7 Hodnocení a finálová ukázka

| Kritérium | Váha | Čím body získáme |
|---|---|---|
| **Klinická hodnota & UX** | **30 %** | orientace do 30 s, role-specific pohledy a posouzení role, rychlost, čistý UI, prezentační režim |
| **Spolehlivost AI** | **20 %** | citace u každého tvrzení, grounding validátor (čísla, data, vektorová podobnost), explicitní „údaj chybí“, eval s čísly do pitche |
| **Nastavitelnost** | **20 %** | konfigurátor sekcí, pořadí, rolí a detailu; presety; přegenerování podle nastavení |
| **Propojení dat a standardy** | **15 %** | IRIS FHIR jako zdroj, zápis závěru ve struktuře datasetu, LOINC/MKN-10/ATC, FHIR export, mCODE profily |
| **Podpora procesu & zodpovědná AI** | **15 %** | 3 fáze MDT (nominace, readiness, zasedání, úkoly, re-review), human-in-the-loop, Provenance, pseudonymizace |
| Bonusové funkce | **+10 %** | hodnotí se kvalita, ne počet: readiness check, RECIST, AI zapisovatel, shrnutí pro pacienta, mCODE export |

**Finále: 5 minut, jeden pacient, celý cyklus komise živě:**

1. Vygenerovat podklad podle nastavení.
2. Zorientovat se v souhrnu do 30 sekund.
3. Kliknutím ověřit tvrzení AI a varovný signál.
4. Ukázat možnosti léčby s citací a vhodné studie.
5. Zapsat a potvrdit závěr komise.
6. Exportovat výsledek.
7. Krátce vysvětlit, **jaký model AI** používáme, **jak pracuje jen s daty pacienta (RAG)**, **jak brání chybám** a **jak chrání osobní údaje**: pseudonymizace, zpracování v EU, GDPR. V produkci by šlo o vysoce rizikový systém podle AI Act a o zdravotnický prostředek podle MDR.

**Demo pacient:** **P03** (záloha P05). Zdůvodnění je v [DATASET.md §9](DATASET.md#9-vložené-nesrovnalosti--pracovní-hypotézy-týmu).

### 1.8 Výzva InterSystems (kombinovatelná s MDT Copilot)

- **Název:** „Best Use of InterSystems Technology for AI and Interoperability“, 1. místo **1 500 EUR**.
- **Technologie (žádná není povinná):** IRIS for Health, InterSystems FHIR Server, Vector Search (GenAI; přes Python, SQL, LangChain nebo LlamaIndex) a agentní AI.
- **Kritéria:**
  - inovace;
  - reálný dopad;
  - **využití technologie InterSystems**;
  - technická soudržnost.

  Organizátoři chtějí vidět jasně definovaný zdravotnický problém, chytré využití AI a HL7 FHIR, dobře navržený datový model a architekturu a realistickou cestu k MVP nebo startupu.
- **Mentoři:** InterSystems je k dispozici 24/7. Mgr. **Ondřej Hoferek** (technický ředitel InterSystems CZ/SK, HL7 ČR) je zároveň mentorem zadání MDT Copilot.
- **Zdroje:**
  - [FHIR-AI-Hackathon-Kit](https://github.com/intersystems-community/FHIR-AI-Hackathon-Kit) (větev V2) s tutoriály 5.1 agents & tools a 5.2 MCP server;
  - Synthea pro syntetická data;
  - VZP poskytuje IRIS instance v Azure pro kombinované výzvy.

### 1.9 Harmonogram

| Kdy | Co |
|---|---|
| Pá 16. 10. 9:30 / 12:00 | start / **start hackování** |
| So 17. 10. 12:00 | uzávěrka odevzdání projektů (*odevzdání zatím neřešíme*) |
| So 17. 10. 13:00 | lokální pitche |
| So 17. 10. 17:00 | vyhlášení lokální TOP 3 |
| Ne 18. 10. od 14:00 | národní finále (NOC Motol / Homolka), vítězové v 17:00 |

**Kontakty:** Ľuboslav Piljan (Asseco CE, monitor zadání) a Ondřej Hoferek (InterSystems / HL7 ČR, mentor). Obracet se na ně kdykoli: se zadáním, daty, klinickým kontextem, FHIR i směrem řešení.

### 1.10 Požadavky budoucího uživatele (lékaře)

Tým dostal poznámky od lékaře, který by aplikaci používal (Pá 16. 10.). Jsou sladěné se zadáním a promítnuté do požadavků v §2: FR-U1, FR-U2, FR-P4, FR-B8, FR-D4, FR-D5, FR-A5, FR-R5, BON-6 a BON-7. Detail je v [docs/POZADAVKY_LEKARE.md](docs/POZADAVKY_LEKARE.md).

| Požadavek lékaře | Jak je sladěný se zadáním |
|---|---|
| 3 role: administrátor MDT, zadávající lékař, prohlížející | administrátor = předseda: zakládá boardy, mění termíny, **nastavuje podklad** (nastavitelnost, §1.4) a potvrzuje závěr (D-014) |
| zařazení pacienta s varováním, když něco chybí, je mimo normu nebo v rozporu | fáze „před zasedáním“ (§1.1). Odkliknuté varování ani přeskočený údaj **z podkladu nezmizí** (D-019). |
| hlavička s rodným číslem, velkým ECOG a záměrem | místo RČ `P03 · muž · 67 let` (pseudonymizace). Diagnóza, TNM a hlavní otázka jsou nahoře (orientace do 30 s). ECOG lékaře je velký **a vedle něj ECOG pacienta** (D-018). |
| barvy u léčebných postupů | semafor **souladu se stavem pacienta**, ne doporučení. Vždy se ukážou všechny možnosti a barvu počítají pravidla s citací (D-015). |
| úzké okno, všichni na jednom projektoru, údaje podle odborností u sebe | jeden sloupec od 360 px, sekce odborností (min. 3 role, blok B) s barvou odbornosti (D-017) |
| Lung-RADS a Fleischner; vstup přes PDF nebo vložený text | bonusy BON-6 a BON-7, až po povinných blocích |

---

## 2. Katalog požadavků

**Priority:**

- **MUST:** bez toho neprojdeme finálovou ukázkou;
- **SHOULD:** výrazně zvedá skóre;
- **BONUS:** +10 %, kvalita před kvantitou.

Sloupec **Krit.** odkazuje na kritéria z §1.7: UX, AI, CFG, STD, PROC. Značka *(konzultace)* znamená požadavek z konzultace se zadavateli ([MYSLENKOVA_MAPA.md](MYSLENKOVA_MAPA.md)).

### 2.1 Funkční požadavky

| ID | Požadavek | Priorita | Krit. |
|---|---|---|---|
| **FR-A1** | Executive summary: diagnóza (MKN-10 + slovně), stadium (TNM), hlavní otázka komise (`ServiceRequest.reasonCode.text`), čitelné do 30 s. **Diagnóza, TNM a hlavní otázka jsou v hlavičce nahoře**, ne až pod bloky. Místo jména a RČ `Pxx · pohlaví · věk` (D-018). | MUST | UX |
| **FR-A2** | ECOG lékař (`Observation` LOINC 89247-1) vs. pacient (PROMs `samostatnost` 0–4) vedle sebe s datem a citací; **rozdíl ≥ 1 znamená red flag** (OBC-1.3). ECOG lékaře je velkou číslicí (zadává nebo potvrzuje zadávající lékař, předvyplněno z IRIS), vedle něj vždy ECOG pacienta a velké písmeno záměru **C** (kurativní) / **P** (paliativní). | MUST | UX, AI |
| **FR-A3** | Časová osa: diagnóza, výkony, linie léčby, zobrazení, PROMs, předchozí MDT; každý bod klikací | MUST | UX |
| **FR-A4** | Hlavička: **komorbidity** (`Condition` „komorbidita“), **alergie** (PROMs `alergie` + text zpráv), **předchozí výkony a implantáty** (`Procedure`: port, stent, operace) *(konzultace)* | MUST | UX |
| **FR-A5** | Anamnéza: krátký text doslovně, dlouhý (nad `INTAKE_ANAMNESIS_MAX_CHARS`) jako shrnutí AI s citacemi; lékař může přepnout. Sekce OA, FA, RA, SA, GA, NO ze zpráv. *(lékař)* | SHOULD | UX |
| **FR-B1** | Pohled chirurga: resekabilita, TNM, rozsah, předchozí operace v oblasti, operační riziko | MUST | UX |
| **FR-B2** | Pohled onkologa: biomarkery (včetně „nevyšetřeno“), linie léčby (`MedicationAdministration`), odpověď, toxicita (lékař vs. PROMs) | MUST | UX |
| **FR-B3** | Pohled radiologa: vývoj nálezů a rozměrů lézí v čase, srovnání posledních vyšetření, aktuálnost stagingu | MUST (≥ 3 role) | UX |
| **FR-B4** | Pohled patologa: histologie, grade, ICD-O-3, biomarkery z tkáně, diskordance primár vs. metastáza | SHOULD | UX |
| **FR-B5** | Pohled pacienta: trend PROMs (2 vyplnění), nové obtíže, priorita (`delka`/`kvalita`), postoj, podpora doma | MUST | UX, PROC |
| **FR-B6** | Pohled radiačního onkologa: předchozí RT, oblasti, dávky | SHOULD | UX |
| **FR-B7** | **Posouzení role („match“):** pro každou přítomnou roli předběžný verdikt `candidate` / `conditional` / `not_candidate` / `insufficient_data` po kritériích s citací (např. chirurg: resekabilita, FLR, ECOG, komorbidity). Jen podklad, potvrzuje lékař dané role *(konzultace)* | SHOULD | UX, AI |
| **FR-B8** | Údaje podle diagnózy v sekcích odborností: plíce (spirometrie, ppoFEV1/ppoDLCO, kouření), prs (receptory, HER2, LVEF), kolorektum (RAS/BRAF/MMR, FLR, bevacizumab). Seznam: [docs/POZADAVKY_LEKARE.md §4](docs/POZADAVKY_LEKARE.md#4-povinné-a-důležité-údaje-podle-diagnózy). *(lékař)* | MUST | UX |
| **FR-D1** | Možnosti léčby z **dodaných** guidelines s citací **ID pasáže** (`KRC-2.4`); AI nevybírá, předkládá alternativy. Patří k nim i podpůrná péče z OBC-2.x (včasná paliativní péče, geriatrické a nutriční vyšetření, genetické poradenství), když ji pacient splňuje. | MUST | AI, STD |
| **FR-D2** | Screening studií `RKT-01…06`: pro každé kritérium `met` / `not_met` / `unknown` + citace (`RKT-03/V3` ↔ fakt pacienta); celkový stav | MUST | AI |
| **FR-D3** | 2–3 klíčové otázky k diskusi | MUST | UX |
| **FR-D4** | **Semafor souladu léčebného postupu se stavem pacienta** (🟢 nevylučuje · 🟠 pozor · 🔴 vylučuje · ⚪ nelze posoudit) po pravidlech s citací faktu pacienta i pravidla ([§5.9](#59-semafor-souladu-léčebných-postupů-se-stavem-pacienta)). Vždy se zobrazí všechny možnosti, barvu počítá kód, ne LLM (D-015). *(lékař)* | MUST | AI, UX |
| **FR-D5** | Katalog léčebných metod pro diagnózu: u každé metody odborník, který se k ní musí vyjádřit, a data, která má mít u sebe. *(lékař)* | SHOULD | UX |
| **FR-C1** | Strukturovaný zápis rozhodnutí ve struktuře datasetu (Projednaná otázka, Klinické zhodnocení, Léčebný záměr, Doporučený postup, Doplňující diagnostika, Klinická studie, Plánované re-MDT, Závěr MDT) + přítomní. U neúplného případu příznak **podmíněné doporučení** (OBC-1.1), u duplicity malignit **priorita léčby a plán druhého nádoru** (OBC-1.4). | MUST | PROC, STD |
| **FR-C2** | Úkoly (kdo, co, do kdy), kontrola, termín opětovného posouzení | MUST | PROC |
| **FR-C3** | Potvrzení předsedou udělá z draftu oficiální záznam (zápis do IRIS FHIR) | MUST | PROC |
| **FR-C4** | Export PDF + HL7 FHIR (document Bundle) | MUST | STD |
| **FR-R1** | Konfigurátor: sekce zap/vyp, pořadí, přítomné role, úroveň detailu; ukládání presetů. Nastavuje předseda (`mdt_admin`) pro zasedání. Ostatní si bloky mohou jen sbalit nebo přeskládat u sebe (lokálně). Konfigurátor upozorní, když v přítomných rolích chybí role, kterou guidelines pro danou otázku vyžadují (`RF-ROLES`: KRC-2.1, PLI-2.1, PRS-1.4). | MUST | CFG |
| **FR-R2** | Red flags: rozpory mezi zdroji, závažnost (high/moderate/low), citace **obou** zdrojů, odkaz na pasáž guidelines. Odkliknutí varování při zařazení pacienta red flag z podkladu **neodstraní** (D-019). | MUST | AI |
| **FR-R3** | Klikací citace u každého tvrzení otevře zdroj se zvýrazněnou pasáží; chybějící údaj explicitně „Údaj chybí v podkladech“. Údaj, který lékař při zařazení přeskočil, se ukáže jako „Chybí (přeskočeno lékařem)“. | MUST | AI |
| **FR-R4** | AI text vizuálně odlišen (badge „AI návrh“, styl); po potvrzení „Potvrzeno: LEK-…, čas“ | MUST | PROC |
| **FR-R5** | Výklad zkratek podle kontextu (sekce zprávy, oddělení, orgán). Rozmezí („ECOG 0–1“) a nejednoznačné zkratky vyvolají varování NEJISTOTA AI, nikdy odhad. *(lékař)* | SHOULD | AI |
| **FR-P1** | Před zasedáním: **boardy = zasedání MDT** (předseda zakládá board a mění termín), agenda (`Task.restriction.period.start`), zadávající lékař přesouvá své pacienty mezi boardy | MUST | PROC |
| **FR-P2** | Během zasedání: přepínání pacientů v agendě, prezentační režim (velké písmo, projektor) | SHOULD | UX |
| **FR-P3** | Po zasedání: přehled úkolů a jejich stav, naplánování re-MDT | SHOULD | PROC |
| **FR-P4** | **Zařazení pacienta do boardu:** formulář předvyplněný z IRIS; chybějící údaj Doplnit / Přeskočit; varování CHYBÍ, MIMO NORMU, ROZPOR, NEJISTOTA AI (lze odkliknout); ECOG + záměr C/P; checkbox „Snímek mladší než 3 měsíce“ (připomínka; automatická kontrola stagingu zůstává ≤ 6 týdnů, OBC-1.2); ruční údaje se zapíší do IRIS jako FHIR + `Provenance` ([§5.10](#510-zařazení-pacienta-a-kontrola-úplnosti)). **Otázku pro MDT přeskočit nelze** (OBC-1.1). *(lékař)* | MUST | PROC, AI |
| **FR-U1** | Role podle oprávnění: `mdt_admin` (předseda), `mdt_doctor` (zadávající lékař), `mdt_viewer` (člen komise) + odbornost uživatele (D-014). *(lékař)* | MUST | PROC |
| **FR-U2** | Úzké rozložení: použitelné od 360 px, jeden sloupec, bloky pod sebou; podklad jde otevřít v samostatném úzkém okně bez navigace (D-017). *(lékař)* | MUST | UX |

### 2.2 Bonusy

| ID | Bonus | Pozn. |
|---|---|---|
| **BON-1** | **Kontrola připravenosti případu** (readiness): checklist OBC-1.1 (otázka, histologie + grade, TNM, prediktivní biomarkery, ECOG, komorbidity, dosavadní léčba, preference) + aktuálnost stagingu ≤ 6 týdnů (OBC-1.2) | deterministicky + LLM pro text |
| **BON-2** | **Předvýpočet odpovědi dle RECIST 1.1**: SLD baseline vs. nadir vs. aktuální, výsledek CR/PR/SD/PD | P03: 83 → 50 mm (−40 %) = PR; AI jen extrahuje rozměry z popisů |
| **BON-3** | **AI zapisovatel**: přepis diskuse převede na draft rozhodnutí + úkoly (s citací na úsek přepisu) | **Dataset přepis neobsahuje.** Nahrajeme vlastní simulovanou diskusi (audio) a přepíšeme ji Gemini ([§5.6](#56-ai-zapisovatel-bon-3)) |
| **BON-4** | **Shrnutí pro pacienta** v laickém jazyce | po potvrzení závěru; zohlednit `priorita` a `postoj` z PROMs |
| **BON-5** | **Export mapovaný na mCODE / ECCDM** (`meta.profile`, kódy pro biomarkery a TNM, které jsou v datasetu jen textem), případně validace `$validate` v IRIS | zároveň bod pro InterSystems |
| **BON-6** | **Karta Lung-RADS / Fleischner** s kontrolou použitelnosti: Lung-RADS jen pro screeningové CT, Fleischner jen pro náhodný uzel bez známého nádoru | u všech 6 pacientů ukáže „nelze použít“ s důvodem; požadavek lékaře |
| **BON-7** | **Vstup PDF nebo vloženého textu:** překladač do FHIR (Gemini extrakce s odkazem na zdrojový `DocumentReference`) → validace → potvrzení lékařem → IRIS | až po povinných blocích; potřebuje placený tier (Q9); požadavek lékaře |

### 2.3 Nefunkční požadavky

| ID | Požadavek |
|---|---|
| **NFR-1** | Podklad „za pár sekund“: cíl < 20 s na pacienta, sekce generované paralelně, průběh viditelný v UI |
| **NFR-2** | **Grounding:** LLM dostane jen data daného pacienta + relevantní guidelines a studie; vektorové hledání vždy s filtrem `PatientId`; za běhu jen data z IRIS |
| **NFR-3** | **Ochrana údajů:** pseudonymizace před LLM, Gemini **jen v placeném tieru** (data se nepoužívají k trénování), žádné PII v logu, RBAC, IRIS a DB neveřejné |
| **NFR-4** | **Auditovatelnost:** log LLM volání (účel, model, hash promptu, tokeny, latence) a `Provenance` u každého potvrzeného záznamu |
| **NFR-5** | Spolehlivé demo: předgenerovaný podklad pro demo pacienta (cache), záložní video, lokální fallback |
| **NFR-6** | Nasazení: frontend na Vercelu, backend na VPS, HTTPS, žádné secrets ve frontendu |

---

## 3. Architektura

### 3.1 Přehled

```
                         ┌──────────────────────────────────────────┐
  Prohlížeč (lékař) ───▶ │  VERCEL – Next.js 16 (WEB_Template/frontend)
                         │  • UI (App Router, React 19, Tailwind 4)  │
                         │  • proxy.ts (ochrana /dashboard)         │
                         │  • rewrites /api/*  ──────────────┐      │
                         └───────────────────────────────────┼──────┘
                                     HTTPS (same-origin proxy)│
                                                              ▼
┌──────────────────────────────── VPS (Docker Compose) ───────────────────────────────────┐
│  Traefik v3 (TLS Let's Encrypt, api.<doména>)                                           │
│      │                                                                                  │
│      ▼                                                                                  │
│  Django 5.2 + DRF (ASGI/Daphne) – WEB_Template/backend                                  │
│  ├─ apps/patients   – čtení pacientů z FHIR, časová osa, evidence resolver              │
│  ├─ apps/mdt        – zasedání, případy, konfigurace, závěry, export                    │
│  ├─ apps/copilot    – AI orchestrace (A, B, B2, C, red flags, scribe), joby             │
│  ├─ services/fhir   – FHIR REST klient, ingest (sanitizace), write-back, export         │
│  ├─ services/iris   – IRIS DB-API (intersystems-irispython), vector store               │
│  ├─ services/ai     – Gemini provider, prompty, context builder, grounding              │
│  └─ services/rules  – deterministická pravidla (red flags, readiness, RECIST)           │
│      │                     │                         │                                  │
│      ▼                     ▼                         ▼                                  │
│  PostgreSQL 16        Redis 7              InterSystems IRIS for Health (Community)     │
│  (stav aplikace:      (cache, joby,        ├─ FHIR R4 server  /fhir/r4  (port 52773)    │
│   uživatelé, drafty,   channels)           │   = NEMOCNIČNÍ DB, zdroj pravdy            │
│   presety, logy)                           ├─ IRIS SQL + Vector Search  (port 1972)     │
│                                            │   MDT.EvidenceChunk / GuidelineChunk / …   │
│                                            └─ (volitelně) FHIR SQL Builder projekce     │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
                  Google AI Studio – Gemini API (placený tier): LLM · embeddingy · přepis audia
```

### 3.2 Odpovědnosti vrstev

| Vrstva | Dělá | Nedělá |
|---|---|---|
| **Next.js (Vercel)** | UI, routing, ochrana stránek (`proxy.ts`), volání `/api/*` (same-origin) | žádné LLM klíče, žádný přímý přístup k IRIS, žádná business logika |
| **Django** | autentizace (JWT v httpOnly cookies), orchestrace AI, grounding, pravidla, FHIR read/write, ingest, export | neukládá klinická data do Postgresu (jen reference na FHIR ID a drafty); za běhu nečte JSON soubory datasetu |
| **IRIS for Health** | **zdroj pravdy klinických dat** (FHIR R4), vektorové tabulky pro RAG a grounding, potvrzené záznamy komise | (do internetu nevystaven) |
| **PostgreSQL** | uživatelé, role, zasedání MDT, presety konfigurace, drafty podkladů a závěrů, joby, log LLM | klinická data |

### 3.3 Klíčová rozhodnutí

| # | Rozhodnutí | Proč |
|---|---|---|
| D-001 | Frontend na Vercelu, backend na **VPS** | požadavek týmu; IRIS + Postgres + dlouhé LLM joby na serverless nepatří |
| D-002 | **IRIS FHIR = nemocniční DB**, Postgres = stav aplikace | čistá separace; FHIR je společný jazyk (bodovaná kritéria STD + InterSystems); template a auth zůstanou beze změny |
| D-003 | **Same-origin proxy**: Vercel `rewrites` `/api/*` vede na backend | auth template používá httpOnly cookies se `SameSite=Strict` (prod) a `proxy.ts` je čte na doméně frontendu; cross-domain by se rozbily |
| D-004 | Generování jako **asynchronní job + polling** (ne WebSocket) | Vercel neproxyuje WebSockety; dlouhé requesty přes proxy jsou křehké |
| D-005 | **ID z datasetu zachovat** (`P03-img03`) + `PUT` v transaction bundlu | dataset už má stabilní, čitelná ID; seed je idempotentní (opakovaný `POST` v IRIS duplikuje) |
| D-006 | **Evidence ID = ID zdroje z datasetu** (`P03-img03`, `P03-img03#2`, `KRC-2.4`, `RKT-03/V3`) | stejné ID vidí lékař v `.md`, LLM v kontextu i FHIR v IRIS; krátké ID = méně chyb v citacích |
| D-007 | Embeddings **`gemini-embedding-001`**, `output_dimensionality=1536` + L2 normalizace | jeden provider (D-008); 1536 = dobrý kompromis; DDL `VECTOR(DOUBLE, 1536)` |
| D-008 | **LLM provider = Google AI Studio (Gemini API), placený tier** | rozhodnutí týmu; LLM, embeddingy i přepis audia od jednoho providera; v EHP smí být jen placený tier |
| D-009 | **Výstup komise kopíruje strukturu předchozích MDT v datasetu** (`Composition` `mdt-zaznam` + `CarePlan` + `CareTeam` + lokální číselníky) | konzistence se „systémem nemocnice“, nový záznam vypadá jako ty předchozí; snadné porovnání s předchozím MDT |
| D-010 | **Do LLM jde kompletní kontext pacienta** (je malý, cca 8–12 tisíc tokenů); **IRIS Vector Search** slouží k výběru a řazení pasáží, k ověřování citací (podobnost tvrzení a zdroje) a ke škálování | spolehlivější než top-k RAG na malých datech, a přitom smysluplné využití IRIS |
| D-014 | **Role podle oprávnění** (`mdt_admin` = předseda, `mdt_doctor`, `mdt_viewer`) + odbornost u uživatele; **board = zasedání MDT** (`MdtSession`) | požadavek lékaře; předseda drží nastavitelnost a potvrzení závěru (§1.4) |
| D-015 | **Semafor souladu postupů se stavem pacienta počítají deterministická pravidla** (`services/rules/compatibility.py` + datový soubor pravidel s prahy a zdroji). LLM barvu nikdy nepřiřazuje. Vždy se ukážou všechny možnosti. | zadání: „AI předkládá, nevybírá“; dohledatelnost |
| D-016 | **Evidence ID pro externí zdroje `EXT-…`** (EMA, SmPC, ERS…) v `MDT.GuidelineChunk` s `GuidelineSet = "EXT"`, v UI označené „externí zdroj“. Demo stojí hlavně na pravidlech z dodaných guidelines. | grounding (§1.4); porota hodnotí podle dodaných guidelines |
| D-017 | **Úzké rozložení** (od 360 px, jeden sloupec) a **sekce odborností** s barvou odbornosti. Tři oddělené barevné systémy: semafor, odbornost, AI. | lékař má aplikaci v úzkém okně vedle PACS; všichni sledují jeden projektor |
| D-018 | **Hlavička:** `Pxx · pohlaví · věk` (žádné jméno ani RČ), diagnóza + TNM, hlavní otázka, ECOG lékaře velký + ECOG pacienta, záměr **C/P** | orientace do 30 s, ECOG lékař i pacient (§1.3), pseudonymizace |
| D-019 | **Nic se z podkladu neztratí:** odkliknuté varování jen umlčí upozornění při zařazení, přeskočený údaj se ukáže jako „Chybí (přeskočeno lékařem)“ | red flags a „údaj chybí“ (§1.4) |
| D-020 | **Práce ve sprintech** = milníky M0–M4. Na konci sprintu merge do `master`, smoke test a přeplánování v PROGRESS.md. | víc lidí, strojů a agentů paralelně |

### 3.4 Nasazení

#### Frontend — Vercel

- **Root Directory:** `WEB_Template/frontend`. Framework se detekuje automaticky. `output: 'standalone'` může zůstat.
- **Env proměnné:**
  - `BACKEND_URL=https://api.<doména>`: jen pro server, používá se v `rewrites`;
  - `NEXT_PUBLIC_API_URL=`: prázdné, aby se volalo same-origin `/api/...`;
  - `NEXT_PUBLIC_APP_NAME=MDT Copilot`.
- **Úpravy kódu (úkol T-004):**
  - `next.config.ts`:
    ```ts
    skipTrailingSlashRedirect: true,          // Django URL končí lomítkem → jinak smyčka 308 ↔ 301
    async rewrites() {
      return [{ source: '/api/:path*', destination: `${process.env.BACKEND_URL}/api/:path*` }];
    },
    ```
  - `src/lib/api.ts`: `const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';`. Dnes `||` při prázdném stringu spadne na `http://localhost:8000`.
  - `DashboardLayout.tsx`: odkazy na `localhost:8000/8025/8080` zobrazovat jen v dev režimu.
- **Preview deploye** mají jiné URL a backend je musí mít v `CSRF_TRUSTED_ORIGINS` (viz níže).

#### Backend — VPS

- VPS **min. 4 vCPU / 8 GB RAM** (IRIS si vezme 2–3 GB), Ubuntu + Docker, DNS `A api.<doména>`.
- Použít `WEB_Template/docker-compose.yml` (Traefik, backend, db, redis) a **přidat službu `iris`**:

  ```yaml
  iris:
    build: ./iris            # Dockerfile + merge.cpf převzaté z FHIR-AI-Hackathon-Kit/docker-iris-fhir
    restart: unless-stopped
    environment:
      ISC_DATA_DIRECTORY: /durable
    volumes:
      - iris_data:/durable
    networks: [app-network]
    ports:
      - "127.0.0.1:52773:52773"   # Management Portal / FHIR jen přes SSH tunel
    # 1972 nepublikovat; backend se připojuje interně na iris:1972
  ```
- **Dataset** se do backend kontejneru dostane přes volume. Repo na VPS, `DATASET_DIR=/data/dataset`, mount `../Dataset_MDT_Copilot_v1.1_pre_timy/Dataset_MDT_Copilot_v1.1:/data/dataset:ro`.
- **Bezpečnost serveru:**
  - **změnit výchozí heslo IRIS `SYS`**;
  - IRIS ani Postgres nepublikovat ven;
  - Management Portal jen přes `ssh -L 52773:127.0.0.1:52773 vps`.
- **Django prod env:**
  - `ALLOWED_HOSTS=api.<doména>`;
  - `CSRF_TRUSTED_ORIGINS=https://<projekt>.vercel.app,https://*.vercel.app` (wildcard jen pro hackathon, Django ≥ 4.0 ho podporuje);
  - `CORS_ALLOWED_ORIGINS` stejně (potřeba jen při přímých voláních mimo proxy).
- **WebSocket** (template `ws://…/ws/room/…`) přes Vercel nejde. Pokud bude potřeba (live zasedání), připojit se přímo na `wss://api.<doména>/ws/...` s krátkodobým tokenem: middleware už podporuje `?token=`. Je potřeba endpoint `GET /api/auth/ws-ticket/`. **Pro MVP stačí polling.**

---

## 4. InterSystems IRIS for Health — integrace

### 4.1 Co z IRIS použijeme

| Funkce IRIS | Využití v MDT Copilot | Priorita |
|---|---|---|
| **FHIR R4 server** (`/fhir/r4`) | **Nemocniční DB:** celý dataset (6 pacientů, studie, dotazník) jako FHIR resources; backend čte přes REST (search `patient=`, `_tag`, `_summary=count`) | MUST |
| **FHIR write-back** (transaction Bundle) | Potvrzený závěr komise ve struktuře datasetu ([§4.3](#43-fhir-datový-model)) + aktualizace stavu žádanky (`Task`, `ServiceRequest`) | MUST |
| **IRIS SQL + Vector Search** (`VECTOR`, `TO_VECTOR`, `VECTOR_COSINE`) | Odstavce zpráv (filtr na pacienta), pasáže guidelines, kritéria studií: výběr a řazení pasáží, **ověření citací** (podobnost tvrzení a zdroje), propojení přepisu s fakty | MUST |
| **Python DB-API** `intersystems-irispython` (`import iris`) | Přístup z Djanga (SQL, vektory, native API pro inicializaci FHIR serveru) | MUST |
| **FHIR SQL Builder** | Projekce `Observation` (laboratoř, hmotnost, ECOG) do SQL pro trendy, pravidla red flags a dashboard zasedání. **Realizováno (T-309) jako SQL pohled `MDT.ObservationSeries`** nad úložištěm FHIR serveru (`HSFHIR_X0001_R.Rsrc` + `JSON_TABLE`): vždy aktuální, bez ruční konfigurace Builderu v portálu a bez synchronizace; zakládá ho `iris_init`, čte `services/iris/projections.py`. Živě sedí s FHIR REST na všech 13 řadách P03 | SHOULD |
| **MCP server nad IRIS** (FastMCP, kit 5.2) | Nástroje `get_patient_context`, `search_evidence`, `search_guidelines`, `fhir_query` pro copilot agenta; ukázka „IRIS jako MCP backend“ | SHOULD |
| **FHIR packages (mCODE IG) + `$validate`** | Validace exportu proti profilům (`HS.FHIRMeta.Load.NpmLoader.importPackages`) | BONUS |
| Interoperability production | Ingest „surových“ eZdraví zpráv (File → DTL → FHIR); dataset už je FHIR, takže netřeba | stretch, ne |
| IntegratedML | **nepoužijeme**: predikce bez klinické validace by snížila důvěryhodnost | — |

**Pitch pro InterSystems:** IRIS je nemocniční datová platforma, ze které copilot **čte** (FHIR), ve které **hledá a ověřuje** (Vector Search nad stejnými daty, bez další vektorové DB) a do které **zapisuje** auditovatelný závěr komise (FHIR + Provenance). Jedna platforma, standardy end-to-end.

### 4.2 Prostředí (převzato z FHIR-AI-Hackathon-Kit V2)

| Věc | Hodnota (dev) |
|---|---|
| Image | `intersystems/irishealth-community:2026.2` (= `latest-cd` k 16. 10.), `WEB_Template/iris/Dockerfile` |
| `merge.cpf` | `[Actions] ModifyService:Name=%Service_CallIn,Enabled=1,AutheEnabled=48` |
| Superserver (DB-API) | `iris:1972` (lokálně `localhost:1972`) |
| Web (FHIR, portal) | `http://iris:52773` (lokálně `http://localhost:52773`) |
| Credentials | `SuperUser` / `SYS` (**jen dev**, na VPS změnit) |
| Namespace | `FHIRSERVER` |
| FHIR base | `http://localhost:52773/fhir/r4` (capability: `/fhir/r4/metadata`) |
| Management Portal | `http://localhost:52773/csp/sys/UtilHome.csp` |
| FHIR SQL Builder | `http://localhost:52773/csp/fhir-management/sql-projections/home` |
| Swagger (pokud nainstalujeme) | `http://localhost:52773/fhir/swagger-ui/index.html` |

**Inicializace FHIR serveru** (úkol T-003): Django management command `iris_init` podle kitu `fhir_server_setup_native.py`. Kroky:

1. `HS.Util.Installer.Foundation.Install("FHIRSERVER")`;
2. `HS.FHIRServer.Installer.InstallNamespace()`;
3. `InstallInstance("/fhir/r4", "HS.FHIRServer.Storage.JsonAdvSQL.InteractionsStrategy", "hl7.fhir.r4.core@4.0.1")`.

Command musí být idempotentní (`ExistsByUrl`). **Nenahrávat** Synthea data z kitu, nahrává se náš dataset (`ingest_dataset`). Spouští ho `entrypoint.sh` při každém startu backendu (když je nastavené `IRIS_HOST`). První běh trvá cca 2 min, další pár sekund.

### 4.3 FHIR datový model

#### Vstupy: dataset (už je FHIR)

Kompletní popis je v [DATASET.md §4](DATASET.md#4-fhir-model-datasetu-kde-co-je). Pro orientaci:

| Potřeba Copilotu | Kde v IRIS |
|---|---|
| Diagnóza, stadium, histologie | `Condition` „onkologická diagnóza“ (MKN-10, ICD-O-3 extension, `stage.summary.text`) + `Observation` `tnm` |
| **Komorbidity** | `Condition` s `category.text = "komorbidita"` |
| **Předchozí výkony, implantáty** | `Procedure` (port, stent, operace, biopsie, RT, transfuze) + `DocumentReference` typ 28570-0 |
| **Alergie** | PROMs `alergie` + text zpráv („Alergie: …“). Resource `AllergyIntolerance` v datasetu **není**, extrahuje ho LLM s citací |
| Otázka komise, podklady, termín | `ServiceRequest` (`reasonCode.text`, `supportingInfo`, `note`) + `Task` (`restriction.period.start`) |
| Předchozí rozhodnutí | `Composition` `mdt-zaznam` + `CarePlan` + `CareTeam`, `Composition` `rozhodnuti-o-lecbe` |
| Zprávy, popisy zobrazení, patologie (text) | `DocumentReference.content.attachment.data`, `DiagnosticReport.presentedForm.data` (base64) + `conclusion` |
| Laboratoř a trendy | `Observation` `lab` (LOINC, UCUM, `referenceRange`) seskupené v `DiagnosticReport` LAB |
| ECOG lékař / pacient | `Observation` LOINC 89247-1 / `QuestionnaireResponse` item `samostatnost` |
| Biomarkery, toxicita, LVEF, spirometrie | `Observation` `bm` / `neuro`, `anem` / `lvef` / `spiro` (jen `code.text` + `valueString`) |
| Léčba | `MedicationAdministration` (podání, redukce v `note`), `MedicationRequest` (chronická) |
| Studie | `ResearchStudy` + `Group` (kritéria v `characteristic`, `exclude`) |
| Guidelines | jen IRIS SQL `MDT.GuidelineChunk` (nejsou FHIR) |

#### Výstupy: zápis komise do IRIS (jeden transaction Bundle)

Zápis zrcadlí strukturu předchozích MDT v datasetu (D-009). Číslo zasedání `NN` = poslední `PxxmdtNN` + 1 (P03 → `P03-mdt02`, P05 → `P05-mdt03`).

| Výstup | FHIR resource (ID) | Klíčové prvky |
|---|---|---|
| **Záznam MDT** | `Composition/Pxx-mdtNN` | `status` `preliminary` → `final`; `type` `mdt-typ-zaznamu#mdt-zaznam`; `category` = typ projednání (z `ServiceRequest.code`) + zaměření; `author` + `attester` (legal) = předseda; `custodian` `ORG-FN`; `event.detail` → CarePlan + CareTeam; **sekce jako v datasetu:** Projednaná otázka · Klinické zhodnocení · Léčebný záměr · Doporučený postup · Doplňující diagnostika · Klinická studie · Plánované re-MDT · Závěr MDT; navíc sekce **Varovné signály** (odkazy na DetectedIssue); extension `mdt-forma-zasedani`, `mdt-osetrujici-lekar`, `mdt-ucast-pacienta` |
| Doporučení | `CarePlan/Pxx-mdtNN-careplan` | `status=active`, `intent=plan`, `category` `mdt-lecebny-zamer` (kurativni / paliativni / odlozeno), `activity[].detail.code` `mdt-modalita` + `description`, `supportingInfo` → `ServiceRequest/Pxx-zad01` (R4 `basedOn` povoluje jen CarePlan, IRIS jinak vrací 400), `addresses` → Condition |
| Přítomní | `CareTeam/Pxx-mdtNN-careteam` | `participant[].role.text` + `member` (z konfigurace „kdo je přítomen“) |
| Úkoly | `Task/Pxx-mdtNN-task01…` | `basedOn` → CarePlan, `intent=order`, `owner`, `restriction.period.end` = termín, `description` |
| Red flags | `DetectedIssue/Pxx-mdtNN-rf01…` | `severity` high/moderate/low, `implicated[]` = **oba zdroje**, `detail`, `reference` = pasáž guidelines (text), `patient` |
| Vhodnost do studie | `ResearchSubject/Pxx-mdtNN-rs01` | `status=candidate`, `study` → `ResearchStudy/RKT-0n`; jen pokud komise potvrdí |
| Stav nominace | `Task/Pxx-zad01-task` (update) + `ServiceRequest/Pxx-zad01` (update) | `businessStatus` → `projednana` (nový kód), `status` → `completed` |
| ECOG zadaný lékařem (FR-P4) | `Observation/Pxx-ecog-caseNN` | LOINC 89247-1, `valueInteger`, `performer` = zadávající lékař, `note` „Zadáno při zařazení do MDT“; + `Provenance` (ruční zadání) |
| Předpokládaný záměr C/P (FR-P4) | `ServiceRequest/Pxx-zad01` (update) | extension `…/mdt-predpokladany-zamer`, `valueCodeableConcept` z `mdt-lecebny-zamer` (`kurativni` / `paliativni`) |
| Přesun mezi boardy (FR-P1) | `Task/Pxx-zad01-task` (update) | `restriction.period.start` = datum nového zasedání |
| Odkliknuté varování (FR-P4) | `DetectedIssue/Pxx-caseNN-wNN` | `mitigation[]` (`action.text` „Beru na vědomí“, `author`, `date`); v podkladu se zobrazuje dál (D-019) |
| Přepis diskuse (BON-3) | `DocumentReference/Pxx-mdtNN-prepis` | `type` text „Přepis diskuse MDT“, `content.attachment` (text, base64) |
| **Původ a potvrzení** | `Provenance/Pxx-mdtNN-prov` | `target` = vše výše; `agent[]`: `Device/mdt-copilot` (model Gemini, typ `assembler`) + `Practitioner` předseda (`verifier` / `attester`); `entity[]` (`role=source`) = citované zdroje; `recorded` |
| AI systém | `Device/mdt-copilot` (jednou při `iris_init`) | `deviceName` „MDT Copilot“, `version` = model |
| Označení AI obsahu | `meta.security` `AIAST` (`http://terminology.hl7.org/CodeSystem/v3-ObservationValue`) na resources s AI draftem | podle HL7 *AI Transparency on FHIR* (draft IG, **ověřit stav**) |
| PDF | `DocumentReference/Pxx-mdtNN-pdf` | `application/pdf` (base64 v `attachment.data`), `context.related` → Composition (R4 `relatesTo` jen na DocumentReference); vzniká při prvním `GET …/export.pdf` potvrzeného závěru |
| **FHIR export** | `Bundle` `type=document` | `Composition` jako 1. entry + zápis komise + resources, na které přímo odkazuje (pacient, lékaři, citované zdroje, studie); jde znovu nahrát `POST /Bundle` |

### 4.4 ID a idempotentní ingest

- **ID z datasetu zachováváme** (D-005). Sanitizace: `_` se mění na `-` (`P01-lab01-hb_f` → `P01-lab01-hb-f`) v `id`, `fullUrl` i ve všech `reference`; prázdné stringy se odstraní ([DATASET.md §6.2](DATASET.md#62-sanitizace-povinná)).
- Ingest posílá **transaction Bundle s `request.method = "PUT"`** a `request.url = "Type/id"`. Opakované spuštění data přepíše, nic se neduplikuje. Jeden bundle na pacienta (142–215 entries) + bundle studií + Questionnaire.
- Command `python manage.py ingest_dataset [--patients P03,P05] [--skip-vectors] [--dry-run] [--bundle-type batch]` čte z `DATASET_DIR` a po nahrání **ověří počty** proti [DATASET.md §2](DATASET.md#2-pacienti). Logika je v `services/fhir/ingest.py`, detail v [DATASET.md §6.1](DATASET.md#61-postup-python-managepy-ingest_dataset-úkol-t-101).
- Index `ID → ResourceType` pro resolver citací je funkce `services/fhir/ids.py` `resource_type_for_id` (podle konvence ID, žádná tabulka). Tamtéž `parse_evidence_id` pro validaci a rozklad citací (§5.2, §5.3).
- Nové resources z aplikace dodržují konvenci datasetu (`Pxx-mdtNN-…`, viz §4.3), aby šly citovat a dohledat stejně.

### 4.5 Vektorové tabulky (IRIS SQL, namespace FHIRSERVER)

```sql
CREATE TABLE MDT.EvidenceChunk (
    EvidenceId   VARCHAR(200),        -- "P03-img03#2"  (ID zdroje # pořadí odstavce)
    PatientId    VARCHAR(16),         -- "P03"  (POVINNÝ filtr při hledání)
    ResourceType VARCHAR(64),         -- DocumentReference | DiagnosticReport | Composition | ServiceRequest
    ResourceId   VARCHAR(128),        -- "P03-img03"
    ChunkIndex   INTEGER,             -- číslo odstavce = část za "#" (services/ai/text.py)
    CharStart    INTEGER,             -- offset odstavce v resource_text() (zvýraznění v UI)
    CharEnd      INTEGER,
    DocDate      DATE,
    Title        VARCHAR(500),        -- type.text / code.text / název záznamu MDT
    Department   VARCHAR(200),        -- category[].text (A-ONK, RDG, PAT-B…)
    Text         VARCHAR(10000),
    EmbeddingModel VARCHAR(100),      -- "gemini:gemini-embedding-001@1536" | "mock:hashed@1536"
    Embedding    VECTOR(DOUBLE, 1536)
);

CREATE TABLE MDT.GuidelineChunk (
    EvidenceId   VARCHAR(50),         -- "KRC-2.4"
    GuidelineSet VARCHAR(10),         -- KRC | PRS | PLI | OBC | EXT (externí zdroje prahů, D-016)
    Title        VARCHAR(300),        -- "Restaging před resekcí"
    Source       VARCHAR(200),        -- "Rakathon 2026 – výtah (inspirováno ESMO a národními standardy)"
    Region       VARCHAR(20),         -- "CZ"  (konzultace: zdroj a region postupu)
    IcdPrefixes  VARCHAR(100),        -- "C18,C19,C20" | "C50" | "C34" | "*" (OBC)
    Text         VARCHAR(5000),
    Url          VARCHAR(500),        -- odkaz na zdroj u EXT-… (T-504), jinak NULL
    EmbeddingModel VARCHAR(100),
    Embedding    VECTOR(DOUBLE, 1536)
);

CREATE TABLE MDT.TrialCriterion (
    EvidenceId   VARCHAR(50),         -- "RKT-03/V3"
    StudyId      VARCHAR(16),         -- "RKT-03"
    Kind         VARCHAR(10),         -- inclusion | exclusion   (Group.characteristic.exclude)
    Text         VARCHAR(2000),
    EmbeddingModel VARCHAR(100),
    Embedding    VECTOR(DOUBLE, 1536)
);
-- indexy: EvidenceChunk (PatientId), (ResourceId) · GuidelineChunk (GuidelineSet) · TrialCriterion (StudyId)
```

```sql
-- hledání v datech pacienta (grounding = WHERE PatientId)
SELECT TOP 8 EvidenceId, Text, VECTOR_COSINE(Embedding, TO_VECTOR(?, DOUBLE)) AS Score
FROM MDT.EvidenceChunk
WHERE PatientId = ? AND EmbeddingModel = ?
ORDER BY Score DESC
```

- **Implementace (T-102, T-203):** tabulky a dotazy `services/iris/vector_store.py`, plnění `services/iris/indexing.py`, příkazy `ingest_dataset` (FHIR + vektory) a `search_iris` (ruční ověření).
  - Řádky: `MDT.EvidenceChunk` 665 (555 odstavců zpráv a nálezů + 81 sekcí záznamů MDT + 29 odstavců nominací; P03 má 85), `MDT.GuidelineChunk` 42 + 13 `EXT-…` (T-504), `MDT.TrialCriterion` 45 kritérií v 6 studiích.
  - **Pseudonymizace embeddingů (NFR-3):** každý text, který jde do embedding API (odstavce, dotazy, tvrzení pro grounding), projde `services/ai/pseudonymize.py`. U odstavců pacienta se nahrazují i jména pacienta a lékařů (stejně jako v context builderu). V IRIS zůstává originál, protože na něm stojí offsety pro zvýraznění.
  - **Schéma se doplňuje samo:** `ensure_schema()` (volá ho `ingest_dataset`) založí chybějící tabulky a chybějící sloupce přidá přes `ALTER TABLE … ADD` (např. `Url` z T-504), data zůstanou. Zahodit a založit znovu: `--recreate-vector-tables`.
  - **`EmbeddingModel`:** hledá se jen mezi řádky aktuálního modelu (`provider:model@dim`), takže se vektory z mocku a z Gemini nikdy nesmíchají. Po přepnutí `AI_PROVIDER` nebo `EMBEDDING_MODEL` je potřeba reindex: `ingest_dataset --skip-fhir`. Dokud neproběhne, hledání vrací prázdný seznam a loguje varování.
  - **API pro ostatní úkoly:**
    - `search_evidence(pid, q, top_k)` → řádky se `Score`, `EvidenceId` se rovnou hodí do `PatientContext.render(highlight=…)` (T-105). Bez `pid` vyhodí `ValueError` (NFR-2);
    - `search_guidelines(q, guideline_sets)`, `search_trial_criteria(q, study_ids)` (B2, T-204);
    - `get_evidence_chunks(pid, resource_id)`, `get_guideline(id)`, `get_trial_criterion(id)` pro resolver citací (T-104);
    - `similarity(claim, evidence_ids)` = kosinová podobnost s citovanými zdroji pro grounding v2 (T-213, `FACT_VERIFICATION`). Resource bez `#` porovná s nejlepším odstavcem, ID bez textu (např. `Observation`) ve výsledku chybí;
    - `indexing.index_patient(pid)` přečte pacienta z IRIS FHIR a přepočítá jeho odstavce. **Volat po zápisu závěru komise (T-209)**, aby šel `Composition/Pxx-mdtNN` vyhledat.
  - **Testy bez IRIS:** fixture `fake_iris` (`services/conftest.py`) nahradí `services.iris.db.connect` in-memory IRIS SQL (podmnožina SQL včetně `VECTOR_COSINE`, hlídá zavírání spojení), funguje i pro `services/ai/guidelines.py:load_guidelines`. Proti živému IRIS (schéma `MDTTEST`): `pytest -m integration services/iris`.

- **Chunking:** texty jsou krátké (93 dokumentů, max ~1 900 znaků), takže **1 odstavec = 1 chunk**. Kvůli zvýraznění v UI ukládáme i offset v textu.
  - **Jediný zdroj číslování odstavců** je `services/ai/text.py`: `resource_text(resource)` + `split_paragraphs(text)` (nebo `resource_paragraphs(resource)`). Používá ho context builder (T-105) a **musí** ho použít i `MDT.EvidenceChunk` (T-102) a resolver citací (T-104). Jinak `P03-img03#2` ukáže v každé části aplikace na jiný text.
  - Text resource: DocumentReference `content[].attachment.data`, DiagnosticReport `presentedForm[].data` (bez něj `conclusion`), Composition sekce jako `Název: text`, ServiceRequest otázka pro MDT (`#1`) + poznámky `note[]`.
  - Nový odstavec začíná za prázdným řádkem a na řádku s nadpisem (`Závěr:`, `Nález:`, `Subjektivně:`, `OA:`…, regex `^[A-ZÁ-Ž][^:]{0,40}:`). Číslování je od 1. Na datasetu to dává 555 odstavců zpráv a nálezů (s Composition a ServiceRequest 665), nejdelší má 542 znaků.
- **Embeddingy:**
  - `gemini-embedding-001`, `output_dimensionality=1536`;
  - **L2 normalizovat** (pod 3072 dimenzí to Google vyžaduje);
  - `task_type`: `RETRIEVAL_DOCUMENT` pro chunky, `RETRIEVAL_QUERY` pro dotazy a `FACT_VERIFICATION` pro ověření tvrzení;
  - max 2 048 tokenů na vstup;
  - volat dávkově.
- Vkládání: `INSERT … VALUES (?, …, TO_VECTOR(?, DOUBLE))` s `str(list_of_floats)`; batch přes `executemany`. Embedduje se `Title: Text` (u kritérií jen `Text`).
- IRIS SQL používá `SELECT TOP n`, ne `LIMIT`. Parametry vždy přes `?`.

### 4.6 FHIR REST klient — pravidla a gotchas

- Hlavičky `Accept: application/fhir+json` a `Content-Type: application/fhir+json`, Basic auth.
- **Stránkování:** sledovat `link[relation=next]`; `_count=500` (pacient má max ~110 Observation).
- **Neznámé search parametry IRIS tiše ignoruje** (vrátí 200 se vším). Filtry ověřit testem.
- Search parametry se liší od názvů elementů (`recorded-date` vs. `recordedDate`). `Task` a `ImagingStudy` se hledají přes `patient`.
- Kódy: `Observation?patient=P03&code=http://loinc.org|718-7&_sort=date`.
- **`Patient/$everything`:** v IRIS 2026.2 **funguje** (P03: 190 resources včetně odkazovaných lékařů, organizace a studií, vše v jedné odpovědi). Nezná ale `_count` (vrátí ho jako `OperationOutcome` v entry se `search.mode = outcome`, takové entry je potřeba přeskočit). Aplikace zůstává u fallbacku `patient_everything` (paralelní searche přes typy z [DATASET.md §6.3](DATASET.md#63-čtení-za-běhu-context-builder)), který vrací jen resources pacienta.
- **Kontrola serveru (T-313):** `python manage.py iris_check` (po `ingest_dataset`, logika `services/fhir/capabilities.py`) vypíše markdown tabulku:
  - u každého search parametru, na kterém aplikace stojí (`patient` u 14 typů, `_id` i s čárkami, `code`, `subject`, `category`, `status`, `date`, `_tag`, `_sort`), se ptá hodnotou, která nemůže nic najít. Výsledek musí být 0, jinak IRIS parametr ignoruje a vrací cizí data. Povinné kontroly při selhání vrátí chybový kód;
  - dál ověří `Patient/$everything` (a srovná ho s fallbackem), jestli jsou nahrané profily mCODE IG a `$validate`.
  - **Výsledek na IRIS for Health 2026.2 (16. 10. 21:45, @Seb):** všechny povinné kontroly prošly, žádný parametr z allowlistu IRIS neignoruje. P03 má o 11 resources víc než dataset, protože na Sebově stroji už je potvrzený závěr `P03-mdt02` (T-209).

    | Kontrola | Výsledek | Detail |
    |---|---|---|
    | `metadata` | ✓ ok | FHIR 4.0.1, InterSystems IRIS for Health IRIS for UNIX (Ubuntu Server LTS for x86-64 Containers) 2026.2 (Build 221U) Fri Jun 26 2026 09:58:52 EDT [Health:11.1.0] |
    | `Condition?patient` | ✓ ok | 0 pro nesmysl, 5 pro {'patient': 'P03'} (celkem 31) |
    | `DocumentReference?patient` | ✓ ok | 0 pro nesmysl, 8 pro {'patient': 'P03'} (celkem 53) |
    | `DiagnosticReport?patient` | ✓ ok | 0 pro nesmysl, 12 pro {'patient': 'P03'} (celkem 78) |
    | `ImagingStudy?patient` | ✓ ok | 0 pro nesmysl, 4 pro {'patient': 'P03'} (celkem 29) |
    | `Observation?patient` | ✓ ok | 0 pro nesmysl, 85 pro {'patient': 'P03'} (celkem 578) |
    | `MedicationRequest?patient` | ✓ ok | 0 pro nesmysl, 5 pro {'patient': 'P03'} (celkem 25) |
    | `MedicationAdministration?patient` | ✓ ok | 0 pro nesmysl, 32 pro {'patient': 'P03'} (celkem 152) |
    | `Procedure?patient` | ✓ ok | 0 pro nesmysl, 3 pro {'patient': 'P03'} (celkem 17) |
    | `QuestionnaireResponse?patient` | ✓ ok | 0 pro nesmysl, 2 pro {'patient': 'P03'} (celkem 12) |
    | `ServiceRequest?patient` | ✓ ok | 0 pro nesmysl, 1 pro {'patient': 'P03'} (celkem 6) |
    | `Task?patient` | ✓ ok | 0 pro nesmysl, 5 pro {'patient': 'P03'} (celkem 10) |
    | `Composition?patient` | ✓ ok | 0 pro nesmysl, 3 pro {'patient': 'P03'} (celkem 15) |
    | `CarePlan?patient` | ✓ ok | 0 pro nesmysl, 2 pro {'patient': 'P03'} (celkem 8) |
    | `CareTeam?patient` | ✓ ok | 0 pro nesmysl, 2 pro {'patient': 'P03'} (celkem 8) |
    | `Observation?_id` | ✓ ok | 0 pro nesmysl, 2 pro {'_id': 'P03-ecog01,P03-vaha01'} (celkem 578) |
    | `Practitioner?_id` | ✓ ok | 0 pro nesmysl, 1 pro {'_id': 'LEK-P03-01'} (celkem 57) |
    | `Observation?code` | ✓ ok | 0 pro nesmysl, 6 pro {'patient': 'P03', 'code': 'http://loinc.org|2039-6'} (celkem 578) |
    | `Observation?subject` | ✓ ok | 0 pro nesmysl, 85 pro {'subject': 'Patient/P03'} (celkem 578) |
    | `Observation?category` | ✓ ok | 0 pro nesmysl, 76 pro {'patient': 'P03', 'category': 'laboratory'} (celkem 578) |
    | `Observation?status` | ✓ ok | 0 pro nesmysl, 85 pro {'patient': 'P03', 'status': 'final'} (celkem 578) |
    | `Observation?date` | ✓ ok | 0 pro nesmysl, 85 pro {'patient': 'P03', 'date': 'ge2000-01-01'} (celkem 578) |
    | `Patient?_tag` | ✓ ok | 0 pro nesmysl, 6 pro {'_tag': 'https://rakathon.example.org/fhir/tag|fiktivni-data'} (celkem 6) |
    | `_id=a,b (OR)` | ✓ ok | 2 resources, čekáno 2 |
    | `Observation?_sort=-date` | ✓ ok | data: 2026-10-05, 2026-09-21, 2026-08-24, 2026-07-13, 2026-06-01, 2026-04-28 |
    | `Patient/$everything` | ℹ info | funguje: 190 resources (fallback 170, chybí 0, navíc 20) |
    | `mCODE IG` | ℹ info | nenahraný (profily mCODE v IRIS nejsou; BON-5 / T-307) |

  **mCODE v exportu (T-307):** `services/fhir/mcode.py:apply_profiles` doplní kopiím resources v `export.fhir.json` `meta.profile` mCODE (cancer-patient, primary / secondary cancer condition podle C77–C79, tnm-stage-group, tumor-marker-test, ecog-performance-status, cancer-related medication administration / request a surgical procedure) a kódy LOINC tam, kde je význam jistý: skupina stadia 21908-9 (klinicky) / 21902-2 (patologicky), ER 16112-5, PR 16113-3, HER2 48676-1. Ostatní biomarkery mají profil a původní text (kódy doplnit po ověření). IRIS takový Bundle přijme (`POST /Bundle` → 201, ověřeno živě); `$validate` proti mCODE IG čeká na import IG (stretch).
    | `$validate` | ℹ info | funguje, ECOG Observation bez chyb |

  - Parametr, který IRIS ignoruje, je potřeba vyřadit z allowlistu MCP `fhir_query` (§4.7) a nepoužívat v kódu.
- Validace: chyba 400 vrací `OperationOutcome`, logovat `issue[].details.text`.
- **Community Edition má limit spojení.** DB-API spojení vždy zavírat (`try/finally` nebo context manager v `services/iris/db.py`) a nedržet je přes request.

### 4.7 MCP server nad IRIS (SHOULD)

- `WEB_Template/backend/mcp_server.py` (FastMCP, podle kitu `Tutorials/5-ai/mcp-examples`) s nástroji:
  - `get_patient_context(patient_id)`;
  - `fhir_query(resource, params)`;
  - `search_evidence(patient_id, query)`;
  - `search_guidelines(query, icd10)`.
- Copilot ho může používat interně. V pitchi ukážeme, že stejné nástroje fungují i v libovolném MCP klientovi.
- Read-only: jen `SELECT` a jen `GET`, dedikovaný IRIS uživatel s právy pro čtení.
- **Implementace (T-308):** `fastmcp` 4, nástroje v `services/mcp/server.py` (obyčejné funkce, jdou volat i z Pythonu), spouštění `mcp_server.py`.
  - Nástroje (všechny s anotací `readOnlyHint`):
    - `get_patient_context(patient_id, focus)` = text kontextu z T-105 (`build_context().render()`); `focus` seřadí nejrelevantnější odstavce vektorovým hledáním;
    - `search_evidence(patient_id, query, top_k)`, `search_guidelines(query, icd10, top_k)`, `search_trial_criteria(query, study_id, top_k)` nad `MDT.*` (§4.5);
    - `get_evidence(evidence_id)` = zdroj citace: odstavec s offsety, resource, pasáž nebo kritérium;
    - `fhir_query(resource_type, params)` = FHIR search s **allowlistem typů a parametrů** (`_id`, `patient`, `subject`, `code`, `category`, `date`, `status`, `_sort`, `_tag`). Jiné parametry odmítne, protože IRIS by je tiše ignoroval a vrátil všechno. Vrací nejvýš 100 resources.
  - **Ochrana údajů (NFR-3):** výstup jde do cizího LLM klienta, proto se u `Patient` a `Practitioner` zahodí jména, kontakty, adresy, identifikátory a datum narození, base64 přílohy se neposílají a všechny texty projdou `services/ai/pseudonymize.py`. Mimo fiktivní dataset smí být klientem jen schválený LLM (EU, DPA), stejně jako u Gemini (§5.7).
  - Spuštění a připojení klienta (dev stack musí běžet):

    ```bash
    docker compose -f docker-compose.dev.yml exec -T backend python mcp_server.py                  # stdio
    claude mcp add mdt-iris -- docker compose -f WEB_Template/docker-compose.dev.yml exec -T backend python mcp_server.py
    docker compose -f docker-compose.dev.yml exec backend python mcp_server.py --http --port 8765  # HTTP /mcp, jen lokálně
    ```

    Claude Desktop (`claude_desktop_config.json`): `{"mcpServers": {"mdt-iris": {"command": "docker", "args": ["compose", "-f", "<repo>/WEB_Template/docker-compose.dev.yml", "exec", "-T", "backend", "python", "mcp_server.py"]}}}`.

### 4.8 Pro AI agenty v týmu

- Skills z kitu (`iris-fhir`, `iris-vector-search`, `iris-sql-python`, `iris-ai-agents`, `iris-environment`) jsou v `.claude/skills/` (T-011, MIT, kit V2 commit `3ebaee2`). Každý začíná blokem **„V MDT Copilot“**, který má přednost před textem kitu: odkazuje na naše implementace (`services/fhir`, `services/iris`, `services/mcp`) a vypisuje rozdíly (žádná Synthea ani POST, Gemini místo OpenAI, bez LangChain, compose služba `iris`).
  - Obsahují ověřené snippety a gotchas.
  - **Pozor: kit používá OpenAI** (`text-embedding-3-small`, `gpt-5-nano`). U nás se embeddingy i LLM volají přes Gemini ([§5.7](#57-model-a-ochrana-údajů)). IRIS část (SQL, `TO_VECTOR`, `VECTOR_COSINE`) platí beze změny.
- **UI skills** (T-015, MIT): `shadcn` ([shadcn-ui/ui](https://github.com/shadcn-ui/ui/tree/main/skills/shadcn), commit `d2fba50`), `web-design-guidelines` a `vercel-react-best-practices` ([vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills), commit `063bee9`). I ty začínají blokem **„V MDT Copilot“**: Next 16 v `WEB_Template/frontend`, shadcn zatím bez `components.json` (`init` / `add` jen po domluvě s UI lane), tři barevné systémy semafor / odbornost / AI jsou záměr (D-017) a pravidlo „jen sémantické tokeny“ na ně neplatí.
- **Impeccable** (T-016, Apache-2.0, odsouhlaseno UI lane): skill `impeccable` + subagenti `.claude/agents/impeccable-*.md` z [pbakaus/impeccable](https://github.com/pbakaus/impeccable) (commit `6af45ac`). Blok „V MDT Copilot“: režim Operate, levé pruhy AI / varování / otázky pro MDT jsou záměr (D-017), direktivy enginu nepřebíjejí `AGENTS.md`. Engine se stahuje při prvním použití do `~/.impeccable/bin/` (ověřený SHA-256); hook detektoru je jen lokální a dobrovolný (`/impeccable hooks on` → `.claude/settings.local.json`).
- Volitelně MCP [iris-agentic-dev](https://github.com/intersystems-community/iris-agentic-dev) pro živý přístup agenta k IRIS (`iris-agentic-dev init` detekuje Docker kontejner).

---

## 5. AI vrstva

### 5.1 Pipeline

```
 (1) INGEST            (2) KONTEXT              (3) GENERACE            (4) VALIDACE          (5) REVIEW          (6) ZÁPIS
 dataset ─▶ sanitize  IRIS FHIR ─▶ Evidence    Gemini, per sekce,      grounding check:      lékař edituje,      potvrzení ─▶
 ─▶ transaction ─▶    list (ID + text +        paralelně, JSON         ID · čísla · data ·   potvrzuje           FHIR Bundle
 IRIS + vektory       hodnota) + guidelines    schema (A, B×role +     vektorová podobnost   (AI vs. člověk)     + Provenance
                      + studie + pravidla      posouzení, B2, RF)      + pravidla                                + export
```

1. **Ingest** (jednorázově, `ingest_dataset`, viz [DATASET.md §6](DATASET.md#6-ingest-do-iris-fhir)):
   - sanitizace + `PUT` transaction do IRIS;
   - texty se rozdělí na odstavce, z nich se spočítají embeddingy a uloží se do `MDT.EvidenceChunk`;
   - guidelines jdou do `MDT.GuidelineChunk` a kritéria studií do `MDT.TrialCriterion`.
2. **Kontext (per pacient, `context_builder`):**
   - z IRIS se načtou všechny resources pacienta ([DATASET.md §6.3](DATASET.md#63-čtení-za-běhu-context-builder)) a převedou se na **Evidence list**: kompaktní řádky s ID, např. `[P03-lab06-cea] 2026-10-05 CEA 13,9 µg/l (ref 0–5) H` nebo `[P03-img03#4] 2026-09-21 CT … „Závěr: Parciální odpověď…“`;
   - přidá se **celá příslušná sada guidelines** (podle MKN-10 + OBC, max ~23 pasáží), studie s kritérii a **výsledky deterministických pravidel** ([§5.4](#54-red-flags));
   - celek má desítky tisíc tokenů a vejde se do jednoho callu (D-010);
   - IRIS Vector Search pro každou sekci seřadí nejrelevantnější odstavce na začátek a označí je;
   - před odesláním proběhne **pseudonymizace** ([§5.7](#57-model-a-ochrana-údajů)).
   - **Implementace (T-105):** `services/ai/context_builder.py`.
     - `build_context(pid)` čte FHIR přes `services/fhir/client.py`: pacienta, referencované `Practitioner` a `Organization` a studie. Guidelines bere z IRIS `MDT.GuidelineChunk` přes `services/ai/guidelines.py:load_guidelines`. Když tabulka chybí, vyhodí `GuidelinesUnavailable` (nahrává ji T-203; `parse_guidelines()` je připravený parser markdownu).
     - Vrací `PatientContext`:
       - `render(highlight=[…])` = text pro LLM, řádky `[ID] datum text` seskupené podle témat, za nimi guidelines a studie;
       - `allowed_ids` = povolené citace;
       - `source_text(id)` = text zdroje pro grounding validátor;
       - `facts` = pohlaví, věk, datum MDT, otázka, diagnózy (pro hlavičku D-018);
       - `rule_results` = řádky z deterministických pravidel.
     - Výběr sady guidelines a studií je v `services/rules/guideline_sets.py`. Pseudonymizace (`services/ai/pseudonymize.py`) běží nad každým řádkem a `pseudonymized` je počet náhrad pro audit.
     - Kontext P03 má 171 resources, 256 řádků a ~41 tisíc znaků (~12 tisíc tokenů).
3. **Generace:**
   - jeden Gemini call na sekci: A, B (každá přítomná role včetně posouzení role), B2, red flags (LLM část) a otázky; běží **paralelně** (ThreadPool);
   - teplota 0–0.2, **strukturovaný výstup** (`response_mime_type=application/json` + `response_schema` = pydantic schéma z [§8](#8-datové-kontrakty-fe--be));
   - parametry z konfigurace: úroveň detailu, role, jazyk;
   - **rozhraní pro job (T-107 ↔ T-106):** `services/ai/brief.py: generate_brief(case: MdtCase, config: dict, progress: Callable[[int], None]) -> dict`. Vrací validní `Brief` (§8.2), `config` je snapshot `BriefConfig` (§8.5), `progress(0–100)` se ukládá do jobu. Každé LLM volání se loguje přes `LlmCallLog.record(purpose, result)` (`apps/copilot/models.py`). Výjimka = job ve stavu `error` s textem chyby. Registr generátorů je `apps/copilot/jobs.py: GENERATORS`.
4. **Validace (grounding validátor, `services/ai/grounding.py`):** viz [§5.3](#53-anti-halucinace--grounding-validátor).
5. **Review:** UI zobrazí draft s odlišením AI. Lékař edituje a potvrzuje po sekcích nebo celý závěr.
6. **Zápis:** potvrzení vytvoří FHIR transaction do IRIS ([§4.3 výstupy](#výstupy-zápis-komise-do-iris-jeden-transaction-bundle)) a pak export PDF a FHIR document Bundle.

### 5.2 Evidence ID a citace

- **Formát** = ID z datasetu (D-006):

  | Formát | Příklad | Co znamená |
  |---|---|---|
  | `Pxx-…` | `P03-ecog03` | strukturovaný údaj / celý resource |
  | `Pxx-…#n` | `P03-img03#4` | n-tý odstavec textu, číslováno od 1 podle `services/ai/text.py` ([§4.5](#45-vektorové-tabulky-iris-sql-namespace-fhirserver)) |
  | `KRC-2.4` | `KRC-2.4` | pasáž guidelines |
  | `RKT-03` / `RKT-03/V3` | `RKT-03/V3` | studie / kritérium |
  | `EXT-…` | `EXT-EMA-DPD-2020` | externí zdroj prahu (D-016); jen pro pravidla semaforu, nikdy pro fakta pacienta. **Katalog ID (13):** `WEB_Template/backend/services/iris/data/external_sources.json` (přepis docs/POZADAVKY_LEKARE.md §5.3, §6.1, §13), v IRIS `MDT.GuidelineChunk` se sadou `EXT` a `Url` |

  Citace pro guidelines a kritéria studií ukazují na znění guideline nebo studie. Faktům pacienta se vždy cituje ID pacienta.
- LLM dostane **jen povolená ID** (z evidence listu) a smí citovat **pouze je**.
- Resolver `GET /api/evidence/?id=<EvidenceId>`:
  1. podle prefixu najde resource v IRIS (`P03-img03` → `DiagnosticReport/P03-img03`) přes index `ID → ResourceType`, který vznikne při ingestu;
  2. vrátí typ, datum, autora (`LEK-…` + odbornost), celý text se zvýrazněným odstavcem, nebo hodnotu s referenčním rozsahem;
  3. u `Observation` přidá i zdrojový dokument z `derivedFrom`.

### 5.3 Anti-halucinace — grounding validátor

Každé tvrzení (`claim`) z LLM projde kontrolami:

1. **Citace existuje:** každé `citations[i]` je v množině povolených ID. Jinak `verification = "unverified"`.
2. **Čísla sedí:** čísla a jednotky v textu tvrzení (normalizace desetinné čárky, `g/l` ↔ `g/L`, `µg/l`) se musí vyskytovat v citovaném zdroji. Jinak `unverified`.
3. **Data sedí:** data v tvrzení (ISO i „21. 9.“) existují v citovaných zdrojích.
4. **Sémantická podobnost (IRIS Vector Search):** embedding tvrzení (`FACT_VERIFICATION`) se porovná s embeddingem citovaného odstavce přes `VECTOR_COSINE`. Pod prahem je výsledek `unverified`. Práh nastavit podle evalu, výchozí 0,55.
5. **Chybějící údaje:** deterministický checklist pro sekci (OBC-1.1 + povinné biomarkery podle diagnózy, viz [§5.4](#54-red-flags)). Co nemá evidenci nebo má hodnotu „nevyšetřeno“, doplní se jako `kind: "missing"`, i když ho LLM nezmínil.
6. **UI:** `unverified` tvrzení se zobrazí s varováním (nebo se skryjí; přepínač `hide_unverified`). Cíl pro demo je **0 neověřených tvrzení**.

Metriky z validátoru (podíl ověřených tvrzení) jdou do evalu ([§5.8](#58-evaluace)) a do pitche.

**Implementace (T-106, T-213):**

- `services/ai/grounding.py` dělá body 1–4 a pro bod 5 jen kontroluje citace. Čísla porovnává s desetinnou čárkou i tečkou, bere data ISO i ve tvaru „21. 9.“ a čísla uvnitř tokenů (S3, cT3) ignoruje. Bod 4 volá `services/iris/vector_store.py:similarity` a používá `GROUNDING_MIN_SIMILARITY` (výchozí `0.55`); chybějící vektor nebo nedostupné IRIS znamená `unverified`. Bod 4 běží jen u tvrzení, jejichž **všechny** citace mají vektor (odstavce `#n`, textové zprávy `DocumentReference` / `DiagnosticReport` / `Composition` / `ServiceRequest`, pasáže guidelines, kritéria studií). Strukturovaná data (`bm`, `tnm`, `dg`, `proc`, ECOG, labs) vektor nemají a stačí jim body 1–3 (Q23). Bod 4 se přeskočí i u tvrzení, která sestavil kód (`_computed`, např. RECIST), a odvozená čísla (`_derived`, např. % změny SLD) se v bodě 2 nekontrolují. Důvody neověření posílá v `_grounding`, ty se před uložením odstraní. `kind: "missing"` potřebuje pouze platnou citaci.
- `services/ai/brief.py:generate_brief(case, config, progress)` je generátor pro joby z T-107.
  - Hlavička (D-018), časová osa, chybějící údaje (z T-502, přeskočené jako „Chybí (přeskočeno lékařem)“) a red flags jsou deterministické z FHIR.
  - Souhrn píše Gemini (`prompts/summary.md` + pravidla zkratek z T-509), souběžně s RF-LLM.
  - Když LLM selže nebo běží mock, nastoupí souhrn z dat (NFR-5).
  - Na P01–P06 vychází 0 neověřených tvrzení.

### 5.4 Red flags

**Hybrid: deterministická pravidla (`services/rules/red_flags.py`) + LLM detekce rozporů.**

- Každý flag má `severity`, `title`, `description`, **≥ 2 citace** (oba zdroje) a **citaci pasáže guidelines**.
- **Prahy jsou převzaté z guidelines datasetu** (OBC = konvence hackathonu) všude, kde guidelines číslo uvádějí. Prahy označené *(konvence týmu)* guidelines neuvádějí a tým je zvolil sám. Připomínky onkologů zatím nemáme (Q6).
- Úplné pokrytí 42 pasáží guidelines: [§5.11](#511-pokrytí-guidelines).
- Ruční průzkum a očekávané nálezy jsou v [DATASET.md §9](DATASET.md#9-vložené-nesrovnalosti--pracovní-hypotézy-týmu).

| Pravidlo | Podmínka | Severity | Guidelines |
|---|---|---|---|
| `RF-ECOG` | \|poslední ECOG lékaře − `samostatnost` z posledních PROMs\| ≥ 1 | moderate (≥ 2: high) | OBC-1.3 |
| `RF-PROMS` | symptom ≥ 7/10 v posledních PROMs, nebo nárůst ≥ 3 body mezi vyplněními *(konvence týmu)* | moderate | OBC-1.3 |
| `RF-TOX` | toxicita podle lékaře (`neuro`, `anem`) nižší než podle pacienta (`brneni` ≥ 5 *(konvence týmu)* nebo popis omezení instrumentálních činností: knoflíky, psaní, držení předmětů) | high | KRC-3.2, OBC-1.3 |
| `RF-STALE` | poslední zobrazení (`DiagnosticReport` RAD) starší než **42 dní** k datu MDT (`Task.restriction.period.start`); u plánované resekce jater chybí CT hrudníku, břicha a pánve **nebo MR jater s hepatospecifickou k. l.** ne starší než 4–6 týdnů | moderate (resekce: high) | OBC-1.2, KRC-2.4 |
| `RF-MISSING` | biomarker s hodnotou /nevyšetřeno\|probíhá\|nedostupn/; povinné podle dg.: C18 → RAS, BRAF, MMR/MSI · C50 HR+/HER2− při progresi → ESR1, PIK3CA/AKT1/PTEN, gBRCA · C34 neskvamózní → EGFR, ALK, PD-L1; dále checklist OBC-1.1 | moderate | OBC-1.1, KRC-1.1, PRS-1.3, PLI-1.3 |
| `RF-MED` | PROMs `leky-mimo` není „nic“ a lék / doplněk / bylina chybí v medikaci; známé interakce (třezalka + CYP3A substrát, např. PARPi) | moderate (interakce: high) | P05-doc03 |
| `RF-NEWSYMPTOM` | PROMs `nove-obtize` obsahuje nový symptom (bolest kosti, neurologický, dušnost) a poslední zpráva na něj nereaguje (LLM) | high | PRS-4.2 |
| `RF-LAB` | Hb pokles ≥ 20 g/l nebo < 100, < 80: high *(konvence týmu)*; vzestup markeru ≥ 25 % proti nadiru *(konvence týmu)* = důvod k časnějšímu zobrazení, **nikdy „progrese“** (PRS-4.2); Na pod `referenceRange` (v datasetu 136 mmol/l) a klesá → vyšetřit SIADH (osmolalita séra a moči, natriurie) a upravit před léčbou (PLI-3.2); glykémie > 10 mmol/l při kortikoidech u DM *(konvence týmu)*; LVEF pokles ≥ 10 bodů nebo < 50 % | moderate / high | PLI-3.2, OBC-3.1, PRS-3.4, PRS-4.2 |
| `RF-WEIGHT` | úbytek hmotnosti ≥ 5 % za 6 měsíců (`vaha` + PROMs `hmotnost`) nebo pokles albuminu | moderate | OBC-2.3 |
| `RF-GERI` | věk ≥ 70 (extension `vek-k-datu-mdt`) a v dokumentaci chybí G8 / geriatrický screening | low | OBC-2.2 |
| `RF-LESION` | `Condition.verificationStatus = provisional` nebo zobrazení uvádí „nejasné / nelze vyloučit / k dořešení“ bez následné histologie | high | OBC-1.4, PLI-1.2 |
| `RF-GENETIC` | indikace genetického poradenství (rodinná anamnéza v textu, BRCA z NGS nádoru bez germinálního testu) nesplněna | moderate | OBC-2.4, PRS-1.3, PRS-1.4 |
| `RF-NOMINATION` | údaj v nominaci (`ServiceRequest.note`: ECOG, LVEF, toxicita) neodpovídá poslednímu strukturovanému měření; při duplicitě malignit nominace neuvádí všechny nádory | moderate | OBC-1.1, OBC-1.4 |
| `RF-TNM` | více `tnm` Observation se stejným typem a odlišným stadiem | moderate | OBC-1.1 |
| `RF-IDENTITY` *(konzultace)* | dokument nesedí k pacientovi: strana těla (vlevo/vpravo vs. `Condition.bodySite`), pohlaví, věk, datum mimo časovou osu | high | — |
| `RF-PRIOR-PROC` *(konzultace)* | předchozí výkon v oblasti plánované operace / RT, implantát (port, stent), alergie: informační flag pro chirurga a radiačního onkologa | low (info) | — |
| `RF-DATAQUALITY` *(konzultace)* | data mimo pořadí, nesoulad jednotek, duplicitní nálezy, `Observation` bez `derivedFrom` (mezera v dohledatelnosti) | low | — |
| `RF-PALIATIVE` | pokročilé onemocnění a zároveň symptom ≥ 7/10, zhoršení ECOG (lékař nebo pacient) nebo progrese, a v dokumentaci chybí zapojení paliativního týmu | moderate | OBC-2.1 |
| `RF-ROLES` | v přítomných rolích (`roles_present`) chybí role, kterou guidelines vyžadují: resekabilita jaterních metastáz → hepatobiliární chirurg + radiolog (KRC-2.1); NSCLC st. III → hrudní chirurg, radiační onkolog, klinický onkolog, pneumolog, radiolog (PLI-2.1); výsledek NGS → molekulární tumor board (PRS-1.4) | moderate | KRC-2.1, PLI-2.1, PRS-1.4 |
| `RF-STEROID` | kortikoid bez plánu snižování dávky, nebo bez symptomatického edému | low | OBC-3.1, PRS-3.3 |
| `RF-LLM` | LLM porovná páry zdrojů (zpráva vs. lab, zpráva vs. PROMs, nominace vs. data) a vrátí rozpory s citacemi; prochází validátorem | podle LLM | — |

Výstup se před potvrzením ukládá v draftu a po potvrzení jako `DetectedIssue` v IRIS.

**Implementace (T-202):**

- `services/rules/red_flags.py`:
  - `evaluate(resources, roles_present=None)` vrátí `RedFlag[]` ve tvaru §8.2, seřazené podle závažnosti. `id` je stabilní (`RF-ECOG:P03-ecog03`) a hodí se pro `acknowledged_warnings` i `DetectedIssue`.
  - Deterministické flagy mají `verification = "verified"`, citace jsou ID z datasetu včetně odstavců (`P03-img03#1`) a pasáž guidelines je vždy ze sady pacienta.
  - Prahy jsou konstanty na začátku souboru; konvence týmu jsou v popisu flagu označené.
  - `RF-ROLES` se vyhodnocuje jen s `roles_present` z konfigurace.
  - Pravidla z konzultace (T-312):
    - `RF-IDENTITY` kontroluje stranu těla u spojení „karcinom/nádor + strana + orgán“, kvadrant prsu a pohlaví;
    - `RF-PRIOR-PROC` je informační, při zařazení se neodklikává;
    - `RF-DATAQUALITY` hlídá hodnotu bez `derivedFrom`, nesoulad jednotek, datum po MDT a duplicity.

    Věk v textu deterministicky kontrolovat nejde (zmínky jsou o příbuzných), řeší ho `RF-LLM`.
- `services/rules/alerts.py:header_alerts(resources)` vrátí `Claim[]` pro `header.alerts` (FR-A4): alergie (PROMs i zprávy sloučené), implantáty, předchozí operace a radioterapie s citacemi.
- `build_context()` pravidla spustí nad stejnými resources: `ctx.red_flags` a řádky v `ctx.rule_results` (sekce „Výsledky deterministických pravidel“ v kontextu).
- `services/ai/red_flags_llm.py`:
  - `detect_llm_red_flags(ctx, provider)` (prompt `services/ai/prompts/red_flags.md`) hledá jen další rozpory;
  - citace mimo `ctx.allowed_ids` nebo méně než dva zdroje vedou na `unverified`;
  - pasáž mimo sadu pacienta se zahodí.

Odkliknutí varování při zařazení pacienta (FR-P4) red flag z podkladu **neodstraní** (D-019). Přeskočený údaj se v podkladu zobrazí jako „Chybí (přeskočeno lékařem)“ a pravidla, která na něm závisí, jako „neposuzováno“.

### 5.5 B2 — podpora rozhodování a posouzení rolí

- **Výběr guidelines podle diagnózy** (MKN-10 primární `Condition`):
  - C50 → PRS;
  - C18–C20 → KRC;
  - C34 → PLI;
  - **OBC vždy**.

  Sada se pošle celá (≤ 23 pasáží). IRIS Vector Search ji seřadí podle relevance k otázce komise.
- **Možnosti léčby:**
  1. LLM vrátí **2–4 možnosti**, každou s citací pasáže (`PRS-3.3`) a s vazbou na fakta pacienta (citace);
  2. u každé možnosti uvede, co pro ni chybí (např. „EGFR neznámý, viz PLI-1.3“);
  3. **žádné pořadí jako doporučení** a žádné „doporučujeme“;
  4. mezi možnosti patří i **podpůrná péče**, když ji pacient splňuje: včasná paliativní péče (OBC-2.1), geriatrické (OBC-2.2) a nutriční vyšetření (OBC-2.3), genetické poradenství (OBC-2.4);
  5. u každé možnosti je semafor souladu se stavem pacienta (§5.9).
- **Klinické studie** (`RKT-01…06`):
  1. pro studie odpovídající diagnóze (a vždy RKT-05 podpůrná a RKT-06 basket) se vyhodnotí každé kritérium `Zn` / `Vn` (`met` / `not_met` / `unknown`) s citací faktu pacienta;
  2. celkový stav: `eligible` / `potentially_eligible` (chybí data) / `not_eligible`;
  3. u `unknown` doplnit, co je potřeba dodat;
  4. u P05 (už ve studii RKT-06) vyhodnotit pravidla protokolu (úprava dávky).
- **Posouzení role** (FR-B7, *konzultace*):
  - pro každou přítomnou roli se vyhodnotí otázka (chirurg: „kandidát resekce?“, radiační onkolog: „kandidát SRS / RT?“, onkolog: „kandidát další linie / studie?“) po kritériích s citacemi;
  - verdikt je `candidate` / `conditional` / `not_candidate` / `insufficient_data`;
  - vždy s poznámkou „podklad, rozhoduje lékař“.
- **RECIST 1.1 (BON-2):** pohled radiologa může obsahovat předběžný výsledek cílových lézí vypočtený z explicitně uvedených SLD v radiologických zprávách. LLM vytěží hodnotu, datum a Evidence ID; `services/rules/recist.py` deterministicky určí baseline, nadir a aktuální změnu. PR = pokles ≥ 30 % od baseline; PD = nárůst ≥ 20 % a zároveň ≥ 5 mm od nadiru; SD = ani PR ani PD; CR jen při SLD 0. Tvrzení cituje baseline i aktuální zprávu. Jde pouze o předběžné hodnocení cílových lézí; nové a necílové léze potvrzuje radiolog podle [RECIST 1.1](https://project.eortc.org/recist/recist-1-1/). Pokud jsou méně než dvě explicitní měření, výsledek nevznikne.
- **Otázky k diskusi:** 2–3 otázky odvozené z red flags, chybějících dat a otázky z nominace.
- **Implementace bloku B (T-201):** `services/ai/roles.py` + role jako data `services/ai/data/roles.yaml` (název, zaměření, otázka posouzení podle sady guidelines, modality semaforu).
  - Pro každou roli z `roles_present` jedno volání Gemini (`prompts/role_view.md`), všechna souběžně se souhrnem a RF-LLM.
  - Kritérium posouzení s citací mimo kontext dostane `unknown`.
  - Bez LLM (mock nebo chyba) vzniknou tvrzení z dat podle zaměření role a posouzení ze semaforu postupů, za které role odpovídá (red → `not_candidate`, orange → `conditional`, šedá → `insufficient_data`; u radiologa pravidla stagingu). Podpůrná léčba verdikt onkologa netvoří.
- **Údaje podle diagnózy a katalog metod (FR-B8, FR-D5, T-506):** `services/ai/diagnosis_data.py` + data `services/ai/data/diagnosis_data.yaml` (docs/POZADAVKY_LEKARE.md §4 a §5.2).
  - Ke každé sekci odbornosti kód připojí údaje podle sady guidelines pacienta: KRC chirurg FLR, poslední dávka bevacizumabu, restaging; onkolog RAS / BRAF / MMR, neuropatie. PLI: chirurg ppoFEV1 / ppoDLCO / VO2max, pneumolog spirometrie a kouření, onkolog EGFR / ALK / ROS1 / PD-L1. PRS: onkolog ER / PR / HER2 / Ki-67 a LVEF, kardiolog trend LVEF. Údaje se přidají vždy, i když je LLM nezmínil, a nekrátí se podle detailu.
  - Chybějící údaj je `missing` s `expected_source` = pasáž, která ho vyžaduje (např. VO2max → PLI-3.1).
  - Sekce `modalities` („Léčebné metody a odborníci“): pro každou `mdt-modalita` ze semaforu kdo se musí vyjádřit, co má mít u sebe a které postupy ze sady guidelines k ní patří, s citací pasáží a faktů pacienta.
  - Obojí sestavuje kód (`_computed`), proto se přeskočí bod 4 groundingu. Body 1–3 platí.
- **Anamnéza (FR-A5, T-507):** `services/ai/anamnesis.py` vezme z odstavců `DocumentReference` nejnovější znění každé sekce (NO, OA, FA včetně „Léková anamnéza“, alergie, RA, GA, SA, „Anamnéza“) s citací odstavce. Do `INTAKE_ANAMNESIS_MAX_CHARS` (600) jde doslovně, nad limit shrnutí LLM s citacemi jen na tyto odstavce (fallback: první věta každé sekce + „…“). Sekce `anamnesis` běží v poolu souběžně s ostatními voláními. Doslovné znění otevře klik na citaci (přepínač `AnamnesisBlock` je volitelný UI krok).
- **Lung-RADS / Fleischner (BON-6, T-508):** `services/rules/scales.py:evaluate_scales(resources)` → `{scale, applicable, category, reason, patient_citations, rule_citation}` (`EXT-LUNGRADS-2022`, `EXT-FLEISCHNER-2017`). Lung-RADS jen u screeningového nízkodávkového CT plic (kategorie podle velikosti solidního uzlu), Fleischner jen u náhodného uzlu bez známého nádoru, ≥ 35 let a mimo screening (tabulka intervalů zatím ⚪). Výsledek je tvrzení v sekci radiologa a pneumologa; u všech 6 pacientů „nelze použít“ s důvodem. Imunosuprese se zatím nekontroluje.

### 5.6 AI zapisovatel (BON-3)

- **Dataset přepis neobsahuje**, proto:
  1. nahrajeme vlastní simulovanou diskusi komise k demo pacientovi (2–3 min, více mluvčích, audio `m4a`/`mp3`);
  2. případně napíšeme textový přepis.
- **Přepis:**
  - Gemini s audio vstupem (`gemini-3.8-flash`; v seznamu modelů je i `gemini-3.5-transcribe`, **ověřit**);
  - prompt: mluvčí (role), časové značky `MM:SS`, výstup jako JSON segmenty (`response_schema`);
  - limity: inline audio ≤ 20 MB na request, větší soubory přes Files API.
- **Výstup:**
  - draft `Decision` (rozhodnutí, zdůvodnění, úkoly s vlastníkem a termínem, re-MDT) s citacemi na segmenty přepisu (`P03-mdt02-prepis#12`);
  - přepis se uloží jako `DocumentReference/Pxx-mdtNN-prepis`.
- Vždy jen **draft**. Předseda edituje a potvrzuje.
- **Implementace (T-305):** `POST /api/mdt/cases/{cid}/scribe/` (předseda, lékař; multipart `audio` ≤ 20 MB, nebo JSON `{transcript}` „MM:SS mluvčí: text“ / `{segments}`) → job `scribe` → `services/ai/scribe.py:generate_scribe`.
  1. Audio přepíše `provider.transcribe` (Gemini, `Transcript`).
  2. Přepis se uloží jako `DocumentReference/{next_mdt_id}-prepis` (text/plain, úsek = odstavec, takže `#n` = n-tý úsek a resolver citací ho umí); vazba `context.related` na nominaci `ServiceRequest`, protože `Composition` vznikne až potvrzením.
  3. LLM (`ScribeDraft`) z přepisu a kontextu pacienta sestaví draft `Decision`. Citace mimo přepis a kontext se zahodí, úkol bez termínu dostane termín re-MDT (jinak MDT + 14 dní), `study_ids` jen `RKT-nn`, `transcript_ref` = ID přepisu.
  4. Bez LLM (mock) se nic nevymýšlí: závěr = poslední slovo předsedy s citací, úkoly prázdné.
  5. Potvrzený závěr zapisovatel nepřepíše (409). Živě s Gemini: nahrávka P03 (3:01) → 13 úseků a draft se 4 úkoly jako v `expected_decision` za 54 s.

### 5.7 Model a ochrana údajů

**Provider: Google AI Studio, Gemini API** (D-008). SDK `google-genai` (`from google import genai`).

**Rozhraní provideru** (`WEB_Template/backend/services/ai_service.py`, T-012). `get_ai_provider()` vrátí `GeminiProvider` nebo `MockAIProvider` podle `AI_PROVIDER`. Jiné providery nejsou, data smí jen do Gemini. `gemini` bez klíče spadne na mock a výsledek má `is_mock: true`.

- `generate(prompt, system_prompt=…, response_schema=PydanticModel)` vrátí dict:
  - `status`, `response` (text), `data`, `model`, `tokens_in`, `tokens_out`, `latency_ms`, `prompt_hash` (pro `LlmCallLog`);
  - `data` je vždy zvalidované pydantic schématem. Nevalidní nebo uříznutý výstup (`MAX_TOKENS`) vrátí `status: "error"`, nikdy `success`;
  - Gemini dostane system prompt v `system_instruction` a schéma jako `response_json_schema`. Schéma se nejdřív očistí na podmnožinu, kterou Gemini přijme (bez `const`, `default`, `pattern`, `minLength`, sourozenců `$ref`), a přidá se `propertyOrdering`. Omezení pak hlídá až validace pydantic.
- `embed(texts, task_type=…)` vrátí `EMBEDDING_DIM` čísel na text s L2 normalizací, po dávkách 100. Konstanty `TASK_RETRIEVAL_DOCUMENT`, `TASK_RETRIEVAL_QUERY`, `TASK_FACT_VERIFICATION`.
- `transcribe(audio, mime_type)` vrátí totéž co `generate`, `data` podle schématu `Transcript` (`segments[]`: `speaker`, `start` `MM:SS`, `text`). Audio nad 20 MB jde přes Files API.
- **Mock** je deterministický a bez sítě:
  - se schématem vrátí minimální validní instanci, nebo odpověď zaregistrovanou v `MockAIProvider(responses={"NázevSchématu": data})`;
  - `embed` vrací hashované bag-of-words vektory, takže podobné texty mají vyšší kosinovou podobnost (použitelné v testech groundingu);
  - živý test: `AI_LIVE_TESTS=1 pytest -m integration services/tests/test_ai_service.py`, s klíčem Gemini (free tier jen nad syntetickým datasetem, D-021).

| Účel | Model (výchozí) | Pozn. |
|---|---|---|
| Generace sekcí, red flags (LLM), B2 | **`gemini-3.8-flash`** (stable, doporučený pro nové projekty) | rychlost kvůli NFR-1 |
| Porovnání kvality v evalu | `gemini-4-argon` (flagship, 1M kontext) nebo `gemini-3.1-pro-preview` | rozhodne T-301 podle čísel |
| Levné pomocné úlohy | `gemini-3.5-flash-lite` | např. normalizace textu, klasifikace symptomů |
| Embeddingy | **`gemini-embedding-001`** @ 1536 + L2 normalizace | alternativa `gemini-embedding-2` (auto-normalizace, 8 192 tokenů, bez `task_type`) |
| Přepis audia | `gemini-3.8-flash` (audio vstup) | případně `gemini-3.5-transcribe` |

Model ID se mohou měnit. Před použitím ověřit na [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models) a držet je **jen v env** (`AI_MODEL`, …). **Testy a CI vždy na `AI_PROVIDER=mock`.**

**Podmínky Gemini API, které nás přímo ovlivňují:**

- **V EHP (tedy i v ČR) smí aplikace používat jen placené služby.** Bezplatný tier smí data používat ke zlepšování produktů a k lidské revizi a výslovně se do něj nemají posílat osobní údaje. Proto je nutné **zapnout billing v AI Studio** (Q9). **Výjimka týmu (D-021):** pro vývoj a demo nad syntetickým, veřejným datasetem hackathonu (žádné osobní údaje) smí běžet i free tier. Skutečná data pacientů nikdy, ta jen placený tier / Vertex AI EU.
- V placeném tieru Google prompty k trénování nepoužívá, loguje je ale omezenou dobu kvůli zneužití. Data mohou být dočasně uložena v jakékoli zemi.
- Podmínky **zakazují použití v klinické praxi a pro lékařské rady** a tam, kde je nutné schválení jako zdravotnický prostředek. Prototyp na fiktivních datech je v pořádku. **Cesta do produkce vede přes Vertex AI v EU regionu** (data residency, DPA) + certifikaci podle MDR. Tohle říct v pitchi.

**Pseudonymizace** (`services/ai/pseudonymize.py`):

- dataset PII neobsahuje (pacient = ID, lékaři = kódy `LEK-…`), pipeline ale stavíme jako pro reálná data;
- jméno, rodné číslo, adresa a kontakty se do LLM **nikdy** neposílají (ani do embedding API, §4.5);
- místo data narození se posílá věk;
- lékaři jsou zastoupeni kódem a odborností.

**Audit:** `LlmCallLog` (účel, model, hash promptu, počet tokenů, latence, bez PII). Potvrzené záznamy mají `Provenance` (kdo, kdy, z čeho, jakým modelem).

**Regulace (do pitche):**

- **GDPR:** zvláštní kategorie údajů, minimalizace, pseudonymizace.
- **AI Act:** high-risk systém (lidský dohled, logování, transparentnost = naše pravidla 1–4).
- **MDR:** software jako zdravotnický prostředek.
- **EHDS.**

### 5.8 Evaluace

Oficiální ground truth zatím **není** (organizátor ho zveřejní po odevzdání). Postup:

1. **Vývojová sada (T-013):** `data/dev_ground_truth/Pxx.json` z hypotéz v [DATASET.md §9](DATASET.md#9-vložené-nesrovnalosti--pracovní-hypotézy-týmu). Struktura stejná jako ohlášený oficiální ground truth: časová osa, klíčová fakta, red flags se závažností, chybějící údaje, otázky k diskusi, RECIST, studie po kritériích, relevantní pasáže, vše s ID zdrojů.
2. **Command** `python manage.py eval_ground_truth [--gt data/dev_ground_truth]` pro každého pacienta spočítá:
   - **recall red flags** (shoda podle pravidla a citovaných ID);
   - **pokrytí klíčových faktů;**
   - **míru neověřených tvrzení** (z validátoru);
   - **správnost „údaj chybí“;**
   - **přesnost screeningu studií** (shoda `met` / `not_met` / `unknown`).
3. Výsledek se zapíše do `docs/EVAL.md`. Čísla jdou do pitche (kritérium 20 %). Až přijde oficiální ground truth, jen se přepne `--gt`.

### 5.9 Semafor souladu léčebných postupů se stavem pacienta

Požadavek lékaře (FR-D4, D-015). Barva **není doporučení**. Říká, jestli stav pacienta postup nevylučuje (např. pacientovi se špatnou spirometrií nelze odebrat plíci).

- **Stavy:**
  - 🟢 nevylučuje;
  - 🟠 pozor: hraniční hodnota, relativní kontraindikace, nutné další vyšetření nebo rozpor;
  - 🔴 vylučuje (podle zdroje);
  - ⚪ nelze posoudit: chybí údaj nebo práh;
  - „neposuzováno“: lékař údaj přeskočil.
- **Vyhodnocení:**
  1. počítá ho `services/rules/compatibility.py` nad fakty z IRIS. LLM jen extrahuje hodnoty z textu s citací;
  2. pravidla jsou data (`services/rules/data/compatibility_rules.yaml`), katalog je v [docs/POZADAVKY_LEKARE.md §5.3](docs/POZADAVKY_LEKARE.md#53-pravidla);
  3. každá barva má citaci faktu pacienta a citaci pravidla (pasáž guidelines, kritérium studie nebo `EXT-…`);
  4. červená jen tam, kde zdroj říká „vylučuje / nepodávat / vysoké riziko“, nebo kde práh potvrdil tým (značka ⚠ v katalogu);
  5. celková barva postupu = nejhorší z pravidel: 🔴 > 🟠 > ⚪ > 🟢;
  6. odvozené hodnoty (CrCl podle Cockcrofta-Gaulta, % úbytku hmotnosti, dny od bevacizumabu) se ukazují se vzorcem a citacemi vstupů;
  7. preference pacienta barvu nemění, zobrazí se jako štítek.
- **Zobrazení:** v B2 u každé možnosti léčby (`DecisionSupport.treatment_options[].compatibility`, §8.3). **Vždy se zobrazí všechny možnosti** z guidelines, i červené. Nadpis zní „Soulad se stavem pacienta“, nikdy „doporučujeme“.
- **Očekávané barvy pro P03 a P04** (dev ground truth, T-013): [docs/POZADAVKY_LEKARE.md §5.4](docs/POZADAVKY_LEKARE.md#54-očekávané-barvy-pro-demo-podklad-pro-dev-ground-truth-t-013).
- **Implementace (T-503):**
  - `services/rules/data/compatibility_rules.yaml` drží data: pravidla `VS-*` (prahy, `source`, volitelně `threshold_source`, pole formuláře `fields`, `team_threshold` pro prahy ⚠ podle Q-7) a katalog postupů podle sady guidelines (`requires_icd` / `requires` určují, kdy postup dává smysl).
  - `services/rules/compatibility.py` obsahuje kontrolní funkce. `evaluate_compatibility(resources, skipped_fields=[], comorbidities_confirmed=False)` vrátí `{id, title, guideline_citations, compatibility: TreatmentCompatibility}[]`.
  - Externí zdroje `EXT-…` bere jen z katalogu T-504 (`services/iris/data/external_sources.json`).
  - „Není v dokumentaci“ (IM, ILD, MDS) je zelené jen s `comorbidities_confirmed`, jinak šedé (docs/POZADAVKY_LEKARE.md §5.1).
  - **Možnosti léčby v B2 (T-204) se berou z tohoto katalogu:** `treatment_options[].id/title/guideline_citations/compatibility` dodá kód, LLM píše jen `rationale`, `prerequisites_missing` a `considerations`. Díky tomu se červená možnost nikdy neztratí.
- **Znalostní báze `data/onko/` (T-315):** nadmnožina katalogu pro další diagnózy a modality (postupy, pravidla se strojovými podmínkami, fakta, studie, normy). Stejná ID `VS-*` a stejné zdroje jako YAML hlídá `services/eval/test_onko_kb.py`. Napojení do aplikace je T-316, do té doby platí YAML.
- **Napojení báze (T-316):** `services/rules/onko_kb.py:kb_for_patient(resources)` přidá do B2, bloku „Léčebné metody a odborníci“ a do `GET /cases/{cid}/compatibility/` **další postupy pro diagnózu pacienta**, které katalog nemá. Katalog a jeho kontrolní funkce zůstávají zdrojem pravdy (barvy P03 / P04 beze změny, pohledy rolí stojí jen na katalogu).
  - Fakta z FHIR s citacemi (`patient_facts`): MKN-10, věk, pohlaví, ECOG lékař / pacient a rozdíl, laboratoř podle LOINC z `fakta.tsv`, CrCl, ×ULN, LVEF a pokles, komorbidity podle MKN-10, léky podle ATC, IM / stent ve dnech, biomarkery (RAS, BRAF, MMR, EGFR, ALK, ROS1, PD-L1, HER2, HR, BRCA; poslední **známá** hodnota). Textová fakta (např. předchozí RT) zatím nejsou → ⚪.
  - Výběr postupů: diagnóza, stadium (M1 vs. ne, římská stadia v kontextu), histologie SCLC / NSCLC, fenotyp (TNBC, HER2+/−, HR+, RAS wt), marker postupu; obecné postupy (`dg = *`) jen při indikaci OBC-2.x (paliativní péče, nutrice, G8 ≥ 70 let, genetika při RF-GENETIC, biopsie při RF-LESION). Studie se hodnotí ve screeningu RKT, ne tady.
  - Barvu počítá `data/onko/q.py` (D-015). **Červená jen u pravidla z dodaných guidelines (`ov = D`) s faktem pacienta;** prahy báze mimo dataset sestavil AI agent a nikdo je zatím neověřil → max. oranžová a text „práh k ověření“. ⚪ pravidla jsou shrnutá v jednom řádku („N pravidel nelze posoudit; chybí údaj: …“), celková barva je dál nejhorší ze všech.
  - Nové zdroje `zdroje.tsv` (93) jsou v `external_sources.json` s `verified: ⚠ neověřeno`, resolver citací je vrátí. Báze se do backendu mountuje (`ONKO_KB_DIR`, dev compose `../data/onko:/data/onko:ro`); bez ní běží jen katalog.

### 5.10 Zařazení pacienta a kontrola úplnosti

Požadavek lékaře (FR-P4). Zároveň je to fáze „před zasedáním“ ze zadání a základ readiness (BON-1).

1. Zadávající lékař vybere board a pacienta z IRIS.
2. `services/rules/intake.py` předvyplní povinné údaje podle diagnózy ([docs/POZADAVKY_LEKARE.md §4](docs/POZADAVKY_LEKARE.md#4-povinné-a-důležité-údaje-podle-diagnózy)), každý s citací.
3. Chybějící údaj lékař buď **doplní** (uloží se do IRIS jako FHIR + `Provenance`), nebo **přeskočí** (nevyvolá varování, v podkladu „Chybí (přeskočeno lékařem)“). **Otázku pro MDT přeskočit nelze** (OBC-1.1: bez otázky je případ neúplný). Neúplný případ může předseda vrátit k doplnění (`MdtCase.status = returned`), nebo ho komise projedná s podmíněným doporučením (OBC-1.1).
4. Varování se počítají deterministicky, LLM jen u volného textu:

   | Typ | Kdy |
   |---|---|
   | CHYBÍ | povinný údaj chybí nebo má hodnotu „nevyšetřeno / probíhá“ |
   | MIMO NORMU | hodnota mimo `referenceRange` nebo nepravděpodobná (skok, nesedí jednotka, datum mimo časovou osu) |
   | ROZPOR | pravidla RF-* (§5.4) |
   | NEJISTOTA AI | rozmezí („ECOG 0–1“), nejednoznačná zkratka, neověřené tvrzení (FR-R5) |

5. Lékař varování může odkliknout (stačí klik, bez důvodu). Komise v podkladu dál vidí problém, ale ne to, kdo ho odklikl (D-019). Odkliknutí jde do auditu (`DetectedIssue.mitigation`).
6. Lékař zadá nebo potvrdí ECOG (velká číslice) a záměr **C/P** a zaškrtne připomínku „Snímek mladší než 3 měsíce“. Záměr se předvyplní z poslední MDT; když minulá MDT rozhodnutí odložila, nepředvyplní se.

**Doporučené údaje a šablony (T-317 → T-318):** `data/onko/udaje.tsv` doplňuje povinná pole o doporučené údaje podle diagnózy. Chybějící se hlásí jako `IntakeWarning` s `kind: "missing"`, `severity: "low"`, id `DOP:<údaj>`, titulkem „Doporučeno: …“ a citací zmínky v podkladech. Do readiness se nepočítají. `data/onko/sablony.tsv` dává doporučený `BriefConfig` pro projektor podle diagnózy.

**Zkratky (T-509, FR-R5):** `services/ai/abbreviations.py` a pravidla jako data v `services/ai/data/abbreviations.yaml` (docs/POZADAVKY_LEKARE.md §7.2).

- Výklad je deterministický: sekce („OA:“), pak nejbližší kontextové slovo v odstavci, pak název zprávy a oddělení. Když se výklady přetahují nebo kontext chybí, je výsledek NEJISTOTA AI, nikdy odhad.
- `uncertainty_warnings(resources)` dodává tato varování do intake.
- `prompt_rules()` je text pravidel pro systémové prompty (T-106, T-201).
- Na datasetu se všech 200+ výskytů vyloží jednoznačně.

**Implementace (T-502):** `services/rules/intake.py`, `intake_prefill(resources, skipped_fields=[])` vrátí `IntakePrefill` (§8.6).

- **Pole:** obecná (OBC-1.1: otázka, histologie a grade, TNM, zobrazení ≤ 6 týdnů, ECOG lékař i pacient, komorbidity, léčba, preference, alergie, hmotnost, G8 od 70 let) a podle diagnózy (plíce, prs, kolorektum, docs/POZADAVKY_LEKARE.md §4). Každé pole má citaci a `required_by`.
- **Varování:** red flags mají stejné `id` jako flag (`RF-TOX:P03-neuro01`), takže odkliknutí jde spárovat s podkladem (D-019). K nim se přidá:
  - CHYBÍ pro pole, které žádný flag nehlásí;
  - MIMO NORMU pro poslední laboratorní hodnotu s příznakem H/L;
  - NEJISTOTA AI pro rozmezí ECOG v textu.
- **Přeskočené pole** dostane stav `skipped` a umlčí flagy, které citují jeho zdroj. Otázku pro MDT přeskočit nejde.

**Readiness (BON-1, T-303):** `services/rules/readiness.py:evaluate_readiness(resources, skipped_fields=[])` vrátí `Readiness` (§8.6). Skóre tvoří přítomná pole checklistu OBC-1.1, biomarkery a povinné doplňující snímky podle diagnózy; staging starší než 42 dní se zapíše zvlášť. Přeskočené a pending údaje zůstávají nevyřešené. Stav `ready` znamená, že všechna započtená pole jsou `present`; jinak `incomplete`. Výpočet je deterministický, neúplný případ může komise i tak projednat s podmíněným doporučením.

### 5.11 Pokrytí guidelines

Guidelines datasetu jsou závazný obsah aplikace (zadání: možnosti léčby z dodaných guidelines s citací). Každá ze 42 pasáží má v aplikaci své místo:

| Pasáž | Co aplikace dělá | Kde |
|---|---|---|
| OBC-1.1 | úplnost podkladů (otázka, histologie + grade, TNM, biomarkery, ECOG, komorbidity, léčba, preference); otázku nelze přeskočit; neúplný případ vrátit, nebo podmíněné doporučení | `RF-MISSING`, §5.10, FR-P4, FR-C1, BON-1 |
| OBC-1.2 | staging ≤ 6 týdnů k datu MDT | `RF-STALE`, VS-OBC-09 |
| OBC-1.3 | ECOG lékař vs. pacient ≥ 1 a symptom ≥ 7/10 výslovně ukázat | `RF-ECOG`, `RF-PROMS`, hlavička (D-018), otázky k diskusi |
| OBC-1.4 | nové ložisko ověřit histologicky + IHC; duplicita: priorita a plán druhého nádoru, oba nádory v nominaci | `RF-LESION`, `RF-NOMINATION`, VS-OBC-10, FR-C1 |
| OBC-2.1 | včasná paliativní péče | `RF-PALIATIVE`, podpůrná péče v B2 |
| OBC-2.2 | G8 u věku ≥ 70 | `RF-GERI`, VS-OBC-03 |
| OBC-2.3 | úbytek ≥ 5 % za 6 měsíců → nutriční vyšetření | `RF-WEIGHT`, VS-OBC-04, studie RKT-05 |
| OBC-2.4 | indikace genetického poradenství | `RF-GENETIC` |
| OBC-3.1 | kortikoidy v nejnižší dávce s plánem snižování, glykémie u diabetiků | `RF-STEROID`, `RF-LAB`, VS-OBC-05 |
| KRC-1.1 | RAS, BRAF, MMR/MSI povinně; HER2 u RAS/BRAF wild-type | `RF-MISSING` |
| KRC-1.2 | dMMR → imunoterapie v 1. linii a genetika | VS-KRC-07, `RF-GENETIC` |
| KRC-2.1 | resekabilita: HPB chirurg + radiolog, R0, FLR ≥ 30 / 40 %, cévy a žlučová drenáž, bez extrahepatálního onemocnění | `RF-ROLES`, VS-KRC-01 až 03 |
| KRC-2.2 | konverzní chemo, restaging po 4–8 cyklech, po dosažení resekability neprodlužovat | VS-KRC-10 |
| KRC-2.3 | bevacizumab ≥ 6 týdnů před operací | VS-CHIR-03 |
| KRC-2.4 | restaging CT hrudník, břicho, pánev + MR jater ≤ 4–6 týdnů; vymizelá ložiska do plánu | `RF-STALE`, VS-KRC-02, VS-KRC-03 |
| KRC-2.5 | oba laloky: dvoudobá hepatektomie nebo ablace; pořadí výkonů | možnosti v B2 |
| KRC-3.1 | RAS mutovaný: FOLFOX / FOLFIRI ± bevacizumab, ne anti-EGFR | VS-KRC-06 |
| KRC-3.2 | neuropatie G2 → stop-and-go oxaliplatiny, hodnotit i podle pacienta | `RF-TOX`, VS-KRC-05 |
| PLI-1.1 | staging PET-CT, MR mozku, invazivní staging mediastina | VS-PLI-05, `RF-MISSING` |
| PLI-1.2 | ložisko měnící stadium ověřit, jinak nelze stanovit M | `RF-LESION`, VS-PLI-04 |
| PLI-1.3 | EGFR, ALK, PD-L1; při nedostatku tkáně rebiopsie nebo tekutá biopsie | `RF-MISSING`, VS-PLI-06 |
| PLI-2.1 | složení MDT u st. III | `RF-ROLES` |
| PLI-2.2 | resekabilní II–IIIB bez EGFR/ALK: neoadjuvantní chemoimunoterapie + lobektomie | možnost v B2 + semafor |
| PLI-2.3 | EGFR+ po resekci: osimertinib, ne imunoterapie | možnost v B2, VS-PLI-06 |
| PLI-2.4 | inoperabilní: CHRT + durvalumab (PD-L1 ≥ 1 %, ne EGFR/ALK+) | možnost v B2, VS-PLI-06, VS-PLI-07 |
| PLI-3.1 | funkční operabilita: ppo < 60 % → zátěžový test, < 30 % vysoké riziko, subjektivní dušnost | VS-PLI-01 až 03 |
| PLI-3.2 | hyponatrémie → vyšetřit SIADH, upravit před léčbou | `RF-LAB`, VS-PLI-09 |
| PLI-3.3 | odvykání kouření před operací i radioterapií | VS-CHIR-02 |
| PRS-1.1 | rebiopsie metastázy, nejaktuálnější vzorek, HER2-low z kteréhokoli vzorku | `RF-LESION`, VS-PRS-03 |
| PRS-1.2 | definice HER2-low | VS-PRS-03 |
| PRS-1.3 | ESR1 (ctDNA), PIK3CA / AKT1 / PTEN, gBRCA | `RF-MISSING` |
| PRS-1.4 | NGS → molekulární komise; BRCA z nádoru → genetika; doporučení komise je podklad, ne rozhodnutí | `RF-GENETIC`, `RF-ROLES` |
| PRS-2.1 | endokrinní léčba + CDK4/6, pokud nejde o viscerální krizi; premenopauza | VS-PRS-04 |
| PRS-2.2 | linie po CDK4/6 podle biomarkerů, účast ve studii | možnosti v B2, screening studií |
| PRS-2.3 | HER2-low → T-DXd po vyčerpání endokrinní léčby, riziko ILD | VS-PRS-02, VS-PRS-03 |
| PRS-2.4 | definice viscerální krize | VS-PRS-04 |
| PRS-3.1 | HER2+ 1. linie pertuzumab + trastuzumab + taxan, pak udržovací PH | možnost v B2 |
| PRS-3.2 | 2. linie trastuzumab deruxtekan | možnost v B2 |
| PRS-3.3 | mozkové metastázy: SRS, pokračovat anti-HER2, celomozkovou RT odložit, kortikoidy jen při edému | VS-PRS-11, `RF-STEROID` |
| PRS-3.4 | LVEF á 3 měsíce, pokles ≥ 10 bodů | VS-PRS-01, `RF-LAB` |
| PRS-4.1 | kostní metastázy: denosumab / zoledronát, Ca + D, stomatologie; RT nebo ortopedie | VS-PRS-12, VS-PRS-13 |
| PRS-4.2 | nový lokalizovaný symptom → cílené zobrazení; vzestup markeru bez zobrazení není progrese | `RF-NEWSYMPTOM`, `RF-LAB` |

---

## 6. Backend (Django) — struktura

### 6.1 Moduly

Zachováváme modulární monolit z templatu. Nové soubory a složky jsou označené `★`.

```
WEB_Template/backend/
├── apps/
│   ├── authentication/          # beze změny (JWT httpOnly cookies) + role uživatelů (Group)
│   ├── patients/            ★   # čtení z FHIR: seznam, detail, časová osa, evidence resolver
│   ├── mdt/                 ★   # boardy (MdtSession), MdtCase (zařazení, ECOG, C/P, varování), role, BriefConfig, Decision; potvrzení; export
│   ├── copilot/             ★   # Brief, GenerationJob, LlmCallLog; endpointy generování
│   │   └── management/commands/ ★ iris_init, ingest_dataset, eval_ground_truth, seed_mdt
│   ├── projects/ items/ ws/     # z templatu – skrýt z UI, nemazat (nerozbíjet seed/migrace)
├── services/
│   ├── ai_service.py            # providery; GeminiProvider přepsat (google-genai, schema, embed, transcribe)
│   ├── fhir/                ★   # client.py, ingest.py (sanitize + to_transaction), writeback.py, export.py
│   ├── iris/                ★   # db.py (connect ctx manager), vector_store.py
│   ├── ai/                  ★   # context_builder.py, text.py (odstavce), guidelines.py, pseudonymize.py, red_flags_llm.py, grounding.py, anamnesis.py, prompts/*.md
│   └── rules/               ★   # red_flags.py, intake.py, compatibility.py (+ data/compatibility_rules.yaml), readiness.py, recist.py, scales.py, guideline_sets.py
└── mcp_server.py            ★   # (SHOULD) FastMCP nad IRIS
```

Nové závislosti v `requirements.txt`:

- `intersystems-irispython`;
- **`google-genai`**;
- `pydantic` (schémata a `response_schema`);
- `fhir.resources` (volitelně, validace výstupů);
- `weasyprint` nebo `reportlab` (PDF);
- `fastmcp` (SHOULD).

`langchain` ani `openai` nepotřebujeme.

### 6.2 Modely (PostgreSQL)

| Model | Pole (hlavní) |
|---|---|
| `MdtSession` (= board) | `date`, `title` (zaměření komise), `chair` (User), `status` (planned/in_progress/closed), `config` → `BriefConfig` (výchozí podklad nastavený předsedou); zakládá a mění jen `mdt_admin` |
| `MdtCase` | `session` FK, `order`, `patient_fhir_id` (`P03`), `service_request_fhir_id` (`P03-zad01`), `question`, `status` (nominated → ready → in_discussion → decided → confirmed; `returned` = vráceno k doplnění, OBC-1.1), `created_by` (zadávající lékař), `ecog` (0–4), `intent` (`C` / `P`), `imaging_recent_checked`, `skipped_fields` JSON, `acknowledged_warnings` JSON (`{id, by, at}`) |
| `BriefConfig` | `name`, `owner`, `is_preset`, `sections` JSON (`[{id, enabled, order, detail}]`), `roles_present` JSON, `detail_level` (brief/standard/detailed), `language`, `hide_unverified` |
| `Brief` | `case` FK, `config_snapshot` JSON, `content` JSON (schéma [§8.2](#82-brief-podklad)), `model`, `created_at` |
| `GenerationJob` | `case` FK, `kind` (brief/scribe/patient_summary), `status` (queued/running/done/error), `progress` (0–100), `result_id`, `error` |
| `Decision` | `case` FK, `content` JSON (schéma [§8.4](#84-decision-závěr-komise)), `status` (draft/confirmed), `confirmed_by`, `confirmed_at`, `fhir_ids` JSON, `fhir_bundle` JSON |
| `LlmCallLog` | `purpose`, `provider`, `model`, `prompt_hash`, `tokens_in`, `tokens_out`, `latency_ms`, `ok` |
| `UserProfile` | `user` 1:1, `specialty` (hodnoty `RoleId` z §8.1); role = Django `Group` (`mdt_admin`, `mdt_doctor`, `mdt_viewer`) |

`seed_mdt` vytvoří zasedání a případy **z nominací v IRIS**: `ServiceRequest.category` (zaměření komise) + `Task.restriction.period.start` (datum MDT). Vzniknou 4 zasedání:

| Datum | Komise | Pacienti |
|---|---|---|
| 2026-10-14 14:00 | Mamární komise (urgentní) | P02 |
| 2026-10-21 14:00 | Mamární komise | P01, P05 (s molekulárním tumor boardem), P06 (s hrudní komisí a urologem) |
| 2026-10-21 14:00 | GIT – kolorektální / hepatobiliární | P03 |
| 2026-10-21 14:00 | Hrudní – karcinom plic | P04 |

Demo uživatelé (1-click přihlášení jako v templatu):

| Účet | Skupina | Odbornost |
|---|---|---|
| `predseda` | `mdt_admin` | klinický onkolog, předseda komise |
| `onkolog` | `mdt_doctor` | klinický onkolog, zadávající lékař (P01, P02, P03, P05, P06) |
| `pneumolog` | `mdt_doctor` | pneumolog, zadávající lékař (P04) |
| `chirurg`, `radiolog`, `patolog`, `radioterapeut` | `mdt_viewer` | podle názvu účtu |

### 6.3 REST API

Všechny endpointy pod `/api/`, autentizace JWT cookie, schéma v Swaggeru (`/api/docs/`).

| Metoda | Endpoint | Popis |
|---|---|---|
| GET | `/api/patients/` | seznam pacientů (z FHIR `Patient` + primární `Condition`) |
| GET | `/api/patients/{pid}/` | detail: demografie, diagnózy, komorbidity, TNM, ECOG |
| GET | `/api/patients/{pid}/timeline/` | události časové osy s Evidence ID |
| GET | `/api/patients/{pid}/observations/?code=…[&source=sql]` | časové řady (labs, hmotnost, ECOG, PROMs skóre) pro grafy; `source=sql` čte kódované číselné `Observation` ze SQL pohledu `MDT.ObservationSeries` (T-309) |
| GET | `/api/evidence/?id={EvidenceId}` | zdroj citace (text + zvýraznění / hodnota / pasáž guidelines / kritérium studie) |
| GET, POST | `/api/mdt/sessions/` | zasedání |
| GET | `/api/mdt/sessions/{sid}/` | detail + agenda (`MdtCase[]`) |
| PATCH, DELETE | `/api/mdt/sessions/{sid}/` | změna termínu a názvu boardu (jen `mdt_admin`) |
| GET | `/api/mdt/me/` | role (`mdt_admin` / `mdt_doctor` / `mdt_viewer`) a odbornost přihlášeného |
| GET | `/api/mdt/patients/{pid}/intake/` | předvyplnění formuláře zařazení: povinné údaje s citacemi + varování (`IntakePrefill`, §8.6) |
| POST | `/api/mdt/patients/{pid}/import/` | vstup zprávy (BON-7): JSON `{text}` nebo multipart `pdf` (text z PDF přečte Gemini) → **návrh** `{patient_id, document_id: "Pxx-impNN", title, date, text, values[], rejected[]}`; každá hodnota má `citation` = odstavec zprávy a je ověřená (číslo musí být v odstavci), neověřené jsou v `rejected` s důvodem. Nic se nezapisuje (předseda, lékař) |
| POST | `/api/mdt/patients/{pid}/import/confirm/` | potvrzení lékařem: tělo = návrh (případně jen vybrané `values`); server ho znovu ověří proti `text` a zapíše jednou transakcí `DocumentReference/Pxx-impNN` + `Observation/Pxx-impNN-obsNN` (`derivedFrom` → dokument, tag AI) + `Provenance` (lékař + `Device/mdt-copilot`), pak přepočítá vektory → 201 `{fhir_written}` |
| POST | `/api/mdt/cases/` | zařazení pacienta do boardu (FR-P4, `MdtCase` §8.6): `{session, patient_id, ecog, intent, imaging_recent_checked, skipped_fields, acknowledge}`; předseda a lékař. Nominace, která už případ má (`seed_mdt`), se doplní a přesune (200), jinak vznikne nový případ (201); stav → `ready`. Bez otázky pro MDT 400 (OBC-1.1). Ruční ECOG, záměr a odkliknutá varování jdou do IRIS (§4.3) jednou transakcí s `Provenance/Pxx-caseNN-prov`; odpověď nese `fhir_written` |
| PATCH | `/api/mdt/cases/{cid}/` | přesun do jiného boardu, ECOG, záměr, checkbox, odkliknutí varování (zadávající lékař svého pacienta, `mdt_admin` jakéhokoli); `status` (např. `returned`) jen `mdt_admin`; zápis do IRIS stejně jako u POST |
| GET, POST, PUT | `/api/mdt/configs/` · `/api/mdt/configs/{cid}/` | presety konfigurace (`BriefConfig` §8.5); zakládá a mění jen `mdt_admin`; `sections[].id` jen `SectionId`, `roles_present` jen `RoleId` (jde do promptů, jinak 400); presety „Standardní podklad“ a „Stručně (30 s)“ zakládá `seed_mdt` |
| GET | `/api/mdt/cases/{cid}/readiness/` | kontrola připravenosti (BON-1) |
| GET | `/api/mdt/cases/{cid}/compatibility/` | semafor souladu postupů se stavem pacienta (FR-D4): `{id, title, guideline_citations, compatibility: TreatmentCompatibility}[]` (§8.3), všechny postupy ze sady guidelines včetně červených; `= services/rules/compatibility.py:evaluate_compatibility` |
| POST | `/api/mdt/cases/{cid}/brief/` | `{config_id \| config}`, vrátí `{job_id}` |
| GET | `/api/mdt/cases/{cid}/brief/` | poslední podklad (schéma §8.2) |
| GET | `/api/jobs/{jid}/` | `{status, progress, result_id, error}`; FE polluje à 1 s |
| GET, POST | `/api/mdt/cases/{cid}/patient-summary/` | shrnutí pro pacienta (BON-4): POST (předseda, lékař) spustí job nad **potvrzeným** závěrem (jinak 409) → `Decision.patient_summary` + `DocumentReference/Pxx-mdtNN-pacient` (v PDF i FHIR exportu); GET vrátí uložené (404, dokud není) |
| POST | `/api/mdt/cases/{cid}/scribe/` | multipart `audio` nebo JSON `{transcript}` → přepis (Gemini) → draft závěru (job) (BON-3) |
| GET, PUT | `/api/mdt/cases/{cid}/decision/` | draft závěru (schéma §8.4) |
| POST | `/api/mdt/cases/{cid}/decision/confirm/` | potvrzení: zápis FHIR transaction do IRIS, vrátí `fhir_ids` |
| GET | `/api/mdt/cases/{cid}/export.pdf` | PDF |
| GET | `/api/mdt/cases/{cid}/export.fhir.json` | FHIR document Bundle |
| GET | `/api/mdt/tasks/?status=…&patient=…` | úkoly po zasedání (z FHIR `Task/Pxx-mdtNN-taskNN`, `MdtTask[]` §8.6), seřazené podle stavu a termínu |
| PATCH | `/api/mdt/tasks/{tid}/` | `{status}` → `Task.status` v IRIS (předseda, lékař) |

---

## 7. Frontend (Next.js 16) — struktura

> **Pozor:** Next.js 16 má breaking changes (např. `middleware.ts` je nově `proxy.ts`). Před psaním kódu si přečti `WEB_Template/frontend/AGENTS.md` a příslušný guide v `node_modules/next/dist/docs/`.

### 7.1 Routy

| Route | Obsah |
|---|---|
| `/` | přesměruje na `/dashboard` (veřejná landing page není) |
| `/login` | z templatu + 1-click demo účty (předseda, chirurg, onkolog…) |
| `/dashboard` | **kalendář zasedání** (UI v2, [NAVRH_UI §6](docs/NAVRH_UI.md#6-přehled--kalendář-zasedání)): 2 týdny, sloupce = dny, dlaždice zasedání s pacienty a připraveností; přesun pacienta drag & drop (myš, dotyk, klávesnice) i „Přesunout na…“ s „Vrátit“; „+“ na dlaždici zařadí pacienta (boční panel); klik na pacienta = rychlý přehled v bočním panelu; stav v `?tyden=&pacient=&komise=` |
| `/dashboard/mdt` | **seznam zasedání** v řádcích (nadcházející, minulá); předseda zakládá board a posílá odkaz na registraci kolegovi |
| `/dashboard/mdt/[sessionId]` | **jednání komise** ([NAVRH_UI §7](docs/NAVRH_UI.md#7-jednání-komise)): vlevo agenda (pořadí, projednáno, čas u pacienta), vpravo 30s rychlý přehled; zkratky ↑↓ / J K, D detail, Z závěr, P projektor, H projednáno; výběr pacienta se publikuje do `/projector` (BroadcastChannel); stav v `?pacient=` |
| `/dashboard/mdt/[sessionId]/add` | **zařazení pacienta** (FR-P4) jako stránka, záloha k bočnímu panelu: předvyplnění z IRIS, Doplnit / Přeskočit, varování, ECOG + C/P, checkbox snímku |
| `/dashboard/mdt/[sessionId]/setup` | **konfigurátor** (sekce, pořadí, role, detail, presety) |
| `/dashboard/cases/[caseId]` | **detail pacienta** ([NAVRH_UI §8](docs/NAVRH_UI.md#8-detail-pacienta)): přilepená hlavička (D-018, PS lékař / pacient, C/P, varování, předchozí / další pacient boardu), navigace po sekcích; rychlý přehled a varovné signály otevřené, souhrn a časová osa (AI / události z IRIS), anamnéza, odbornosti, léčba a studie, hlas pacienta a otázky sbalené |
| `/brief/[caseId]` | totéž v samostatném úzkém okně bez navigace (FR-U2); v `proxy.ts` chráněno stejně jako `/dashboard` |
| `/projector` | **úzký panel pro projektor** vedle snímku z PACS (T-512, 320–420 px, bez navigace, chráněno v `proxy.ts`): hlavička `Pxx · pohlaví · věk` + PS (lékař / pacient) + C/P, anamnéza (AI, citace), klíčové údaje podle diagnózy ze šablony intake + laboratoř (normalita jen z referenčního rozmezí a pravidel, `components/mdt/key-facts.ts`), všechny postupy se semaforem z `/compatibility/`, dole otázka pro MDT + MKN-10; případ přijímá z jednání komise (`/dashboard/mdt/[sessionId]`) |
| `…/cases/demo`, `/brief/demo` | podklad P03 z fixtures (`data/fixtures/brief_P03.json` + zdroje citací `evidence_P03.json`), funguje bez backendu; obě stránky skládá `CaseBriefScreen` |
| `/dashboard/cases/[caseId]/record` | **zápis závěru**: editor (sekce jako záznam MDT), úkoly, potvrzení, export |
| `/dashboard/patients/[patientId]` | pacient: časová osa, labs/PROMs grafy, dokumenty, předchozí MDT |
| `/dashboard/tasks` | úkoly po zasedání |

Shell (`app/dashboard/layout.tsx`, UI v2): sidebar **Přehled**, **Zasedání**, **Úkoly** (počet po termínu) + nejbližší zasedání jedním klikem + okno projektoru; horní lišta s drobečky, hledáním Ctrl K (pacienti, zasedání, akce) a avatarem (Nastavení, Klávesové zkratky, Odhlásit). Sdílená cache dat je TanStack Query (`src/lib/queries.ts`, providery v `app/providers.tsx`). Template stránky `projects`, `storage`, `realtime` a `ai` jsou z navigace skryté (kód zůstává). Dev služby (Swagger, Mailhog, Traefik) v aplikaci nejsou, jen v README a `dev.ps1`.

### 7.2 Klíčové komponenty (`src/components/mdt/` ★)

| Komponenta | Účel |
|---|---|
| `CaseHeader` | sticky hlavička (D-018): `Pxx · pohlaví · věk`, diagnóza + TNM, **hlavní otázka**, **ECOG lékaře velkou číslicí + ECOG pacienta**, velké **C/P**, komorbidity, alergie, implantáty / předchozí výkony, počet red flags (orientace do 30 s) |
| `AiBlock` | obal AI obsahu: štítek „AI návrh“ a fialový levý pruh (token `--ai`, NAVRH_UI Q1, neplete se s primární akcí ani semaforem), stav `draft` / `confirmed` (zeleně „Potvrzeno lékařem“) |
| `Claim` + `CitationChip` | věta s čísly citací `[1]`; `unverified` se zobrazí s varováním |
| `SourceDrawer` | boční panel: zdroj citace se zvýrazněným odstavcem / hodnota + referenční rozsah + zdrojový dokument (`derivedFrom`) / znění pasáže guidelines / kritéria |
| `MissingData` | „Chybí: …“ s přerušovaným okrajem + co doplnit; přeskočený údaj „Chybí (přeskočeno lékařem)“ (D-019) |
| `RedFlagList` | kompaktní seznam varovných signálů: závažnost (ikona + text), název, pravidlo; rozbalení = popis a **dva zdroje vedle sebe**; filtr podle závažnosti |
| `CaseQuickView` (`quick-view.tsx`) | 30s rychlý přehled ve stejném pořadí všude (boční panel, jednání, detail, `/projector`): hlavička, klíčové údaje (závažné a chybějící nahoře, normální sbalené), všechny postupy se semaforem, anamnéza (AI), otázka pro MDT |
| `EcogCompare` | dvě hodnoty + rozdíl + data + text odpovědi pacienta |
| `Timeline` | horizontální časová osa (dg., léčba, zobrazení, PROMs, předchozí MDT) |
| `TrendChart` | Hb, markery, Na, hmotnost, LVEF, skóre PROMs v čase (doporučení: `recharts`) |
| `RoleSection` + `RoleAssessmentCard` | sekce odborností pod sebou (v úzkém rozložení místo záložek), štítek a barva odbornosti; údaje podle diagnózy (FR-B8); verdikt role po kritériích (FR-B7) |
| `TreatmentOptions` / `TrialScreening` | B2: možnosti s citací pasáží a semaforem `CompatibilityLight` u každé; tabulka kritérií `Zn`/`Vn` × met / not_met / unknown |
| `SectionConfigurator` | zap/vyp sekce, drag & drop pořadí, role, detail; uložit preset |
| `DecisionEditor` | sekce záznamu MDT (jako v datasetu), úkoly (owner, termín), re-MDT; AI předvyplnění odlišené |
| `ConfirmDialog` | potvrzení: kdo potvrzuje, co se zapíše (výpis FHIR resources s ID `Pxx-mdtNN-…`) |
| `JobProgress` | průběh generování (polling `/api/jobs/{id}`) |
| `CompatibilityLight` | semafor 🟢/🟠/🔴/⚪ s ikonou a textem, rozbalení na pravidla s citacemi (FR-D4) |
| `IntakeForm` + `IntakeWarning` | formulář zařazení: předvyplněné údaje s citací, Doplnit / Přeskočit, varování s „Beru na vědomí“, ECOG + C/P, checkbox snímku (FR-P4) |
| `AnamnesisBlock` | anamnéza doslovně nebo jako shrnutí s citacemi, přepínač (FR-A5) |
| `ModalityCatalog` | léčebné metody pro diagnózu s odborníkem a daty k ruce (FR-D5) |
| `ScaleCard` | Lung-RADS / Fleischner s kontrolou použitelnosti (BON-6) |
| `BoardList` / `BoardEditor` | boardy, termíny (mění jen předseda), přesun pacientů (FR-P1) |

### 7.3 UX principy

1. **30 sekund:** `CaseHeader` (s diagnózou, TNM a hlavní otázkou) a 3–5 odrážek souhrnu nahoře, bez scrollování. Otázku lze zopakovat velkým písmem na konci podkladu.
2. **Každé tvrzení je ověřitelné jedním klikem.** Citace jsou čísla, ne dlouhé odkazy.
3. **AI vs. člověk je vidět na první pohled** (barva, badge, stav).
4. **Prezentační režim** pro projektor: velké písmo, tmavé téma (theme toggle je v templatu).
5. Ovládání klávesnicí: Ctrl+K (command palette z templatu) pro přepínání pacientů v agendě.
6. Typy `src/types/mdt.ts` přesně odpovídají [§8](#8-datové-kontrakty-fe--be). Pro vývoj UI bez backendu existují fixtures `data/fixtures/*.json` (demo pacient P03).
7. **Úzké rozložení** (FR-U2, D-017): od 360 px, jeden sloupec, bloky pod sebou, každý jde sbalit. Výchozí obsah a pořadí nastavuje předseda (FR-R1).
8. **Tři barevné systémy se nesmí plést:**
   - semafor: zelená, oranžová, červená, šedá;
   - odbornost: štítek s textem v jiných odstínech;
   - AI: fialový okraj + „AI návrh“.

   Barva nikdy nenese informaci sama, vždy je u ní i text nebo ikona.
9. **Výchozí pořadí bloků:** hlavička → souhrn A (+ časová osa) → red flags → anamnéza → sekce odborností (B, včetně hlasu pacienta) → léčebné metody a odborníci → možnosti léčby se semaforem, studie a otázky k diskusi (B2) → otázka pro MDT → po zasedání závěr (C). Detail: [docs/POZADAVKY_LEKARE.md §3](docs/POZADAVKY_LEKARE.md#3-obrazovka-podkladu-úzké-rozložení).

---

## 8. Datové kontrakty (FE ↔ BE)

> **Zdroj pravdy:** backend `apps/copilot/schemas.py` (pydantic; zároveň `response_schema` pro Gemini) ↔ frontend `src/types/mdt.ts`. Při změně uprav obojí + tuto sekci + fixtures.
>
> **Zmrazeno v T-009 (Pá 16. 10.):**
>
> - Vnořené typy mají v kódu jména: `BriefHeader`, `TreatmentOption`, `TrialScreening` (BE i FE stejně). Struktura je přesně podle této sekce. Typy API pacientů (`PatientListItem`, `PatientDetail`, `ObservationSeries`, T-103) jsou v `schemas.py` i `mdt.ts` také.
> - `intake_P03.json` a `red_flags` v `brief_P03.json` jsou vygenerované z pravidel (`intake_prefill()` T-502, `evaluate()` T-202) nad P03, ostatní části jsou ruční vzor výstupu LLM. Test `TestProducersMatchContract` ověřuje, že výstupy T-202, T-502 a T-103 pro P01–P06 přesně odpovídají schématům (žádný klíč navíc ani chybějící).
> - **Fixtures** demo pacienta P03 jsou v `data/fixtures/` (`brief_P03.json`, `decision_P03.json`, `intake_P03.json`), jen s reálnými ID z datasetu. Frontend má kopii v `src/fixtures/` a typovaný import v `src/lib/fixtures.ts`, protože frontend kontejner ani Vercel nevidí složky mimo `WEB_Template/frontend`. Test `apps/copilot/test_schemas.py` hlídá validaci pydantic (round-trip bez ztráty klíčů), existenci každé citace v datasetu a shodu kopie.
> - Pydantic hlídá jen strukturu a výčty. Sémantiku (citace u tvrzení, ≥ 2 zdroje u red flagu, barva semaforu) hlídá grounding validátor a pravidla: chybná citace z LLM nemá shodit celý podklad, má skončit jako `unverified`. Proto má `verification` v pydantic výchozí hodnotu `"unverified"`.
> - Formát Evidence ID rozkládá jen `services/fhir/ids.py` (`parse_evidence_id`), odstavce `#n` počítá jen `services/ai/text.py` (T-105, §4.5). Fixtures i testy je používají také.
> - Typy odpovědí `/api/evidence/` (`EvidenceSource`, T-104) a `/api/mdt/cases/{cid}/compatibility/` (`ProcedureCompatibility` = `{id, title, guideline_citations, compatibility}`, T-503) jsou v `schemas.py` i `mdt.ts`. Semafor v `brief_P03.json` je výstup `evaluate_compatibility()` (T-503). Test ověřuje, že resolver T-104 otevře každou citaci z fixtures.

### 8.1 Společné typy

```ts
type EvidenceId = string;                       // "P03-ecog03" | "P03-img03#4" | "KRC-2.4" | "RKT-03/V3" | "EXT-EMA-DPD-2020"
type Verification = "verified" | "unverified";
type Severity = "high" | "moderate" | "low";
type Light = "green" | "orange" | "red" | "grey" | "skipped";   // semafor souladu (§5.9)
type RoleId = "surgeon" | "oncologist" | "radiation_oncologist" | "radiologist" | "pathologist" | "pulmonologist" | "cardiologist" | "patient";
type SectionId = "summary" | "timeline" | "role_views" | "red_flags" | "decision_support" | "trials" | "questions" | "anamnesis" | "modalities" | "mdt_question";

interface Claim {
  id: string;
  kind: "claim" | "missing";
  text: string;                                 // u "missing": co chybí
  citations: EvidenceId[];                      // u "claim" ≥ 1
  verification: Verification;                   // nastavuje grounding validátor, ne LLM
  expected_source?: string;                     // u "missing": kde by měl údaj být
}

interface Criterion {                           // společné pro studie i posouzení role
  criterion_id?: EvidenceId;                    // "RKT-03/V3" (u studií)
  text: string;
  kind?: "inclusion" | "exclusion";
  status: "met" | "not_met" | "unknown";        // u "exclusion" znamená "met", že vylučující okolnost platí (pacient vyřazen)
  citations: EvidenceId[];                      // fakta pacienta
  guideline?: EvidenceId;                       // "KRC-2.1"
  missing?: string;                             // u unknown: co dodat
}
```

### 8.2 Brief (podklad)

```ts
interface Brief {
  case_id: string;
  patient_id: string;                           // "P03"
  generated_at: string;                         // ISO 8601
  model: string;                                // "gemini-3.8-flash"
  config: BriefConfig;                          // snapshot
  status: "draft" | "confirmed";
  header: {
    display_name: string;                       // "P03 · muž · 67 let" (žádné jméno ani RČ, D-018)
    age: number;                                // extension vek-k-datu-mdt
    sex: "male" | "female" | "other" | "unknown";
    diagnosis: { text: string; icd10: string; citation: EvidenceId };
    tnm?: { text: string; stage?: string; citation: EvidenceId };   // dataset má TNM jako text
    ecog: {
      physician?: { value: number; date: string; citation: EvidenceId; entered_by?: string };   // Observation 89247-1; entered_by = zadávající lékař (FR-P4)
      patient?:   { value: number; date: string; citation: EvidenceId; answer_text: string };  // PROMs samostatnost
    };
    intent?: { letter: "C" | "P"; code: "kurativni" | "paliativni"; source: "previous_mdt" | "physician" | "mdt_decision" };   // velké písmeno v hlavičce
    mdt_question: { text: string; citation: EvidenceId };   // ServiceRequest.reasonCode.text
    mdt_date: string;                                       // Task.restriction.period.start
    comorbidities: { text: string; icd10?: string; citation: EvidenceId }[];
    alerts: Claim[];                            // alergie, implantáty, předchozí výkony (FR-A4)
  };
  sections: BriefSection[];                     // textové sekce v pořadí podle config
  red_flags: RedFlag[];
  decision_support?: DecisionSupport;
  stats: { claims_total: number; claims_unverified: number; missing_total: number };   // ze všech Claim v podkladu (hlavička, sekce i B2), compute_stats()
}

// sections[] obsahuje jen textové sekce: summary, timeline, anamnesis, role_views, modalities.
// red_flags, decision_support, trials, questions a mdt_question mají vlastní pole (red_flags,
// decision_support, header.mdt_question); config.sections u nich určuje jen pořadí a viditelnost.
interface BriefSection {
  id: SectionId;
  role?: RoleId;                                // jen u role_views
  title: string;
  ai_generated: true;
  items: Claim[];
  assessment?: RoleAssessment;                  // jen u role_views (FR-B7)
}

interface RoleAssessment {
  role: RoleId;
  question: string;                             // "Je pacient kandidátem resekce jaterních metastáz?"
  verdict: "candidate" | "conditional" | "not_candidate" | "insufficient_data";
  criteria: Criterion[];
  note: string;                                 // "Podklad pro diskusi, rozhoduje lékař."
}

interface RedFlag {
  id: string;
  rule: string;                                 // "RF-ECOG" | "RF-TOX" | "RF-LLM" … (ARCHITEKTURA §5.4)
  severity: Severity;
  title: string;
  description: string;
  citations: EvidenceId[];                      // ≥ 2 (oba zdroje)
  guideline?: EvidenceId;                       // "OBC-1.3"
  verification: Verification;
}

interface TimelineEvent {                       // GET /api/patients/{pid}/timeline/ → TimelineEvent[] (seřazené podle data)
  date: string;                                 // "2026-09-21", může být částečné "2019-03"
  type: "diagnosis" | "procedure" | "medication" | "imaging" | "pathology" | "lab" | "proms" | "mdt" | "document";
  label: string;
  citation: EvidenceId;
}

interface PatientListItem {                     // GET /api/patients/ → PatientListItem[]
  id: string;                                   // "P03"
  display_name: string;                         // "P03 · muž · 67 let"
  sex: "male" | "female" | "other" | "unknown";
  age: number | null;
  diagnosis: { text: string; icd10: string; citation: EvidenceId } | null;   // první onkologická
  mdt_question: string | null;                  // ServiceRequest.reasonCode.text
  mdt_question_citation: EvidenceId | null;     // "P03-zad01"
  mdt_date: string | null;                      // Task.restriction.period.start (ISO)
}

interface PatientDetail extends PatientListItem {   // GET /api/patients/{pid}/
  diagnoses: { text: string; icd10: string; onset?: string; verification: string; stage: string | null; citation: EvidenceId }[];
  comorbidities: { text: string; icd10: string | null; citation: EvidenceId }[];
  tnm: { text: string; kind: string; date: string; citation: EvidenceId }[];   // Observation tnm, chronologicky
  ecog: {
    physician: { value: number; date: string; citation: EvidenceId } | null;                    // poslední Observation 89247-1
    patient: { value: number; date: string; citation: EvidenceId; answer_text: string } | null;  // poslední PROMs samostatnost
  };
}

interface EvidenceSource {                      // GET /api/evidence/?id=P03-img03%232 (400 neplatné ID, 404 nenalezeno)
  evidence_id: EvidenceId;
  kind: "resource" | "paragraph" | "guideline" | "trial_criterion" | "external";
  title: string;                                // "CT břicha a pánve…", "KRC-2.4 – Restaging před resekcí", "RKT-03 – kritérium vyřazení V3"
  text?: string;                                // celý text zprávy / PROMs „otázka: odpověď“ / znění pasáže či kritéria
  highlight?: { paragraph: number; start: number; end: number };   // u "#n": text.slice(start, end), offsety ve znacích (BMP = JS indexy)
  resource_type?: string; resource_id?: string; patient_id?: string | null;
  date?: string | null;
  department?: string | null;                   // category text ("RDG – Radiodiagnostické oddělení")
  author?: { id: string; text: string; specialty: string | null } | null;   // LEK-… + odbornost
  value?: { text: string; value: number | null; unit: string | null; ref_low: number | null; ref_high: number | null; interpretation: string | null };   // Observation
  derived_from?: EvidenceSource[];              // Observation → zdrojový dokument (derivedFrom + extension derived-from, Q15), bez další rekurze
  source?: string; region?: string;             // guidelines
  url?: string | null;                          // odkaz na externí zdroj EXT-… (T-504)
  study_id?: string; criterion_kind?: "inclusion" | "exclusion";   // kritérium studie
}

interface ObservationSeries {                   // GET /api/patients/{pid}/observations/?code=718-7,lvef,proms:brneni → ObservationSeries[]
  code: string;                                 // LOINC | druh z ID bez LOINC ("lvef") | "proms:<linkId>"
  label: string;
  unit: string | null;
  points: { date: string; value: number; citation: EvidenceId; ref_low?: number; ref_high?: number; interpretation?: "H" | "L" }[];
}
```

### 8.3 DecisionSupport (B2)

```ts
interface DecisionSupport {
  treatment_options: {
    id: string;
    title: string;                              // např. "Resekce jater dvoudobě + resekce primárního tumoru"
    rationale: Claim[];                         // vazba na fakta pacienta
    guideline_citations: EvidenceId[];          // ["KRC-2.1", "KRC-2.5"]
    prerequisites_missing: Claim[];             // co chybí (kind: "missing")
    considerations: string[];                   // rizika, kontraindikace (citované v rationale)
    compatibility: TreatmentCompatibility;      // semafor souladu se stavem pacienta (FR-D4, §5.9)
  }[];
  trials: {
    study_id: string;                           // "RKT-03"
    title: string;
    overall: "eligible" | "potentially_eligible" | "not_eligible";
    criteria: Criterion[];                      // criterion_id "RKT-03/Z1"… ; kind inclusion/exclusion
  }[];
  discussion_questions: { text: string; citations: EvidenceId[] }[];   // 2–3
  disclaimer: string;                           // "AI předkládá možnosti, nerozhoduje."
}

interface CompatibilityRuleResult {
  rule_id: string;                              // "VS-PLI-01" (katalog docs/POZADAVKY_LEKARE.md §5.3)
  status: Light;
  text: string;                                 // "ppoDLCO 38 % < 60 % → zátěžový test"
  patient_citations: EvidenceId[];              // ["P04-spiro04"]
  rule_citation: EvidenceId;                    // "PLI-3.1" | "RKT-06/Z4" | "EXT-…"
  derived?: { formula: string; inputs: EvidenceId[] };   // např. Cockcroft-Gault
}

interface TreatmentCompatibility {
  modality: string;                             // mdt-modalita
  owner_role: RoleId;                           // kdo se k metodě vyjadřuje
  overall: Light;                               // nejhorší z rules
  rules: CompatibilityRuleResult[];
  patient_preferences: Claim[];                 // štítek, barvu nemění
}
```

### 8.4 Decision (závěr komise)

Sekce odpovídají `Composition` „Záznam MDT“ v datasetu.

```ts
type Source = "ai" | "human" | "ai_edited";

interface Decision {
  case_id: string;
  status: "draft" | "confirmed";
  mdt_type: "primarni" | "progrese" | "restaging";            // mdt-typ-projednani
  attendees: { user_id: string; name: string; role: RoleId | "chair" }[];   // → CareTeam
  patient_present: boolean;                                    // ext. mdt-ucast-pacienta
  sections: {                                                  // → Composition.section
    question:        { text: string; source: Source };         // Projednaná otázka
    assessment:      { text: string; source: Source; citations: EvidenceId[] };  // Klinické zhodnocení
    intent:          "kurativni" | "paliativni" | "odlozeno";  // Léčebný záměr (mdt-lecebny-zamer)
    recommendation:  { modality: string; text: string; source: Source }[];       // Doporučený postup (mdt-modalita) → CarePlan.activity
    extra_diagnostics?: { text: string; source: Source };      // Doplňující diagnostika
    trial?:          { text: string; study_ids: string[]; source: Source };      // Klinická studie
    re_mdt?:         { date: string; reason: string };         // Plánované re-MDT
    conclusion:      { text: string; source: Source };         // Závěr MDT
    conditional?:    { text: string; missing: string[]; source: Source };   // podmíněné doporučení u neúplného případu (OBC-1.1)
    tumor_priority?: { text: string; source: Source };         // duplicita malignit: priorita a plán druhého nádoru (OBC-1.4)
  };
  tasks: {                                                     // → Task
    id: string;
    description: string;
    owner: string;                                             // LEK-… / role
    due_date: string;                                          // YYYY-MM-DD
    status: "requested" | "in-progress" | "completed";
    source: Source;
  }[];
  red_flags_acknowledged: string[];                            // RedFlag.id → DetectedIssue
  transcript_ref?: EvidenceId;                                 // "P03-mdt02-prepis" (BON-3)
  confirmed_by?: { user_id: string; name: string };
  confirmed_at?: string;
  fhir_ids?: {                                                 // po potvrzení
    composition: string;  careplan: string;  careteam: string;
    tasks: string[];  detected_issues: string[];  research_subjects: string[];
    provenance: string;  document_reference_pdf?: string;  document_reference_patient?: string;   // "P03-mdt02-pacient"
  };
  patient_summary?: { items: Claim[]; generated_at: string; document_reference: string };   // BON-4, po potvrzení
}
```

### 8.5 BriefConfig

```ts
interface BriefConfig {
  id?: string;
  name: string;
  is_preset?: boolean;                          // preset v konfigurátoru (GET /api/mdt/configs/)
  sections: { id: SectionId; enabled: boolean; order: number; detail?: "brief" | "standard" | "detailed" }[];
  roles_present: RoleId[];                      // ovlivní role_views, posouzení i záložky
  detail_level: "brief" | "standard" | "detailed";
  language: "cs" | "sk" | "en";
  hide_unverified: boolean;
}
```

### 8.6 Zařazení pacienta (MdtCase, IntakeWarning)

```ts
type WarningKind = "missing" | "out_of_range" | "conflict" | "ai_uncertain";   // CHYBÍ · MIMO NORMU · ROZPOR · NEJISTOTA AI

interface IntakeField {
  id: string;                                   // "bm.mmr" | "spiro.ppo_dlco" | "ecog.physician"
  label: string;
  value?: string;
  citation?: EvidenceId;
  status: "present" | "missing" | "pending" | "skipped";
  required_by?: EvidenceId;                     // proč je údaj povinný: "KRC-1.1"
}

interface IntakeWarning {
  id: string;                                   // stabilní (pravidlo + citace)
  kind: WarningKind;
  severity: Severity;
  title: string;
  detail: string;
  citations: EvidenceId[];
}

interface IntakePrefill {                        // GET /api/mdt/patients/{pid}/intake/
  patient_id: string;
  service_request_id: string;                   // "P03-zad01"
  fields: IntakeField[];
  warnings: IntakeWarning[];
  ecog_physician?: { value: number; citation: EvidenceId };
  intent_prefill?: "C" | "P";                   // z poslední MDT; „odloženo“ → nepředvyplněno
}

interface Readiness {                             // GET /api/mdt/cases/{cid}/readiness/
  patient_id: string;
  status: "ready" | "incomplete";
  score: { present: number; total: number; percent: number };
  unresolved: IntakeField[];                     // missing, pending nebo skipped; se zachovaným stavem
  stale_staging: { id: string; age_days: number; citation?: EvidenceId }[];
}

interface MdtCase {                             // POST /api/mdt/cases/, PATCH /api/mdt/cases/{cid}/
  id?: number;
  session: number;                              // board
  patient_id: string;
  service_request_id: string;
  created_by?: { user_id: number; name: string };
  ecog: number | null;
  intent: "C" | "P" | null;
  imaging_recent_checked: boolean;              // „Snímek mladší než 3 měsíce“
  skipped_fields: string[];                     // IntakeField.id
  acknowledged_warnings: { id: string; by: number; at: string }[];
  status: "nominated" | "ready" | "in_discussion" | "decided" | "confirmed" | "returned";   // returned = vráceno k doplnění (OBC-1.1)
  order?: number;                               // pořadí v agendě (jen čtení)
  question?: string;                            // otázka pro MDT z nominace (jen čtení)
  patient?: PatientListItem | null;             // jen v detailu boardu (hlavička z IRIS, §8.2)
}

// PATCH /api/mdt/cases/{cid}/ přijímá { session?, ecog?, intent?, imaging_recent_checked?, skipped_fields?, acknowledge?: string[] }.
// `acknowledge` = ID varování; server přidá { id, by, at } do acknowledged_warnings, nikdy neodebírá (D-019).
// Změna `session` zapíše datum nového boardu do Task.restriction.period.start v IRIS (FR-P1).

interface Me {                                  // GET /api/mdt/me/
  user_id: number;
  username: string;                             // demo: predseda | onkolog | pneumolog | chirurg | radiolog | patolog | radioterapeut
  name: string;
  role: "mdt_admin" | "mdt_doctor" | "mdt_viewer";   // superuser = mdt_admin, bez skupiny = mdt_viewer
  specialty: RoleId | null;
}

interface MdtTask {                             // GET /api/mdt/tasks/ → MdtTask[] (FR-P3)
  id: string;                                   // "P03-mdt02-task01" (FHIR Task)
  patient_id: string;
  mdt_record: string;                           // "P03-mdt02" (Composition)
  case_id: number | null;                       // MdtCase s potvrzeným závěrem
  description: string;
  owner: { id: string | null; name: string };   // LEK-… / role
  due_date: string | null;                      // Task.restriction.period.end
  status: "requested" | "in-progress" | "completed";
  authored_on: string | null;
  re_mdt: { date: string | null; reason: string } | null;   // z CarePlan (activity „Plánované re-MDT“, scheduledPeriod.start)
}

interface MdtSession {                          // GET /api/mdt/sessions/ → (MdtSession & { patients: string[] })[]
  id: number;                                   // GET /api/mdt/sessions/{sid}/ → MdtSession & { cases: MdtCase[] } (agenda)
  date: string;                                 // místní čas "2026-10-21T14:00:00+02:00"
  title: string;                                // "Mamární komise", "Mamární komise (urgentní)", "GIT – kolorektální karcinom / hepatobiliární"
  status: "planned" | "in_progress" | "closed";
  chair: { user_id: number; name: string } | null;
  config_id: number | null;                     // výchozí BriefConfig boardu
}
```

---

## 9. Konfigurace (env proměnné)

| Proměnná | Kde | Příklad / pozn. |
|---|---|---|
| `BACKEND_URL` | Vercel (server) | `https://api.<doména>` (rewrites) |
| `NEXT_PUBLIC_API_URL` | Vercel / lokálně | `''` na Vercelu (same-origin), lokálně `http://localhost:8000` |
| `NEXT_PUBLIC_DEMO_PASSWORD` | Vercel / lokálně | heslo pro 1-click demo účty na loginu (výchozí `demo123456`); musí se shodovat s `MDT_DEMO_PASSWORD` backendu. Je veřejné, demo účty pracují jen s fiktivními daty |
| `IRIS_HOST` / `IRIS_PORT` | backend | `iris` / `1972` |
| `IRIS_NAMESPACE` | backend | `FHIRSERVER` |
| `IRIS_USER` / `IRIS_PASSWORD` | backend | dev `SuperUser` / `SYS`, **na VPS jiné** |
| `FHIR_BASE_URL` | backend | `http://iris:52773/fhir/r4` |
| `DATASET_DIR` | backend | `/data/dataset` (kontejner) · lokálně `../Dataset_MDT_Copilot_v1.1_pre_timy/Dataset_MDT_Copilot_v1.1`; bez proměnné ho `ingest.dataset_dir()` najde v checkoutu repa (CI, testy) |
| `AI_PROVIDER` | backend | `gemini` (prod) / `mock` (testy, CI) |
| `GEMINI_API_KEY` | backend | Google AI Studio (free tier jen nad syntetickým datasetem, D-021; jinak placený tier); nikdy do gitu ani do frontendu |
| `AI_MODEL` | backend | `gemini-3.8-flash` |
| `AI_MODEL_STRONG` | backend | `gemini-4-argon` (volitelně, pro porovnání a těžké sekce) |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | backend | `gemini-embedding-001` / `1536` |
| `TRANSCRIBE_MODEL` | backend | `gemini-3.8-flash` |
| `AI_TIMEOUT_S` | backend | `90` (timeout jednoho volání Gemini; SDK opakuje 408, 429 a 5xx, celkem 3 pokusy) |
| `AI_THINKING_LEVEL` | backend | nenastaveno = výchozí podle modelu; `minimal` / `low` / `medium` / `high` (latence vs. kvalita, NFR-1, ladí T-302) |
| `GROUNDING_MIN_SIMILARITY` | backend | `0.55` (ladit podle evalu) |
| `INTAKE_ANAMNESIS_MAX_CHARS` | backend | `600` (FR-A5: delší anamnéza se zkrátí na shrnutí) |
| `COMPATIBILITY_RULES_FILE` | backend | `services/rules/data/compatibility_rules.yaml` (D-015) |
| `CSRF_TRUSTED_ORIGINS` / `CORS_ALLOWED_ORIGINS` | backend | Vercel doména(y) |

---

## 10. Lokální vývoj

```powershell
# celý stack (Next.js, Django, Postgres, Redis, Mailhog, Traefik) + IRIS (po T-002)
cd WEB_Template
.\dev.ps1 up                       # nebo: make dev
docker compose -f docker-compose.dev.yml exec backend python manage.py iris_init   # spouští i entrypoint, ručně jen při chybě
docker compose -f docker-compose.dev.yml exec backend python manage.py ingest_dataset          # celý dataset
docker compose -f docker-compose.dev.yml exec backend python manage.py ingest_dataset --patients P03 --skip-vectors   # rychle, bez Gemini
```

- **Demo (T-311):**
  - `python manage.py demo reset P03`: z IRIS smaže jen zápisy aplikace (`Pxx-mdtNN…` nad rámec datasetu, `Pxx-ecog-caseNN`, `Pxx-caseNN-…`), pacienta znovu nahraje z datasetu (nominace zpět „naplánovaná“), případ založí znovu na původním boardu a načte podklad z cache. Použít před každou zkouškou dema;
  - `python manage.py demo save P03` uloží poslední podklad do `data/demo_cache/brief_P03.json` (v gitu; po zapnutí placeného Gemini přegenerovat), `demo load P03` ho nahraje do případu;
  - `MDT_DEMO_OFFLINE=True` (env backendu): `POST …/brief/` vrátí podklad z cache bez volání LLM; když cache chybí, generuje se normálně.
- **Jen frontend** (doporučeno pro UI lane): `cd WEB_Template/frontend && npm run dev`. Pak buď `BACKEND_URL` na nasazený backend, nebo práce nad fixtures v `data/fixtures/`.
- **Kontrola IRIS:**
  - `curl -u SuperUser:SYS http://localhost:52773/fhir/r4/metadata` vrátí 200;
  - `…/fhir/r4/Observation?patient=P03&_summary=count` vrátí `total` 85.
- **Reset dat:** `docker compose -f docker-compose.dev.yml down -v`. Smaže **i** Postgres volume.
- Porty: FE 3000, BE 8000, Postgres 5432, Redis 6379, Mailhog 8025, Traefik 8080, IRIS 1972 / 52773.
- **Windows:** s `core.autocrlf=true` dostane `entrypoint.sh` v pracovní kopii konce řádků CRLF a backend kontejner nenaběhne. Dokud T-001 nepřidá `.gitattributes`: `git config core.autocrlf input`, pak `git rm --cached -r . -q && git reset --hard` (jen v čisté pracovní kopii).
- **Node lokálně není nutný:** frontend běží v Dockeru. Dokumentace Next 16: `docker compose -f docker-compose.dev.yml exec frontend ls node_modules/next/dist/docs`.

### Struktura repa

```
Rakhaton2026/
├── AGENTS.md / CLAUDE.md                 # pravidla pro AI agenty
├── ARCHITEKTURA.md                       # tento dokument
├── DATASET.md                            # průvodce datasetem
├── PROGRESS.md                           # roadmapa, úkoly, stav, deník
├── MYSLENKOVA_MAPA.md                    # přehled + poznámky z konzultace
├── Dataset_MDT_Copilot_v1.1_pre_timy/    # dataset od Asseco (v gitu, repo je veřejné)
│   └── Dataset_MDT_Copilot_v1.1/         #   = DATASET_DIR
├── docs/
│   ├── zadani/                           # pptx zadání (přesunout z WEB_Template/)
│   └── EVAL.md                           # výsledky evaluace
├── data/
│   ├── dev_ground_truth/                 # naše evaluační sada (T-013)
│   ├── fixtures/                         # JSON pro FE vývoj (Brief, Decision… pro P03)
│   └── audio/                            # simulovaná diskuse MDT (BON-3)
├── .claude/skills/                       # IRIS skills z FHIR-AI-Hackathon-Kit
└── WEB_Template/
    ├── frontend/                         # → Vercel
    ├── backend/                          # → VPS
    ├── iris/                       ★     # Dockerfile + merge.cpf (z kitu)
    └── docker-compose*.yml               # + služba iris
```

---

## 11. Otevřené otázky

| # | Otázka | Stav |
|---|---|---|
| Q1 | Formát a doručení datasetu | ✅ dataset v1.1 je FHIR R4, viz [DATASET.md](DATASET.md) |
| Q2 | LLM provider a klíč | ✅ Google AI Studio (Gemini), viz D-008. Zbývá Q9 |
| Q3 | Server pro backend | ✅ VPS (doménu doplní INFRA) |
| Q4 | Pravidla odevzdání a commity po So 12:00 | ⏸ zatím neřešíme |
| Q5 | Veřejné repo, dataset v gitu | ✅ ano, smí |
| Q6 | Klinické prahy red flags: připomínky onkologů | ⬜ zatím nemáme; prahy bereme z guidelines OBC/KRC/PRS/PLI datasetu ([§5.4](#54-red-flags)) |
| Q7 | Podpora `Patient/$everything` a import mCODE IG ve verzi IRIS | ✅ `$everything` funguje (bez `_count`), `$validate` funguje, mCODE IG není nahraný (import = T-307), viz §4.6 |
| Q8 | Kdy a v jakém formátu bude oficiální ground truth? | ⬜ Ľ. Piljan |
| Q9 | Kdo zapne billing (placený tier) v Google AI Studio? Bez něj nesmíme posílat data | ✅ D-021: free tier smí nad syntetickým datasetem; billing až pro skutečná data |
| Q10 | Sprint 0 (M0, Pá 18:00) nestihnutý: potvrdit nové časy sprintů | ✅ sprinty startují Pá 19:00, M0 co nejdřív, M1–M4 beze změny |
| Q11 | Owneři lanes (PROGRESS §2) | ✅ Seb (INFRA + API), Maty (DATA), Jarda (AI), Mira (UI + PITCH) |
| Q12 | Windows + `core.autocrlf=true` rozbije `entrypoint.sh` (CRLF) → `.gitattributes` v T-001 | ✅ `.gitattributes` (T-001) |

---

## 12. Zdroje

- Zadání: `docs/zadani/MDT_Copilot_zadani_upravené_2026_v02.pptx` (Asseco CE)
- Dataset: `Dataset_MDT_Copilot_v1.1_pre_timy/Dataset_MDT_Copilot_v1.1/README.md` + [DATASET.md](DATASET.md)
- [InterSystems Challenge at Rakathon 2026](https://developer.intersystems.com/intersystems-challenge-at-rakathon-2026/)
- [FHIR-AI-Hackathon-Kit (V2)](https://github.com/intersystems-community/FHIR-AI-Hackathon-Kit): tutoriály 3.x FHIR, 3.5 FHIR SQL Builder, 4.1 Vector Search, 5.1 agenti, 5.2 MCP; `skills/`
- [iris-agentic-dev](https://github.com/intersystems-community/iris-agentic-dev): MCP pro AI coding agenty nad IRIS
- Gemini API: [modely](https://ai.google.dev/gemini-api/docs/models) · [embeddingy](https://ai.google.dev/gemini-api/docs/embeddings) · [audio](https://ai.google.dev/gemini-api/docs/audio) · [podmínky](https://ai.google.dev/gemini-api/terms)
- [Rakathon 2026](https://www.rakathon.cz/eng): harmonogram
- HL7 [FHIR R4](https://hl7.org/fhir/R4/) · [mCODE](https://hl7.org/fhir/us/mcode/) · HL7 Europe Common Cancer Model (ECCDM, 1.0.0-ballot) · [IPS](https://hl7.org/fhir/uv/ips/) · [Patient $everything](https://www.hl7.org/fhir/R4/operation-patient-everything.html)
- Klinika: ESMO guidelines · RECIST 1.1 · EORTC QLQ-C30 · PRO-CTCAE
