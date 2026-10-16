# MDT Copilot — roadmapa a progress

> Harmonogram hackathonu: odevzdání So 17. 10. 12:00 (*zatím neřešíme*) · lokální pitch 13:00 · TOP 3 v 17:00 · národní finále v neděli od 14:00
>
> - Architektura, požadavky a kontrakty: [ARCHITEKTURA.md](ARCHITEKTURA.md)
> - Dataset: [DATASET.md](DATASET.md)
> - Pravidla pro AI agenty: [AGENTS.md](AGENTS.md)
> - Přehled: [MYSLENKOVA_MAPA.md](MYSLENKOVA_MAPA.md)

**Stav:** 🟢 M0 Setup · dataset ✅ popsán · LLM = Gemini ✅ · aktualizováno: Pá 16. 10. 16:20

---

## 1. Jak tady pracujeme (lidé i AI agenti)

### Legenda stavů

| | Stav | Význam |
|---|---|---|
| ⬜ | `todo` | volné, kdo chce, vezme si |
| 🟨 | `doing` | někdo na tom pracuje (viz Owner) |
| 👀 | `review` | hotové, čeká na kontrolu nebo merge |
| ✅ | `done` | splněno DoD, v `master` |
| ⛔ | `blocked` | čeká na něco (napiš do Blokerů) |
| ⏸ | `paused` | odloženo rozhodnutím týmu |
| ✂️ | `cut` | vyškrtnuto / nahrazeno |

### Protokol (krok za krokem)

1. **Sync:** `git pull --rebase origin master`.
2. **Přečti:**
   - [AGENTS.md](AGENTS.md);
   - relevantní sekce [ARCHITEKTURA.md](ARCHITEKTURA.md) (každý úkol na ně odkazuje);
   - u datových a AI úkolů **[DATASET.md](DATASET.md)**;
   - tento soubor.
3. **Vyber úkol:**
   - stav ⬜;
   - všechny úkoly ve sloupci *Závisí na* jsou ✅;
   - ideálně ze své lane;
   - přednost má nižší milník (M0 před M1…).
4. **Zaber ho (claim commit):**
   1. v tabulce přepiš stav na 🟨 a Owner na `@jméno` (agent: `@jméno+agent`);
   2. commitni **jen tuto změnu**: `git commit -m "T-xxx: claim"` a hned `git push`;
   3. když push selže, `git pull --rebase` a zkontroluj, jestli úkol mezitím nezabral někdo jiný.
