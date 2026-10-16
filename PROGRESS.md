# MDT Copilot — roadmapa a progress

> Harmonogram hackathonu: odevzdání So 17. 10. 12:00 (*zatím neřešíme*) · lokální pitch 13:00 · TOP 3 v 17:00 · národní finále v neděli od 14:00
>
> - Architektura, požadavky a kontrakty: [ARCHITEKTURA.md](ARCHITEKTURA.md)
> - Dataset: [DATASET.md](DATASET.md)
> - Pravidla pro AI agenty: [AGENTS.md](AGENTS.md)
> - Přehled: [MYSLENKOVA_MAPA.md](MYSLENKOVA_MAPA.md)
> - Požadavky lékaře (obrazovky, semafor, škály, zkratky): [docs/POZADAVKY_LEKARE.md](docs/POZADAVKY_LEKARE.md)

**Stav:** 🟢 Sprint 0 běží od Pá 19:00 · owneři lanes ✅ · dataset ✅ · LLM = `gemini-3.8-flash` ✅ · požadavky lékaře zapracované ✅ · aktualizováno: Pá 16. 10. 19:11

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

### Sprinty a paralelní práce (víc lidí, strojů a agentů)

- **Sprint = milník** ([§3](#3-milníky--sprinty)). Na konci sprintu:
  1. všechno hotové je v `master`;
  2. proběhne smoke test (`.\dev.ps1 up`, přihlášení, podklad P03);
  3. tým přeplánuje §4 (stavy, owneři, nové úkoly) a zapíše to do Deníku.
- **Na začátku sprintu** si každý člověk zapíše svou lane do [§2](#2-lanes-pracovní-proudy-a-lidé). Agent pracuje vždy za konkrétního člověka (`@jméno+agent`).
- **Jeden agent = jeden úkol = jedna větev.** Když na jednom stroji pracuje víc agentů, každý má vlastní `git worktree`, ne společnou pracovní kopii:

  ```bash
  git fetch origin
  git worktree add -b t-xxx-popis ../rk-t-xxx origin/master
  ```
- **Před claimem i před každým push:** `git pull --rebase origin master`. Když push selže, znovu `pull --rebase`, vyřeš konflikty a zkontroluj, že úkol mezitím nezabral někdo jiný.
- **Sdílené soubory** (PROGRESS.md, ARCHITEKTURA.md, `apps/copilot/schemas.py`, `src/types/mdt.ts`, `data/fixtures/`): malé samostatné commity a hned push. Konflikt v PROGRESS.md řeš tak, že ponecháš obě strany.
- **Nikdo nečeká na nikoho:**
  - UI jede nad fixtures (T-009);
  - AI nad `AI_PROVIDER=mock` a pacientem P03;
  - DATA a INFRA táhnou kritickou cestu.

  Kontrakty se mění jen v PR, který upraví i ARCHITEKTURA.md ([§1](#1-jak-tady-pracujeme-lidé-i-ai-agenti), bod 7).
- **Nový stroj:**
  1. `git clone`;
  2. na Windows **před prvním checkoutem** `git config --global core.autocrlf input`. Dokud T-001 nepřidá `.gitattributes`, dostane jinak `entrypoint.sh` CRLF a backend nenaběhne (Q12);
  3. `cd WEB_Template; .\dev.ps1 up` (vytvoří `.env` z `.env.dev.example`).

  Node lokálně není nutný, frontend běží v Dockeru. Klíč Gemini mají jen lidé s placeným tierem (Q9), ostatní pracují s `AI_PROVIDER=mock`.
- **Merge:**
  - úkol jen v mé lane → merge po lint a testech;
  - úkol přes víc lanes nebo se změnou kontraktu → PR a review od ownera dotčené lane.

---

## 2. Lanes (pracovní proudy) a lidé

| Lane | Zaměření | Klíčové složky | Owner |
|---|---|---|---|
| **INFRA** | Vercel, VPS, Docker, IRIS kontejner, deploy | `WEB_Template/docker-compose*.yml`, `WEB_Template/iris/`, `next.config.ts` | `@Seb` |
| **DATA** | ingest datasetu do IRIS, sanitizace, vektory, guidelines, studie, MCP | `backend/services/fhir/ingest.py`, `backend/services/iris/`, `DATASET.md`, `data/` | `@Maty` |
| **AI** | Gemini provider, context builder, prompty, grounding, red flags, B2, **semafor souladu, kontrola úplnosti**, scribe, eval | `backend/services/ai/`, `backend/services/rules/` (`compatibility.py`, `intake.py`, `data/`), `backend/services/ai_service.py` | `@Jarda` |
| **API** | Django apps, modely, endpointy, **role a boardy**, FHIR write-back, export | `backend/apps/{patients,mdt,copilot}/`, `backend/services/fhir/{writeback,export}.py` | `@Seb` |
| **UI** | Next.js stránky a komponenty, UX, **úzké rozložení** | `frontend/src/app/dashboard/`, `frontend/src/app/brief/`, `frontend/src/components/mdt/`, `frontend/src/types/` | `@Mira` |
| **PITCH** | demo scénář, slidy, video, QA, dev ground truth, požadavky lékaře, koordinace | `docs/` (`POZADAVKY_LEKARE.md`), `data/dev_ground_truth/`, `PROGRESS.md` | `@Mira` |

> Rozdělení od Pá 19:00: **Seb** = INFRA + API, **Maty** = DATA, **Jarda** = AI, **Mira** = UI + PITCH. Jeden člověk může mít víc lanes; změnu zapiš sem a do Deníku. Agent pracuje vždy za ownera své lane (`@jméno+agent`).

---

## 3. Milníky = sprinty

| Milník | Cíl | Do kdy | Stav |
|---|---|---|---|
| **M0** · Sprint 0: Setup a kontrakty | IRIS běží lokálně i na VPS, Vercel deploy „hello“, Gemini provider, kontrakty zmrazené, fixtures P03, dataset popsán ✅, požadavky lékaře ✅ (T-500), `.gitignore` + `.gitattributes` (T-001), CI (T-014) | start **Pá 19:00**, co nejdřív (blokuje M1) | 🟨 |
| **M1** · Sprint 1: Vertikální řez | P03 end-to-end: dataset v IRIS → blok A s citacemi → UI → klik na citaci ukáže zdroj; hlavička podle D-018; role a boardy (T-501) | **Pá 23:00** | ⬜ |
| **M2** · Sprint 2: Kompletní funkce | B (≥ 3 role + posouzení), B2 (guidelines + studie), red flags, konfigurátor, zápis + potvrzení → IRIS FHIR, export PDF + FHIR; zařazení pacienta s varováním (T-211, T-502), semafor (T-503), externí zdroje (T-504), úzké rozložení se sekcemi odborností (T-505, T-506), úkoly po zasedání (T-511) | **So 04:00** | ⬜ |
| **M3** · Sprint 3: Spolehlivost a bonusy | všech 6 pacientů, eval proti dev ground truth, readiness, RECIST, zapisovatel, shrnutí pro pacienta, pravidla z konzultace; anamnéza (T-507), Lung-RADS / Fleischner (T-508), zkratky (T-509), vstup PDF (T-510, stretch) | **So 09:00** | ⬜ |
| **M4** · Sprint 4: Freeze a demo | feature freeze 10:00 · code freeze 11:00 · nasazeno + tag · demo nacvičené. Odevzdání ⏸ | **So 11:00** | ⬜ |
| **M5** · (podmíněně) Finále | pokud TOP 3: doladění dema a pitche pro národní finále | **Ne 14:00** | ⬜ |

**Start sprintů: Pá 16. 10. 19:00.** Sprint 0 (M0) se dotahuje jako první, termíny M1–M4 platí beze změny.

**Nejdůležitější cesta:** T-002 → T-003 → T-006 → T-101 → T-105 → T-106 → T-108, pak paralelně M2. UI se do té doby nečeká, jede nad fixtures (T-009). AI ladí prompty nad P03 hned po T-101.

**Tok lékaře** (požadavky lékaře): T-109 → T-501 → T-502 → T-211, souběžně T-503 → T-505.

---

## 4. Task board

### Požadavky → úkoly

Každý požadavek z [ARCHITEKTURA §2](ARCHITEKTURA.md#2-katalog-požadavků) má aspoň jeden úkol. Pokrytí guidelines je v [ARCH §5.11](ARCHITEKTURA.md#511-pokrytí-guidelines).

| Požadavky | Úkoly |
|---|---|
| FR-A1, FR-A2, FR-A4 (hlavička, souhrn, ECOG, alerts) | T-106, T-108, T-312 |
| FR-A3 (časová osa) | T-103, T-205 |
| FR-A5 (anamnéza) | T-507 |
| FR-B1 až FR-B6 (pohledy rolí) | T-201, T-205 |
| FR-B7 (posouzení role) | T-201, T-205 |
| FR-B8 (údaje podle diagnózy) | T-506 |
| FR-D1 až FR-D3 (možnosti léčby, studie, otázky) | T-203, T-204, T-205 |
| FR-D4 (semafor) | T-503, T-505 |
| FR-D5 (katalog metod a odborníků) | T-506 |
| FR-C1 až FR-C4 (závěr, úkoly, potvrzení, export) | T-208, T-209, T-210 |
| FR-R1 (konfigurátor) | T-206, T-207 |
| FR-R2 (red flags) | T-202, T-312 |
| FR-R3 (citace, „údaj chybí“) | T-104, T-108, T-213 |
| FR-R4 (odlišení AI) | T-108, T-208 |
| FR-R5 (zkratky, nejistota AI) | T-509 |
| FR-P1 (boardy a agenda) | T-109, T-501 |
| FR-P2 (zasedání, prezentační režim) | T-109, T-310 |
| FR-P3 (úkoly po zasedání) | T-511 |
| FR-P4 (zařazení pacienta) | T-211, T-502 |
| FR-U1 (role) | T-501 |
| FR-U2 (úzké rozložení) | T-505 |
| BON-1 až BON-5 | T-303, T-304, T-305 (+ T-314), T-306, T-307 |
| BON-6, BON-7 | T-508, T-510 |
| NFR-1 (podklad < 20 s) | T-201, T-301 |
| NFR-2 (grounding) | T-102, T-105, T-213 |
| NFR-3 (ochrana údajů) | T-005, T-105 |
| NFR-4 (audit) | T-107, T-209 |
| NFR-5 (spolehlivé demo) | T-311, T-403 |
| NFR-6 (nasazení) | T-004, T-005, T-110 |

### M0 — Setup a kontrakty (do Pá 18:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-001 | Struktura repa: `docs/zadani/` (přesun pptx), `data/{dev_ground_truth,fixtures,audio}/`, root `.gitignore` (`.env`, `.venv`, `node_modules`, `.claude/settings.local.json`) a **`.gitattributes`** (`* text=auto`, `*.sh text eol=lf`, `*.ps1 text eol=crlf`; jinak Windows s `autocrlf=true` rozbije `entrypoint.sh`, Q12). Dataset zůstává v `Dataset_MDT_Copilot_v1.1_pre_timy/` (smí do gitu) | INFRA | — | složky, dataset, `.gitignore` a `.gitattributes` v `master`; `git ls-files --eol` ukazuje u `*.sh` v pracovní kopii LF | `@Seb+claude` | ✅ |
| T-002 | Služba `iris` v `docker-compose.dev.yml` (Dockerfile + `merge.cpf` z kitu do `WEB_Template/iris/`, volume, porty 1972/52773), mount datasetu do backendu (`DATASET_DIR`) — ARCH §3.4, §4.2 | INFRA | T-001 | `curl -u SuperUser:SYS localhost:52773/fhir/r4/metadata` vrátí 200 po `dev.ps1 up` | `@?` | ⬜ |
| T-003 | Command `iris_init` (native API: namespace FHIRSERVER + endpoint `/fhir/r4`, `Device/mdt-copilot`, idempotentní, bez Synthea) — ARCH §4.2 | INFRA | T-002 | 2× spuštění bez chyby, endpoint existuje | `@?` | ⬜ |
| T-004 | Vercel: projekt (root `WEB_Template/frontend`), `rewrites` `/api/*` → `BACKEND_URL`, `skipTrailingSlashRedirect`, `api.ts` same-origin (`??`), dev odkazy jen v dev — ARCH §3.4 | INFRA | — | přihlášení demo účtem funguje na `*.vercel.app` proti nasazenému BE | `@?` | ⬜ |
| T-005 | **VPS:** DNS `api.<doména>`, prod compose (Traefik, backend, db, redis, **iris interně**), změnit heslo IRIS, `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`, dataset volume — ARCH §3.4 | INFRA | T-002 | `https://api.<doména>/api/health/` vrátí 200, IRIS zvenku nedostupný | `@?` | ⬜ |
| T-006 | `services/iris/db.py` (connect ctx manager, env `IRIS_*`) + `services/fhir/client.py` (auth, paging, search, transaction, fallback místo `$everything`) — ARCH §4.6 | API | T-002 | pytest proti lokálnímu IRIS: `PUT` a čtení `Patient` | `@?` | ⬜ |
| T-007 | Získat dataset, popsat formát a obsah | DATA | — | [DATASET.md](DATASET.md) | `@jaram+claude` | ✅ |
| T-008 | ~~Pacient 0 (ručně vytvořený bundle)~~: nahrazeno datasetem, dev pacient = **P03** | DATA | — | — | — | ✂️ |
| T-009 | **Zmrazit kontrakty:** `apps/copilot/schemas.py` (pydantic, zároveň Gemini `response_schema`) + `frontend/src/types/mdt.ts` + fixtures `data/fixtures/brief_P03.json`, `decision_P03.json` s reálnými ID z P03 (DATASET §9) — ARCH §8 (včetně `RoleAssessment`, `header.comorbidities` / `alerts` / `intent`, `Decision.sections`, `TreatmentCompatibility`, `IntakePrefill` a `MdtCase` z §8.6) + fixture `intake_P03.json` | AI + UI | — | FE i BE importují typy, fixture projde validací pydantic | `@?` | ⬜ |
| T-010 | UI čistka: branding „MDT Copilot“, navigace MDT (Přehled, Zasedání, Úkoly), skrýt Projekty / Úložiště / WS / AI Studio | UI | — | nová navigace v `master`, build projde | `@?` | ⬜ |
| T-011 | Zkopírovat IRIS skills z FHIR-AI-Hackathon-Kit `skills/*` do `.claude/skills/` (+ volitelně `iris-agentic-dev` v `.mcp.json`); poznámka, že kit používá OpenAI a my Gemini — ARCH §4.8 | PITCH | — | skills v repu, agent je umí načíst | `@?` | ⬜ |
| T-012 | **Gemini provider:** přepsat `GeminiProvider` (`google-genai`, `system_instruction`, `response_schema`, výchozí `gemini-3.8-flash` místo vypnutého `gemini-1.5-flash`), `embed()` (`gemini-embedding-001` @ 1536 + L2 normalizace, `task_type`), `transcribe()`; upravit `ai_views.py`, `.env.example` (`GEMINI_API_KEY`, `AI_MODEL`…) — ARCH §5.7 | AI | — | `mock` i `gemini` vrací validní JSON podle schématu; `embed` vrací 1536 normalizovaných čísel | `@?` | ⬜ |
| T-013 | **Dev ground truth** `data/dev_ground_truth/P01…P06.json` z [DATASET §9](DATASET.md#9-vložené-nesrovnalosti--pracovní-hypotézy-týmu) (red flags + pravidlo + severity + ID zdrojů, chybějící údaje, studie po kritériích, RECIST, klíčová fakta, **barvy semaforu** podle docs/POZADAVKY_LEKARE.md §5.4) — ARCH §5.8 | AI + PITCH | T-009 | 6 souborů, každá položka má ID zdrojů a pasáž guidelines | `@?` | ⬜ |
| T-014 | **CI:** GitHub Actions: backend `pytest` (`AI_PROVIDER=mock`, služba Postgres), frontend `npm run lint` + `npm run build`. Opravit `backend/conftest.py`: testovací DB brát z env `POSTGRES_*`, ne natvrdo `localhost`, jinak DB testy v kontejneru ani v CI neprojdou | INFRA | T-001 | PR ukáže zelené testy; `.\dev.ps1 test` projde i v kontejneru | `@?` | ⬜ |
| T-500 | Požadavky lékaře sepsat a sladit se zadáním ([docs/POZADAVKY_LEKARE.md](docs/POZADAVKY_LEKARE.md)), promítnout do ARCHITEKTURA.md | PITCH | — | dokument + FR-U1, FR-U2, FR-P4, FR-B8, FR-D4, FR-D5, FR-A5, FR-R5, BON-6, BON-7 a D-014 až D-020 v ARCH | `@xxzoomczexx+claude` | ✅ |

### M1 — Vertikální řez na P03 (do Pá 23:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-101 | **`ingest_dataset`:** sanitizace (`_` → `-` v ID a referencích, prázdné stringy, `meta.tag`), `collection` → `transaction` s `PUT`, pořadí Questionnaire → studie → pacienti, index `ID → ResourceType`, **kontrola počtů** — [DATASET §6](DATASET.md#6-ingest-do-iris-fhir), ARCH §4.4 | DATA | T-006 | všech 1 091 resources v IRIS, počty sedí s DATASET §2, 2. běh bez duplikátů | `@?` | ⬜ |
| T-102 | Chunking odstavců (DocumentReference, DiagnosticReport, Composition) + Gemini embeddingy → `MDT.EvidenceChunk` (DDL, batch insert, `search_evidence(patient_id, q)`) — ARCH §4.5 | DATA | T-101, T-012 | dotaz vrací jen odstavce daného pacienta se skóre | `@?` | ⬜ |
| T-103 | API pacientů: `GET /api/patients/`, `/{pid}/`, `/{pid}/timeline/`, `/{pid}/observations/` z IRIS — ARCH §6.3 | API | T-101 | Swagger ukazuje P01–P06 | `@?` | ⬜ |
| T-104 | Evidence resolver `GET /api/evidence/?id=` (prefix index, text + offset odstavce, hodnota + `derivedFrom`, pasáž guidelines, kritérium studie) — ARCH §5.2 | API | T-101, T-102 | pro každý typ Evidence ID vrátí zdroj | `@?` | ⬜ |
| T-105 | `context_builder` (IRIS → evidence list s ID; sada guidelines podle MKN-10; studie; výsledky pravidel) + `pseudonymize` — ARCH §5.1, §5.7 | AI | T-101 | kontext P03 obsahuje všech 171 resources jako řádky s ID, guidelines KRC + OBC | `@?` | ⬜ |
| T-106 | Generátor **bloku A** (souhrn, ECOG lékař vs. `samostatnost`, časová osa, komorbidity, alerts, hlavička podle D-018: diagnóza, TNM, otázka, záměr C/P) + **grounding validátor v1** (ID, čísla, data, missing checklist) — ARCH §5.3 | AI | T-105, T-009, T-012 | Brief A pro P03 validní podle schématu, 0 neověřených tvrzení, ECOG 0 vs. 1 zobrazen | `@?` | ⬜ |
| T-107 | Modely `MdtSession`, `MdtCase`, `Brief`, `GenerationJob`, `LlmCallLog` + job endpointy `POST /cases/{cid}/brief/`, `GET /jobs/{jid}/` (ThreadPool) — ARCH §6.2, §6.3 | API | T-106 | FE spustí generování a polluje výsledek | `@?` | ⬜ |
| T-108 | Stránka podkladu: `CaseHeader` (D-018), `AiBlock`, `Claim` + `CitationChip`, `SourceDrawer`, `MissingData`, `JobProgress` (nejdřív nad fixture) — ARCH §7.2 | UI | T-009, T-010 | klik na citaci otevře zdroj; běží na fixture i na živém API | `@?` | ⬜ |
| T-109 | `seed_mdt` (4 zasedání = boardy z `ServiceRequest` + `Task`) + agenda `/dashboard/mdt/[sessionId]` + přehled `/dashboard` — ARCH §6.2 | API + UI | T-101, T-107 | 4 zasedání a 6 případů, přechod na podklad | `@?` | ⬜ |
| T-110 | Deploy M1 na prod (Vercel + VPS, ingest na VPS) + smoke test | INFRA | T-004, T-005, T-101, T-107, T-108 | vertikální řez funguje na veřejné URL | `@?` | ⬜ |
| T-501 | **Role a boardy** (FR-U1, FR-P1, D-014): skupiny `mdt_admin` / `mdt_doctor` / `mdt_viewer` + `UserProfile.specialty`, demo účty (ARCH §6.2), `GET /api/mdt/me/`, board = `MdtSession` (předseda zakládá a mění termín), přesun případu mezi boardy (update `Task.restriction.period.start` v IRIS) — ARCH §6.2, §6.3 | API + UI | T-107, T-109 | každá role smí jen to, co je v ARCH §6.3; přesun P01 na jiný board změní datum v `Task` | `@?` | ⬜ |

### M2 — Kompletní funkce (do So 04:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-201 | **Blok B:** prompty pro role (chirurg, onkolog, radiolog, patolog, pacient, radiační onkolog) + **posouzení role** `RoleAssessment` (FR-B7), paralelní generace | AI | T-106 | ≥ 3 role validní s verdiktem, celý podklad < 20 s | `@?` | ⬜ |
| T-202 | **Red flags:** `rules/red_flags.py` (RF-ECOG, RF-PROMS, RF-TOX, RF-STALE, RF-MISSING, RF-MED, RF-NEWSYMPTOM, RF-LAB, RF-WEIGHT, RF-GERI, RF-LESION, RF-GENETIC, RF-NOMINATION, RF-TNM, RF-PALIATIVE, RF-ROLES, RF-STEROID) + `RF-LLM`; ≥ 2 citace + pasáž; odkliknutí varování red flag neodstraní (D-019) — ARCH §5.4 | AI | T-105 | najde hypotézy z DATASET §9 pro P03 a P05 (včetně třezalky) | `@?` | ⬜ |
| T-203 | Guidelines (42 pasáží, regex z DATASET §7) → `MDT.GuidelineChunk`; studie (`Group.characteristic`) → `MDT.TrialCriterion` — ARCH §4.5 | DATA | T-102 | vyhledání s filtrem MKN-10 vrací relevantní pasáže; 42 + 6 studií v IRIS | `@?` | ⬜ |
| T-204 | **B2:** sada guidelines podle dg., možnosti s ID pasáží + co chybí (včetně podpůrné péče z OBC-2.x, když ji pacient splňuje), screening `RKT-01…06` po kritériích (včetně protokolu RKT-06), 2–3 otázky — ARCH §5.5 | AI | T-203, T-106 | `DecisionSupport` validní; P03 má RKT-03 s `unknown` u Z1 a V2; žádné „doporučujeme“ | `@?` | ⬜ |
| T-205 | UI: `RoleSection` (sekce odborností pod sebou s barvou odbornosti, FR-B8) + `RoleAssessmentCard`, `RedFlagCard`, `EcogCompare`, `Timeline`, `TrendChart` (Hb, markery, Na, hmotnost, LVEF, PROMs), `TreatmentOptions`, `TrialScreening` | UI | T-108 | všechny sekce §8 se vykreslí z fixture i API | `@?` | ⬜ |
| T-206 | **Konfigurátor** `/setup`: sekce zap/vyp, drag & drop pořadí, přítomné role, detail, presety; přegenerovat. Nastavuje jen předseda (`mdt_admin`), ostatní si bloky jen sbalí lokálně; upozorní, když chybí role vyžadovaná guidelines (`RF-ROLES`) — FR-R1 | UI | T-108 | změna nastavení se projeví v novém podkladu | `@?` | ⬜ |
| T-207 | API konfigurace: `BriefConfig` CRUD + promítnutí do promptů (sekce, role, detail, jazyk) | API + AI | T-107 | různé presety dávají různé výstupy | `@?` | ⬜ |
| T-208 | **Editor závěru** `/record`: sekce záznamu MDT jako v datasetu, záměr (`mdt-lecebny-zamer`), postup po modalitách, úkoly (owner, termín), re-MDT, přítomní, podmíněné doporučení (OBC-1.1), priorita a plán druhého nádoru (OBC-1.4); AI vs. člověk odlišení — FR-C1, C2, R4 | UI | T-205 | draft se ukládá, AI předvyplnění je vizuálně odlišené | `@?` | ⬜ |
| T-209 | **Potvrzení → IRIS FHIR:** `writeback.py` transaction: `Composition/Pxx-mdtNN`, `CarePlan`, `CareTeam`, `Task[]`, `DetectedIssue[]`, `ResearchSubject`, `Provenance`, update `Pxx-zad01` + `-task` (`projednana`) — ARCH §4.3 výstupy | API | T-107, T-006 | po potvrzení P03 je v IRIS `Composition/P03-mdt02` s vazbami a `fhir_ids` v `Decision` | `@?` | ⬜ |
| T-210 | **Export:** `export.fhir.json` (document Bundle) + `export.pdf` (+ `DocumentReference/Pxx-mdtNN-pdf` v IRIS) — FR-C4 | API | T-209 | oba soubory ke stažení, Bundle jde znovu nahrát do IRIS | `@?` | ⬜ |
| T-211 | **Zařazení pacienta do boardu** (FR-P4, FR-P1): `GET /api/mdt/patients/{pid}/intake/`, `POST` / `PATCH /api/mdt/cases/`, formulář `IntakeForm` (Doplnit / Přeskočit, varování s „Beru na vědomí“, ECOG + C/P, checkbox „Snímek mladší než 3 měsíce“), zápis FHIR (`Observation` ECOG, extension záměru, `DetectedIssue.mitigation`, `Provenance`); otázku pro MDT nelze přeskočit, neúplný případ jde vrátit k doplnění (OBC-1.1) — ARCH §5.10, §8.6 | API + UI | T-107, T-501, T-502 | P03 jde zařadit; přeskočený údaj nevyvolá varování, ale v podkladu je „Chybí (přeskočeno lékařem)“; ruční ECOG je v IRIS s `Provenance` | `@?` | ⬜ |
| T-212 | Deploy M2 + smoke test celého cyklu na prod | INFRA | T-201…T-210 | 6 kroků finálové ukázky projde na veřejné URL | `@?` | ⬜ |
| T-213 | **Grounding v2:** vektorová podobnost tvrzení ↔ citovaný odstavec (IRIS `VECTOR_COSINE`, `FACT_VERIFICATION`, práh `GROUNDING_MIN_SIMILARITY`) — ARCH §5.3 | AI | T-102, T-106 | špatně citované tvrzení v testu je `unverified` | `@?` | ⬜ |
| T-502 | **Kontrola úplnosti a varování** (`services/rules/intake.py`): povinné údaje podle diagnózy (docs/POZADAVKY_LEKARE.md §4), CHYBÍ, MIMO NORMU, ROZPOR (RF-*), NEJISTOTA AI (rozmezí ECOG); kontrola, že nominace uvádí všechny nádory (OBC-1.4) — ARCH §5.10 | AI | T-105, T-202 | P03: chybí MMR a CT hrudníku, rozpor neuropatie, nejistota „ECOG 0–1“; P04: chybí G8 a VO2max | `@?` | ⬜ |
| T-503 | **Semafor souladu postupů se stavem pacienta** (`services/rules/compatibility.py` + `data/compatibility_rules.yaml`, D-015) + unit testy — ARCH §5.9 | AI | T-105 | testy dávají barvy z docs/POZADAVKY_LEKARE.md §5.4 pro P03 a P04; červená jen se zdrojem | `@?` | ⬜ |
| T-504 | **Externí zdroje `EXT-…`** jako `MDT.GuidelineChunk` (`GuidelineSet = "EXT"`, D-016) + resolver | DATA | T-203, T-104 | `GET /api/evidence/?id=EXT-EMA-DPD-2020` vrátí znění a odkaz | `@?` | ⬜ |
| T-505 | **Úzké rozložení** (FR-U2, D-017): od 360 px, bloky pod sebou ve výchozím pořadí ARCH §7.3, `/brief/[caseId]` v samostatném okně, barvy odborností, `CompatibilityLight` | UI | T-108, T-205 | podklad P03 jde číst v okně 360 px bez vodorovného posouvání | `@?` | ⬜ |
| T-506 | **Údaje podle diagnózy a katalog metod** (FR-B8, FR-D5): bloky pro plíce, prs a kolorektum v sekcích odborností + `ModalityCatalog` | AI + UI | T-105, T-205 | P04 ukáže spirometrii, P02 LVEF, P03 FLR a bevacizumab | `@?` | ⬜ |
| T-511 | **Úkoly po zasedání** (FR-P3): `GET /api/mdt/tasks/`, `/dashboard/tasks`, stav úkolů, termín re-MDT | API + UI | T-209 | po potvrzení P03 se jeho úkoly objeví v přehledu | `@?` | ⬜ |

### M3 — Spolehlivost a bonusy (do So 09:00)

| ID | Úkol | Lane | Závisí na | Hotovo když (DoD) | Owner | Stav |
|---|---|---|---|---|---|---|
| T-301 | **Eval** `eval_ground_truth --gt data/dev_ground_truth` → `docs/EVAL.md` (recall red flags, pokrytí faktů, % neověřených, „údaj chybí“, screening studií) + porovnání `gemini-3.8-flash` vs. `gemini-4-argon` — ARCH §5.8 | AI + PITCH | T-013, T-202, T-204 | tabulka metrik pro všech 6 pacientů a 2 modely | `@?` | ⬜ |
| T-302 | Ladění promptů a validátoru podle evalu (cíl: 0 neověřených, všechny dev-GT flags) | AI | T-301 | metriky lepší než první běh, zapsané v EVAL.md | `@?` | ⬜ |
| T-303 | BON-1 **Readiness** nad T-502 (`rules/readiness.py`: skóre úplnosti podle checklistu OBC-1.1, staging ≤ 42 dní OBC-1.2, povinné biomarkery) + badge v agendě | AI + UI | T-502 | P01 a P05 mají zastaralý staging, P03 chybí MMR a CT hrudníku | `@?` | ⬜ |
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
| T-507 | **Anamnéza** (FR-A5): sekce OA/FA/RA/SA/GA/NO ze zpráv, doslovně nebo jako shrnutí AI s citacemi podle `INTAKE_ANAMNESIS_MAX_CHARS`, přepínač `AnamnesisBlock` | AI + UI | T-106 | dlouhá anamnéza má shrnutí s citacemi, krátká je doslovně | `@?` | ⬜ |
| T-508 | BON-6 **Karta Lung-RADS / Fleischner** s kontrolou použitelnosti (`services/rules/scales.py`, `ScaleCard`) | AI + UI | T-503 | u všech 6 pacientů „nelze použít“ s důvodem; test na fiktivní screeningový uzel | `@?` | ⬜ |
| T-509 | **Zkratky a NEJISTOTA AI** (FR-R5): pravidla výkladu podle kontextu v promptech + testy na tabulku docs/POZADAVKY_LEKARE.md §7.2 | AI | T-502 | každý řádek tabulky se vyloží správně, nebo vyhodí varování | `@?` | ⬜ |
| T-510 | BON-7 **Vstup PDF nebo vloženého textu** → překladač do FHIR (Gemini, odkaz na zdrojový `DocumentReference`) → validace → potvrzení lékařem → IRIS | DATA + AI | T-012, T-502, Q9 | vložená zpráva vznikne v IRIS jako `DocumentReference` + `Observation` s `Provenance` | `@?` | ⬜ |

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
| Q10 | Sprint 0 (M0, Pá 18:00) nestihnutý: potvrdit nové časy sprintů | M1–M4 | tým | ✅ sprinty startují Pá 19:00, M0 co nejdřív, M1–M4 beze změny |
| Q11 | Owneři lanes nejsou přiřazení (§2) | všechny | tým | ✅ Seb (INFRA + API), Maty (DATA), Jarda (AI), Mira (UI + PITCH) |
| Q12 | Na Windows s `core.autocrlf=true` má `entrypoint.sh` v pracovní kopii CRLF a backend kontejner nenaběhne. Řeší `.gitattributes` (T-001), do té doby `git config core.autocrlf input` | T-002, `dev.ps1 up` | INFRA | ✅ `.gitattributes` (T-001); stará pracovní kopie: smazat `*.sh` a `git checkout -- .` |

---

## 6. Deník (append-only)

> Formát: `- Den HH:MM · @kdo · T-xxx · co se stalo (větev / odkaz)`. Nové řádky přidávej **na konec**.

- Pá 15:15 · @jaram+claude · — · Založena ARCHITEKTURA.md, PROGRESS.md, AGENTS.md (extrakce zadání, výzkum InterSystems a FHIR-AI-Hackathon-Kit).
- Pá 15:57 · @xxzoomczexx · — · MYSLENKOVA_MAPA.md: přehled + poznámky z konzultace se zadavateli.
- Pá 16:20 · @jaram+claude · T-007 · Dataset v1.1 popsán v DATASET.md: FHIR R4, 1 091 resources, sanitizace (`_` v ID, prázdný string), guidelines, studie, hypotézy nesrovnalostí. ARCHITEKTURA přepsána: Gemini (D-008), výstup ve struktuře datasetu (D-009), plný kontext + vektory pro grounding (D-010), požadavky z konzultace (FR-A4, FR-B7, RF-IDENTITY / PRIOR-PROC / DATAQUALITY). ⚠️ KONTRAKT: §8 Evidence ID = ID z datasetu, `RoleAssessment`, `Criterion`, `header.comorbidities` / `alerts` / `mdt_date`, `Decision.sections` podle záznamu MDT. Nové úkoly T-013, T-213, T-312–T-314; T-008 ✂️.
- Pá 18:15 · @xxzoomczexx+claude · — · Návrh [docs/POZADAVKY_LEKARE.md](docs/POZADAVKY_LEKARE.md) (požadavky lékaře: 3 role, zařazení pacienta s Přeskočit a varováními, úzké rozložení, ECOG + C/P, semafor souladu postupů se stavem pacienta, škály, slovník zkratek). Změny kontraktu a úkoly T-501–T-510 jsou zatím **jen návrh**, ARCHITEKTURA.md beze změny. Nové nesrovnalosti v DATASET §9 (doplněk 18:15).
- Pá 18:54 · @xxzoomczexx+claude · T-500 · Požadavky lékaře sladěné se zadáním a zapracované. ⚠️ KONTRAKT: ARCH §6.2 (`MdtSession` = board, `MdtCase` pole zařazení, `UserProfile`), §6.3 (`/api/mdt/me/`, `/patients/{pid}/intake/`, `PATCH /cases/{cid}/`, `/cases/{cid}/compatibility/`), §8.1 (`Light`, `RoleId` + `pulmonologist` / `cardiologist`, nové `SectionId`, `EXT-…`), §8.2 (`header.intent`, `display_name` bez jména), §8.3 (`TreatmentCompatibility`), nová §8.6 (`IntakePrefill`, `MdtCase`). Nové FR-U1, FR-U2, FR-P4, FR-B8, FR-D4, FR-D5, FR-A5, FR-R5, BON-6, BON-7 a D-014 až D-020. Nové úkoly T-014, T-501–T-511; T-211 a T-303 přepracované. Pravidla pro sprinty a paralelní práci v §1. Blokery Q10–Q12.
- Pá 19:03 · @xxzoomczexx+claude · T-500 · Kontrola architektury proti 42 pasážím guidelines: nová ARCH §5.11 (pokrytí guidelines), pravidla `RF-PALIATIVE` (OBC-2.1), `RF-ROLES` (KRC-2.1, PLI-2.1, PRS-1.4), `RF-STEROID` (OBC-3.1); `RF-STALE` + MR jater (KRC-2.4); `RF-LAB`: Na podle `referenceRange`, marker ≠ progrese (PRS-4.2), prahy bez zdroje označené jako konvence týmu. ⚠️ KONTRAKT: `MdtCase.status` + `returned`, `Decision.sections.conditional` a `tumor_priority` (OBC-1.1, OBC-1.4). Otázku pro MDT nelze přeskočit.
- Pá 19:11 · @xxzoomczexx+claude · — · Owneři lanes: Seb (INFRA + API), Maty (DATA), Jarda (AI), Mira (UI + PITCH). Start sprintů Pá 19:00, Sprint 0 běží. Q10 a Q11 vyřešeny.
- Pá 19:16 · @Seb+claude · T-001 · Root `.gitignore` + `.gitattributes` (`*.sh` a `Makefile` LF, `*.ps1` CRLF), `data/{dev_ground_truth,fixtures,audio}/`, zadání přesunuto do `docs/zadani/`. Q12 vyřešena (větev `t-001-repo-struktura`).

---

## 7. Demo checklist (finále, 5 min, pacient P03)

| # | Krok | Co ukázat | Funkce | ✔ |
|---|---|---|---|---|
| 0 | Zařazení (volitelně, 30 s) | onkolog zařadí P03 do boardu GIT: varování (chybí MMR, rozpor v neuropatii, „ECOG 0–1“), „Beru na vědomí“, ECOG 0 + **C**, snímek ✓ | T-211, T-502 | ⬜ |
| 1 | Nastavení | předseda naklikne sekce, pořadí, přítomné role (onkolog, hepatobiliární chirurg, radiolog, patolog, pacient), detail | T-206 | ⬜ |
| 2 | Generování | podklad za pár sekund (průběh) | T-107, T-201 | ⬜ |
| 3 | 30 s orientace | `CaseHeader` v úzkém okně: `P03 · muž · 67 let`, C18.7 + jaterní mts, cT3 cN1 cM1a, **ECOG 0 (lékař) vs. 1 (pacient)**, velké **C**, otázka resekability, komorbidity (IM, stent), red flags | T-108, T-505 | ⬜ |
| 4 | Ověření | klik na tvrzení → zdroj (`P03-img03` „hrudník nebyl požadován“); red flag **neuropatie G1 vs. pacient „padají mi věci z ruky“** → oba zdroje + KRC-3.2 | T-104, T-202 | ⬜ |
| 5 | B2 | možnosti (resekce dvoudobě / pokračovat v systémové léčbě) s pasážemi KRC-2.x a **semaforem** (resekce 🟠: FLR 38 %, chybí CT hrudníku; anti-EGFR 🔴: KRAS G12D) + **RKT-03** (Z1, V2 `unknown`, V3 sporné) + RECIST PR | T-204, T-503, T-304 | ⬜ |
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
| D-014 | Role podle oprávnění (`mdt_admin` = předseda, `mdt_doctor`, `mdt_viewer`) + odbornost; board = zasedání MDT | Pá 18:54 | tým (požadavky lékaře) |
| D-015 | Semafor souladu postupů se stavem pacienta počítají deterministická pravidla; LLM barvu nepřiřazuje; vždy všechny možnosti | Pá 18:54 | tým (požadavky lékaře) |
| D-016 | Evidence ID pro externí zdroje `EXT-…` (`GuidelineSet = "EXT"`); demo stojí hlavně na dodaných guidelines | Pá 18:54 | tým |
| D-017 | Úzké rozložení (od 360 px) se sekcemi odborností; tři oddělené barevné systémy | Pá 18:54 | tým (požadavky lékaře) |
| D-018 | Hlavička `Pxx · pohlaví · věk` (bez jména a RČ), diagnóza + TNM, otázka, ECOG lékař velký + pacient, záměr C/P | Pá 18:54 | tým (požadavky lékaře) |
| D-019 | Odkliknuté varování a přeskočený údaj se z podkladu neztratí | Pá 18:54 | tým |
| D-020 | Práce ve sprintech = milníky M0–M4, pravidla paralelní práce v §1 | Pá 18:54 | tým |
