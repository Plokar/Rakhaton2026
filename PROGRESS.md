# MDT Copilot — roadmapa a progress

> **Uzávěrka: sobota 17. 10. 2026, 12:00** · lokální pitch 13:00 · TOP 3 v 17:00 · národní finále v neděli od 14:00
>
> Architektura, požadavky a kontrakty: [ARCHITEKTURA.md](ARCHITEKTURA.md) · pravidla pro AI agenty: [AGENTS.md](AGENTS.md)

**Stav:** 🟢 M0 Setup · aktualizováno: Pá 16. 10. 15:15

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
| ✂️ | `cut` | vyškrtnuto kvůli času |

### Protokol (krok za krokem)

1. **Sync:** `git pull --rebase origin master`.
2. **Přečti:** [AGENTS.md](AGENTS.md), pak relevantní sekce [ARCHITEKTURA.md](ARCHITEKTURA.md) (každý úkol na ně odkazuje) a tento soubor.
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
8. **Zablokovaný?** Stav ⛔, zápis do [Blokerů](#5-blokery-a-otevřené-otázky) a vezmi si jiný úkol.

### Pravidla

- **Nikdy** necommituj `.env`, API klíče ani hesla. Nikdy nedělej `push --force` do `master`.
- Neupravuj soubory jiné lane bez domluvy. Neformátuj hromadně cizí soubory.
- V tabulce úkolů **1 úkol = 1 řádek**. Deník je append-only (nové řádky na konec). Konflikty v tomto souboru řeš tak, že **ponecháš obě strany**.
- Testy a vývoj pracují s `AI_PROVIDER=mock` a placené LLM se volá jen ručně.
- Když úkol nestihneš (např. musíš odejít), vrať ho na ⬜ a do Deníku napiš, v jakém je stavu a na jaké větvi.

---

## 2. Lanes (pracovní proudy) a lidé

| Lane | Zaměření | Klíčové složky | Owner |
|---|---|---|---|
| **INFRA** | Vercel, server, Docker, IRIS kontejner, deploy | `WEB_Template/docker-compose*.yml`, `WEB_Template/iris/`, `next.config.ts` | `@?` |
| **DATA** | dataset → FHIR, seed do IRIS, vektory, guidelines, studie | `backend/services/fhir/mappers/`, `backend/services/iris/`, `data/` | `@?` |
| **AI** | context builder, prompty, grounding, red flags, B2, scribe, eval | `backend/services/ai/`, `backend/services/rules/` | `@?` |
| **API** | Django apps, modely, endpointy, FHIR write-back, export | `backend/apps/{patients,mdt,copilot}/`, `backend/services/fhir/{writeback,export}.py` | `@?` |
| **UI** | Next.js stránky a komponenty, UX | `frontend/src/app/dashboard/`, `frontend/src/components/mdt/`, `frontend/src/types/` | `@?` |
| **PITCH** | demo scénář, slidy, video, QA, koordinace | `docs/`, `PROGRESS.md` | `@?` |

> Doplňte jména. Jeden člověk může mít víc lanes. Doporučení pro 4 lidi: (1) INFRA + API, (2) DATA, (3) AI, (4) UI + PITCH.

---

## 3. Milníky

| Milník | Cíl | Do kdy | Stav |
|---|---|---|---|
| **M0** Setup a kontrakty | běží IRIS lokálně i na serveru, Vercel deploy „hello“, kontrakty zmrazené, fixtures, pacient 0 | **Pá 18:00** | 🟨 |
| **M1** Vertikální řez | 1 pacient end-to-end: FHIR v IRIS → blok A s citacemi → UI → klik na citaci ukáže zdroj | **Pá 23:00** | ⬜ |
| **M2** Kompletní funkce | B (≥ 3 role), B2 (guidelines + studie), red flags, konfigurátor, zápis + potvrzení → IRIS FHIR, export PDF + FHIR | **So 04:00** | ⬜ |
| **M3** Spolehlivost a bonusy | všichni pacienti z datasetu, eval proti ground truth, readiness, RECIST, zapisovatel, shrnutí pro pacienta | **So 09:00** | ⬜ |
| **M4** Freeze a odevzdání | feature freeze 10:00 · code freeze 11:00 · nasazeno + tag · odevzdáno **do 12:00** | **So 12:00** | ⬜ |
| **M5** (podmíněně) Finále | pokud TOP 3: doladění dema a pitche pro národní finále (ověřit, co pravidla dovolují) | **Ne 14:00** | ⬜ |

**Nejdůležitější cesta:** T-002 → T-003 → T-008 → T-101 → T-105 → T-106 → T-108, pak paralelně M2. UI se do té doby nečeká, jede nad fixtures (T-009).

---

## 4. Task board

### M0 — Setup a kontrakty (do Pá 18:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-001 | Struktura repa: `docs/zadani/` (přesun pptx), `data/{raw,fhir,guidelines,trials,ground_truth,fixtures}/`, `.gitignore` (`.env`, `.venv`) | INFRA | — | složky v `master`, pptx přesunuté | `@?` | ⬜ |
| T-002 | Služba `iris` v `docker-compose.dev.yml` (Dockerfile + `merge.cpf` z kitu do `WEB_Template/iris/`, volume, porty 1972/52773) — ARCH §3.4, §4.2 | INFRA | T-001 | `curl -u SuperUser:SYS localhost:52773/fhir/r4/metadata` vrátí 200 po `dev.ps1 up` | `@?` | ⬜ |
| T-003 | Command `iris_init` (native API: namespace FHIRSERVER + endpoint `/fhir/r4`, idempotentní, bez Synthea) — ARCH §4.2 | INFRA | T-002 | 2× spuštění bez chyby, endpoint existuje | `@?` | ⬜ |
| T-004 | Vercel: projekt (root `WEB_Template/frontend`), `rewrites` `/api/*` → `BACKEND_URL`, `skipTrailingSlashRedirect`, `api.ts` same-origin (`??`), dev odkazy jen v dev — ARCH §3.4 | INFRA | — | přihlášení demo účtem funguje na `*.vercel.app` proti nasazenému BE | `@?` | ⬜ |
| T-005 | Server: VPS + DNS `api.<doména>`, prod compose (Traefik, backend, db, redis, **iris interně**), změnit heslo IRIS, `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` — ARCH §3.4 | INFRA | T-002 | `https://api.<doména>/api/health/` vrátí 200, IRIS zvenku nedostupný | `@?` | ⬜ |
| T-006 | `services/iris/db.py` (connect ctx manager, env `IRIS_*`) + `services/fhir/client.py` (auth, paging, search, transaction, fallback místo `$everything`) — ARCH §4.6 | API | T-002 | pytest proti lokálnímu IRIS: zápis a čtení `Patient` | `@?` | ⬜ |
| T-007 | Získat dataset od Asseco, popsat formát a obsah v `data/README.md` (pacienti, typy dokumentů, ground truth) | DATA | — | inventář v repu, Q1 vyřešená | `@?` | ⬜ |
| T-008 | **Pacient 0:** ručně vytvořený FHIR transaction bundle (např. kolorektum, 2× PROMs, vložený rozpor Hb vs. únava a ECOG 1 vs. 3) pokrývající typy z ARCH §4.3 → `data/fhir/p00.json` | DATA | — | bundle se nahraje do IRIS přes `PUT`, opakovaně bez duplikátů | `@?` | ⬜ |
| T-009 | **Zmrazit kontrakty:** `apps/copilot/schemas.py` (pydantic) + `frontend/src/types/mdt.ts` + fixtures `data/fixtures/brief_p00.json`, `decision_p00.json` — ARCH §8 | AI + UI | — | FE i BE importují typy, fixture projde validací pydantic | `@?` | ⬜ |
| T-010 | UI čistka: branding „MDT Copilot“, navigace MDT (Přehled, Zasedání, Úkoly), skrýt Projekty/Úložiště/WS/AI Studio | UI | — | nová navigace v `master`, build projde | `@?` | ⬜ |
| T-011 | Zkopírovat IRIS skills z FHIR-AI-Hackathon-Kit `skills/*` do `.claude/skills/` (+ volitelně `iris-agentic-dev` v `.mcp.json`) — ARCH §4.8 | PITCH | — | skills v repu, agent je umí načíst | `@?` | ⬜ |
| T-012 | Rozhodnout LLM provider + model + klíč (EU?) a zapsat do Rozhodnutí; rozšířit `ai_service.py` o structured output + `embed()` — ARCH §5.7 | AI | — | `mock` i reálný provider vrací validní JSON dle schématu | `@?` | ⬜ |

### M1 — Vertikální řez (do Pá 23:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-101 | Mappery dataset → FHIR + `ingest_dataset` (stabilní ID, `PUT` transaction, pořadí resources) — ARCH §4.3, §4.4 | DATA | T-006, T-007 | všichni pacienti datasetu v IRIS, 2. běh bez duplikátů | `@?` | ⬜ |
| T-102 | Chunking + embeddingy textů → `MDT.EvidenceChunk` (DDL, batch insert, `search_evidence(patient_id, q)`) — ARCH §4.5 | DATA | T-006, T-012 | dotaz vrací jen úseky daného pacienta se skóre | `@?` | ⬜ |
| T-103 | API pacientů: `GET /api/patients/`, `/{pid}/`, `/{pid}/timeline/`, `/{pid}/observations/` z FHIR — ARCH §6.3 | API | T-006, T-008 | Swagger ukazuje data pacienta 0 | `@?` | ⬜ |
| T-104 | Evidence resolver `GET /api/evidence/?id=` (structured hodnota / text + offset zvýraznění) — ARCH §5.2 | API | T-006, T-102 | pro každý typ Evidence ID vrátí zdroj | `@?` | ⬜ |
| T-105 | `context_builder` (FHIR → evidence list s ID) + `pseudonymize` — ARCH §5.1, §5.7 | AI | T-006, T-008 | výstup pro p00 neobsahuje jméno ani datum narození; ID odpovídají FHIR | `@?` | ⬜ |
| T-106 | Generátor **bloku A** (souhrn, ECOG compare, časová osa) + **grounding validátor v1** (citace, čísla, data, missing checklist) — ARCH §5.3 | AI | T-105, T-009, T-012 | Brief A pro p00 validní podle schématu, 0 neověřených tvrzení | `@?` | ⬜ |
| T-107 | Modely `MdtSession`, `MdtCase`, `Brief`, `GenerationJob`, `LlmCallLog` + job endpointy `POST /cases/{cid}/brief/`, `GET /jobs/{jid}/` (ThreadPool) + `seed_mdt` — ARCH §6.2, §6.3 | API | T-106 | FE spustí generování a polluje výsledek | `@?` | ⬜ |
| T-108 | Stránka podkladu: `CaseHeader`, `AiBlock`, `Claim` + `CitationChip`, `SourceDrawer`, `MissingData`, `JobProgress` (nejdřív nad fixture) — ARCH §7.2 | UI | T-009, T-010 | klik na citaci otevře zdroj; běží na fixture i na živém API | `@?` | ⬜ |
| T-109 | Agenda zasedání `/dashboard/mdt/[sessionId]` + přehled `/dashboard` | UI | T-009, T-107 | seznam případů, přechod na podklad | `@?` | ⬜ |
| T-110 | Deploy M1 na prod (Vercel + server, ingest na serveru) + smoke test | INFRA | T-004, T-005, T-101, T-107, T-108 | vertikální řez funguje na veřejné URL | `@?` | ⬜ |

### M2 — Kompletní funkce (do So 04:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-201 | **Blok B:** prompty pro role (chirurg, onkolog, radiolog, patolog, pacient, radiační onkolog) + vector dotazy pro sekce, paralelní generace — FR-B1–B6 | AI | T-106 | ≥ 3 role validní, celý podklad < 20 s | `@?` | ⬜ |
| T-202 | **Red flags:** `rules/red_flags.py` (RF-ECOG, RF-HB-FATIGUE, RF-MARKER, RF-TOX, RF-STALE, RF-MISSING) + `RF-LLM` rozpory; ≥ 2 citace — ARCH §5.4 | AI | T-105 | najde vložené rozpory v p00 (a v datasetu dle ground truth) | `@?` | ⬜ |
| T-203 | Guidelines + studie: ingest do `MDT.GuidelineChunk`, `ResearchStudy` v FHIR + `MDT.TrialCriterion` — ARCH §4.5 | DATA | T-102, T-007 | vyhledání podle `CancerType` vrací relevantní sekce | `@?` | ⬜ |
| T-204 | **B2:** možnosti léčby s citací guidelines, screening studií po kritériích, 2–3 otázky — ARCH §5.5 | AI | T-203, T-106 | `DecisionSupport` validní; žádné „doporučujeme“ | `@?` | ⬜ |
| T-205 | UI: `RoleTabs`, `RedFlagCard`, `EcogCompare`, `Timeline`, `TrendChart` (Hb, markery, PROMs), `TreatmentOptions`, `TrialScreening` | UI | T-108 | všechny sekce §8 se vykreslí z fixture i API | `@?` | ⬜ |
| T-206 | **Konfigurátor** `/setup`: sekce zap/vyp, drag & drop pořadí, přítomné role, detail, presety; přegenerovat — FR-R1 | UI | T-108 | změna nastavení se projeví v novém podkladu | `@?` | ⬜ |
| T-207 | API konfigurace: `BriefConfig` CRUD + promítnutí do promptů (sekce, role, detail, jazyk) | API + AI | T-107 | různé presety dávají různé výstupy | `@?` | ⬜ |
| T-208 | **Editor závěru** `/record`: rozhodnutí, zdůvodnění, úkoly (owner, termín), re-review, přítomní; AI vs. člověk odlišení — FR-C1, C2, R4 | UI | T-205 | draft se ukládá, AI předvyplnění je vizuálně odlišené | `@?` | ⬜ |
| T-209 | **Potvrzení → IRIS FHIR:** `writeback.py` transaction (`CarePlan`, `Task[]`, `DetectedIssue[]`, `Provenance`, `Composition`, volitelně `Encounter`, `ResearchSubject`) — ARCH §4.3 výstupy | API | T-107, T-006 | po potvrzení jsou resources v IRIS a `fhir_ids` v `Decision` | `@?` | ⬜ |
| T-210 | **Export:** `export.fhir.json` (document Bundle) + `export.pdf` (+ `DocumentReference` PDF v IRIS) — FR-C4 | API | T-209 | oba soubory ke stažení, Bundle jde znovu POSTnout do IRIS | `@?` | ⬜ |
| T-211 | Nominace (`POST /api/mdt/cases/` → FHIR `ServiceRequest`) + formulář v UI — FR-P1 | API + UI | T-107 | nový případ se objeví v agendě | `@?` | ⬜ |
| T-212 | Deploy M2 + smoke test celého cyklu na prod | INFRA | T-201…T-210 | 6 kroků finálové ukázky projde na veřejné URL | `@?` | ⬜ |

### M3 — Spolehlivost a bonusy (do So 09:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-301 | **Eval** `eval_ground_truth` → `docs/EVAL.md` (recall red flags, pokrytí faktů, % neověřených, „údaj chybí“) — ARCH §5.8 | AI + PITCH | T-202, T-101 | tabulka metrik pro všechny pacienty | `@?` | ⬜ |
| T-302 | Ladění promptů a validátoru podle evalu (cíl: 0 neověřených, všechny ground-truth flags) | AI | T-301 | metriky lepší než první běh, zapsané v EVAL.md | `@?` | ⬜ |
| T-303 | BON-1 **Readiness check** (`rules/readiness.py` + badge v agendě) | AI + UI | T-202 | případům s mezerami se ukáže, co chybí | `@?` | ⬜ |
| T-304 | BON-2 **RECIST 1.1** předvýpočet (`rules/recist.py`, SLD, CR/PR/SD/PD) v pohledu radiologa | AI | T-201 | výsledek s citacemi měření | `@?` | ⬜ |
| T-305 | BON-3 **AI zapisovatel:** přepis → draft `Decision` s citacemi na úseky přepisu | AI + UI | T-208 | z přepisu vznikne editovatelný draft | `@?` | ⬜ |
| T-306 | BON-4 **Shrnutí pro pacienta** (laický jazyk, po potvrzení) | AI + UI | T-209 | text se zobrazí a je v exportu | `@?` | ⬜ |
| T-307 | BON-5 **mCODE:** `meta.profile` + kódy v exportu; (stretch) import mCODE IG do IRIS + `$validate` | DATA | T-210 | export odkazuje profily; validace (pokud se stihne) projde | `@?` | ⬜ |
| T-308 | **MCP server** nad IRIS (FastMCP: `get_patient_context`, `search_evidence`, `search_guidelines`, `fhir_query`), read-only — ARCH §4.7 | DATA | T-102 | dotaz z MCP klienta vrátí data | `@?` | ⬜ |
| T-309 | FHIR SQL Builder projekce (labs) a použití pro `TrendChart` / dashboard | DATA | T-101 | SQL dotaz nad projekcí vrací řady | `@?` | ⬜ |
| T-310 | UI polish: prezentační režim, loading a empty stavy, projektor (kontrast, velikost), dark mode | UI | T-205 | projde kontrolou na projektoru / velkém monitoru | `@?` | ⬜ |
| T-311 | **Demo fallback:** předgenerovaný a uložený podklad demo pacienta (cache), přepínač „offline demo“ | INFRA + API | T-212 | demo jede i bez LLM | `@?` | ⬜ |

### M4 — Freeze a odevzdání (do So 12:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-401 | **Demo scénář** 5 min / 1 pacient (viz [§7](#7-demo-checklist-finále-5-min)) + nácvik 3× se stopkami | PITCH | T-212 | scénář v `docs/DEMO.md`, čas < 5:00 | `@?` | ⬜ |
| T-402 | **Pitch slidy:** problém → řešení → demo → tech (model, RAG v IRIS, anti-halucinace + eval čísla, ochrana dat) → InterSystems → dopad a cesta k MVP | PITCH | T-301 | slidy hotové, odkaz v Deníku | `@?` | ⬜ |
| T-403 | Záložní **video** celého dema (screen recording) | PITCH | T-212 | video nahrané, odkaz v Deníku | `@?` | ⬜ |
| T-404 | Feature freeze 10:00 → jen bugfixy; code freeze 11:00, tag `v1.0-submission`, ověřit prod | INFRA | — | tag v gitu, prod = tag | `@?` | ⬜ |
| T-405 | **Odevzdání** (repo, popis, odkazy, případně video) + přihláška do výzvy InterSystems | PITCH | T-404 | potvrzení o odevzdání **do 12:00** | `@?` | ⬜ |

---

## 5. Blokery a otevřené otázky

| # | Otázka / bloker | Blokuje | Kdo řeší | Stav |
|---|---|---|---|---|
| Q1 | Formát a doručení datasetu (včetně ground truth a přepisu) | T-007, T-101 | `@?` → Ľ. Piljan | ⬜ |
| Q2 | LLM provider a klíč (kdo platí, EU region) | T-012 | tým | ⬜ |
| Q3 | Server a doména pro backend (VPS / VZP Azure?) | T-005 | `@?` | ⬜ |
| Q4 | Pravidla odevzdání a zda lze commitovat po So 12:00 (finále) | T-405, M5 | `@?` → organizátoři | ⬜ |
| Q5 | Je repo veřejné? Smí dataset do gitu? | T-007 | `@?` | ⬜ |
| Q6 | Klinické prahy red flags a obsah rolí: připomínky onkologů | T-202 | `@?` → mentoři | ⬜ |
| Q7 | `Patient/$everything` a import mCODE IG ve verzi IRIS | T-006, T-307 | `@?` → O. Hoferek | ⬜ |

---

## 6. Deník (append-only)

> Formát: `- Den HH:MM · @kdo · T-xxx · co se stalo (větev / odkaz)`. Nové řádky přidávej **na konec**.

- Pá 15:15 · @jaram+claude · — · Založena ARCHITEKTURA.md, PROGRESS.md, AGENTS.md (extrakce zadání, výzkum InterSystems a FHIR-AI-Hackathon-Kit).

---

## 7. Demo checklist (finále, 5 min)

| # | Krok | Co ukázat | Funkce | ✔ |
|---|---|---|---|---|
| 1 | Nastavení | předseda naklikne sekce, pořadí, přítomné role, detail | T-206 | ⬜ |
| 2 | Generování | podklad za pár sekund (průběh) | T-107, T-201 | ⬜ |
| 3 | 30 s orientace | `CaseHeader` + souhrn: dg., TNM, ECOG lékař vs. pacient, otázka | T-108 | ⬜ |
| 4 | Ověření | klik na tvrzení → zdroj; klik na red flag → oba zdroje | T-104, T-202 | ⬜ |
| 5 | B2 | možnosti léčby s citací guidelines + vhodné studie po kritériích | T-204 | ⬜ |
| 6 | Závěr | zápis (případně z AI zapisovatele), potvrzení předsedou → **zápis do IRIS FHIR** (ukázat `CarePlan` / `Provenance`) | T-208, T-209 | ⬜ |
| 7 | Export | PDF + FHIR Bundle (mCODE profily) | T-210 | ⬜ |
| 8 | Tech (30 s) | model, RAG nad IRIS Vector Search s filtrem na pacienta, grounding validátor + **čísla z evalu**, pseudonymizace a EU, AI Act / MDR | T-301 | ⬜ |

---

## 8. Rozhodnutí (decision log)

| # | Rozhodnutí | Kdy | Kdo |
|---|---|---|---|
| D-001 | FE Next.js 16 na Vercelu, BE Django na externím serveru | Pá 15:00 | tým |
| D-002 | IRIS for Health FHIR = nemocniční DB (zdroj pravdy), Postgres = jen stav aplikace | Pá 15:15 | návrh |
| D-003 | Same-origin proxy přes Vercel `rewrites` (httpOnly cookies, `SameSite=Strict`) | Pá 15:15 | návrh |
| D-004 | Generování = async job + polling (Vercel neproxyuje WebSockety) | Pá 15:15 | návrh |
| D-005 | Stabilní FHIR ID + `PUT` transaction (idempotentní seed) | Pá 15:15 | návrh |
| D-006 | Evidence ID = `ResourceType/id[#fragment]` | Pá 15:15 | návrh |
| D-007 | Embeddings `text-embedding-3-small` (1536) jako v kitu | Pá 15:15 | návrh |
| D-008 | LLM provider / model: _doplnit (T-012)_ | | |