5. **Pracuj ve větvi** `t-xxx-kratky-popis`. Commity piš jako `T-xxx: co se změnilo`. Commituj malé kroky a často pushuj.
6. **Hotovo:**
   1. splněno **DoD**, projde lint a testy (`npm run lint`, `make test`);
   2. merge do `master` (PR, nebo rovnou merge, pokud jde jen o tvou lane a nic nerozbiješ);
   3. stav → ✅ a jeden řádek do [Deníku](#6-deník-append-only).
7. **Změna kontraktu** (API, JSON schémata v ARCHITEKTURA §6.3 / §8):
   1. nejdřív uprav ARCHITEKTURA.md, ve stejném PR jako kód;
   2. do Deníku napiš `⚠️ KONTRAKT: …`;
   3. dej vědět v týmovém chatu.
8. **Nový nález v datech** (nesrovnalost, chyba ingestu): připiš ho do [DATASET.md §9](DATASET.md#9-vložené-nesrovnalosti--pracovní-hypotézy-týmu) nebo §6.2 a zapiš do Deníku.
9. **Zablokovaný?** Stav ⛔, zápis do [Blokerů](#5-blokery-a-otevřené-otázky) a vezmi si jiný úkol.

### Pravidla

- **Nikdy** necommituj `.env`, API klíče ani hesla. Nikdy nedělej `push --force` do `master`.
- Neupravuj soubory jiné lane bez domluvy. Neformátuj hromadně cizí soubory. **Dataset neměň**, opravy patří do sanitizace v ingestu.
- V tabulce úkolů **1 úkol = 1 řádek**. Deník je append-only (nové řádky na konec). Konflikty v tomto souboru řeš tak, že **ponecháš obě strany**.
- Testy a vývoj pracují s `AI_PROVIDER=mock`. Gemini se volá jen ručně a **jen s placeným tierem** (Q9).
- Když úkol nestihneš (např. musíš odejít), vrať ho na ⬜ a do Deníku napiš, v jakém je stavu a na jaké větvi.

---

## 2. Lanes (pracovní proudy) a lidé

| Lane | Zaměření | Klíčové složky | Owner |
|---|---|---|---|
| **INFRA** | Vercel, VPS, Docker, IRIS kontejner, deploy | `WEB_Template/docker-compose*.yml`, `WEB_Template/iris/`, `next.config.ts` | `@?` |
| **DATA** | ingest datasetu do IRIS, sanitizace, vektory, guidelines, studie, MCP | `backend/services/fhir/ingest.py`, `backend/services/iris/`, `DATASET.md`, `data/` | `@?` |
| **AI** | Gemini provider, context builder, prompty, grounding, red flags, B2, scribe, eval | `backend/services/ai/`, `backend/services/rules/`, `backend/services/ai_service.py` | `@?` |
| **API** | Django apps, modely, endpointy, FHIR write-back, export | `backend/apps/{patients,mdt,copilot}/`, `backend/services/fhir/{writeback,export}.py` | `@?` |
| **UI** | Next.js stránky a komponenty, UX | `frontend/src/app/dashboard/`, `frontend/src/components/mdt/`, `frontend/src/types/` | `@?` |
| **PITCH** | demo scénář, slidy, video, QA, dev ground truth, koordinace | `docs/`, `data/dev_ground_truth/`, `PROGRESS.md` | `@?` |

> Doplňte jména. Jeden člověk může mít víc lanes. Doporučení pro 4 lidi: (1) INFRA + API, (2) DATA, (3) AI, (4) UI + PITCH.

---

## 3. Milníky

| Milník | Cíl | Do kdy | Stav |
|---|---|---|---|
| **M0** Setup a kontrakty | IRIS běží lokálně i na VPS, Vercel deploy „hello“, Gemini provider, kontrakty zmrazené, fixtures P03, dataset popsán ✅ | **Pá 18:00** | 🟨 |
| **M1** Vertikální řez | P03 end-to-end: dataset v IRIS → blok A s citacemi → UI → klik na citaci ukáže zdroj | **Pá 23:00** | ⬜ |
| **M2** Kompletní funkce | B (≥ 3 role + posouzení), B2 (guidelines + studie), red flags, konfigurátor, zápis + potvrzení → IRIS FHIR, export PDF + FHIR | **So 04:00** | ⬜ |
| **M3** Spolehlivost a bonusy | všech 6 pacientů, eval proti dev ground truth, readiness, RECIST, zapisovatel, shrnutí pro pacienta, pravidla z konzultace | **So 09:00** | ⬜ |
| **M4** Freeze a demo | feature freeze 10:00 · code freeze 11:00 · nasazeno + tag · demo nacvičené. Odevzdání ⏸ | **So 11:00** | ⬜ |
| **M5** (podmíněně) Finále | pokud TOP 3: doladění dema a pitche pro národní finále | **Ne 14:00** | ⬜ |

**Nejdůležitější cesta:** T-002 → T-003 → T-006 → T-101 → T-105 → T-106 → T-108, pak paralelně M2. UI se do té doby nečeká, jede nad fixtures (T-009). AI ladí prompty nad P03 hned po T-101.

---

## 4. Task board

### M0 — Setup a kontrakty (do Pá 18:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-001 | Struktura repa: `docs/zadani/` (přesun pptx), `data/{dev_ground_truth,fixtures,audio}/`, `.gitignore` (`.env`, `.venv`). Dataset zůstává v `Dataset_MDT_Copilot_v1.1_pre_timy/` (smí do gitu) | INFRA | — | složky a dataset v `master` | `@?` | ⬜ |
| T-002 | Služba `iris` v `docker-compose.dev.yml` (Dockerfile + `merge.cpf` z kitu do `WEB_Template/iris/`, volume, porty 1972/52773), mount datasetu do backendu (`DATASET_DIR`) — ARCH §3.4, §4.2 | INFRA | T-001 | `curl -u SuperUser:SYS localhost:52773/fhir/r4/metadata` vrátí 200 po `dev.ps1 up` | `@?` | ⬜ |
| T-003 | Command `iris_init` (native API: namespace FHIRSERVER + endpoint `/fhir/r4`, `Device/mdt-copilot`, idempotentní, bez Synthea) — ARCH §4.2 | INFRA | T-002 | 2× spuštění bez chyby, endpoint existuje | `@?` | ⬜ |
| T-004 | Vercel: projekt (root `WEB_Template/frontend`), `rewrites` `/api/*` → `BACKEND_URL`, `skipTrailingSlashRedirect`, `api.ts` same-origin (`??`), dev odkazy jen v dev — ARCH §3.4 | INFRA | — | přihlášení demo účtem funguje na `*.vercel.app` proti nasazenému BE | `@?` | ⬜ |
| T-005 | **VPS:** DNS `api.<doména>`, prod compose (Traefik, backend, db, redis, **iris interně**), změnit heslo IRIS, `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`, dataset volume — ARCH §3.4 | INFRA | T-002 | `https://api.<doména>/api/health/` vrátí 200, IRIS zvenku nedostupný | `@?` | ⬜ |
| T-006 | `services/iris/db.py` (connect ctx manager, env `IRIS_*`) + `services/fhir/client.py` (auth, paging, search, transaction, fallback místo `$everything`) — ARCH §4.6 | API | T-002 | pytest proti lokálnímu IRIS: `PUT` a čtení `Patient` | `@?` | ⬜ |
| T-007 | Získat dataset, popsat formát a obsah | DATA | — | [DATASET.md](DATASET.md) | `@jaram+claude` | ✅ |
| T-008 | ~~Pacient 0 (ručně vytvořený bundle)~~: nahrazeno datasetem, dev pacient = **P03** | DATA | — | — | — | ✂️ |
| T-009 | **Zmrazit kontrakty:** `apps/copilot/schemas.py` (pydantic, zároveň Gemini `response_schema`) + `frontend/src/types/mdt.ts` + fixtures `data/fixtures/brief_P03.json`, `decision_P03.json` s reálnými ID z P03 (DATASET §9) — ARCH §8 (včetně `RoleAssessment`, `header.comorbidities` / `alerts`, `Decision.sections`) | AI + UI | — | FE i BE importují typy, fixture projde validací pydantic | `@?` | ⬜ |
| T-010 | UI čistka: branding „MDT Copilot“, navigace MDT (Přehled, Zasedání, Úkoly), skrýt Projekty / Úložiště / WS / AI Studio | UI | — | nová navigace v `master`, build projde | `@?` | ⬜ |
| T-011 | Zkopírovat IRIS skills z FHIR-AI-Hackathon-Kit `skills/*` do `.claude/skills/` (+ volitelně `iris-agentic-dev` v `.mcp.json`); poznámka, že kit používá OpenAI a my Gemini — ARCH §4.8 | PITCH | — | skills v repu, agent je umí načíst | `@?` | ⬜ |
| T-012 | **Gemini provider:** přepsat `GeminiProvider` (`google-genai`, `system_instruction`, `response_schema`, výchozí `gemini-3.8-flash` místo vypnutého `gemini-1.5-flash`), `embed()` (`gemini-embedding-001` @ 1536 + L2 normalizace, `task_type`), `transcribe()`; upravit `ai_views.py`, `.env.example` (`GEMINI_API_KEY`, `AI_MODEL`…) — ARCH §5.7 | AI | — | `mock` i `gemini` vrací validní JSON podle schématu; `embed` vrací 1536 normalizovaných čísel | `@?` | ⬜ |
| T-013 | **Dev ground truth** `data/dev_ground_truth/P01…P06.json` z [DATASET §9](DATASET.md#9-vložené-nesrovnalosti--pracovní-hypotézy-týmu) (red flags + pravidlo + severity + ID zdrojů, chybějící údaje, studie po kritériích, RECIST, klíčová fakta) — ARCH §5.8 | AI + PITCH | T-009 | 6 souborů, každá položka má ID zdrojů a pasáž guidelines | `@?` | ⬜ |

### M1 — Vertikální řez na P03 (do Pá 23:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-101 | **`ingest_dataset`:** sanitizace (`_` → `-` v ID a referencích, prázdné stringy, `meta.tag`), `collection` → `transaction` s `PUT`, pořadí Questionnaire → studie → pacienti, index `ID → ResourceType`, **kontrola počtů** — [DATASET §6](DATASET.md#6-ingest-do-iris-fhir), ARCH §4.4 | DATA | T-006 | všech 1 091 resources v IRIS, počty sedí s DATASET §2, 2. běh bez duplikátů | `@?` | ⬜ |
| T-102 | Chunking odstavců (DocumentReference, DiagnosticReport, Composition) + Gemini embeddingy → `MDT.EvidenceChunk` (DDL, batch insert, `search_evidence(patient_id, q)`) — ARCH §4.5 | DATA | T-101, T-012 | dotaz vrací jen odstavce daného pacienta se skóre | `@?` | ⬜ |
| T-103 | API pacientů: `GET /api/patients/`, `/{pid}/`, `/{pid}/timeline/`, `/{pid}/observations/` z IRIS — ARCH §6.3 | API | T-101 | Swagger ukazuje P01–P06 | `@?` | ⬜ |
| T-104 | Evidence resolver `GET /api/evidence/?id=` (prefix index, text + offset odstavce, hodnota + `derivedFrom`, pasáž guidelines, kritérium studie) — ARCH §5.2 | API | T-101, T-102 | pro každý typ Evidence ID vrátí zdroj | `@?` | ⬜ |
| T-105 | `context_builder` (IRIS → evidence list s ID; sada guidelines podle MKN-10; studie; výsledky pravidel) + `pseudonymize` — ARCH §5.1, §5.7 | AI | T-101 | kontext P03 obsahuje všech 171 resources jako řádky s ID, guidelines KRC + OBC | `@?` | ⬜ |
| T-106 | Generátor **bloku A** (souhrn, ECOG lékař vs. `samostatnost`, časová osa, komorbidity, alerts) + **grounding validátor v1** (ID, čísla, data, missing checklist) — ARCH §5.3 | AI | T-105, T-009, T-012 | Brief A pro P03 validní podle schématu, 0 neověřených tvrzení, ECOG 0 vs. 1 zobrazen | `@?` | ⬜ |
| T-107 | Modely `MdtSession`, `MdtCase`, `Brief`, `GenerationJob`, `LlmCallLog` + job endpointy `POST /cases/{cid}/brief/`, `GET /jobs/{jid}/` (ThreadPool) — ARCH §6.2, §6.3 | API | T-106 | FE spustí generování a polluje výsledek | `@?` | ⬜ |
| T-108 | Stránka podkladu: `CaseHeader`, `AiBlock`, `Claim` + `CitationChip`, `SourceDrawer`, `MissingData`, `JobProgress` (nejdřív nad fixture) — ARCH §7.2 | UI | T-009, T-010 | klik na citaci otevře zdroj; běží na fixture i na živém API | `@?` | ⬜ |
| T-109 | `seed_mdt` (4 zasedání z `ServiceRequest` + `Task`) + agenda `/dashboard/mdt/[sessionId]` + přehled `/dashboard` — ARCH §6.2 | API + UI | T-101, T-107 | 4 zasedání a 6 případů, přechod na podklad | `@?` | ⬜ |
| T-110 | Deploy M1 na prod (Vercel + VPS, ingest na VPS) + smoke test | INFRA | T-004, T-005, T-101, T-107, T-108 | vertikální řez funguje na veřejné URL | `@?` | ⬜ |

### M2 — Kompletní funkce (do So 04:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-201 | **Blok B:** prompty pro role (chirurg, onkolog, radiolog, patolog, pacient, radiační onkolog) + **posouzení role** `RoleAssessment` (FR-B7), paralelní generace | AI | T-106 | ≥ 3 role validní s verdiktem, celý podklad < 20 s | `@?` | ⬜ |
| T-202 | **Red flags:** `rules/red_flags.py` (RF-ECOG, RF-PROMS, RF-TOX, RF-STALE, RF-MISSING, RF-MED, RF-NEWSYMPTOM, RF-LAB, RF-WEIGHT, RF-GERI, RF-LESION, RF-GENETIC, RF-NOMINATION, RF-TNM) + `RF-LLM`; ≥ 2 citace + pasáž — ARCH §5.4 | AI | T-105 | najde hypotézy z DATASET §9 pro P03 a P05 (včetně třezalky) | `@?` | ⬜ |
| T-203 | Guidelines (42 pasáží, regex z DATASET §7) → `MDT.GuidelineChunk`; studie (`Group.characteristic`) → `MDT.TrialCriterion` — ARCH §4.5 | DATA | T-102 | vyhledání s filtrem MKN-10 vrací relevantní pasáže; 42 + 6 studií v IRIS | `@?` | ⬜ |
| T-204 | **B2:** sada guidelines podle dg., možnosti s ID pasáží + co chybí, screening `RKT-01…06` po kritériích (včetně protokolu RKT-06), 2–3 otázky — ARCH §5.5 | AI | T-203, T-106 | `DecisionSupport` validní; P03 má RKT-03 s `unknown` u Z1 a V2; žádné „doporučujeme“ | `@?` | ⬜ |
| T-205 | UI: `RoleTabs` + `RoleAssessmentCard`, `RedFlagCard`, `EcogCompare`, `Timeline`, `TrendChart` (Hb, markery, Na, hmotnost, LVEF, PROMs), `TreatmentOptions`, `TrialScreening` | UI | T-108 | všechny sekce §8 se vykreslí z fixture i API | `@?` | ⬜ |
| T-206 | **Konfigurátor** `/setup`: sekce zap/vyp, drag & drop pořadí, přítomné role, detail, presety; přegenerovat — FR-R1 | UI | T-108 | změna nastavení se projeví v novém podkladu | `@?` | ⬜ |
| T-207 | API konfigurace: `BriefConfig` CRUD + promítnutí do promptů (sekce, role, detail, jazyk) | API + AI | T-107 | různé presety dávají různé výstupy | `@?` | ⬜ |
| T-208 | **Editor závěru** `/record`: sekce záznamu MDT jako v datasetu, záměr (`mdt-lecebny-zamer`), postup po modalitách, úkoly (owner, termín), re-MDT, přítomní; AI vs. člověk odlišení — FR-C1, C2, R4 | UI | T-205 | draft se ukládá, AI předvyplnění je vizuálně odlišené | `@?` | ⬜ |
| T-209 | **Potvrzení → IRIS FHIR:** `writeback.py` transaction: `Composition/Pxx-mdtNN`, `CarePlan`, `CareTeam`, `Task[]`, `DetectedIssue[]`, `ResearchSubject`, `Provenance`, update `Pxx-zad01` + `-task` (`projednana`) — ARCH §4.3 výstupy | API | T-107, T-006 | po potvrzení P03 je v IRIS `Composition/P03-mdt02` s vazbami a `fhir_ids` v `Decision` | `@?` | ⬜ |
| T-210 | **Export:** `export.fhir.json` (document Bundle) + `export.pdf` (+ `DocumentReference/Pxx-mdtNN-pdf` v IRIS) — FR-C4 | API | T-209 | oba soubory ke stažení, Bundle jde znovu nahrát do IRIS | `@?` | ⬜ |
| T-211 | Nominace (`POST /api/mdt/cases/` → FHIR `ServiceRequest` + `Task`) + formulář v UI — FR-P1 | API + UI | T-107 | nový případ se objeví v agendě | `@?` | ⬜ |
| T-212 | Deploy M2 + smoke test celého cyklu na prod | INFRA | T-201…T-210 | 6 kroků finálové ukázky projde na veřejné URL | `@?` | ⬜ |
| T-213 | **Grounding v2:** vektorová podobnost tvrzení ↔ citovaný odstavec (IRIS `VECTOR_COSINE`, `FACT_VERIFICATION`, práh `GROUNDING_MIN_SIMILARITY`) — ARCH §5.3 | AI | T-102, T-106 | špatně citované tvrzení v testu je `unverified` | `@?` | ⬜ |

### M3 — Spolehlivost a bonusy (do So 09:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-301 | **Eval** `eval_ground_truth --gt data/dev_ground_truth` → `docs/EVAL.md` (recall red flags, pokrytí faktů, % neověřených, „údaj chybí“, screening studií) + porovnání `gemini-3.8-flash` vs. `gemini-4-argon` — ARCH §5.8 | AI + PITCH | T-013, T-202, T-204 | tabulka metrik pro všech 6 pacientů a 2 modely | `@?` | ⬜ |
| T-302 | Ladění promptů a validátoru podle evalu (cíl: 0 neověřených, všechny dev-GT flags) | AI | T-301 | metriky lepší než první běh, zapsané v EVAL.md | `@?` | ⬜ |
| T-303 | BON-1 **Readiness check** (`rules/readiness.py`: checklist OBC-1.1, staging ≤ 42 dní OBC-1.2, povinné biomarkery) + badge v agendě | AI + UI | T-202 | P01 a P05 mají zastaralý staging, P03 chybí MMR a CT hrudníku | `@?` | ⬜ |
| T-304 | BON-2 **RECIST 1.1** předvýpočet (`rules/recist.py`, SLD, CR/PR/SD/PD; rozměry z popisů přes LLM s citací) v pohledu radiologa | AI | T-201 | P03: 83 → 50 mm = PR (−40 %) s citacemi `P03-img01`, `P03-img03` | `@?` | ⬜ |
| T-305 | BON-3 **AI zapisovatel:** audio / text → Gemini přepis (mluvčí, `MM:SS`, JSON) → `DocumentReference/Pxx-mdtNN-prepis` → draft `Decision` s citacemi segmentů — ARCH §5.6 | AI + UI | T-208, T-012, T-314 | z nahrávky P03 vznikne editovatelný draft | `@?` | ⬜ |
| T-306 | BON-4 **Shrnutí pro pacienta** (laický jazyk, zohlední PROMs `priorita` a `postoj`, po potvrzení) | AI + UI | T-209 | text se zobrazí a je v exportu | `@?` | ⬜ |
| T-307 | BON-5 **mCODE:** `meta.profile` + kódy pro biomarkery a TNM v exportu (vstup je jen text); (stretch) import mCODE IG do IRIS + `$validate` | DATA | T-210 | export odkazuje profily; validace (pokud se stihne) projde | `@?` | ⬜ |
| T-308 | **MCP server** nad IRIS (FastMCP: `get_patient_context`, `search_evidence`, `search_guidelines`, `fhir_query`), read-only — ARCH §4.7 | DATA | T-102 | dotaz z MCP klienta vrátí data | `@?` | ⬜ |
| T-309 | FHIR SQL Builder projekce (`Observation` labs, hmotnost, ECOG) a použití pro `TrendChart` / pravidla | DATA | T-101 | SQL dotaz nad projekcí vrací řady | `@?` | ⬜ |
| T-310 | UI polish: prezentační režim, loading a empty stavy, projektor (kontrast, velikost), dark mode | UI | T-205 | projde kontrolou na projektoru / velkém monitoru | `@?` | ⬜ |
| T-311 | **Demo fallback:** předgenerovaný a uložený podklad P03 (cache), přepínač „offline demo“ | INFRA + API | T-212 | demo jede i bez Gemini | `@?` | ⬜ |
| T-312 | **Pravidla z konzultace:** `RF-IDENTITY` (strana těla, pohlaví, věk, datum), `RF-PRIOR-PROC` (předchozí výkony, implantáty, alergie), `RF-DATAQUALITY` (pořadí dat, jednotky, `Observation` bez `derivedFrom`) + FR-A4 alerts v hlavičce — ARCH §5.4 | AI | T-202 | P02: LVEF bez zdroje jsou označené; P03: port a stent jsou v alerts | `@?` | ⬜ |
| T-313 | Ověřit `Patient/$everything` a import mCODE IG v naší verzi IRIS (Q7), výsledek zapsat do ARCH §4.6 | DATA | T-101 | odpověď v Blokerech, ARCH aktualizovaná | `@?` | ⬜ |
| T-314 | **Nahrát simulovanou diskusi MDT** k P03 (2–3 min, více mluvčích podle rolí, závěr + úkoly) → `data/audio/P03_mdt02.m4a` + referenční text | PITCH | — | nahrávka a text v repu | `@?` | ⬜ |

### M4 — Freeze a demo (do So 11:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-401 | **Demo scénář** 5 min / P03 (viz [§7](#7-demo-checklist-finále-5-min-pacient-p03)) + nácvik 3× se stopkami | PITCH | T-212 | scénář v `docs/DEMO.md`, čas < 5:00 | `@?` | ⬜ |
| T-402 | **Pitch slidy:** problém → řešení → demo → tech (Gemini, IRIS FHIR + Vector Search, anti-halucinace + eval čísla, ochrana dat: placený tier, cesta přes Vertex AI EU) → InterSystems → dopad a cesta k MVP | PITCH | T-301 | slidy hotové, odkaz v Deníku | `@?` | ⬜ |
| T-403 | Záložní **video** celého dema (screen recording) | PITCH | T-212 | video nahrané, odkaz v Deníku | `@?` | ⬜ |
| T-404 | Feature freeze 10:00 → jen bugfixy; code freeze 11:00, tag `v1.0-demo`, ověřit prod | INFRA | — | tag v gitu, prod = tag | `@?` | ⬜ |
| T-405 | Odevzdání (repo, popis, odkazy, video) + přihláška do výzvy InterSystems | PITCH | T-404 | **zatím neřešíme** (rozhodnutí týmu) | `@?` | ⏸ |

---

## 5. Blokery a otevřené otázky

| # | Otázka / bloker | Blokuje | Kdo řeší | Stav |
|---|---|---|---|---|
| Q1 | Formát a doručení datasetu | T-101 | — | ✅ dataset v1.1 je FHIR R4 ([DATASET.md](DATASET.md)) |
| Q2 | LLM provider a klíč | T-012 | tým | ✅ Google AI Studio / Gemini (D-008); billing viz Q9 |
| Q3 | Server pro backend | T-005 | tým | ✅ VPS; doménu doplní INFRA |
| Q4 | Pravidla odevzdání, commity po So 12:00 | T-405, M5 | tým | ⏸ zatím neřešíme |
| Q5 | Veřejné repo, dataset v gitu | T-001 | tým | ✅ ano, smí |
| Q6 | Klinické prahy red flags: připomínky onkologů | T-202 | `@?` → mentoři | ⬜ zatím nemáme; prahy z guidelines OBC/KRC/PRS/PLI |
| Q7 | `Patient/$everything` a import mCODE IG ve verzi IRIS | T-006, T-307 | `@?` → O. Hoferek (T-313) | ⬜ |
| Q8 | Kdy a v jakém formátu bude oficiální ground truth? | T-301 | `@?` → Ľ. Piljan | ⬜ |
| Q9 | **Zapnout billing (placený tier) v Google AI Studio.** Bez něj nesmíme posílat data (podmínky Gemini API pro EHP) | T-012, T-102 | `@?` | ⬜ |

---

## 6. Deník (append-only)

> Formát: `- Den HH:MM · @kdo · T-xxx · co se stalo (větev / odkaz)`. Nové řádky přidávej **na konec**.

- Pá 15:15 · @jaram+claude · — · Založena ARCHITEKTURA.md, PROGRESS.md, AGENTS.md (extrakce zadání, výzkum InterSystems a FHIR-AI-Hackathon-Kit).
- Pá 15:57 · @xxzoomczexx · — · MYSLENKOVA_MAPA.md: přehled + poznámky z konzultace se zadavateli.
- Pá 16:20 · @jaram+claude · T-007 · Dataset v1.1 popsán v DATASET.md: FHIR R4, 1 091 resources, sanitizace (`_` v ID, prázdný string), guidelines, studie, hypotézy nesrovnalostí. ARCHITEKTURA přepsána: Gemini (D-008), výstup ve struktuře datasetu (D-009), plný kontext + vektory pro grounding (D-010), požadavky z konzultace (FR-A4, FR-B7, RF-IDENTITY / PRIOR-PROC / DATAQUALITY). ⚠️ KONTRAKT: §8 Evidence ID = ID z datasetu, `RoleAssessment`, `Criterion`, `header.comorbidities` / `alerts` / `mdt_date`, `Decision.sections` podle záznamu MDT. Nové úkoly T-013, T-213, T-312–T-314; T-008 ✂️.

---

## 7. Demo checklist (finále, 5 min, pacient P03)

| # | Krok | Co ukázat | Funkce | ✔ |
|---|---|---|---|---|
| 1 | Nastavení | předseda naklikne sekce, pořadí, přítomné role (onkolog, hepatobiliární chirurg, radiolog, patolog, pacient), detail | T-206 | ⬜ |
| 2 | Generování | podklad za pár sekund (průběh) | T-107, T-201 | ⬜ |
| 3 | 30 s orientace | `CaseHeader`: C18.7 + jaterní mts, cT3 cN1 cM1a, **ECOG 0 (lékař) vs. 1 (pacient)**, otázka resekability, komorbidity (IM, stent), red flags | T-108 | ⬜ |
| 4 | Ověření | klik na tvrzení → zdroj (`P03-img03` „hrudník nebyl požadován“); red flag **neuropatie G1 vs. pacient „padají mi věci z ruky“** → oba zdroje + KRC-3.2 | T-104, T-202 | ⬜ |
| 5 | B2 | možnosti (resekce dvoudobě / pokračovat v systémové léčbě) s pasážemi KRC-2.x + **RKT-03** (Z1, V2 `unknown`, V3 sporné) + RECIST PR | T-204, T-304 | ⬜ |
| 6 | Závěr | AI zapisovatel z nahrávky / ruční zápis, potvrzení předsedou → **zápis do IRIS** (ukázat `Composition/P03-mdt02` + `Provenance` v Management Portalu / Swaggeru) | T-208, T-209, T-305 | ⬜ |
| 7 | Export | PDF + FHIR document Bundle (mCODE profily) | T-210, T-307 | ⬜ |
| 8 | Tech (30 s) | Gemini (placený tier, cesta k Vertex AI EU), RAG nad IRIS FHIR + Vector Search s filtrem na pacienta, grounding validátor + **čísla z evalu**, pseudonymizace, AI Act / MDR | T-301 | ⬜ |

---

## 8. Rozhodnutí (decision log)

| # | Rozhodnutí | Kdy | Kdo |
|---|---|---|---|
| D-001 | FE Next.js 16 na Vercelu, BE Django na **VPS** | Pá 15:00 / 16:00 | tým |
| D-002 | IRIS for Health FHIR = nemocniční DB (zdroj pravdy), Postgres = jen stav aplikace | Pá 15:15 | návrh |
| D-003 | Same-origin proxy přes Vercel `rewrites` (httpOnly cookies, `SameSite=Strict`) | Pá 15:15 | návrh |
| D-004 | Generování = async job + polling (Vercel neproxyuje WebSockety) | Pá 15:15 | návrh |
| D-005 | ID z datasetu zachovat (sanitizace `_` → `-`) + `PUT` transaction (idempotentní ingest) | Pá 16:20 | návrh |
| D-006 | Evidence ID = ID zdroje z datasetu (`P03-img03`, `#n`, `KRC-2.4`, `RKT-03/V3`) | Pá 16:20 | návrh |
| D-007 | Embeddings `gemini-embedding-001` @ 1536 + L2 normalizace (místo OpenAI z kitu) | Pá 16:20 | návrh |
| D-008 | **LLM, embeddingy i přepis = Google AI Studio (Gemini API), placený tier**; výchozí `gemini-3.8-flash` | Pá 16:00 | tým |
| D-009 | Zápis komise ve struktuře předchozích MDT z datasetu (`Composition` `mdt-zaznam` + `CarePlan` + `CareTeam` + lokální číselníky) | Pá 16:20 | návrh |
| D-010 | Do LLM plný kontext pacienta; IRIS Vector Search pro řazení, citace a ověření tvrzení | Pá 16:20 | návrh |
| D-011 | Dataset smí do gitu (repo je veřejné) | Pá 16:00 | tým |
| D-012 | Odevzdání zatím neřešíme | Pá 16:00 | tým |
| D-013 | Demo pacient P03, záloha P05 | Pá 16:20 | návrh |
