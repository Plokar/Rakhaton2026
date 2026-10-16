# Dataset MDT Copilot v1.1 — průvodce pro vývojáře a AI agenty

> Dataset od Asseco CE pro zadání MDT Copilot. **Všechna data jsou fiktivní** a klinicky neověřená. Smí do gitu a repo je veřejné (rozhodnutí týmu).
>
> **Umístění:** `Dataset_MDT_Copilot_v1.1_pre_timy/Dataset_MDT_Copilot_v1.1/`. V kódu vždy přes proměnnou `DATASET_DIR`, cestu nehardcoduj.
>
> Architektura: [ARCHITEKTURA.md](ARCHITEKTURA.md) · úkoly: [PROGRESS.md](PROGRESS.md) · pravidla: [AGENTS.md](AGENTS.md) · požadavky lékaře: [docs/POZADAVKY_LEKARE.md](docs/POZADAVKY_LEKARE.md)

---

## 0. TL;DR pro agenty

1. **Dataset už je HL7 FHIR R4.** Každý pacient je jeden `Bundle` (`type: collection`) se 142–215 resources. Nic se nemusí „mapovat do FHIR“, jen **převést `collection` na `transaction`** a nahrát do IRIS ([§6](#6-ingest-do-iris-fhir)).
2. **Dvě vady, kvůli kterým IRIS bundle odmítne:**
   - ID s podtržítkem (`P01-lab01-hb_f`), které FHIR nepovoluje;
   - prázdný string (`P03-prom02`, odpověď `bolest-misto`).

   Obě opravuje sanitizace při ingestu ([§6.2](#62-sanitizace-povinná)).
3. **ID zdroje = citační klíč.** `Pxx_pacient.md` označuje každý záznam `[P03-img02]` a ve FHIR je to `id`. AI cituje tato ID, guidelines se citují `KRC-2.4` a kritéria studií `RKT-03/V3`.
4. **Ground truth v této verzi chybí.** Organizátor ho zveřejní až po odevzdání. Pro vývoj máme vlastní hypotézy v [§9](#9-vložené-nesrovnalosti--pracovní-hypotézy-týmu) a evaluační sadu stavíme v úkolu T-013.
5. **Za běhu se čte jen z IRIS**, ne z JSON souborů. Soubory slouží jen pro ingest, testy a čtení člověkem (`.md`).
6. Data jsou malá: celý pacient má cca 8–12 tisíc tokenů textu a guidelines 42 pasáží. Kompletní kontext se vejde do jednoho LLM callu, viz [ARCHITEKTURA §5.1](ARCHITEKTURA.md#51-pipeline).

---

## 1. Soubory

```
Dataset_MDT_Copilot_v1.1/
├── README.md                                    originální popis od organizátora
├── pacienti/Pxx/Pxx_bundle.json                 FHIR R4 Bundle (collection), kompletní pacient
├── pacienti/Pxx/Pxx_pacient.md                  totéž čitelně, s ID zdrojů [Pxx-…]; NEPOSÍLAT do LLM (bereme z FHIR)
├── fhir/bundles.ndjson                          6 bundlů pacientů, jeden na řádek (hromadný import)
├── dotaznik/dotaznik_PROMs.md                   popis dotazníku MDT-PROMS-1
├── dotaznik/dotaznik_PROMs_Questionnaire.json   FHIR Questionnaire MDT-PROMS-1
├── guidelines/{KRC,OBC,PLI,PRS}_*.md            výtahy z doporučených postupů, číslované pasáže
├── studie/studie.md | studie.json               6 fiktivních studií s kritérii (čitelně / strojově)
└── studie/studie_ResearchStudy_bundle.json      totéž jako FHIR (6× ResearchStudy + 6× Group), type collection
```

**Chybí oproti README organizátora:** `ground_truth/` (bude po odevzdání) a přepis diskuse MDT (bonus; obstaráme si sami, viz [ARCHITEKTURA §5.6](ARCHITEKTURA.md#56-ai-zapisovatel-bon-3)).

---

## 2. Pacienti

| ID | Pohlaví, věk | Diagnózy (MKN-10) | Otázka pro MDT (zkráceně) | MDT | Předchozí MDT | Guidelines | Studie (hypotéza) |
|---|---|---|---|---|---|---|---|
| **P01** | Ž, 63 | C50.4 HR+/HER2-low · C78.7 játra · C79.5 kost | progrese po letrozolu + ribociklibu: další linie (endokrinní podle biomarkerů / T-DXd / chemo), RKT-01? | 2026-10-21 | `P01-mdt01` | PRS, OBC | RKT-01, RKT-06 |
| **P02** | Ž, 68 | C50.4 HER2+ · C78.0 plíce · C79.3 mozek | 2 nové mozkové metastázy: SRS + pokračovat PH, nebo změna linie (T-DXd / RKT-02)? | 2026-10-14 (urgentní) | `P02-mdt01` | PRS, OBC | RKT-02 |
| **P03** | M, 67 | C18.7 sigma · C78.7 játra | resekabilita jaterních metastáz po 8× FOLFOX + bevacizumab, pořadí výkonů | 2026-10-21 | `P03-mdt01` | KRC, OBC | RKT-03, RKT-05 |
| **P04** | M, 70 | C34.1 PHL · C77.1 uzliny | st. III single-station N2: resekce po neoadjuvantní chemoimunoterapii, nebo CHRT? Operabilita? | 2026-10-21 | `P04-mdt01` | PLI, OBC | RKT-04, RKT-05 |
| **P05** | Ž, 68 | C50.4 HR+/HER2-low · C78.7 · C79.5 · C77.8 | ve studii RKT-06 (PARPi) PR, ale opakovaná anémie G3: pokračovat v redukci, nebo změnit? Germinální BRCA2? | 2026-10-21 | `P05-mdt01`, `P05-mdt02` | PRS, OBC | RKT-06 (zařazena) |
| **P06** | Ž, 76 | C50.4 HER2+ · C78.0 (provizorně) · D41.0 ledvina | smíšená odpověď: rostoucí plicní ložisko (metastáza vs. 2. primární nádor), rebiopsie, pořadí řešení ledviny | 2026-10-21 | `P06-mdt01` | PRS, OBC | RKT-02 |

**Počty resources v bundlech:**

| | Patient | Org | Practitioner | Condition | DocumentReference | DiagnosticReport | ImagingStudy | Observation | MedicationRequest | MedicationAdministration | Procedure | QuestionnaireResponse | ServiceRequest | Task | Composition | CarePlan | CareTeam | **Σ** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P01 | 1 | 1 | 8 | 5 | 7 | 14 | 6 | 86 | 4 | 20 | 4 | 2 | 1 | 1 | 2 | 1 | 1 | **164** |
| P02 | 1 | 1 | 9 | 5 | 11 | 13 | 6 | 106 | 5 | 45 | 2 | 2 | 1 | 1 | 2 | 1 | 1 | **212** |
| P03 | 1 | 1 | 8 | 5 | 7 | 12 | 4 | 85 | 5 | 32 | 3 | 2 | 1 | 1 | 2 | 1 | 1 | **171** |
| P04 | 1 | 1 | 9 | 5 | 6 | 12 | 4 | 91 | 3 | 0 | 2 | 2 | 1 | 1 | 2 | 1 | 1 | **142** |
| P05 | 1 | 1 | 12 | 5 | 10 | 13 | 4 | 110 | 3 | 5 | 3 | 2 | 1 | 1 | 4 | 2 | 2 | **179** |
| P06 | 1 | 1 | 11 | 6 | 11 | 14 | 5 | 100 | 5 | 50 | 3 | 2 | 1 | 1 | 2 | 1 | 1 | **215** |

`Organization/ORG-FN` je **sdílená** všemi bundly (obsah je identický, `PUT` je idempotentní). Ostatní ID jsou unikátní napříč datasetem, protože nesou prefix pacienta.

Celkem je unikátních resources 1 078 + `Questionnaire` + 12 resources studií = **1 091**. Tyto počty slouží jako kontrola po ingestu (T-101).

---

## 3. Konvence ID (= citační klíče)

| Vzor | Resource | Význam |
|---|---|---|
| `P03` | Patient | pacient |
| `ORG-FN` | Organization | fiktivní fakultní nemocnice (sdílená) |
| `LEK-P03-01` | Practitioner | lékař (kód + odbornost v `name.text` a `qualification.code.text`, **bez jmen**) |
| `P03-dg1`, `P03-dg2` | Condition | onkologické diagnózy (`category.text = "onkologická diagnóza"`) |
| `P03-kom1…` | Condition | komorbidity (`category.text = "komorbidita"`) |
| `P05-ae1` | Condition | nežádoucí účinek léčby (`category.text = "nežádoucí účinek léčby"`; v datasetu jen tento, D64.8 anémie G3 při PARPi) |
| `P03-doc01…` | DocumentReference | lékařské zprávy (ambulance, propouštěcí, konzilia) |
| `P03-pat01…` | DiagnosticReport (SP) | patologie, molekulární patologie |
| `P03-img01…` | DiagnosticReport (RAD) | popis zobrazení (CT/MR/PET/scinti/mamografie) |
| `P03-img01-study` | ImagingStudy | metadata studie (modalita DICOM), **bez snímků** |
| `P03-lab01…` | DiagnosticReport (LAB) | laboratorní panel jednoho odběru (`result[]`) |
| `P03-lab01-<param>` | Observation | jedna lab. hodnota (viz [§4.3](#43-laboratoř-param-v-id--loinc)) |
| `P03-ecog01…` | Observation | ECOG hodnocený **lékařem** |
| `P03-vaha01…` | Observation | hmotnost |
| `P03-bm01…` | Observation | biomarker (ER, PR, HER2, Ki-67, KRAS, EGFR, PD-L1, BRCA…) |
| `P03-tnm01…` | Observation | TNM (klinické / patologické), `focus` → Condition |
| `P03-neuro01`, `P05-anem01` | Observation | toxicita (CTCAE) hodnocená lékařem |
| `P02-lvef01…` | Observation | LVEF (echo) |
| `P04-spiro01…` | Observation | funkční vyšetření plic (FEV1, DLCO, ppoFEV1, ppoDLCO) |
| `P04-kour01` | Observation | kouření |
| `P03-med01…` | MedicationRequest | chronická medikace (ATC) |
| `P03-tx-<lék>-NN` | MedicationAdministration | jednotlivá podání protinádorové léčby (`oxa`, `5fu`, `lv`, `bev`, …) |
| `P03-proc01…` | Procedure | výkony, radioterapie, transfuze |
| `P03-prom01`, `P03-prom02` | QuestionnaireResponse | 2 vyplnění dotazníku pacientem |
| `P03-zad01` | ServiceRequest | **nominace na MDT** (žádanka) |
| `P03-zad01-task` | Task | stav žádanky + termín zasedání |
| `P03-mdt01` | Composition | **předchozí záznam MDT** |
| `P03-mdt01-careplan` / `-careteam` | CarePlan / CareTeam | doporučení / účastníci předchozího MDT |
| `P03-mdt01-rozhodnuti` | Composition | rozhodnutí ošetřujícího lékaře po MDT (+ stanovisko pacienta) |
| `KRC-2.4` | (guideline pasáž) | citace doporučeného postupu |
| `RKT-03`, `RKT-03/V3` | ResearchStudy / kritérium | studie / kritérium zařazení `Zn` nebo vyřazení `Vn` |

> **Sanitizované ID:** 26 Observation má v ID `_` (`Pxx-labNN-hb_f`, Hb s referencí pro ženy: P01, P02, P05, P06). Ve FHIR je ukládáme jako `Pxx-labNN-hb-f` ([§6.2](#62-sanitizace-povinná)). V `.md` zůstává původní tvar. **Citace a API vždy používají FHIR (sanitizované) ID.**

---

## 4. FHIR model datasetu: kde co je

### 4.1 Resources a klíčová pole

| Resource | Kde je informace | Poznámky |
|---|---|---|
| `Patient` | `gender`, `birthDate` (jen rok, např. `"1959"`), věk k datu MDT v extension `…/vek-k-datu-mdt` | `name.text = "Pacient P03 (fiktivní)"`, žádné PII |
| `Condition` | `code` MKN-10 (`http://hl7.org/fhir/sid/icd-10`), `onsetDateTime` (i částečné `"2019-03"`), `bodySite.text`, `stage[].summary.text` (TNM jako text), extension `…/icd-o-3-morfologie`, `…/icd-o-3-topografie` | `category.text` odliší diagnózu (`onkologická diagnóza`), komorbiditu (`komorbidita`) a nežádoucí účinek léčby (`nežádoucí účinek léčby`, `P05-ae1`); `verificationStatus` může být `provisional` (P06-dg2) |
| `DocumentReference` | **plný text** v `content[0].attachment.data` (base64, UTF-8, `text/plain`), `type` LOINC, `category[0].text` = oddělení (např. `"A-ONK – Ambulance klinické onkologie"`), `date`, `author` | typy LOINC: 11506-3 Progress note (29), 11488-4 Consult note (10), 28570-0 Procedure note (7), 34552-0 Cardiology note (4), 18842-5 Discharge summary (2) |
| `DiagnosticReport` | `category` v2-0074: `SP` patologie, `RAD` zobrazení, `LAB` laboratoř; **text** v `presentedForm[0].data` (base64); `conclusion` = závěr; `imagingStudy` → ImagingStudy; `result[]` → lab Observation | 2. položka `category[].text` = pracoviště (RDG, NM, PAT-B, PAT-M…) |
| `ImagingStudy` | `modality` (DICOM: CT, MR, PT, NM, MG…), `started`, `description` | snímky nejsou (`…/snimky-v-pacs` = „ne“) |
| `Observation` | viz [§4.2](#42-observation--taxonomie); `derivedFrom` → **zdrojový dokument** (důležité pro citace a dohledatelnost) | |
| `MedicationRequest` | chronická medikace: `medicationCodeableConcept` ATC, `dosageInstruction[0].text`, `authoredOn` | změny dávek jsou v textu dávkování |
| `MedicationAdministration` | podání: `effectiveDateTime`, `dosage.text`, `category.text` = režim (např. „protinádorová léčba – FOLFOX + bevacizumab“), `note` = redukce a důvody | P04 nemá žádné |
| `Procedure` | `code.text`, `category.text` (chirurgický výkon, bioptický, radioterapie, transfuze…), `performedDateTime` / `performedPeriod`, `report` → DocumentReference | |
| `QuestionnaireResponse` | `questionnaire` = `https://rakathon.example.org/fhir/Questionnaire/MDT-PROMS-1`, `authored`, `item[].linkId` + `answer[]` | viz [§5](#5-dotazník-proms-mdt-proms-1) |
| `ServiceRequest` (nominace) | **otázka pro MDT = `reasonCode[0].text`**; typ otázky `reasonCode[0].coding` (`mdt-typ-otazky`); typ projednání `code` (`mdt-typ-projednani`); `category[0].text` = zaměření komise; `priority`; `requester`; `occurrenceDateTime` = **nejzazší požadovaný termín**; `reasonReference` → diagnózy; **`supportingInfo[]` = podklady** vybrané lékařem; `note[]` = histologie, předchozí léčba, komorbidity, preference pacienta; extension `…/mdt-pacient-informovan`, `…/mdt-zadajici-pracoviste` | |
| `Task` (stav žádanky) | `focus` → ServiceRequest, `businessStatus` (`mdt-stav-zadanky`: `naplanovana`), **`restriction.period.start` = datum a čas zasedání MDT** | |
| `Composition` „Záznam MDT“ | `type` `mdt-typ-zaznamu#mdt-zaznam`, `category` (typ projednání + zaměření), `date`, `author` = předsedající, `attester` (legal), `event[0].detail` → CarePlan + CareTeam, `section[]` (title + XHTML `text.div`), extension `…/mdt-forma-zasedani`, `…/mdt-osetrujici-lekar`, `…/mdt-ucast-pacienta` | **vzor pro náš výstup**, viz [ARCHITEKTURA §4.3](ARCHITEKTURA.md#43-fhir-datový-model) |
| `CarePlan` | `category` léčebný záměr (`mdt-lecebny-zamer`), `activity[].detail.code` modalita (`mdt-modalita`) + `description`, `careTeam` | |
| `CareTeam` | `participant[].role[0].text` (odbornost) + `member` | člen může chybět (jen role) |
| `Composition` „Rozhodnutí o léčbě“ | `relatesTo` (`appends`) → záznam MDT; sekce Léčebný záměr, Zvolený postup, Vztah k doporučení MDT, **Stanovisko pacienta** | |

**Sekce `Composition` „Záznam MDT“** (pořadí podle datasetu):

1. Projednaná otázka
2. Klinické zhodnocení
3. Léčebný záměr
4. Doporučený postup
5. *(Doplňující diagnostika)*
6. Klinická studie
7. *(Plánované re-MDT)*
8. Závěr MDT

### 4.2 Observation — taxonomie

| Prefix ID | `category` | `code` | Hodnota |
|---|---|---|---|
| `lab` | `laboratory` + v2-0074 `HM` / `CH` / `IMM` (text Hematologie / Biochemie / Imunochemie) | LOINC | `valueQuantity` (UCUM), `referenceRange`, `interpretation` H/L |
| `ecog` | `survey` | LOINC **89247-1** (text „ECOG – hodnoceno lékařem“) | `valueInteger` 0–4, `performer` = Practitioner |
| `vaha` | `vital-signs` | LOINC 29463-7 | `valueQuantity` kg |
| `bm` | `laboratory` + text „Biomarker / molekulární patologie“ | **jen `code.text`** (ER, PR, HER2 IHC, Ki-67, KRAS, NRAS, BRAF V600E, MMR/MSI, PD-L1, ALK, ROS1, EGFR, ESR1, PIK3CA/AKT1/PTEN, BRCA, TMB, TTF-1, GATA3…) | `valueString` (např. `"nevyšetřeno"`, `"1+ (HER2-low)"`), `specimen.display` |
| `tnm` | text „Staging“ | `code.text` „TNM (klinické)“ / „TNM (patologické)“ | `valueString`, `focus` → Condition |
| `neuro`, `anem` | text „Toxicita léčby“ | `code.text` (CTCAE, hodnocení lékařem) | `valueString` `"grade 1"` |
| `lvef` | text „Kardiologie“ | `code.text` LVEF | `valueQuantity` % |
| `spiro` | text „Funkční vyšetření plic“ | FEV1, DLCO, ppoFEV1, ppoDLCO | `valueString` |
| `kour` | text „Rizikové faktory“ | Kouření | `valueString` |

> Biomarkery, TNM a toxicita **nemají kódy** (jen text). Pro export do mCODE (BON-5) je mapujeme při zápisu, vstup neměníme.
>
> Hodnota `"nevyšetřeno"` / `"vyšetření probíhá"` je **chybějící údaj**. Je důležitá pro readiness a pro screening studií (`unknown`).

### 4.3 Laboratoř (param v ID → LOINC)

| param | LOINC | Parametr | Jednotka |
|---|---|---|---|
| `hb` / `hb_f` (→ `hb-f`) | 718-7 | Hemoglobin (`hb_f` = referenční meze pro ženy 120–160) | g/l |
| `leu` | 6690-2 | Leukocyty | 10^9/l |
| `neu` | 751-8 | Neutrofily abs. | 10^9/l |
| `plt` | 777-3 | Trombocyty | 10^9/l |
| `krea` | 14682-9 | Kreatinin | µmol/l |
| `bili` | 14631-6 | Bilirubin celkový | µmol/l |
| `alt` | 1742-6 | ALT | µkat/l |
| `ast` | 1920-8 | AST | µkat/l |
| `alp` | 6768-6 | ALP | µkat/l |
| `alb` | 1751-7 | Albumin | g/l |
| `na` / `k` | 2951-2 / 2823-3 | Sodík / Draslík | mmol/l |
| `glu` | 15074-8 | Glukóza | mmol/l |
| `crp` | 1988-5 | CRP | mg/l |
| `ldh` | 14804-9 | LD | µkat/l |
| `cea` | 2039-6 | CEA | µg/l |
| `ca199` | 24108-3 | CA 19-9 | kU/l |
| `ca153` | 6875-3 | CA 15-3 | kU/l |

- Odběry jsou číslované `lab01…lab07` chronologicky.
- Některé hodnoty v odběru chybí. Například P04 CEA má jen odběry 01, 03 a 05 a v `.md` je na jejich místě `—`.
- UCUM kódy: `g/L`, `ug/L`, `10*9/L`… Jednotka pro zobrazení je v `valueQuantity.unit` (např. `µg/l`).

### 4.4 Lokální číselníky a extensions

Systémy `https://rakathon.example.org/fhir/...` jsou **jen jména (URI), nic se z nich nestahuje**.

| CodeSystem | Kódy |
|---|---|
| `mdt-typ-projednani` | `primarni` Primární projednání · `progrese` Progrese / recidiva · `restaging` Restaging / hodnocení odpovědi |
| `mdt-typ-otazky` | `systemova-lecba` · `klinicka-studie` · `indikace-rt` · `indikace-operace` · `lecebny-plan` · `diagnosticka-nejasnost` |
| `mdt-lecebny-zamer` | `kurativni` · `paliativni` · `odlozeno` (rozhodnutí odloženo, doplnit diagnostiku) |
| `mdt-modalita` | `chirurgie` · `chemoterapie` · `rt` · `hormonalni` · `cilena` · `imunoterapie` · `jina-systemova` · `diagnostika` · `sledovani` |
| `mdt-typ-zaznamu` | `mdt-zaznam` Záznam MDT · `rozhodnuti-o-lecbe` Rozhodnutí o léčbě |
| `mdt-stav-zadanky` | `naplanovana` (v datasetu jen tento; pro výstup přidáváme `projednana`) |
| `proms-odpovedi` | odpovědi choice otázek dotazníku ([§5](#5-dotazník-proms-mdt-proms-1)) |

Identifier systémy (`…/sid/…`): `pacient`, `lekar`, `accession`, `mdt-zaznam`, `mdt-zadanka`, `studie`.

Extensions (`…/StructureDefinition/…`):

- `vek-k-datu-mdt`;
- `icd-o-3-morfologie`, `icd-o-3-topografie`;
- `snimky-v-pacs`;
- `mdt-forma-zasedani`, `mdt-osetrujici-lekar`, `mdt-ucast-pacienta`, `mdt-pacient-informovan`, `mdt-zadajici-pracoviste`.

### 4.5 Graf referencí (pro context builder a citace)

```
ServiceRequest (nominace) ──supportingInfo──▶ podklady (DiagnosticReport, DocumentReference, Observation, Composition)
      ▲ focus                └─reasonReference─▶ Condition (dg)
Task (stav, termín MDT)
Observation ──derivedFrom──▶ DocumentReference / DiagnosticReport   (strukturovaná hodnota ← zdrojový text)
DiagnosticReport(LAB) ──result──▶ Observation (lab)
DiagnosticReport(RAD) ──imagingStudy──▶ ImagingStudy
Procedure ──report──▶ DocumentReference
Composition(mdt) ──event.detail──▶ CarePlan + CareTeam ;  Composition(rozhodnutí) ──relatesTo(appends)──▶ Composition(mdt)
Všechno klinické ──subject/for──▶ Patient ;  autoři ──▶ Practitioner LEK-Pxx-nn
```

**Tip:** `Observation.derivedFrom` umožní ke strukturovanému faktu (např. ECOG 0) ukázat i větu ze zprávy, ze které pochází. Ve `SourceDrawer` zobrazit obojí.

---

## 5. Dotazník PROMs (MDT-PROMS-1)

- Vlastní ilustrační dotazník. Tematicky odpovídá EORTC QLQ-C30, PRO-CTCAE a Distress Thermometer, jejich znění ale nepřebírá.
- Škály 0–10: **0 = žádné potíže, 10 = nejhorší**.
- Každý pacient má **2 vyplnění** (`Pxx-prom01`, `Pxx-prom02`).

| linkId | Otázka | Typ | Použití v Copilotu |
|---|---|---|---|
| `bolest`, `unava`, `nevolnost`, `dusnost`, `chut`, `brneni`, `prujem`, `psychika`, `spanek` | symptomy 0–10 | integer | trend mezi vyplněními; **≥ 7 = výrazná zátěž** (OBC-1.3) |
| `bolest-misto` | kde bolí | string | lokalizace nové bolesti (PRS-4.2) |
| **`samostatnost`** | Jak zvládáte běžný den? | choice `0`–`4` | **ECOG podle pacienta** (kód = stupeň ECOG), srovnání s `ecog` lékaře (OBC-1.3) |
| `chuze` | Kolik zvládnete ujít? | choice `bez-omezeni` · `1-patro` · `1-patro-zastavka` · `rovina` · `byt` | výkonnost, operabilita (PLI-3.1) |
| `hmotnost`, `hmotnost-zmena` | kg, změna za 3 měsíce | decimal | nutriční screening (OBC-2.3) |
| `nove-obtize` | nové obtíže (volný text) | string | **nové symptomy**, často klíč k red flag |
| `alergie` | alergie | string | |
| `leky-mimo` | léky, doplňky, byliny navíc | string | **porovnat s medikací**: interakce (např. třezalka) |
| `priorita` | co je nejdůležitější | choice `delka` · `kvalita` · `oboji` · `nevim` | preference pro B (pohled pacienta) |
| `postoj` | co mají lékaři vědět | string | preference, obavy |
| `podpora` | podpora v domácnosti | choice `dostatecna` · `castecna` · `zadna` | sociální kontext |

---

## 6. Ingest do IRIS FHIR

### 6.1 Postup (`python manage.py ingest_dataset`, úkol T-101)

1. **Questionnaire** `dotaznik/dotaznik_PROMs_Questionnaire.json` → `PUT Questionnaire/MDT-PROMS-1`.
2. **Studie** `studie/studie_ResearchStudy_bundle.json` → sanitizace → transaction (Group + ResearchStudy v jednom bundlu).
3. **Pacienti** `pacienti/Pxx/Pxx_bundle.json` (nebo `fhir/bundles.ndjson`): pro každého pacienta sanitizace ([§6.2](#62-sanitizace-povinná)) → transaction → `POST {FHIR_BASE_URL}/`.
4. **Kontrola:** `GET /Observation?patient=P03&_summary=count` atd. se porovná s tabulkou v [§2](#2-pacienti). Rozdíl znamená chybu ingestu.
5. **Texty → vektory:** dekódovat `DocumentReference.content[].attachment.data`, `DiagnosticReport.presentedForm[].data` a `Composition.section[].text.div` (odstranit XHTML), rozdělit na odstavce a uložit do `MDT.EvidenceChunk` ([ARCHITEKTURA §4.5](ARCHITEKTURA.md#45-vektorové-tabulky-iris-sql-namespace-fhirserver)).
6. **Guidelines → `MDT.GuidelineChunk`:** 1 pasáž = 1 řádek. **Studie → `MDT.TrialCriterion`:** 1 kritérium = 1 řádek.

Bundle `collection` FHIR server **nezpracuje**. Musí to být `transaction` a každý entry potřebuje `request`:

```python
def to_transaction(bundle: dict) -> dict:
    entries = []
    for e in bundle["entry"]:
        r = sanitize(e["resource"])                       # §6.2
        rtype, rid = r["resourceType"], r["id"]
        entries.append({
            "fullUrl": f"https://rakathon.example.org/fhir/{rtype}/{rid}",
            "resource": r,
            "request": {"method": "PUT", "url": f"{rtype}/{rid}"},   # idempotentní upsert, ID z datasetu
        })
    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}
```

**Implementace (T-101):**

- Logika je v `services/fhir/ingest.py` (`collect` bez sítě, `ingest` nahraje a ověří), příkaz jen obaluje:

  ```bash
  python manage.py ingest_dataset                       # celý dataset (1 091 resources) + kontrola počtů
  python manage.py ingest_dataset --patients P03,P05    # Questionnaire + studie + vybraní pacienti
  python manage.py ingest_dataset --dry-run             # bez sítě: sanitizace + počty ze souborů
  python manage.py ingest_dataset --bundle-type batch   # když IRIS transakci odmítne: chyby po resources
  ```
- Entries v transakci jsou seřazené tak, aby odkazované resources byly před těmi, které na ně odkazují (`order_by_references`), a mají `fullUrl` `https://rakathon.example.org/fhir/Type/id`.
- Kontrola počtů: každý resource přes `GET Type?_id=…&_summary=count` (přesně) a pacientské typy přes `?patient=Pxx` (aspoň tolik, víc je v pořádku, protože aplikace zapisuje `Pxx-mdtNN…`).
- Index `ID → ResourceType` je funkce `services/fhir/ids.py` `resource_type_for_id` podle konvence z §3 (+ výstupy z ARCHITEKTURA §4.3). Test ověřuje, že sedí pro všech 1 091 resources. `parse_evidence_id` rozloží citaci (`P03-img03#2`, `KRC-2.4`, `RKT-03/V3`, `EXT-…`).
- **Testy bez IRIS (i pro ostatní lanes):** fixture `fake_fhir_dataset` (`services/conftest.py`) nahradí `services.fhir.client.request` in-memory serverem s celým sanitizovaným datasetem. `client.patient_everything('P03')` atd. pak funguje jako proti IRIS. Fake server odmítá to co IRIS (neplatné ID, prázdné hodnoty, reference na neexistující resource) a neznámé search parametry tiše ignoruje (zapíše je do `ignored_params`).
- DoD proti skutečnému IRIS: `docker compose -f docker-compose.dev.yml exec backend pytest -m integration services/fhir`.

### 6.2 Sanitizace (povinná)

| Problém | Kde | Oprava |
|---|---|---|
| **Neplatné FHIR ID** (`_` mimo povolené `[A-Za-z0-9\-\.]{1,64}`) | 26× `Observation/Pxx-labNN-hb_f` (P01, P02, P05, P06) a reference na ně v `DiagnosticReport.result` | `re.sub(r"[^A-Za-z0-9.\-]", "-", id)` v `id`, ve `fullUrl` i ve **všech** `reference`. Kolize nevzniknou (ověřeno). |
| **Prázdný string** (FHIR zakazuje `""`) | `QuestionnaireResponse/P03-prom02` → item `bolest-misto` → `answer[0].valueString = ""` | odstranit prázdné hodnoty; když je `answer` prázdný, odstranit `answer` (item bez odpovědi je validní) |
| Bundle `type: collection` | všechny bundly | převést na `transaction` ([§6.1](#61-postup-python-managepy-ingest_dataset-úkol-t-101)) |
| `meta.tag` `fiktivni-data` na úrovni Bundle | všechny bundly | zkopírovat do `meta.tag` každého resource, aby šlo fiktivní data v IRIS filtrovat (`_tag`) |

Nic dalšího se neupravuje. Částečná data (`"1959"`, `"2019-03"`), resources bez `code.coding` a `CareTeam.participant` bez `member` jsou ve FHIR R4 validní. Kdyby IRIS přesto něco odmítl, `OperationOutcome` zapiš do Blokerů v PROGRESS.md a sem doplň řádek.

### 6.3 Čtení za běhu (context builder)

- Klinická data pacienta: `GET {type}?patient=P03&_count=500` pro každý typ z [§4.1](#41-resources-a-klíčová-pole). Task se hledá přes `patient` (= `Task.for`), ImagingStudy také přes `patient`.
- Lékaři: ID z referencí → `GET Practitioner?_id=LEK-P03-01,LEK-P03-02,…`.
- Studie: `GET ResearchStudy?_count=50` + `GET Group?_id=RKT-01-kriteria,…`.
- Texty: base64 decode na straně backendu. LLM dostane čistý text s ID.
- `Patient/$everything` zatím neověřeno, viz ARCHITEKTURA §4.6.

---

## 7. Guidelines (pro B2 a red flags)

Výtahy jsou **parafráze** (inspirováno ESMO), ne oficiální doporučení. Pasáže mají formát `**KRC-2.3 – Název.** text…` (regex `^\*\*([A-Z]{3}-\d+\.\d+) – (.+?)\.\*\*\s*(.*)`) a pokračují až do další prázdné řádky.

| Soubor | Kód | Téma | Pasáže |
|---|---|---|---|
| `KRC_kolorektalni_karcinom.md` | **KRC** | metastatický kolorektální karcinom | 1.1–1.2 biomarkery (RAS, BRAF, **MMR/MSI povinně**), 2.1–2.5 jaterní metastázy (resekabilita, **FLR ≥ 30 % / ≥ 40 % po chemo**, konverzní chemo, **bevacizumab ≥ 6 týdnů před operací**, **restaging vč. CT hrudníku ≤ 4–6 týdnů**, disappearing metastases, dvoudobá hepatektomie), 3.1–3.2 systémová léčba (**neuropatie G2 vede ke stop-and-go oxaliplatiny, podle výpovědi pacienta**) |
| `PRS_karcinom_prsu_metastaticky.md` | **PRS** | metastatický karcinom prsu | 1.1–1.4 rebiopsie a receptorová diskordance, **HER2-low**, testování ESR1/PIK3CA/**gBRCA**, NGS a tumor board; 2.1–2.4 HR+/HER2− (linie po CDK4/6, T-DXd, **viscerální krize**); 3.1–3.4 HER2+ (linie, **mozkové metastázy: SRS + pokračovat anti-HER2**, **kardiotoxicita LVEF**); 4.1–4.2 kostní metastázy, **nový lokalizovaný symptom → cílené zobrazení** |
| `PLI_nemalobunecny_karcinom_plic.md` | **PLI** | NSCLC st. III | 1.1–1.3 staging (PET-CT, MR mozku, **EBUS**), **ložisko měnící stadium ověřit**, **EGFR/ALK před perioperační IO**; 2.1–2.4 léčba st. III (resekabilní single-station N2 → neoadj. chemoIO + lobektomie; inoperabilní → CHRT + durvalumab); 3.1 **funkční operabilita (ppoFEV1/ppoDLCO < 60 % → zátěžový test, < 30 % vysoké riziko)**, 3.2 **hyponatrémie → SIADH**, 3.3 kouření |
| `OBC_obecne_principy_MDT.md` | **OBC** | obecné principy MDT (pro všechny) | **1.1 úplnost podkladů (checklist)**, **1.2 staging ≤ 6 týdnů k datu MDT**, **1.3 ECOG lékař vs. pacient (rozdíl ≥ 1) a symptomy ≥ 7/10**, **1.4 nové ložisko ověřit histologicky, duplicita malignit**; 2.1 paliativní péče, **2.2 geriatrický screening ≥ 70 let (G8)**, **2.3 úbytek hmotnosti ≥ 5 % / 6 měsíců**, **2.4 genetické poradenství**; **3.1 kortikoidy u diabetiků → glykémie** |

Celkem **42 pasáží** (KRC 9, PRS 14, PLI 10, OBC 9).

**Výběr podle diagnózy:**

- C50 → PRS;
- C18–C20 → KRC;
- C34 → PLI;
- **OBC vždy**.

Zbytek se dá poslat celý: je malý (≤ 14 pasáží na soubor). Pasáže OBC jsou zároveň **konvence pro hackathon** a slouží jako zdroj prahů pro deterministická pravidla ([ARCHITEKTURA §5.4](ARCHITEKTURA.md#54-red-flags)).

---

## 8. Klinické studie (pro screening v B2)

| ID | Akronym | Fáze | Diagnóza | Klíčová kritéria (zkráceně) |
|---|---|---|---|---|
| **RKT-01** | MERIDIAN-B | II | HR+/HER2− mBC, progrese po AI + CDK4/6 | Z2 **ESR1 v ctDNA ≤ 3 měsíce**, Z4 ≤ 1 linie chemo, Z5 ECOG 0–1; V1 viscerální krize, V2 neléčené/symptomatické mozkové mts, V3 bilirubin > 1,5× ULN, V4 předchozí SERD/fulvestrant |
| **RKT-02** | HELIX-2 | III | HER2+ mBC po trastuzumabu a taxanu | Z3 mozkové mts povoleny (léčené stabilní, nebo neléčené **asymptomatické bez dexametazonu > 2 mg/den**), Z4 ECOG 0–1, **Z5 LVEF ≥ 50 %**; V1 ILD/pneumonitida, V2 předchozí T-DXd, V3 leptomeningy |
| **RKT-03** | COLUMBA-LM | III | KRC s jaterními mts po indukční chemo | Z1 **mts jen v játrech**, Z2 odpověď po ≥ 6 cyklech, Z3 ECOG 0–1, Z4 resekabilita potvrzená MDT; V1 extrahepatální, **V2 MSI-H/dMMR**, **V3 neuropatie ≥ G2**, V4 FLR < 30 % |
| **RKT-04** | PULMO-NEO | III | resekabilní NSCLC II–IIIB | Z1 st. II–IIIB, single-station N2 OK, Z2 ECOG 0–1, **Z3 ppoFEV1 a ppoDLCO ≥ 40 % nebo zátěžový test**, **Z4 známý EGFR a ALK**; V1 EGFR/ALK+, V2 autoimunita, **V3 M1** |
| **RKT-05** | VITALIS | N/A (podpůrná) | solidní nádory s úbytkem hmotnosti | Z1 probíhající léčba, **Z2 úbytek ≥ 5 % / 6 měsíců**, Z3 ECOG 0–2; V1 jen BSC, V2 enterální/parenterální výživa, V3 neschopnost samostatné chůze |
| **RKT-06** | ORION-HRR | II (basket) | solidní nádory s alterací BRCA1/2 / HRR | Z1 HRR alterace z NGS nádoru, Z2 ≥ 1 linie, Z3 ECOG 0–1, Z4 Hb ≥ 90, neu ≥ 1,5, plt ≥ 100; V1 předchozí PARPi, V2 MDS/AML, V3 neléčené mozkové mts. **Protokol:** Hb < 80 → přerušit, po úpravě ≥ 90 pokračovat 250 mg 2×, pak 200 mg 2×; **anémie G3 při 200 mg znamená ukončení** |

FHIR:

- `ResearchStudy/RKT-0n`: `title`, `phase.text`, `condition[].text`, `description` (kritéria jako text), `arm[]`;
- `enrollment` → `Group/RKT-0n-kriteria`, v `characteristic[]`: `code.text` = `Z1…`/`V1…`, `valueCodeableConcept.text` = znění, **`exclude`** = false (zařazení) / true (vyřazení).

**Citace kritéria:** `RKT-03/V3`. Výstup screeningu: `met` / `not_met` / `unknown` (chybí údaj, např. „nevyšetřeno“), vždy s citací faktu pacienta.

---

## 9. Vložené nesrovnalosti — pracovní hypotézy týmu

> ⚠️ **Toto není oficiální ground truth.** Jde o výsledek ručního průzkumu datasetu (Pá 16. 10.), který slouží pro vývoj pravidel, promptů, demo a vlastní evaluační sadu (T-013). Oficiální řešení přijde až po odevzdání. Každá položka má ID zdrojů a pasáž guidelines, takže se dá ověřit. Nové nálezy připisuj sem.

**Typy problémů, které dataset systematicky obsahuje**, a mapování na pravidla red flags v [ARCHITEKTURA §5.4](ARCHITEKTURA.md#54-red-flags):

| Typ | Pravidlo | Guidelines |
|---|---|---|
| ECOG lékař vs. pacient (`samostatnost`) se liší o ≥ 1 | `RF-ECOG` | OBC-1.3 |
| Symptom v PROMs ≥ 7/10 nebo výrazný vzestup mezi vyplněními | `RF-PROMS` | OBC-1.3 |
| Toxicita podle lékaře (G1) nižší než podle popisu pacienta (omezení instrumentálních činností = G2) | `RF-TOX` | KRC-3.2, OBC-1.3 |
| Zastaralý nebo neúplný staging (> 6 týdnů k datu MDT, chybí CT hrudníku) | `RF-STALE` | OBC-1.2, KRC-2.4 |
| Chybějící povinný biomarker (`"nevyšetřeno"` / `"probíhá"`) | `RF-MISSING` | OBC-1.1, KRC-1.1, PRS-1.3, PLI-1.3 |
| Lék, doplněk nebo bylina z PROMs (`leky-mimo`) chybí v medikaci, případně interakce | `RF-MED` | (P05-doc03) |
| Nový symptom v PROMs (`nove-obtize`) bez reakce v dokumentaci | `RF-NEWSYMPTOM` | PRS-4.2 |
| Rozpor mezi dokumenty (TNM, LVEF v nominaci vs. poslední měření, HER2 „negativní“ vs. 1+) | `RF-LLM` / `RF-NOMINATION` | PRS-1.2, PRS-3.4 |
| Trend v laboratoři (pokles Hb, vzestup markerů, hyponatrémie, glykémie) | `RF-LAB` | PLI-3.2, OBC-3.1, PRS-4.2 |
| Úbytek hmotnosti ≥ 5 % / 6 měsíců | `RF-WEIGHT` | OBC-2.3 |
| Věk ≥ 70 bez geriatrického screeningu | `RF-GERI` | OBC-2.2 |
| Nejasné ložisko / druhý nádor bez histologie | `RF-LESION` | OBC-1.4, PLI-1.2 |
| Indikace genetického poradenství nesplněna | `RF-GENETIC` | OBC-2.4, PRS-1.3, PRS-1.4 |

### P01: HR+/HER2-low mBC, progrese po CDK4/6

- **ECOG 1** (`P01-ecog05`) vs. pacientka **2** (`P01-prom02` `samostatnost` = 2); únava 8, bolest 6 (`P01-prom02`). OBC-1.3.
- **Nová bolest pravé kyčle a třísla 3 týdny**, chůze jen po rovině, paracetamol (`P01-prom02`). Při kostních metastázách vyžaduje cílené zobrazení (PRS-4.2). Paracetamol chybí v medikaci.
- **Staging zastaralý:** poslední CT `P01-img06` z 2026-09-01, k MDT 2026-10-21 je to 7 týdnů (OBC-1.2).
- **Nevyšetřeno:**
  - ESR1 ctDNA `P01-bm09`, takže RKT-01/Z2 = `unknown`;
  - PIK3CA/AKT1/PTEN `P01-bm10`;
  - **germinální BRCA** `P01-bm11` (PRS-1.3).
- **Rodinná anamnéza:** matka karcinom prsu v 60 letech, **sestra karcinom ovaria ve 49 letech**, genetika neprovedena (`P01-doc06`). OBC-2.4.
- **HER2 diskordance:** primární nádor 1+ (HER2-low, `P01-bm03`) vs. metastáza 0 (`P01-bm07`), což je relevantní pro T-DXd (PRS-1.1, PRS-1.2, PRS-2.3).
- **Laboratoř:**
  - Hb 123 → 104 (`P01-lab04-hb-f` → `P01-lab06-hb-f`);
  - ALT/AST rostou (`P01-lab06-alt`), bilirubin v normě, tedy **nejde o viscerální krizi** (PRS-2.4);
  - CA 15-3 28 → 121.

### P02: HER2+ mBC, nové mozkové metastázy (MDT 2026-10-14, urgentní)

- **ECOG 1** (`P02-ecog04`) vs. pacientka **2** (`P02-prom02`); bolest 7, psychika 8. OBC-1.3.
- **Nové symptomy:** bolest hlavy, ranní nauzea, **rozmazané vidění**, horší spánek po nových lécích (`P02-prom02`). Mozkové metastázy jsou tedy **symptomatické**.
- **Dexametazon 4 mg/den** (`P02-med03`), takže **RKT-02/Z3 nesplněno** (> 2 mg/den).
- **Glykémie 11,8 mmol/l** (`P02-lab06-glu`) u diabetičky na metforminu (`P02-med01`) a dexametazonu. OBC-3.1.
- **LVEF 60 → 52 %** (`P02-lvef06` → `P02-lvef07`). Hlídat podle PRS-3.4; RKT-02/Z5 (≥ 50 %) je těsně splněno.
- **LVEF bez zdrojového dokumentu:** `P02-lvef03`, `P02-lvef04`, `P02-lvef06` nemají `derivedFrom` (mezera v dohledatelnosti).

### P03: KRC s jaterními metastázami, resekabilita

- **ECOG 0** (`P03-ecog03`) vs. pacient **1** (`P03-prom02` `samostatnost` = 1, `chuze` = 1 patro). OBC-1.3.
- **Neuropatie:**
  - lékař uvádí **G1** (`P03-neuro01`);
  - pacient hlásí brnění 6/10, „špatně zapínám knoflíky, padají mi věci z ruky“ (`P03-prom02`), což odpovídá **G2**;
  - podle KRC-3.2 to znamená stop oxaliplatiny;
  - **RKT-03/V3** (neuropatie ≥ G2) je proto sporné;
  - pacient je profesionální řidič a teď nemůže řídit.
- **Restaging neúplný:** CT `P03-img03` „hrudník nebyl požadován“, poslední CT hrudníku `P03-img01` je z 2026-04-28 (KRC-2.4). Tím je **RKT-03/Z1** (jen játra) `unknown`.
- **MMR/MSI nevyšetřeno** (`P03-bm04`), přitom je povinné (KRC-1.1); **RKT-03/V2** = `unknown`. Otec měl karcinom tlustého střeva (`P03-doc02`), OBC-2.4.
- **Úbytek hmotnosti** 84 → 78 kg (−7 %, `P03-vaha01` → `P03-vaha04`). OBC-2.3, RKT-05/Z2.
- **CEA znovu roste:** 9,1 → 13,9 (`P03-lab05-cea` → `P03-lab06-cea`).
- **Doplňky mimo medikaci:** hořčík a vitamin B (`P03-prom02`).
- **Plánování resekce:**
  - vymizelá metastáza S5 (`P03-img04`) se musí zahrnout do plánu (KRC-2.4);
  - FLR levého laloku 38 % (`P03-img04`) je pod hranicí ≥ 40 % po intenzivní chemo (KRC-2.1);
  - bevacizumab naposledy 2026-09-07 (`P03-tx-bev-08`), operace tedy nejdříve ~19. 10. (KRC-2.3).
- **RECIST:** 83 → 50 mm (−40 %), PR (`P03-img01` → `P03-img03`). Vhodné pro test BON-2.

### P04: NSCLC st. III, operabilita

- **Rozpor TNM:** cT3 cN2 **IIIB** (`P04-tnm01`, `P04-doc05`) vs. cT2b cN2 **IIIA** (`P04-tnm02`, `P04-doc06`).
- **Ložisko levé nadledviny 14 mm, SUVmax 4,1**, doporučeno ověření (`P04-img03`). Nominace ho bagatelizuje jako „pravděpodobně adenom“ (`P04-doc05`). M kategorie tak **nelze stanovit** (PLI-1.2), RKT-04/V3 = `unknown`.
- **EGFR stále neznámý** (`P04-bm04` nedostatečný vzorek, `P04-bm05` probíhá). Podle PLI-1.3 je potřeba před perioperační IO; **RKT-04/Z4** = `unknown`.
- **Funkční operabilita:** ppoFEV1 49 %, **ppoDLCO 38 %** (`P04-spiro03`, `P04-spiro04`), obě < 60 %, takže je potřeba **zátěžový test** (PLI-3.1); RKT-04/Z3 (≥ 40 %) nesplněno bez testu.
- **Progredující hyponatrémie** 136 → 129 mmol/l (`P04-lab01-na` → `P04-lab05-na`). PLI-3.2 (SIADH).
- **ECOG 0** (`P04-ecog03`) vs. pacient **1**, **dušnost 7/10**, 1 patro jen se zastávkou (`P04-prom02`). OBC-1.3.
- **Úbytek hmotnosti** 78 → 71 kg (−9 % za 2,5 měsíce, `P04-vaha01` → `P04-vaha03`). OBC-2.3, RKT-05.
- **Věk 70:** chybí G8 (OBC-2.2). Aktivní kuřák (`P04-kour01`, PLI-3.3). CEA roste 8,2 → 11,5.

### P05: HR+/HER2-low mBC s BRCA2, PARPi ve studii RKT-06

- **Anémie G3 opakovaně:**
  - Hb 76 a 77 g/l (`P05-lab04-hb-f`, `P05-lab06-hb-f`; `P05-anem01`, `P05-anem02`), 2× transfuze;
  - podle protokolu RKT-06 je **povolena ještě redukce na 200 mg 2×** a teprve G3 při 200 mg znamená ukončení.
- **Třezalka:**
  - pacientka pije **třezalkový čaj** každý večer a bere železo (`P05-prom02`);
  - klinický farmaceut **výslovně varoval před třezalkou** (CYP3A, `P05-doc03`);
  - v medikaci to chybí; **léková interakce se studijním PARPi**.
- **Germinální BRCA nevyšetřeno**, poradenství doporučené 15. 4. neproběhlo (`P05-bm14`; PRS-1.4, OBC-2.4). Pacientka zvažuje vyšetření kvůli dceři.
- **Staging zastaralý:** poslední CT `P05-img04` z 2026-07-30, k MDT 2026-10-21 je to ~12 týdnů (OBC-1.2).
- **HER2:** dokumentace uvádí „negativní“, správně je 1+ = **HER2-low** (`P05-bm03`, `P05-bm07`), což otevírá T-DXd (PRS-1.2, PRS-2.3). ESR1 v ctDNA nevyšetřeno (`P05-bm12`, PRS-1.3).
- **Únava 8**, psychika 7, dušnost 5, bušení srdce (`P05-prom02`). OBC-1.3.
- `P05-dg1` nemá datum vzniku (mezera).

### P06: HER2+ mBC, smíšená odpověď, nádor ledviny

- **LVEF:**
  - pokles 65 → 55 % (`P06-lvef01` → `P06-lvef04`) = −10 bodů, podle PRS-3.4 je nutné častější sledování;
  - **nominace uvádí zastaralé „LVEF 61 % (1/2026)“** (`P06-zad01`) místo 55 % z 8/2026.
- **ECOG 1** (`P06-ecog04`) vs. pacientka **2** (`P06-prom02`); dříve ECOG 2 i podle lékaře (`P06-ecog03`); únava 7. OBC-1.3.
- **Rostoucí plicní ložisko nejasného původu:**
  - TTF-1−, GATA3−;
  - **HER2 a ER/PR nevyšetřeny** pro nedostatek materiálu (`P06-bm07`, `P06-bm08`);
  - dg. `P06-dg2` jen `provisional`;
  - vyžaduje rebiopsii a IHC (OBC-1.4);
  - obava pacientky z biopsie po pneumotoraxu (`P06-proc02`).
- **Druhý nádor:** suspektní RCC pravé ledviny (`P06-dg3`, D41.0) neověřen. OBC-1.4, pořadí řešení.
- **Věk 76:** chybí G8 (OBC-2.2). Úbytek hmotnosti 67 → 63 kg (`P06-vaha03` → `P06-vaha04`). Albumin 34. Kreatinin 106 (CKD G3a).
- **Markery rostou:** CA 15-3 24 → 52, CEA 3,8 → 8,6, LD 4,4 (`P06-lab05-*` → `P06-lab07-*`).

### Doplněk Pá 16. 10. 18:15 (revize pro požadavky lékaře, [docs/POZADAVKY_LEKARE.md](docs/POZADAVKY_LEKARE.md))

- **P01:** `P01-doc07` (2026-10-06) uvádí „Únava mírná, jinak bez nových obtíží“, ale den předtím pacientka v `P01-prom02` hlásí únavu 8/10 a 3 týdny bolest pravé kyčle. `RF-NEWSYMPTOM` / `RF-LLM` (zpráva vs. PROMs), PRS-4.2.
- **P02, strana:** `P02-doc03` (implantace portu) uvádí „karcinom **levého** prsu“, pacientka má karcinom pravého prsu (`P02-dg1`, `P02-pat01`). `RF-IDENTITY`.
- **P02, TNM:** `P02-mdt01` (klinické zhodnocení) uvádí „cT4b **N2** M1“, kdežto `P02-tnm01` a `P02-doc02` uvádějí cN1. `RF-TNM` / `RF-LLM`.
- **P02, LVEF:** `P02-doc11` (2026-10-01) uvádí „EF v normě“, poslední LVEF je ale 52 % s mírně sníženou funkcí LK (`P02-lvef07`, `P02-doc08`). Kontrolní echo doporučené za 3–4 týdny (`P02-doc08`) v datech chybí. `RF-NOMINATION` / `RF-MISSING`, PRS-3.4.
- **P04:** `P04-doc05` uvádí „Hmotnost 71 kg, hmotnost stabilní“, přitom `P04-vaha01` je 78 kg (−9 %). Rozpor v textu + `RF-WEIGHT`, OBC-2.3.
- **P06, lokalizace:** `P06-doc01` v místním nálezu popisuje rezistenci „v horních a dolních vnitřních kvadrantech“, kdežto `P06-img01`, `P06-pat01` i `P06-dg1` uvádějí horní zevní kvadrant. `RF-IDENTITY`.
- **P06, echo:** kontrolní echo doporučené „začátkem října 2026“ (`P06-doc10`) v datech není. Poslední LVEF je 55 % z 2026-08-24 (`P06-lvef04`). `RF-MISSING`, PRS-3.4.
- **Rozmezí ECOG v textu:**
  - „ECOG 0–1“ (`P03-doc06`) je strukturovaně uloženo jako 1 (`P03-ecog02`);
  - „ECOG 1–2“ (`P06-doc06`) je uloženo jako 2 (`P06-ecog02`);
  - „ECOG 0–1“ (`P05-doc06`, `P05-doc08`) strukturovaný záznam nemá.

  Strukturovaná data berou horší hodnotu. AI má rozmezí hlásit jako nejistotu, ne převádět na jedno číslo.
- **Paliativní péče (OBC-2.1)** není v dokumentaci zmíněna u žádného pacienta. Přitom P01 (únava 8), P02 (bolest 7, psychika 8), P05 (únava 8, psychika 7) a P06 (únava 7) mají pokročilé onemocnění s výraznou symptomovou zátěží (`Pxx-prom02`); u P04 (dušnost 7/10) k diskusi. `RF-PALIATIVE`.
- **Kortikoidy bez plánu snižování (OBC-3.1):** P02 dexametazon 4 mg od 23. 9. (`P02-med03`, `P02-doc11` „pokračuje“), plán snižování v dokumentaci není. `RF-STEROID`.
- **Hyponatrémie bez vyšetření SIADH (PLI-3.2):** P04 Na 136 → 129 mmol/l, osmolalita séra a moči ani natriurie v datech nejsou. `RF-LAB`.
- **Očekávané barvy semaforu** pro P03 a P04 (podklad pro T-013): [docs/POZADAVKY_LEKARE.md §5.4](docs/POZADAVKY_LEKARE.md#54-očekávané-barvy-pro-demo-podklad-pro-dev-ground-truth-t-013).

### Doplněk Pá 16. 10. (T-101, ingest)

- **P05-ae1:** třetí kategorie `Condition`, „nežádoucí účinek léčby“ (D64.8, anémie G3 při PARPi, od 2026-08-17). Není to onkologická diagnóza ani komorbidita: context builder a hlavička (komorbidity, FR-A4) ji musí rozlišit podle `category.text`. Pro P05 je to další zdroj k anémii G3 (`P05-anem01`, `P05-anem02`, protokol RKT-06).

**Doporučený demo pacient:** **P03**. Má jasnou otázku, vizuálně silné rozpory (ECOG, neuropatie podle pacienta, chybějící hrudník, MMR), RECIST, studii RKT-03 s několika `unknown` kritérii a je nejmenší. Záloha je **P05** (třezalka jako „wow“ red flag, protokol studie).
