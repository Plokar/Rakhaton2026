# MDT Copilot — technická specifikace a architektura

> **Rakathon 2026** · Praha 16.–18. 10. 2026 · zadání **Asseco Central Europe** (MDT Copilot) + souběžná výzva **InterSystems** („Best Use of InterSystems Technology for AI and Interoperability“)
>
> Tento dokument je **jediný zdroj pravdy** pro architekturu, požadavky a datové kontrakty.
>
> - Dataset (struktura, FHIR, ingest, ID, vložené nesrovnalosti): [DATASET.md](DATASET.md)
> - Úkoly a stav: [PROGRESS.md](PROGRESS.md)
> - Pravidla pro AI agenty: [AGENTS.md](AGENTS.md)
> - Přehled a poznámky z konzultace: [MYSLENKOVA_MAPA.md](MYSLENKOVA_MAPA.md)
>
> Změnu kontraktu ([§8](#8-datové-kontrakty-fe--be)) nebo API ([§6.3](#63-rest-api)) udělej **nejdřív tady**, ve stejném PR jako kód, a zapiš ji do Deníku v PROGRESS.md.

---

## 0. TL;DR

- **Co stavíme:** webovou aplikaci, která z dat onkologického pacienta během pár sekund připraví podklad pro multidisciplinární komisi (MDT). Podklad má čtyři bloky: **A** souhrn, **B** pohledy odborníků, **B2** podpora rozhodování a **C** závěr a akční plán. Každé tvrzení AI má klikací citaci zdroje, AI hlásí rozpory (red flags) a **rozhoduje vždy lékař** (human-in-the-loop).
- **Stack:**
  - **Next.js 16** na **Vercelu** (`WEB_Template/frontend`);
  - **Django 4.2 + DRF** na **VPS** (`WEB_Template/backend`) v Dockeru s Traefikem;
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

---

## 1. Zadání v kostce

Výtah ze zadání `WEB_Template/MDT_Copilot_zadani_upravené_2026_v02.pptx`, včetně poznámek řečníka.

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
| **FR-A1** | Executive summary: diagnóza (MKN-10 + slovně), stadium (TNM), hlavní otázka komise (`ServiceRequest.reasonCode.text`), čitelné do 30 s | MUST | UX |
| **FR-A2** | ECOG lékař (`Observation` LOINC 89247-1) vs. pacient (PROMs `samostatnost` 0–4) vedle sebe s datem a citací; **rozdíl ≥ 1 znamená red flag** (OBC-1.3) | MUST | UX, AI |
| **FR-A3** | Časová osa: diagnóza, výkony, linie léčby, zobrazení, PROMs, předchozí MDT; každý bod klikací | MUST | UX |
| **FR-A4** | Hlavička: **komorbidity** (`Condition` „komorbidita“), **alergie** (PROMs `alergie` + text zpráv), **předchozí výkony a implantáty** (`Procedure`: port, stent, operace) *(konzultace)* | MUST | UX |
| **FR-B1** | Pohled chirurga: resekabilita, TNM, rozsah, předchozí operace v oblasti, operační riziko | MUST | UX |
| **FR-B2** | Pohled onkologa: biomarkery (včetně „nevyšetřeno“), linie léčby (`MedicationAdministration`), odpověď, toxicita (lékař vs. PROMs) | MUST | UX |
| **FR-B3** | Pohled radiologa: vývoj nálezů a rozměrů lézí v čase, srovnání posledních vyšetření, aktuálnost stagingu | MUST (≥ 3 role) | UX |
| **FR-B4** | Pohled patologa: histologie, grade, ICD-O-3, biomarkery z tkáně, diskordance primár vs. metastáza | SHOULD | UX |
| **FR-B5** | Pohled pacienta: trend PROMs (2 vyplnění), nové obtíže, priorita (`delka`/`kvalita`), postoj, podpora doma | MUST | UX, PROC |
| **FR-B6** | Pohled radiačního onkologa: předchozí RT, oblasti, dávky | SHOULD | UX |
| **FR-B7** | **Posouzení role („match“):** pro každou přítomnou roli předběžný verdikt `candidate` / `conditional` / `not_candidate` / `insufficient_data` po kritériích s citací (např. chirurg: resekabilita, FLR, ECOG, komorbidity). Jen podklad, potvrzuje lékař dané role *(konzultace)* | SHOULD | UX, AI |
| **FR-D1** | Možnosti léčby z **dodaných** guidelines s citací **ID pasáže** (`KRC-2.4`); AI nevybírá, předkládá alternativy | MUST | AI, STD |
| **FR-D2** | Screening studií `RKT-01…06`: pro každé kritérium `met` / `not_met` / `unknown` + citace (`RKT-03/V3` ↔ fakt pacienta); celkový stav | MUST | AI |
| **FR-D3** | 2–3 klíčové otázky k diskusi | MUST | UX |
| **FR-C1** | Strukturovaný zápis rozhodnutí ve struktuře datasetu (Projednaná otázka, Klinické zhodnocení, Léčebný záměr, Doporučený postup, Doplňující diagnostika, Klinická studie, Plánované re-MDT, Závěr MDT) + přítomní | MUST | PROC, STD |
| **FR-C2** | Úkoly (kdo, co, do kdy), kontrola, termín opětovného posouzení | MUST | PROC |
| **FR-C3** | Potvrzení předsedou udělá z draftu oficiální záznam (zápis do IRIS FHIR) | MUST | PROC |
| **FR-C4** | Export PDF + HL7 FHIR (document Bundle) | MUST | STD |
| **FR-R1** | Konfigurátor: sekce zap/vyp, pořadí, přítomné role, úroveň detailu; ukládání presetů | MUST | CFG |
| **FR-R2** | Red flags: rozpory mezi zdroji, závažnost (high/moderate/low), citace **obou** zdrojů, odkaz na pasáž guidelines | MUST | AI |
| **FR-R3** | Klikací citace u každého tvrzení otevře zdroj se zvýrazněnou pasáží; chybějící údaj explicitně „Údaj chybí v podkladech“ | MUST | AI |
| **FR-R4** | AI text vizuálně odlišen (badge „AI návrh“, styl); po potvrzení „Potvrzeno: LEK-…, čas“ | MUST | PROC |
| **FR-P1** | Před zasedáním: nominace (`ServiceRequest` + `Task`), agenda zasedání (`Task.restriction.period.start`) | SHOULD | PROC |
| **FR-P2** | Během zasedání: přepínání pacientů v agendě, prezentační režim (velké písmo, projektor) | SHOULD | UX |
| **FR-P3** | Po zasedání: přehled úkolů a jejich stav, naplánování re-MDT | SHOULD | PROC |

### 2.2 Bonusy

| ID | Bonus | Pozn. |
|---|---|---|
| **BON-1** | **Kontrola připravenosti případu** (readiness): checklist OBC-1.1 (otázka, histologie + grade, TNM, prediktivní biomarkery, ECOG, komorbidity, dosavadní léčba, preference) + aktuálnost stagingu ≤ 6 týdnů (OBC-1.2) | deterministicky + LLM pro text |
| **BON-2** | **Předvýpočet odpovědi dle RECIST 1.1**: SLD baseline vs. nadir vs. aktuální, výsledek CR/PR/SD/PD | P03: 83 → 50 mm (−40 %) = PR; AI jen extrahuje rozměry z popisů |
| **BON-3** | **AI zapisovatel**: přepis diskuse převede na draft rozhodnutí + úkoly (s citací na úsek přepisu) | **Dataset přepis neobsahuje.** Nahrajeme vlastní simulovanou diskusi (audio) a přepíšeme ji Gemini ([§5.6](#56-ai-zapisovatel-bon-3)) |
| **BON-4** | **Shrnutí pro pacienta** v laickém jazyce | po potvrzení závěru; zohlednit `priorita` a `postoj` z PROMs |
| **BON-5** | **Export mapovaný na mCODE / ECCDM** (`meta.profile`, kódy pro biomarkery a TNM, které jsou v datasetu jen textem), případně validace `$validate` v IRIS | zároveň bod pro InterSystems |

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
│  Django 4.2 + DRF (ASGI/Daphne) – WEB_Template/backend                                  │
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
| **FHIR SQL Builder** | Projekce `Observation` (laboratoř, hmotnost, ECOG) do SQL pro trendy, pravidla red flags a dashboard zasedání | SHOULD |
| **MCP server nad IRIS** (FastMCP, kit 5.2) | Nástroje `get_patient_context`, `search_evidence`, `search_guidelines`, `fhir_query` pro copilot agenta; ukázka „IRIS jako MCP backend“ | SHOULD |
| **FHIR packages (mCODE IG) + `$validate`** | Validace exportu proti profilům (`HS.FHIRMeta.Load.NpmLoader.importPackages`) | BONUS |
| Interoperability production | Ingest „surových“ eZdraví zpráv (File → DTL → FHIR); dataset už je FHIR, takže netřeba | stretch, ne |
| IntegratedML | **nepoužijeme**: predikce bez klinické validace by snížila důvěryhodnost | — |

**Pitch pro InterSystems:** IRIS je nemocniční datová platforma, ze které copilot **čte** (FHIR), ve které **hledá a ověřuje** (Vector Search nad stejnými daty, bez další vektorové DB) a do které **zapisuje** auditovatelný závěr komise (FHIR + Provenance). Jedna platforma, standardy end-to-end.

### 4.2 Prostředí (převzato z FHIR-AI-Hackathon-Kit V2)

| Věc | Hodnota (dev) |
|---|---|
| Image | `intersystems/irishealth-community:latest-cd` → **zafixovat konkrétní tag**, až ho stáhneme (`docker image inspect`) |
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

Command musí být idempotentní (`ExistsByUrl`). **Nenahrávat** Synthea data z kitu, nahrává se náš dataset (`ingest_dataset`).

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
| Doporučení | `CarePlan/Pxx-mdtNN-careplan` | `status=active`, `intent=plan`, `category` `mdt-lecebny-zamer` (kurativni / paliativni / odlozeno), `activity[].detail.code` `mdt-modalita` + `description`, `basedOn` → `ServiceRequest/Pxx-zad01`, `addresses` → Condition |
| Přítomní | `CareTeam/Pxx-mdtNN-careteam` | `participant[].role.text` + `member` (z konfigurace „kdo je přítomen“) |
| Úkoly | `Task/Pxx-mdtNN-task01…` | `basedOn` → CarePlan, `intent=order`, `owner`, `restriction.period.end` = termín, `description` |
| Red flags | `DetectedIssue/Pxx-mdtNN-rf01…` | `severity` high/moderate/low, `implicated[]` = **oba zdroje**, `detail`, `reference` = pasáž guidelines (text), `patient` |
| Vhodnost do studie | `ResearchSubject/Pxx-mdtNN-rs01` | `status=candidate`, `study` → `ResearchStudy/RKT-0n`; jen pokud komise potvrdí |
| Stav nominace | `Task/Pxx-zad01-task` (update) + `ServiceRequest/Pxx-zad01` (update) | `businessStatus` → `projednana` (nový kód), `status` → `completed` |
| Přepis diskuse (BON-3) | `DocumentReference/Pxx-mdtNN-prepis` | `type` text „Přepis diskuse MDT“, `content.attachment` (text, base64) |
| **Původ a potvrzení** | `Provenance/Pxx-mdtNN-prov` | `target` = vše výše; `agent[]`: `Device/mdt-copilot` (model Gemini, typ `assembler`) + `Practitioner` předseda (`verifier` / `attester`); `entity[]` (`role=source`) = citované zdroje; `recorded` |
| AI systém | `Device/mdt-copilot` (jednou při `iris_init`) | `deviceName` „MDT Copilot“, `version` = model |
| Označení AI obsahu | `meta.security` `AIAST` (`http://terminology.hl7.org/CodeSystem/v3-ObservationValue`) na resources s AI draftem | podle HL7 *AI Transparency on FHIR* (draft IG, **ověřit stav**) |
| PDF | `DocumentReference/Pxx-mdtNN-pdf` | `application/pdf`, `relatesTo` → Composition |
| **FHIR export** | `Bundle` `type=document` | `Composition` jako 1. entry + všechny odkazované resources |

### 4.4 ID a idempotentní ingest

- **ID z datasetu zachováváme** (D-005). Sanitizace: `_` se mění na `-` (`P01-lab01-hb_f` → `P01-lab01-hb-f`) v `id`, `fullUrl` i ve všech `reference`; prázdné stringy se odstraní ([DATASET.md §6.2](DATASET.md#62-sanitizace-povinná)).
- Ingest posílá **transaction Bundle s `request.method = "PUT"`** a `request.url = "Type/id"`. Opakované spuštění data přepíše, nic se neduplikuje. Jeden bundle na pacienta (142–215 entries) + bundle studií + Questionnaire.
- Command `python manage.py ingest_dataset [--patients P03,P05] [--skip-vectors]` čte z `DATASET_DIR` a po nahrání **ověří počty** proti [DATASET.md §2](DATASET.md#2-pacienti).
- Nové resources z aplikace dodržují konvenci datasetu (`Pxx-mdtNN-…`, viz §4.3), aby šly citovat a dohledat stejně.

### 4.5 Vektorové tabulky (IRIS SQL, namespace FHIRSERVER)

```sql
CREATE TABLE MDT.EvidenceChunk (
    EvidenceId   VARCHAR(200),        -- "P03-img03#2"  (ID zdroje # pořadí odstavce)
    PatientId    VARCHAR(16),         -- "P03"  (POVINNÝ filtr při hledání)
    ResourceType VARCHAR(64),         -- DocumentReference | DiagnosticReport | Composition
    ResourceId   VARCHAR(128),        -- "P03-img03"
    ChunkIndex   INTEGER,
    DocDate      DATE,
    Title        VARCHAR(500),        -- type.text / code.text
    Department   VARCHAR(200),        -- category[].text (A-ONK, RDG, PAT-B…)
    Text         VARCHAR(10000),
    Embedding    VECTOR(DOUBLE, 1536)
);

CREATE TABLE MDT.GuidelineChunk (
    EvidenceId   VARCHAR(50),         -- "KRC-2.4"
    GuidelineSet VARCHAR(10),         -- KRC | PRS | PLI | OBC
    Title        VARCHAR(300),        -- "Restaging před resekcí"
    Source       VARCHAR(200),        -- "Rakathon 2026 – výtah (inspirováno ESMO a národními standardy)"
    Region       VARCHAR(20),         -- "CZ"  (konzultace: zdroj a region postupu)
    IcdPrefixes  VARCHAR(100),        -- "C18,C19,C20" | "C50" | "C34" | "*" (OBC)
    Text         VARCHAR(5000),
    Embedding    VECTOR(DOUBLE, 1536)
);

CREATE TABLE MDT.TrialCriterion (
    EvidenceId   VARCHAR(50),         -- "RKT-03/V3"
    StudyId      VARCHAR(16),         -- "RKT-03"
    Kind         VARCHAR(10),         -- inclusion | exclusion   (Group.characteristic.exclude)
    Text         VARCHAR(2000),
    Embedding    VECTOR(DOUBLE, 1536)
);
```

```sql
-- hledání v datech pacienta (grounding = WHERE PatientId)
SELECT TOP 8 EvidenceId, Text, VECTOR_COSINE(Embedding, TO_VECTOR(?, DOUBLE)) AS Score
FROM MDT.EvidenceChunk
WHERE PatientId = ?
ORDER BY Score DESC
```

- **Chunking:** texty jsou krátké (93 dokumentů, max ~1 900 znaků), takže **1 odstavec = 1 chunk** (dělit podle prázdných řádků a řádků „Závěr:“, „Nález:“). Kvůli zvýraznění v UI ukládáme i offset v textu.
- **Embeddingy:**
  - `gemini-embedding-001`, `output_dimensionality=1536`;
  - **L2 normalizovat** (pod 3072 dimenzí to Google vyžaduje);
  - `task_type`: `RETRIEVAL_DOCUMENT` pro chunky, `RETRIEVAL_QUERY` pro dotazy a `FACT_VERIFICATION` pro ověření tvrzení;
  - max 2 048 tokenů na vstup;
  - volat dávkově.
- Vkládání: `INSERT … VALUES (?, …, TO_VECTOR(?))` s `str(list_of_floats)`; batch přes `executemany`.
- IRIS SQL používá `SELECT TOP n`, ne `LIMIT`. Parametry vždy přes `?`.

### 4.6 FHIR REST klient — pravidla a gotchas

- Hlavičky `Accept: application/fhir+json` a `Content-Type: application/fhir+json`, Basic auth.
- **Stránkování:** sledovat `link[relation=next]`; `_count=500` (pacient má max ~110 Observation).
- **Neznámé search parametry IRIS tiše ignoruje** (vrátí 200 se vším). Filtry ověřit testem.
- Search parametry se liší od názvů elementů (`recorded-date` vs. `recordedDate`). `Task` a `ImagingStudy` se hledají přes `patient`.
- Kódy: `Observation?patient=P03&code=http://loinc.org|718-7&_sort=date`.
- **`Patient/$everything`:** podporu v naší verzi IRIS **ověřit** (komunita naznačuje, že není out-of-the-box). Fallback: paralelní searche přes typy z [DATASET.md §6.3](DATASET.md#63-čtení-za-běhu-context-builder).
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

### 4.8 Pro AI agenty v týmu

- Do repa zkopírovat skills z kitu (`skills/iris-fhir`, `iris-vector-search`, `iris-sql-python`, `iris-ai-agents`, `iris-environment`) do `.claude/skills/` (úkol T-011).
  - Obsahují ověřené snippety a gotchas.
  - **Pozor: kit používá OpenAI** (`text-embedding-3-small`, `gpt-5-nano`). U nás se embeddingy i LLM volají přes Gemini ([§5.7](#57-model-a-ochrana-údajů)). IRIS část (SQL, `TO_VECTOR`, `VECTOR_COSINE`) platí beze změny.
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
3. **Generace:**
   - jeden Gemini call na sekci: A, B (každá přítomná role včetně posouzení role), B2, red flags (LLM část) a otázky; běží **paralelně** (ThreadPool);
   - teplota 0–0.2, **strukturovaný výstup** (`response_mime_type=application/json` + `response_schema` = pydantic schéma z [§8](#8-datové-kontrakty-fe--be));
   - parametry z konfigurace: úroveň detailu, role, jazyk.
4. **Validace (grounding validátor, `services/ai/grounding.py`):** viz [§5.3](#53-anti-halucinace--grounding-validátor).
5. **Review:** UI zobrazí draft s odlišením AI. Lékař edituje a potvrzuje po sekcích nebo celý závěr.
6. **Zápis:** potvrzení vytvoří FHIR transaction do IRIS ([§4.3 výstupy](#výstupy-zápis-komise-do-iris-jeden-transaction-bundle)) a pak export PDF a FHIR document Bundle.

### 5.2 Evidence ID a citace

- **Formát** = ID z datasetu (D-006):

  | Formát | Příklad | Co znamená |
  |---|---|---|
  | `Pxx-…` | `P03-ecog03` | strukturovaný údaj / celý resource |
  | `Pxx-…#n` | `P03-img03#4` | n-tý odstavec textu |
  | `KRC-2.4` | `KRC-2.4` | pasáž guidelines |
  | `RKT-03` / `RKT-03/V3` | `RKT-03/V3` | studie / kritérium |

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

### 5.4 Red flags

**Hybrid: deterministická pravidla (`services/rules/red_flags.py`) + LLM detekce rozporů.**

- Každý flag má `severity`, `title`, `description`, **≥ 2 citace** (oba zdroje) a **citaci pasáže guidelines**.
- **Prahy jsou převzaté z guidelines datasetu** (OBC = konvence hackathonu). Připomínky onkologů zatím nemáme (Q6).
- Ruční průzkum a očekávané nálezy jsou v [DATASET.md §9](DATASET.md#9-vložené-nesrovnalosti--pracovní-hypotézy-týmu).

| Pravidlo | Podmínka | Severity | Guidelines |
|---|---|---|---|
| `RF-ECOG` | \|poslední ECOG lékaře − `samostatnost` z posledních PROMs\| ≥ 1 | moderate (≥ 2: high) | OBC-1.3 |
| `RF-PROMS` | symptom ≥ 7/10 v posledních PROMs, nebo nárůst ≥ 3 body mezi vyplněními | moderate | OBC-1.3 |
| `RF-TOX` | toxicita podle lékaře (`neuro`, `anem`) nižší než podle pacienta (`brneni` ≥ 5 nebo popis omezení instrumentálních činností: knoflíky, psaní, držení předmětů) | high | KRC-3.2, OBC-1.3 |
| `RF-STALE` | poslední zobrazení (`DiagnosticReport` RAD) starší než **42 dní** k datu MDT (`Task.restriction.period.start`); u plánované resekce jater chybí CT hrudníku | moderate (resekce: high) | OBC-1.2, KRC-2.4 |
| `RF-MISSING` | biomarker s hodnotou /nevyšetřeno\|probíhá\|nedostupn/; povinné podle dg.: C18 → RAS, BRAF, MMR/MSI · C50 HR+/HER2− při progresi → ESR1, PIK3CA/AKT1/PTEN, gBRCA · C34 neskvamózní → EGFR, ALK, PD-L1; dále checklist OBC-1.1 | moderate | OBC-1.1, KRC-1.1, PRS-1.3, PLI-1.3 |
| `RF-MED` | PROMs `leky-mimo` není „nic“ a lék / doplněk / bylina chybí v medikaci; známé interakce (třezalka + CYP3A substrát, např. PARPi) | moderate (interakce: high) | P05-doc03 |
| `RF-NEWSYMPTOM` | PROMs `nove-obtize` obsahuje nový symptom (bolest kosti, neurologický, dušnost) a poslední zpráva na něj nereaguje (LLM) | high | PRS-4.2 |
| `RF-LAB` | Hb pokles ≥ 20 g/l nebo < 100 (< 80: high); marker vzestup ≥ 25 % proti nadiru; Na < 135 s klesajícím trendem; glykémie > 10 při kortikoidech u DM; LVEF pokles ≥ 10 bodů nebo < 50 % | moderate / high | PLI-3.2, OBC-3.1, PRS-3.4, PRS-4.2 |
| `RF-WEIGHT` | úbytek hmotnosti ≥ 5 % za 6 měsíců (`vaha` + PROMs `hmotnost`) nebo pokles albuminu | moderate | OBC-2.3 |
| `RF-GERI` | věk ≥ 70 (extension `vek-k-datu-mdt`) a v dokumentaci chybí G8 / geriatrický screening | low | OBC-2.2 |
| `RF-LESION` | `Condition.verificationStatus = provisional` nebo zobrazení uvádí „nejasné / nelze vyloučit / k dořešení“ bez následné histologie | high | OBC-1.4, PLI-1.2 |
| `RF-GENETIC` | indikace genetického poradenství (rodinná anamnéza v textu, BRCA z NGS nádoru bez germinálního testu) nesplněna | moderate | OBC-2.4, PRS-1.3, PRS-1.4 |
| `RF-NOMINATION` | údaj v nominaci (`ServiceRequest.note`: ECOG, LVEF, toxicita) neodpovídá poslednímu strukturovanému měření | moderate | OBC-1.1 |
| `RF-TNM` | více `tnm` Observation se stejným typem a odlišným stadiem | moderate | OBC-1.1 |
| `RF-IDENTITY` *(konzultace)* | dokument nesedí k pacientovi: strana těla (vlevo/vpravo vs. `Condition.bodySite`), pohlaví, věk, datum mimo časovou osu | high | — |
| `RF-PRIOR-PROC` *(konzultace)* | předchozí výkon v oblasti plánované operace / RT, implantát (port, stent), alergie: informační flag pro chirurga a radiačního onkologa | low (info) | — |
| `RF-DATAQUALITY` *(konzultace)* | data mimo pořadí, nesoulad jednotek, duplicitní nálezy, `Observation` bez `derivedFrom` (mezera v dohledatelnosti) | low | — |
| `RF-LLM` | LLM porovná páry zdrojů (zpráva vs. lab, zpráva vs. PROMs, nominace vs. data) a vrátí rozpory s citacemi; prochází validátorem | podle LLM | — |

Výstup se před potvrzením ukládá v draftu a po potvrzení jako `DetectedIssue` v IRIS.

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
  3. **žádné pořadí jako doporučení** a žádné „doporučujeme“.
- **Klinické studie** (`RKT-01…06`):
  1. pro studie odpovídající diagnóze (a vždy RKT-05 podpůrná a RKT-06 basket) se vyhodnotí každé kritérium `Zn` / `Vn` (`met` / `not_met` / `unknown`) s citací faktu pacienta;
  2. celkový stav: `eligible` / `potentially_eligible` (chybí data) / `not_eligible`;
  3. u `unknown` doplnit, co je potřeba dodat;
  4. u P05 (už ve studii RKT-06) vyhodnotit pravidla protokolu (úprava dávky).
- **Posouzení role** (FR-B7, *konzultace*):
  - pro každou přítomnou roli se vyhodnotí otázka (chirurg: „kandidát resekce?“, radiační onkolog: „kandidát SRS / RT?“, onkolog: „kandidát další linie / studie?“) po kritériích s citacemi;
  - verdikt je `candidate` / `conditional` / `not_candidate` / `insufficient_data`;
  - vždy s poznámkou „podklad, rozhoduje lékař“.
- **Otázky k diskusi:** 2–3 otázky odvozené z red flags, chybějících dat a otázky z nominace.

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

### 5.7 Model a ochrana údajů

**Provider: Google AI Studio, Gemini API** (D-008). SDK `google-genai` (`from google import genai`).

> Existující `GeminiProvider` v `WEB_Template/backend/services/ai_service.py` volá **vypnutý model `gemini-1.5-flash`** a system prompt jen simuluje. Přepsat ho v úkolu T-012:
>
> - `system_instruction`;
> - `response_schema` (structured output);
> - `embed()`;
> - `transcribe()`.

| Účel | Model (výchozí) | Pozn. |
|---|---|---|
| Generace sekcí, red flags (LLM), B2 | **`gemini-3.8-flash`** (stable, doporučený pro nové projekty) | rychlost kvůli NFR-1 |
| Porovnání kvality v evalu | `gemini-4-argon` (flagship, 1M kontext) nebo `gemini-3.1-pro-preview` | rozhodne T-301 podle čísel |
| Levné pomocné úlohy | `gemini-3.5-flash-lite` | např. normalizace textu, klasifikace symptomů |
| Embeddingy | **`gemini-embedding-001`** @ 1536 + L2 normalizace | alternativa `gemini-embedding-2` (auto-normalizace, 8 192 tokenů, bez `task_type`) |
| Přepis audia | `gemini-3.8-flash` (audio vstup) | případně `gemini-3.5-transcribe` |

Model ID se mohou měnit. Před použitím ověřit na [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models) a držet je **jen v env** (`AI_MODEL`, …). **Testy a CI vždy na `AI_PROVIDER=mock`.**

**Podmínky Gemini API, které nás přímo ovlivňují:**

- **V EHP (tedy i v ČR) smí aplikace používat jen placené služby.** Bezplatný tier smí data používat ke zlepšování produktů a k lidské revizi a výslovně se do něj nemají posílat osobní údaje. Proto je nutné **zapnout billing v AI Studio** (Q9).
- V placeném tieru Google prompty k trénování nepoužívá, loguje je ale omezenou dobu kvůli zneužití. Data mohou být dočasně uložena v jakékoli zemi.
- Podmínky **zakazují použití v klinické praxi a pro lékařské rady** a tam, kde je nutné schválení jako zdravotnický prostředek. Prototyp na fiktivních datech je v pořádku. **Cesta do produkce vede přes Vertex AI v EU regionu** (data residency, DPA) + certifikaci podle MDR. Tohle říct v pitchi.

**Pseudonymizace** (`services/ai/pseudonymize.py`):

- dataset PII neobsahuje (pacient = ID, lékaři = kódy `LEK-…`), pipeline ale stavíme jako pro reálná data;
- jméno, rodné číslo, adresa a kontakty se do LLM **nikdy** neposílají;
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

---

## 6. Backend (Django) — struktura

### 6.1 Moduly

Zachováváme modulární monolit z templatu. Nové soubory a složky jsou označené `★`.

```
WEB_Template/backend/
├── apps/
│   ├── authentication/          # beze změny (JWT httpOnly cookies) + role uživatelů (Group)
│   ├── patients/            ★   # čtení z FHIR: seznam, detail, časová osa, evidence resolver
│   ├── mdt/                 ★   # MdtSession, MdtCase, BriefConfig, Decision; potvrzení; export
│   ├── copilot/             ★   # Brief, GenerationJob, LlmCallLog; endpointy generování
│   │   └── management/commands/ ★ iris_init, ingest_dataset, eval_ground_truth, seed_mdt
│   ├── projects/ items/ ws/     # z templatu – skrýt z UI, nemazat (nerozbíjet seed/migrace)
├── services/
│   ├── ai_service.py            # providery; GeminiProvider přepsat (google-genai, schema, embed, transcribe)
│   ├── fhir/                ★   # client.py, ingest.py (sanitize + to_transaction), writeback.py, export.py
│   ├── iris/                ★   # db.py (connect ctx manager), vector_store.py
│   ├── ai/                  ★   # context_builder.py, pseudonymize.py, grounding.py, prompts/*.md
│   └── rules/               ★   # red_flags.py, readiness.py, recist.py, guideline_sets.py
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
| `MdtSession` | `date`, `title` (zaměření komise), `chair` (User), `status` (planned/in_progress/closed) |
| `MdtCase` | `session` FK, `order`, `patient_fhir_id` (`P03`), `service_request_fhir_id` (`P03-zad01`), `question`, `status` (nominated → ready → in_discussion → decided → confirmed) |
| `BriefConfig` | `name`, `owner`, `is_preset`, `sections` JSON (`[{id, enabled, order, detail}]`), `roles_present` JSON, `detail_level` (brief/standard/detailed), `language`, `hide_unverified` |
| `Brief` | `case` FK, `config_snapshot` JSON, `content` JSON (schéma [§8.2](#82-brief-podklad)), `model`, `created_at` |
| `GenerationJob` | `case` FK, `kind` (brief/scribe/patient_summary), `status` (queued/running/done/error), `progress` (0–100), `result_id`, `error` |
| `Decision` | `case` FK, `content` JSON (schéma [§8.4](#84-decision-závěr-komise)), `status` (draft/confirmed), `confirmed_by`, `confirmed_at`, `fhir_ids` JSON, `fhir_bundle` JSON |
| `LlmCallLog` | `purpose`, `provider`, `model`, `prompt_hash`, `tokens_in`, `tokens_out`, `latency_ms`, `ok` |

`seed_mdt` vytvoří zasedání a případy **z nominací v IRIS**: `ServiceRequest.category` (zaměření komise) + `Task.restriction.period.start` (datum MDT). Vzniknou 4 zasedání:

| Datum | Komise | Pacienti |
|---|---|---|
| 2026-10-14 14:00 | Mamární komise (urgentní) | P02 |
| 2026-10-21 14:00 | Mamární komise | P01, P05 (s molekulárním tumor boardem), P06 (s hrudní komisí a urologem) |
| 2026-10-21 14:00 | GIT – kolorektální / hepatobiliární | P03 |
| 2026-10-21 14:00 | Hrudní – karcinom plic | P04 |

Demo uživatelé:

- `predseda` (předseda komise);
- `chirurg`, `onkolog`, `radiolog`, `patolog`, `radioterapeut`;
- 1-click přihlášení jako v templatu.

### 6.3 REST API

Všechny endpointy pod `/api/`, autentizace JWT cookie, schéma v Swaggeru (`/api/docs/`).

| Metoda | Endpoint | Popis |
|---|---|---|
| GET | `/api/patients/` | seznam pacientů (z FHIR `Patient` + primární `Condition`) |
| GET | `/api/patients/{pid}/` | detail: demografie, diagnózy, komorbidity, TNM, ECOG |
| GET | `/api/patients/{pid}/timeline/` | události časové osy s Evidence ID |
| GET | `/api/patients/{pid}/observations/?code=…` | časové řady (labs, hmotnost, ECOG, PROMs skóre) pro grafy |
| GET | `/api/evidence/?id={EvidenceId}` | zdroj citace (text + zvýraznění / hodnota / pasáž guidelines / kritérium studie) |
| GET, POST | `/api/mdt/sessions/` | zasedání |
| GET | `/api/mdt/sessions/{sid}/` | detail + agenda (`MdtCase[]`) |
| POST | `/api/mdt/cases/` | nominace (vytvoří FHIR `ServiceRequest` + `Task`) |
| GET, POST, PUT | `/api/mdt/configs/` · `/api/mdt/configs/{cid}/` | presety konfigurace |
| GET | `/api/mdt/cases/{cid}/readiness/` | kontrola připravenosti (BON-1) |
| POST | `/api/mdt/cases/{cid}/brief/` | `{config_id \| config}`, vrátí `{job_id}` |
| GET | `/api/mdt/cases/{cid}/brief/` | poslední podklad (schéma §8.2) |
| GET | `/api/jobs/{jid}/` | `{status, progress, result_id, error}`; FE polluje à 1 s |
| POST | `/api/mdt/cases/{cid}/scribe/` | multipart `audio` nebo JSON `{transcript}` → přepis (Gemini) → draft závěru (job) (BON-3) |
| GET, PUT | `/api/mdt/cases/{cid}/decision/` | draft závěru (schéma §8.4) |
| POST | `/api/mdt/cases/{cid}/decision/confirm/` | potvrzení: zápis FHIR transaction do IRIS, vrátí `fhir_ids` |
| GET | `/api/mdt/cases/{cid}/export.pdf` | PDF |
| GET | `/api/mdt/cases/{cid}/export.fhir.json` | FHIR document Bundle |
| GET | `/api/mdt/tasks/?status=…` | úkoly po zasedání (z FHIR `Task`) |

---

## 7. Frontend (Next.js 16) — struktura

> **Pozor:** Next.js 16 má breaking changes (např. `middleware.ts` je nově `proxy.ts`). Před psaním kódu si přečti `WEB_Template/frontend/AGENTS.md` a příslušný guide v `node_modules/next/dist/docs/`.

### 7.1 Routy

| Route | Obsah |
|---|---|
| `/login` | z templatu + 1-click demo účty (předseda, chirurg, onkolog…) |
| `/dashboard` | přehled: zasedání (2026-10-14, 2026-10-21), případy a jejich stav, úkoly po termínu |
| `/dashboard/mdt/[sessionId]` | agenda zasedání: pacienti, readiness, stav |
| `/dashboard/mdt/[sessionId]/setup` | **konfigurátor** (sekce, pořadí, role, detail, presety) |
| `/dashboard/cases/[caseId]` | **podklad**: hlavička případu + A / B (záložky rolí s posouzením) / B2 / red flags |
| `/dashboard/cases/[caseId]/record` | **zápis závěru**: editor (sekce jako záznam MDT), úkoly, potvrzení, export |
| `/dashboard/patients/[patientId]` | pacient: časová osa, labs/PROMs grafy, dokumenty, předchozí MDT |
| `/dashboard/tasks` | úkoly po zasedání |

Template stránky `projects`, `storage`, `realtime` a `ai` skrýt z navigace (`DashboardLayout.tsx`).

### 7.2 Klíčové komponenty (`src/components/mdt/` ★)

| Komponenta | Účel |
|---|---|
| `CaseHeader` | sticky hlavička: pacient, věk, diagnóza + TNM, **ECOG lékař vs. pacient**, otázka komise, **komorbidity, alergie, implantáty / předchozí výkony**, počet red flags (orientace do 30 s) |
| `AiBlock` | obal AI obsahu: badge „AI návrh“, odlišný styl (např. fialový levý okraj + ikona ✨ + jemné pozadí), stav `draft` / `confirmed` |
| `Claim` + `CitationChip` | věta s čísly citací `[1]`; `unverified` se zobrazí s varováním |
| `SourceDrawer` | boční panel: zdroj citace se zvýrazněným odstavcem / hodnota + referenční rozsah + zdrojový dokument (`derivedFrom`) / znění pasáže guidelines / kritéria |
| `MissingData` | šedý chip „Údaj chybí v podkladech“ + co doplnit |
| `RedFlagCard` | závažnost (barva), popis, **dva zdroje vedle sebe**, odkaz na pasáž guidelines |
| `EcogCompare` | dvě hodnoty + rozdíl + data + text odpovědi pacienta |
| `Timeline` | horizontální časová osa (dg., léčba, zobrazení, PROMs, předchozí MDT) |
| `TrendChart` | Hb, markery, Na, hmotnost, LVEF, skóre PROMs v čase (doporučení: `recharts`) |
| `RoleTabs` + `RoleAssessmentCard` | záložky podle přítomných rolí; verdikt role po kritériích (FR-B7) |
| `TreatmentOptions` / `TrialScreening` | B2: možnosti s citací pasáží; tabulka kritérií `Zn`/`Vn` × met / not_met / unknown |
| `SectionConfigurator` | zap/vyp sekce, drag & drop pořadí, role, detail; uložit preset |
| `DecisionEditor` | sekce záznamu MDT (jako v datasetu), úkoly (owner, termín), re-MDT; AI předvyplnění odlišené |
| `ConfirmDialog` | potvrzení: kdo potvrzuje, co se zapíše (výpis FHIR resources s ID `Pxx-mdtNN-…`) |
| `JobProgress` | průběh generování (polling `/api/jobs/{id}`) |

### 7.3 UX principy

1. **30 sekund:** `CaseHeader` a 3–5 odrážek souhrnu nad ohybem stránky, bez scrollování.
2. **Každé tvrzení je ověřitelné jedním klikem.** Citace jsou čísla, ne dlouhé odkazy.
3. **AI vs. člověk je vidět na první pohled** (barva, badge, stav).
4. **Prezentační režim** pro projektor: velké písmo, tmavé téma (theme toggle je v templatu).
5. Ovládání klávesnicí: Ctrl+K (command palette z templatu) pro přepínání pacientů v agendě.
6. Typy `src/types/mdt.ts` přesně odpovídají [§8](#8-datové-kontrakty-fe--be). Pro vývoj UI bez backendu existují fixtures `data/fixtures/*.json` (demo pacient P03).

---

## 8. Datové kontrakty (FE ↔ BE)

> **Zdroj pravdy:** backend `apps/copilot/schemas.py` (pydantic; zároveň `response_schema` pro Gemini) ↔ frontend `src/types/mdt.ts`. Při změně uprav obojí + tuto sekci + fixtures.

### 8.1 Společné typy

```ts
type EvidenceId = string;                       // "P03-ecog03" | "P03-img03#4" | "KRC-2.4" | "RKT-03/V3"
type Verification = "verified" | "unverified";
type Severity = "high" | "moderate" | "low";
type RoleId = "surgeon" | "oncologist" | "radiation_oncologist" | "radiologist" | "pathologist" | "patient";
type SectionId = "summary" | "timeline" | "role_views" | "red_flags" | "decision_support" | "trials" | "questions";

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
  status: "met" | "not_met" | "unknown";
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
    display_name: string;                       // "Pacient P03"
    age: number;                                // extension vek-k-datu-mdt
    sex: "male" | "female" | "other" | "unknown";
    diagnosis: { text: string; icd10: string; citation: EvidenceId };
    tnm?: { text: string; stage?: string; citation: EvidenceId };   // dataset má TNM jako text
    ecog: {
      physician?: { value: number; date: string; citation: EvidenceId };   // Observation 89247-1
      patient?:   { value: number; date: string; citation: EvidenceId; answer_text: string };  // PROMs samostatnost
    };
    mdt_question: { text: string; citation: EvidenceId };   // ServiceRequest.reasonCode.text
    mdt_date: string;                                       // Task.restriction.period.start
    comorbidities: { text: string; icd10?: string; citation: EvidenceId }[];
    alerts: Claim[];                            // alergie, implantáty, předchozí výkony (FR-A4)
  };
  sections: BriefSection[];                     // v pořadí podle config
  red_flags: RedFlag[];
  decision_support?: DecisionSupport;
  stats: { claims_total: number; claims_unverified: number; missing_total: number };
}

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

interface TimelineEvent {                       // GET /api/patients/{pid}/timeline/
  date: string;
  type: "diagnosis" | "procedure" | "medication" | "imaging" | "pathology" | "lab" | "proms" | "mdt" | "document";
  label: string;
  citation: EvidenceId;
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
    provenance: string;  document_reference_pdf?: string;
  };
}
```

### 8.5 BriefConfig

```ts
interface BriefConfig {
  id?: string;
  name: string;
  sections: { id: SectionId; enabled: boolean; order: number; detail?: "brief" | "standard" | "detailed" }[];
  roles_present: RoleId[];                      // ovlivní role_views, posouzení i záložky
  detail_level: "brief" | "standard" | "detailed";
  language: "cs" | "sk" | "en";
  hide_unverified: boolean;
}
```

---

## 9. Konfigurace (env proměnné)

| Proměnná | Kde | Příklad / pozn. |
|---|---|---|
| `BACKEND_URL` | Vercel (server) | `https://api.<doména>` (rewrites) |
| `NEXT_PUBLIC_API_URL` | Vercel / lokálně | `''` na Vercelu (same-origin), lokálně `http://localhost:8000` |
| `IRIS_HOST` / `IRIS_PORT` | backend | `iris` / `1972` |
| `IRIS_NAMESPACE` | backend | `FHIRSERVER` |
| `IRIS_USER` / `IRIS_PASSWORD` | backend | dev `SuperUser` / `SYS`, **na VPS jiné** |
| `FHIR_BASE_URL` | backend | `http://iris:52773/fhir/r4` |
| `DATASET_DIR` | backend | `/data/dataset` (kontejner) · lokálně `../Dataset_MDT_Copilot_v1.1_pre_timy/Dataset_MDT_Copilot_v1.1` |
| `AI_PROVIDER` | backend | `gemini` (prod) / `mock` (testy, CI) |
| `GEMINI_API_KEY` | backend | Google AI Studio, **placený tier**; nikdy do gitu ani do frontendu |
| `AI_MODEL` | backend | `gemini-3.8-flash` |
| `AI_MODEL_STRONG` | backend | `gemini-4-argon` (volitelně, pro porovnání a těžké sekce) |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | backend | `gemini-embedding-001` / `1536` |
| `TRANSCRIBE_MODEL` | backend | `gemini-3.8-flash` |
| `GROUNDING_MIN_SIMILARITY` | backend | `0.55` (ladit podle evalu) |
| `CSRF_TRUSTED_ORIGINS` / `CORS_ALLOWED_ORIGINS` | backend | Vercel doména(y) |

---

## 10. Lokální vývoj

```powershell
# celý stack (Next.js, Django, Postgres, Redis, Mailhog, Traefik) + IRIS (po T-002)
cd WEB_Template
.\dev.ps1 up                       # nebo: make dev
docker compose -f docker-compose.dev.yml exec backend python manage.py iris_init
docker compose -f docker-compose.dev.yml exec backend python manage.py ingest_dataset          # celý dataset
docker compose -f docker-compose.dev.yml exec backend python manage.py ingest_dataset --patients P03 --skip-vectors   # rychle, bez Gemini
```

- **Jen frontend** (doporučeno pro UI lane): `cd WEB_Template/frontend && npm run dev`. Pak buď `BACKEND_URL` na nasazený backend, nebo práce nad fixtures v `data/fixtures/`.
- **Kontrola IRIS:**
  - `curl -u SuperUser:SYS http://localhost:52773/fhir/r4/metadata` vrátí 200;
  - `…/fhir/r4/Observation?patient=P03&_summary=count` vrátí `total` 85.
- **Reset dat:** `docker compose -f docker-compose.dev.yml down -v`. Smaže **i** Postgres volume.
- Porty: FE 3000, BE 8000, Postgres 5432, Redis 6379, Mailhog 8025, Traefik 8080, IRIS 1972 / 52773.

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
| Q7 | Podpora `Patient/$everything` a import mCODE IG ve verzi IRIS | ⬜ otestovat / O. Hoferek |
| Q8 | Kdy a v jakém formátu bude oficiální ground truth? | ⬜ Ľ. Piljan |
| Q9 | Kdo zapne billing (placený tier) v Google AI Studio? Bez něj nesmíme posílat data | ⬜ tým |

---

## 12. Zdroje

- Zadání: `WEB_Template/MDT_Copilot_zadani_upravené_2026_v02.pptx` (Asseco CE)
- Dataset: `Dataset_MDT_Copilot_v1.1_pre_timy/Dataset_MDT_Copilot_v1.1/README.md` + [DATASET.md](DATASET.md)
- [InterSystems Challenge at Rakathon 2026](https://developer.intersystems.com/intersystems-challenge-at-rakathon-2026/)
- [FHIR-AI-Hackathon-Kit (V2)](https://github.com/intersystems-community/FHIR-AI-Hackathon-Kit): tutoriály 3.x FHIR, 3.5 FHIR SQL Builder, 4.1 Vector Search, 5.1 agenti, 5.2 MCP; `skills/`
- [iris-agentic-dev](https://github.com/intersystems-community/iris-agentic-dev): MCP pro AI coding agenty nad IRIS
- Gemini API: [modely](https://ai.google.dev/gemini-api/docs/models) · [embeddingy](https://ai.google.dev/gemini-api/docs/embeddings) · [audio](https://ai.google.dev/gemini-api/docs/audio) · [podmínky](https://ai.google.dev/gemini-api/terms)
- [Rakathon 2026](https://www.rakathon.cz/eng): harmonogram
- HL7 [FHIR R4](https://hl7.org/fhir/R4/) · [mCODE](https://hl7.org/fhir/us/mcode/) · HL7 Europe Common Cancer Model (ECCDM, 1.0.0-ballot) · [IPS](https://hl7.org/fhir/uv/ips/) · [Patient $everything](https://www.hl7.org/fhir/R4/operation-patient-everything.html)
- Klinika: ESMO guidelines · RECIST 1.1 · EORTC QLQ-C30 · PRO-CTCAE
