# MDT Copilot — technická specifikace a architektura

> **Rakathon 2026** · Praha 16.–18. 10. 2026 · zadání **Asseco Central Europe** (MDT Copilot) + souběžná výzva **InterSystems** („Best Use of InterSystems Technology for AI and Interoperability“)
>
> Tento dokument je **jediný zdroj pravdy** pro architekturu, požadavky a datové kontrakty. Postup práce, úkoly a stav jsou v [PROGRESS.md](PROGRESS.md). Pravidla pro AI agenty jsou v [AGENTS.md](AGENTS.md).
>
> Změnu kontraktu (sekce [§8](#8-datové-kontrakty-fe--be)) nebo API ([§6.3](#63-rest-api)) udělej **nejdřív tady**, ve stejném PR jako kód, a zapiš ji do Deníku v PROGRESS.md.

---

## 0. TL;DR

- **Co stavíme:** webovou aplikaci, která z dat onkologického pacienta během pár sekund připraví podklad pro multidisciplinární komisi (MDT). Podklad má čtyři bloky: **A** souhrn, **B** pohledy odborníků, **B2** podpora rozhodování a **C** závěr a akční plán. Každé tvrzení AI má klikací citaci zdroje, AI hlásí rozpory (red flags) a **rozhoduje vždy lékař** (human-in-the-loop).
- **Stack:** **Next.js 16** na **Vercelu** (`WEB_Template/frontend`) a **Django 4.2 + DRF** na **externím serveru** (`WEB_Template/backend`) v Dockeru s Traefikem. Vedle běží **InterSystems IRIS for Health** jako **nemocniční databáze**: FHIR R4 server + Vector Search. PostgreSQL drží jen stav aplikace (uživatele, nastavení, drafty).
- **Totální integrace IRIS/FHIR:** všechna klinická data jsou FHIR resources v IRIS. RAG běží nad IRIS Vector Search s filtrem na pacienta. Potvrzený závěr komise se **zapisuje zpět do IRIS** jako `CarePlan` + `Task` + `DetectedIssue` + `Provenance` + `Composition`. Export je FHIR document Bundle a PDF.
- **Deadline:** odevzdání **v sobotu 17. 10. ve 12:00**, lokální pitch ve 13:00 a národní finále v neděli od 14:00 (viz [§1.9](#19-harmonogram)).

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
| **B2** | Podpora rozhodování | **AI předkládá, nevybírá.** Možnosti léčby z doporučených postupů **s citací**, vhodnost pro klinické studie, 2–3 klíčové otázky k diskusi | povinné minimum: možnosti z dodaných guidelines (ESMO) + screening studií |
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

### 1.5 Dodaná data (smyšlená, mock)

- **Záznamy z eZdraví:** propouštěcí zprávy, krevní testy včetně onkomarkerů, popisy CT/MRI a léky.
- **Dotazník pacienta (PROMs):** bolest, únava a psychika podle ověřených dotazníků (EORTC QLQ-C30, PRO-CTCAE), **min. 2 vyplnění v čase**.
- **Nominace na komisi:** kdo pacienta posílá, s jakou otázkou a proč; předchozí závěry.
- **Doporučené postupy a studie:** výtah z guidelines (ESMO) + 3–5 smyšlených klinických studií.
- **3–5 příběhů pacientů:** různé typy nádorů se **schválně vloženými chybami a mezerami** a se správným řešením (**ground truth**: očekávané red flags a klíčová fakta), podle kterého se měří spolehlivost.
- **Bonus:** přepis diskuse (text, případně audio) pro testování AI zapisovatele.

> Formát datasetu zatím neznáme. Ingest stavíme přes adaptéry ([§4.3](#43-fhir-datový-model)) a do příchodu dat vyvíjíme na ručně vytvořeném „pacientovi 0“.

### 1.6 Standardy

- **HL7 FHIR R4:** `Condition` (diagnóza a rozsah), `Observation` (biomarkery, kondice, dotazník), `CarePlan` + `Task` (rozhodnutí a úkoly), `Provenance` (odkud tvrzení je a kdo ho potvrdil).
- **Onkologické modely:**
  - **mCODE** (minimální onkologická sada ve FHIR, USA);
  - **HL7 Europe Common Cancer Model** (ECCDM, 1.0.0-ballot), mapuje se na FHIR i na OMOP;
  - **IPS** (International Patient Summary);
  - kontext **EHDS**.
- **Číselníky:** MKN-10 / ICD-O-3 (diagnózy, morfologie), LOINC (laboratoř), SNOMED CT (klinické pojmy).
- Mapování exportu na FHIR R4 / mCODE je v zadání **bonus**.

### 1.7 Hodnocení a finálová ukázka

| Kritérium | Váha | Čím body získáme |
|---|---|---|
| **Klinická hodnota & UX** | **30 %** | orientace do 30 s, role-specific pohledy, rychlost, čistý UI, prezentační režim |
| **Spolehlivost AI** | **20 %** | citace u každého tvrzení, grounding validátor, explicitní „údaj chybí“, eval proti ground truth (čísla do pitche) |
| **Nastavitelnost** | **20 %** | konfigurátor sekcí, pořadí, rolí a detailu; presety; přegenerování podle nastavení |
| **Propojení dat a standardy** | **15 %** | IRIS FHIR jako zdroj, mapování na FHIR R4/mCODE, LOINC/ICD kódy, FHIR write-back a export |
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
| **So 17. 10. 12:00** | **uzávěrka odevzdání projektů** |
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

Sloupec **Krit.** odkazuje na kritéria z §1.7: UX, AI, CFG, STD, PROC.

### 2.1 Funkční požadavky

| ID | Požadavek | Priorita | Krit. |
|---|---|---|---|
| **FR-A1** | Executive summary: diagnóza (MKN-10 + slovně), stadium (TNM), hlavní otázka komise, čitelné do 30 s | MUST | UX |
| **FR-A2** | ECOG lékař vs. pacient vedle sebe s datem a citací; rozdíl ≥ 2 znamená red flag (práh ověřit s mentory) | MUST | UX, AI |
| **FR-A3** | Časová osa: diagnóza, výkony, linie léčby, zobrazovací metody, PROMs, předchozí MDT; každý bod klikací | MUST | UX |
| **FR-B1** | Pohled chirurga: resekabilita, TNM, rozsah, předchozí operace | MUST | UX |
| **FR-B2** | Pohled onkologa: biomarkery, dosavadní linie léčby, odpověď, nežádoucí účinky (včetně PRO-CTCAE) | MUST | UX |
| **FR-B3** | Pohled radiologa: vývoj nálezů v čase, srovnání posledních vyšetření | MUST (≥ 3 role) | UX |
| **FR-B4** | Pohled patologa: histologie, grade, ICD-O-3, biomarkery z tkáně | SHOULD | UX |
| **FR-B5** | Pohled pacienta: trend PROMs (QLQ-C30, PRO-CTCAE), symptomy, preference | MUST | UX, PROC |
| **FR-B6** | Pohled radiačního onkologa: předchozí RT, oblasti, dávky | SHOULD | UX |
| **FR-D1** | Možnosti léčby z **dodaných** guidelines s citací (dokument, sekce/strana); AI nevybírá, předkládá alternativy | MUST | AI, STD |
| **FR-D2** | Screening klinických studií: pro každé kritérium splňuje / nesplňuje / nelze určit + citace; celkový stav | MUST | AI |
| **FR-D3** | 2–3 klíčové otázky k diskusi | MUST | UX |
| **FR-C1** | Strukturovaný zápis rozhodnutí + zdůvodnění + přítomní | MUST | PROC |
| **FR-C2** | Úkoly (kdo, co, do kdy), kontrola, termín opětovného posouzení | MUST | PROC |
| **FR-C3** | Potvrzení předsedou udělá z draftu oficiální záznam (zápis do IRIS FHIR) | MUST | PROC |
| **FR-C4** | Export PDF + HL7 FHIR (document Bundle) | MUST | STD |
| **FR-R1** | Konfigurátor: sekce zap/vyp, pořadí, přítomné role, úroveň detailu; ukládání presetů | MUST | CFG |
| **FR-R2** | Red flags: rozpory mezi zdroji, závažnost (high/moderate/low), citace **obou** zdrojů | MUST | AI |
| **FR-R3** | Klikací citace u každého tvrzení otevře zdroj se zvýrazněnou pasáží; chybějící údaj explicitně „Údaj chybí v podkladech“ | MUST | AI |
| **FR-R4** | AI text vizuálně odlišen (badge „AI návrh“, styl); po potvrzení „Potvrzeno: MUDr. X, čas“ | MUST | PROC |
| **FR-P1** | Před zasedáním: nominace (kdo, otázka, proč) jako `ServiceRequest`, agenda zasedání | SHOULD | PROC |
| **FR-P2** | Během zasedání: přepínání pacientů v agendě, prezentační režim (velké písmo, projektor) | SHOULD | UX |
| **FR-P3** | Po zasedání: přehled úkolů a jejich stav, naplánování re-review | SHOULD | PROC |

### 2.2 Bonusy

| ID | Bonus | Pozn. |
|---|---|---|
| **BON-1** | **Kontrola připravenosti případu** (readiness): chybí histologie, staré zobrazení, chybí biomarker relevantní pro diagnózu… | deterministická pravidla + LLM |
| **BON-2** | **Předvýpočet odpovědi dle RECIST 1.1**: SLD baseline vs. nadir vs. aktuální, výsledek CR/PR/SD/PD | deterministicky, AI jen extrahuje měření |
| **BON-3** | **AI zapisovatel**: přepis diskuse převede na draft rozhodnutí + úkoly (s citací na úsek přepisu) | dataset obsahuje přepis |
| **BON-4** | **Shrnutí pro pacienta** v laickém jazyce | po potvrzení závěru |
| **BON-5** | **Export mapovaný na mCODE / ECCDM** (`meta.profile`, kódy), případně validace `$validate` v IRIS | zároveň bod pro InterSystems |

### 2.3 Nefunkční požadavky

| ID | Požadavek |
|---|---|
| **NFR-1** | Podklad „za pár sekund“: cíl < 20 s na pacienta, sekce generované paralelně, průběh viditelný v UI |
| **NFR-2** | **Grounding:** LLM dostane jen data daného pacienta + dodané guidelines a studie; vektorové hledání vždy s filtrem `PatientId` |
| **NFR-3** | **Ochrana údajů:** pseudonymizace před LLM, zpracování v EU (volba providera), žádné PII v logu, RBAC, IRIS a DB neveřejné |
| **NFR-4** | **Auditovatelnost:** log LLM volání (účel, model, hash promptu, tokeny, latence) a `Provenance` u každého potvrzeného záznamu |
| **NFR-5** | Spolehlivé demo: předgenerovaný podklad pro demo pacienta (cache), záložní video, lokální fallback |
| **NFR-6** | Nasazení: frontend na Vercelu, backend na externím serveru, HTTPS, žádné secrets ve frontendu |

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
┌───────────────────────── EXTERNÍ SERVER (VPS, Docker Compose) ──────────────────────────┐
│  Traefik v3 (TLS Let's Encrypt, api.<doména>)                                           │
│      │                                                                                  │
│      ▼                                                                                  │
│  Django 4.2 + DRF (ASGI/Daphne) – WEB_Template/backend                                  │
│  ├─ apps/patients   – čtení pacientů z FHIR, časová osa, evidence resolver              │
│  ├─ apps/mdt        – zasedání, případy, konfigurace, závěry, export                    │
│  ├─ apps/copilot    – AI orchestrace (A, B, B2, C, red flags, scribe), joby             │
│  ├─ services/fhir   – FHIR REST klient, mappery, bundly, write-back                     │
│  ├─ services/iris   – IRIS DB-API (intersystems-irispython), vector store               │
│  ├─ services/ai     – AI providery (existující ai_service.py), prompty, grounding       │
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
                                         LLM + embeddings provider (EU region, viz §5.7)
```

### 3.2 Odpovědnosti vrstev

| Vrstva | Dělá | Nedělá |
|---|---|---|
| **Next.js (Vercel)** | UI, routing, ochrana stránek (`proxy.ts`), volání `/api/*` (same-origin) | žádné LLM klíče, žádný přímý přístup k IRIS, žádná business logika |
| **Django** | autentizace (JWT v httpOnly cookies), orchestrace AI, grounding, pravidla, FHIR read/write, export | neukládá klinická data do Postgresu (jen reference na FHIR ID a drafty) |
| **IRIS for Health** | **zdroj pravdy klinických dat** (FHIR R4), vektorové tabulky pro RAG, potvrzené záznamy komise | (do internetu nevystaven) |
| **PostgreSQL** | uživatelé, role, zasedání MDT, presety konfigurace, drafty podkladů a závěrů, joby, log LLM | klinická data |

### 3.3 Klíčová rozhodnutí

| # | Rozhodnutí | Proč |
|---|---|---|
| D-001 | Frontend na Vercelu, backend na vlastním serveru | požadavek týmu; IRIS + Postgres + dlouhé LLM joby na serverless nepatří |
| D-002 | **IRIS FHIR = nemocniční DB**, Postgres = stav aplikace | čistá separace; FHIR je společný jazyk (bodovaná kritéria STD + InterSystems); template a auth zůstanou beze změny |
| D-003 | **Same-origin proxy**: Vercel `rewrites` `/api/*` vede na backend | auth template používá httpOnly cookies se `SameSite=Strict` (prod) a `proxy.ts` je čte na doméně frontendu; cross-domain by se rozbily |
| D-004 | Generování jako **asynchronní job + polling** (ne WebSocket) | Vercel neproxyuje WebSockety; dlouhé requesty přes proxy jsou křehké |
| D-005 | **Stabilní FHIR ID + `PUT` v transaction bundlu** | seed je idempotentní (opakovaný `POST` v IRIS duplikuje pacienty) a ID jsou citovatelná |
| D-006 | Formát **Evidence ID** = `ResourceType/id[#fragment]` | jedna citace = jeden FHIR resource (+ úsek textu); resolver je triviální |
| D-007 | Embeddings `text-embedding-3-small` (1536 dim), stejně jako v kitu | ověřeno kitem, levné, zvládá češtinu |

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

#### Backend — externí server

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
- **Bezpečnost serveru:**
  - **změnit výchozí heslo IRIS `SYS`**;
  - IRIS ani Postgres nepublikovat ven;
  - Management Portal jen přes `ssh -L 52773:127.0.0.1:52773 server`.
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
| **FHIR R4 server** (`/fhir/r4`) | **Nemocniční DB:** všechna data pacientů jako FHIR resources; backend čte přes REST | MUST |
| **FHIR write-back** (transaction Bundle) | Potvrzený závěr komise: `CarePlan`, `Task`, `DetectedIssue`, `Provenance`, `Composition` | MUST |
| **IRIS SQL + Vector Search** (`VECTOR`, `TO_VECTOR`, `VECTOR_COSINE`) | RAG: textové úseky zpráv (filtr na pacienta), guidelines, kritéria studií | MUST |
| **Python DB-API** `intersystems-irispython` (`import iris`) | Přístup z Djanga (SQL, vektory, native API pro inicializaci FHIR serveru) | MUST |
| **FHIR SQL Builder** | Projekce FHIR do SQL (např. `Observation` laboratoř) pro trendy, časovou osu a dashboard zasedání | SHOULD |
| **MCP server nad IRIS** (FastMCP, kit 5.2) | Nástroje `fhir_query`, `vector_search`, `sql_query` pro copilot agenta; ukázka „IRIS jako MCP backend“ | SHOULD |
| **FHIR packages (mCODE IG) + `$validate`** | Validace exportu proti profilům (`HS.FHIRMeta.Load.NpmLoader.importPackages`) | BONUS |
| Interoperability production | Ingest „surových“ eZdraví zpráv (File → DTL → FHIR) | stretch, nejspíš ne |
| IntegratedML | **nepoužijeme**: predikce bez klinické validace by snížila důvěryhodnost | — |

**Pitch pro InterSystems:** IRIS je nemocniční datová platforma, ze které copilot **čte** (FHIR), ve které **hledá** (Vector Search nad stejnými daty, bez další vektorové DB) a do které **zapisuje** auditovatelný závěr komise (FHIR + Provenance). Jedna platforma, standardy end-to-end.

### 4.2 Prostředí (převzato z FHIR-AI-Hackathon-Kit V2)

| Věc | Hodnota (dev) |
|---|---|
| Image | `intersystems/irishealth-community:latest-cd` → **zafixovat konkrétní tag**, až ho stáhneme (`docker image inspect`) |
| `merge.cpf` | `[Actions] ModifyService:Name=%Service_CallIn,Enabled=1,AutheEnabled=48` |
| Superserver (DB-API) | `iris:1972` (lokálně `localhost:1972`) |
| Web (FHIR, portal) | `http://iris:52773` (lokálně `http://localhost:52773`) |
| Credentials | `SuperUser` / `SYS` (**jen dev**, na serveru změnit) |
| Namespace | `FHIRSERVER` |
| FHIR base | `http://localhost:52773/fhir/r4` (capability: `/fhir/r4/metadata`) |
| Management Portal | `http://localhost:52773/csp/sys/UtilHome.csp` |
| FHIR SQL Builder | `http://localhost:52773/csp/fhir-management/sql-projections/home` |
| Swagger (pokud nainstalujeme) | `http://localhost:52773/fhir/swagger-ui/index.html` |

**Inicializace FHIR serveru** (úkol T-003): Django management command `iris_init` podle kitu `fhir_server_setup_native.py`. Kroky:

1. `HS.Util.Installer.Foundation.Install("FHIRSERVER")`;
2. `HS.FHIRServer.Installer.InstallNamespace()`;
3. `InstallInstance("/fhir/r4", "HS.FHIRServer.Storage.JsonAdvSQL.InteractionsStrategy", "hl7.fhir.r4.core@4.0.1")`.

Command musí být idempotentní (`ExistsByUrl`). **Nenahrávat** Synthea data z kitu, použijeme vlastní dataset.

### 4.3 FHIR datový model

#### Vstupy (dataset → FHIR)

| Zdroj | FHIR resource | Klíčové prvky a kódy |
|---|---|---|
| Pacient | `Patient` | `identifier` (pseudonym), `gender`, `birthDate`; **žádné rodné číslo v plaintextu** |
| Diagnóza | `Condition` (mCODE *PrimaryCancerCondition*) | `code` MKN-10 (`http://hl7.org/fhir/sid/icd-10`, např. C18.7), `bodySite`, histologie ICD-O-3 (např. 8140/3), `onsetDateTime`, `stage` |
| TNM | `Observation` (mCODE TNM) | LOINC klinické `21905-5` cT, `21906-3` cN, `21907-1` cM, `21908-9` stage group; patologické `21899-0` / `21900-6` / `21901-4` / `21902-2` |
| ECOG lékař | `Observation` | LOINC `89247-1`, `performer` = `Practitioner`, `valueInteger` 0–4 |
| Kondice dle pacienta | `Observation` (odvozená z PROMs) | `performer` = `Patient`, `derivedFrom` = `QuestionnaireResponse` |
| Laboratoř vč. onkomarkerů | `Observation` `category=laboratory` | LOINC: Hb `718-7` (g/L), CEA `2039-6`, CA 19-9 `24108-3` …; `referenceRange`, `interpretation` |
| Biomarkery nádoru | `Observation` (mCODE *TumorMarkerTest* / genomika) | HER2, KRAS, MSI, PD-L1 |
| CT / MRI / PET-CT | `DiagnosticReport` `category=RAD` + `DocumentReference` (text) | `conclusion`, `presentedForm`; RECIST měření jako `Observation` (BON-2) |
| Patologie | `DiagnosticReport` `category=PAT` | |
| Propouštěcí zprávy | `DocumentReference` | `type` LOINC `18842-5`, `content.attachment.data` = **base64** text (`text/plain; charset=utf-8`) |
| Léky / linie léčby | `MedicationStatement` / `MedicationRequest` / `MedicationAdministration` | ATC (`http://www.whocc.no/atc`) |
| Operace, radioterapie | `Procedure` | |
| PROMs | `Questionnaire` + `QuestionnaireResponse` (≥ 2 v čase) + skóre jako `Observation` `category=survey` | EORTC QLQ-C30, PRO-CTCAE; `source` = `Patient` |
| Nominace na komisi | `ServiceRequest` | `requester`, `reasonCode` / `reasonReference`, `note` = **otázka pro komisi**, `occurrenceDateTime` = datum MDT |
| Předchozí závěry | `CarePlan` (`status=completed`) | |
| Lékaři | `Practitioner` + `PractitionerRole` | `specialty` (role v MDT) |
| Guidelines | IRIS SQL `MDT.GuidelineChunk` (+ případně `DocumentReference` bez `subject`) | |
| Klinické studie | `ResearchStudy` + IRIS SQL `MDT.TrialCriterion` | `condition`, `phase`, inclusion/exclusion |
| Přepis porady (bonus) | `DocumentReference` (transcript), případně `Media` (audio) | |

#### Výstupy (zápis komise → IRIS FHIR, jeden transaction Bundle)

| Výstup | FHIR resource | Klíčové prvky |
|---|---|---|
| Rozhodnutí komise | `CarePlan` | `status` `draft` → `active` po potvrzení, `intent=plan`, `basedOn` = `ServiceRequest` (nominace), `addresses` = `Condition`, `description` = rozhodnutí, `note` = zdůvodnění, `author` = předseda |
| Úkoly | `Task` (1 na úkol) | `basedOn` = `CarePlan`, `intent=order`, `owner`, `restriction.period.end` = termín, `status` |
| Red flags | `DetectedIssue` | `severity` high/moderate/low, `implicated[]` = **oba zdroje**, `detail`, `patient` |
| Přítomní, zasedání | `Encounter` (volitelně) | `participant[]` = přítomní lékaři a role |
| Vhodnost do studie | `ResearchSubject` `status=candidate` | jen pokud komise potvrdí |
| Re-review | nový `ServiceRequest` | `occurrenceDateTime` |
| **Původ a potvrzení** | `Provenance` | `target` = vše výše; `agent[]`: `Device` „MDT Copilot (model X)“ s typem `assembler` + `Practitioner` (předseda) s typem `verifier` / `attester`; `entity[]` (`role=source`) = citované zdroje; `recorded` |
| Označení AI obsahu | `meta.security` kód `AIAST` (`http://terminology.hl7.org/CodeSystem/v3-ObservationValue`) | podle HL7 *AI Transparency on FHIR* (draft IG, **ověřit stav**) |
| Oficiální dokument | `Composition` (`type` LOINC `11488-4` Consult note, sekce A / B / B2 / C) v `Bundle` `type=document` | **= FHIR export** |
| PDF | `DocumentReference` (`application/pdf`, `relatesTo` → Composition) | **= PDF export** |

### 4.4 Stabilní ID a idempotentní seed

- ID odvozujeme deterministicky z datasetu:
  - `Patient/p01`;
  - `Condition/p01-dx1`;
  - `Observation/p01-hb-20260312`;
  - `DocumentReference/p01-dr-03`;
  - `ServiceRequest/p01-mdt-1`.
- Ingest posílá **transaction Bundle s `request.method = "PUT"`** a `request.url = "Patient/p01"`. Opakované spuštění tak data přepíše místo duplikace.
- Pořadí: `Practitioner` → `Patient` → `Condition` → zbytek. Reference musí být `ResourceType/id`.
- Command: `python manage.py ingest_dataset <cesta>` (adaptér podle formátu datasetu) → `data/fhir/*.json` (vygenerované bundly) → IRIS → vektory.

### 4.5 Vektorové tabulky (IRIS SQL, namespace FHIRSERVER)

```sql
CREATE TABLE MDT.EvidenceChunk (
    EvidenceId   VARCHAR(200),        -- "DocumentReference/p01-dr-03#2"
    PatientId    VARCHAR(64),         -- "p01"  (POVINNÝ filtr při hledání)
    ResourceType VARCHAR(64),
    ResourceId   VARCHAR(128),
    ChunkIndex   INTEGER,
    DocDate      DATE,
    Title        VARCHAR(500),
    Text         VARCHAR(10000),
    Embedding    VECTOR(DOUBLE, 1536)
);

CREATE TABLE MDT.GuidelineChunk (
    EvidenceId   VARCHAR(200),        -- "Guideline/esmo-crc#s4.2-1"
    Source       VARCHAR(200),        -- název dokumentu
    Section      VARCHAR(200),
    Page         INTEGER,
    CancerType   VARCHAR(20),         -- prefix MKN-10, např. "C18"
    Text         VARCHAR(10000),
    Embedding    VECTOR(DOUBLE, 1536)
);

CREATE TABLE MDT.TrialCriterion (
    EvidenceId   VARCHAR(200),        -- "ResearchStudy/rs-02#inc-3"
    StudyId      VARCHAR(64),
    Kind         VARCHAR(10),         -- inclusion | exclusion
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

- Vkládání: `INSERT … VALUES (?, …, TO_VECTOR(?))` s `str(list_of_floats)`; batch přes `executemany`.
- Embeddingy volat dávkově. Chunking: `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)`.
- IRIS SQL používá `SELECT TOP n`, ne `LIMIT`. Parametry vždy přes `?`.

### 4.6 FHIR REST klient — pravidla a gotchas

- Hlavičky `Accept: application/fhir+json` a `Content-Type: application/fhir+json`, Basic auth.
- **Stránkování:** sledovat `link[relation=next]`; `_count=200`.
- **Neznámé search parametry IRIS tiše ignoruje** (vrátí 200 se vším). Filtry ověřit testem.
- Search parametry se liší od názvů elementů (`recorded-date` vs. `recordedDate`).
- Kódy: `Observation?patient=p01&code=http://loinc.org|718-7&_sort=-date`.
- **`Patient/$everything`:** podporu v naší verzi IRIS **ověřit** (komunita naznačuje, že není out-of-the-box). Fallback: paralelní searche přes typy (`Condition`, `Observation`, `DiagnosticReport`, `DocumentReference`, `MedicationStatement`, `MedicationRequest`, `Procedure`, `QuestionnaireResponse`, `ServiceRequest`, `CarePlan`) s `patient=<id>`.
- Validace: chyba 400 vrací `OperationOutcome`, logovat `issue[].details.text`.
- **Community Edition má limit spojení.** DB-API spojení vždy zavírat (`try/finally` nebo context manager v `services/iris/db.py`) a nedržet je přes request.

### 4.7 MCP server nad IRIS (SHOULD)

- `WEB_Template/backend/mcp_server.py` (FastMCP, podle kitu `Tutorials/5-ai/mcp-examples`) s nástroji:
  - `get_patient_context(patient_id)`;
  - `fhir_query(resource, params)`;
  - `search_evidence(patient_id, query)`;
  - `search_guidelines(query, cancer_type)`.
- Copilot ho může používat interně. V pitchi ukážeme, že stejné nástroje fungují i v libovolném MCP klientovi.
- Read-only: jen `SELECT` a jen `GET`, dedikovaný IRIS uživatel s právy pro čtení.

### 4.8 Pro AI agenty v týmu

- Do repa zkopírovat skills z kitu (`skills/iris-fhir`, `iris-vector-search`, `iris-sql-python`, `iris-ai-agents`, `iris-environment`) do `.claude/skills/` (úkol T-011). Obsahují ověřené snippety a gotchas.
- Volitelně MCP [iris-agentic-dev](https://github.com/intersystems-community/iris-agentic-dev) pro živý přístup agenta k IRIS (`iris-agentic-dev init` detekuje Docker kontejner).

---

## 5. AI vrstva

### 5.1 Pipeline

```
 (1) INGEST            (2) KONTEXT             (3) GENERACE            (4) VALIDACE         (5) REVIEW           (6) ZÁPIS
 dataset ─▶ FHIR      FHIR ─▶ Evidence list    per sekce, paralelně    grounding check      lékař edituje,       potvrzení ─▶
 (IRIS) + vektory     (ID + text + hodnota)    strukturovaný JSON      citace/čísla/data    potvrzuje            FHIR Bundle
                      + vector search          (A, B×role, B2, RF)     + pravidla           (AI vs. člověk)      + Provenance
                      + pseudonymizace                                                                           + export
```

1. **Ingest** (jednorázově): mappery vytvoří FHIR v IRIS. Texty (zprávy, popisy zobrazení, patologie) se rozdělí na úseky, z úseků se spočítají embeddingy a uloží se do `MDT.EvidenceChunk`. Guidelines a studie do `MDT.GuidelineChunk` / `MDT.TrialCriterion`.
2. **Kontext (per pacient):**
   - `context_builder` načte FHIR resources pacienta a převede je na **Evidence list**: kompaktní řádky `[Observation/p01-hb-20260312] 2026-03-12 Hemoglobin 92 g/L (ref 135–175) L`;
   - strukturovaná data jdou celá (jsou malá);
   - z textů se pro každou sekci vybere top-k úseků vektorovým hledáním s **filtrem `PatientId`**; pokud se celé texty pacienta vejdou do limitu, jdou celé;
   - před odesláním do LLM proběhne **pseudonymizace** ([§5.7](#57-model-a-ochrana-údajů)).
3. **Generace:**
   - jeden LLM call na sekci: A, B (každá přítomná role), B2 a red flags (LLM část); běží **paralelně** (ThreadPool);
   - teplota 0–0.2, **strukturovaný výstup** podle JSON schématu ([§8](#8-datové-kontrakty-fe--be));
   - parametry z konfigurace: úroveň detailu, role, jazyk.
4. **Validace (grounding validátor, `services/ai/grounding.py`):** viz [§5.3](#53-anti-halucinace--grounding-validátor).
5. **Review:** UI zobrazí draft s odlišením AI. Lékař edituje a potvrzuje po sekcích nebo celý závěr.
6. **Zápis:** potvrzení vytvoří FHIR transaction do IRIS ([§4.3 výstupy](#výstupy-zápis-komise--iris-fhir-jeden-transaction-bundle)) a pak export PDF a FHIR document Bundle.

### 5.2 Evidence ID a citace

- Formát: `ResourceType/id` pro strukturovaný údaj, `ResourceType/id#n` pro úsek textu (n = `ChunkIndex`), `Guideline/<doc>#<sekce>-<n>`, `ResearchStudy/<id>#inc-<n>` / `#exc-<n>`.
- LLM dostane **jen povolené ID** (z evidence listu) a smí citovat **pouze je**.
- Resolver `GET /api/evidence/?id=<EvidenceId>` vrátí zdroj (typ, datum, autor, celý text s offsetem zvýraznění nebo hodnotu Observation s referenčním rozsahem).

### 5.3 Anti-halucinace — grounding validátor

Každé tvrzení (`claim`) z LLM projde kontrolami:

1. **Citace existuje:** každé `citations[i]` je v množině povolených ID. Jinak `verification = "unverified"`.
2. **Čísla sedí:** čísla a jednotky v textu tvrzení (normalizace desetinné čárky, g/l ↔ g/L) se musí vyskytovat v citovaném zdroji. Jinak `unverified`.
3. **Data sedí:** data v tvrzení existují v citovaných zdrojích.
4. **Chybějící údaje:** deterministický checklist pro sekci (např. pro chirurga TNM, poslední zobrazení, předchozí operace). Co nemá evidenci, doplní se jako `kind: "missing"`, i když ho LLM nezmínil.
5. **UI:** `unverified` tvrzení se zobrazí s varováním (nebo se skryjí; přepínač v konfiguraci). Cíl pro demo je **0 neověřených tvrzení**.

Metriky z validátoru (podíl ověřených tvrzení) jdou do evalu ([§5.8](#58-evaluace-proti-ground-truth)) a do pitche.

### 5.4 Red flags

**Hybrid: deterministická pravidla (`services/rules/red_flags.py`) + LLM detekce rozporů.** Každý flag má `severity`, `title`, `description` a **≥ 2 citace** (oba zdroje).

| Pravidlo (ilustrativní prahy, **ověřit s mentory/onkology**) | Severity |
|---|---|
| `RF-ECOG`: \|ECOG lékař − ECOG pacient\| ≥ 2 | high (= 1: moderate) |
| `RF-HB-FATIGUE`: pokles Hb > 20 g/L mezi měřeními nebo Hb < 100 g/L **a** únava v PROMs vysoká | high |
| `RF-MARKER`: vzestup onkomarkeru (CEA, CA 19-9) > 25 % proti předchozí hodnotě, zatímco text zobrazení uvádí „regrese / stabilní“ | moderate |
| `RF-TOX`: PRO-CTCAE toxicita ≥ 3 (např. neuropatie) a pokračující související lék | moderate |
| `RF-STALE`: poslední zobrazení starší než 60 dní před datem MDT | moderate (readiness) |
| `RF-MISSING`: chybí histologie, TNM nebo biomarker relevantní pro diagnózu | moderate (readiness) |
| `RF-LLM`: LLM porovná páry zdrojů (zpráva vs. lab, zpráva vs. PROMs, nominace vs. data) a vrátí rozpory s citacemi; prochází validátorem | podle LLM |

Výstup se před potvrzením ukládá v draftu a po potvrzení jako `DetectedIssue` v IRIS.

### 5.5 B2 — podpora rozhodování

- **Možnosti léčby:**
  1. vektorové hledání v `MDT.GuidelineChunk` s filtrem `CancerType` = prefix MKN-10 pacienta a dotazem složeným ze stadia, biomarkerů a linie léčby;
  2. LLM vrátí **2–4 možnosti**, každou s citací guideline (sekce/strana) a s vazbou na fakta pacienta (citace);
  3. **žádné pořadí jako doporučení** a žádné „doporučujeme“.
- **Klinické studie:**
  1. pro každou `ResearchStudy` odpovídající diagnóze se vyhodnotí každé kritérium (`met` / `not_met` / `unknown`) s citací faktu pacienta;
  2. celkový stav: `eligible` / `potentially_eligible` (chybí data) / `not_eligible`;
  3. u `unknown` doplnit, co je potřeba dodat.
- **Otázky k diskusi:** 2–3 otázky odvozené z red flags, chybějících dat a otázky z nominace.

### 5.6 AI zapisovatel (BON-3)

- Vstup: přepis diskuse (`DocumentReference` transcript, rozdělený na úseky s časem a mluvčím).
- Výstup: draft `decision` (rozhodnutí, zdůvodnění, úkoly s vlastníkem a termínem, re-review) s citacemi na úseky přepisu (`DocumentReference/p01-tr-1#5`).
- Vždy jen **draft**. Předseda edituje a potvrzuje.

### 5.7 Model a ochrana údajů

- **Provider:** existující abstrakce `WEB_Template/backend/services/ai_service.py` (`mock` / `openai` / `gemini` / `ollama`, volba přes `AI_PROVIDER`).
  - Rozšířit o strukturovaný výstup (JSON schema) a o `embed()`.
  - Konkrétní model vybere W3 (AI lane) a zapíše ho do Rozhodnutí v PROGRESS.md.
  - Pro pitch: EU zpracování (např. EU region u cloud providera), případně lokální Ollama jako fallback.
  - **Testy a CI vždy na `mock`** (žádné placené volání).
- **Pseudonymizace** (`services/ai/pseudonymize.py`):
  - jméno, rodné číslo, adresa a kontakty se do LLM **nikdy** neposílají;
  - pacient je „Pacient“ s věkem místo data narození;
  - lékaři jsou zastoupeni rolí („chirurg“);
  - po návratu z LLM se v UI mapují zpět.
- **Data:** všechna data v projektu jsou smyšlená, pipeline ale navrhujeme jako pro reálná data.
- **Audit:** `LlmCallLog` (účel, model, hash promptu, počet tokenů, latence, bez PII). Potvrzené záznamy mají `Provenance` (kdo, kdy, z čeho).
- **Regulace (do pitche):** GDPR (zvláštní kategorie údajů, minimalizace, pseudonymizace), **AI Act**: high-risk systém (lidský dohled, logování, transparentnost = naše pravidla 1–4), **MDR**: software jako zdravotnický prostředek, EHDS.

### 5.8 Evaluace proti ground truth

- Command `python manage.py eval_ground_truth` porovná pro každého pacienta:
  - **recall red flags:** nalezené vs. očekávané;
  - **pokrytí klíčových faktů;**
  - **míru neověřených tvrzení** (z validátoru);
  - **správnost „údaj chybí“** (vložené mezery).
- Výsledek se zapíše do `docs/EVAL.md` (tabulka). Čísla jdou do pitche jako důkaz spolehlivosti (kritérium 20 %).

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
│   │   └── management/commands/ ★ ingest_dataset, iris_init, eval_ground_truth, seed_mdt
│   ├── projects/ items/ ws/     # z templatu – skrýt z UI, nemazat (nerozbíjet seed/migrace)
├── services/
│   ├── ai_service.py            # existující providery (+ structured output, + embed)
│   ├── fhir/                ★   # client.py, mappers/, bundles.py, writeback.py, export.py
│   ├── iris/                ★   # db.py (connect ctx manager), vector_store.py
│   ├── ai/                  ★   # context_builder.py, pseudonymize.py, grounding.py, prompts/*.md
│   └── rules/               ★   # red_flags.py, readiness.py, recist.py
└── mcp_server.py            ★   # (SHOULD) FastMCP nad IRIS
```

Nové závislosti v `requirements.txt`:

- `intersystems-irispython`;
- `openai` (případně jiný SDK);
- `pydantic` (schémata);
- `langchain-text-splitters`;
- `pymupdf` (pokud budou PDF);
- `fhir.resources` (validace mapperů, volitelně);
- `weasyprint` nebo `reportlab` (PDF);
- `fastmcp` (SHOULD).

### 6.2 Modely (PostgreSQL)

| Model | Pole (hlavní) |
|---|---|
| `MdtSession` | `date`, `title`, `chair` (User), `status` (planned/in_progress/closed) |
| `MdtCase` | `session` FK, `order`, `patient_fhir_id`, `service_request_fhir_id`, `question`, `status` (nominated → ready → in_discussion → decided → confirmed) |
| `BriefConfig` | `name`, `owner`, `is_preset`, `sections` JSON (`[{id, enabled, order, detail}]`), `roles_present` JSON, `detail_level` (brief/standard/detailed), `language` |
| `Brief` | `case` FK, `config_snapshot` JSON, `content` JSON (schéma [§8.2](#82-brief-podklad)), `model`, `created_at` |
| `GenerationJob` | `case` FK, `kind` (brief/scribe/patient_summary), `status` (queued/running/done/error), `progress` (0–100), `result_id`, `error` |
| `Decision` | `case` FK, `content` JSON (schéma [§8.4](#84-decision-závěr-komise)), `status` (draft/confirmed), `confirmed_by`, `confirmed_at`, `fhir_ids` JSON, `fhir_bundle` JSON |
| `LlmCallLog` | `purpose`, `provider`, `model`, `prompt_hash`, `tokens_in`, `tokens_out`, `latency_ms`, `ok` |

Demo uživatelé:

- `predseda` (předseda komise);
- `chirurg`, `onkolog`, `radiolog`, `patolog`;
- 1-click přihlášení jako v templatu.

### 6.3 REST API

Všechny endpointy pod `/api/`, autentizace JWT cookie, schéma v Swaggeru (`/api/docs/`).

| Metoda | Endpoint | Popis |
|---|---|---|
| GET | `/api/patients/` | seznam pacientů (z FHIR `Patient` + primární `Condition`) |
| GET | `/api/patients/{pid}/` | detail: demografie (pseudonym), diagnóza, TNM, ECOG |
| GET | `/api/patients/{pid}/timeline/` | události časové osy s Evidence ID |
| GET | `/api/patients/{pid}/observations/?code=…` | časové řady (labs, PROMs skóre) pro grafy |
| GET | `/api/evidence/?id={EvidenceId}` | zdroj citace (text + zvýraznění / hodnota) |
| GET, POST | `/api/mdt/sessions/` | zasedání |
| GET | `/api/mdt/sessions/{sid}/` | detail + agenda (`MdtCase[]`) |
| POST | `/api/mdt/cases/` | nominace (vytvoří i FHIR `ServiceRequest`) |
| GET, POST, PUT | `/api/mdt/configs/` · `/api/mdt/configs/{cid}/` | presety konfigurace |
| GET | `/api/mdt/cases/{cid}/readiness/` | kontrola připravenosti (BON-1) |
| POST | `/api/mdt/cases/{cid}/brief/` | `{config_id \| config}`, vrátí `{job_id}` |
| GET | `/api/mdt/cases/{cid}/brief/` | poslední podklad (schéma §8.2) |
| GET | `/api/jobs/{jid}/` | `{status, progress, result_id, error}`; FE polluje à 1 s |
| POST | `/api/mdt/cases/{cid}/scribe/` | přepis → draft závěru (job) (BON-3) |
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
| `/dashboard` | přehled: dnešní zasedání, případy a jejich stav, úkoly po termínu |
| `/dashboard/mdt/[sessionId]` | agenda zasedání: pacienti, readiness, stav |
| `/dashboard/mdt/[sessionId]/setup` | **konfigurátor** (sekce, pořadí, role, detail, presety) |
| `/dashboard/cases/[caseId]` | **podklad**: hlavička případu + A / B (záložky rolí) / B2 / red flags |
| `/dashboard/cases/[caseId]/record` | **zápis závěru**: editor, úkoly, potvrzení, export |
| `/dashboard/patients/[patientId]` | pacient: časová osa, labs/PROMs grafy, dokumenty |
| `/dashboard/tasks` | úkoly po zasedání |

Template stránky `projects`, `storage`, `realtime` a `ai` skrýt z navigace (`DashboardLayout.tsx`).

### 7.2 Klíčové komponenty (`src/components/mdt/` ★)

| Komponenta | Účel |
|---|---|
| `CaseHeader` | sticky hlavička: pseudonym, věk, diagnóza + TNM, **ECOG lékař vs. pacient**, otázka komise, počet red flags (orientace do 30 s) |
| `AiBlock` | obal AI obsahu: badge „AI návrh“, odlišný styl (např. fialový levý okraj + ikona ✨ + jemné pozadí), stav `draft` / `confirmed` |
| `Claim` + `CitationChip` | věta s čísly citací `[1]`; `unverified` se zobrazí s varováním |
| `SourceDrawer` | boční panel: zdroj citace se zvýrazněným úsekem / hodnota + referenční rozsah |
| `MissingData` | šedý chip „Údaj chybí v podkladech“ + co doplnit |
| `RedFlagCard` | závažnost (barva), popis, **dva zdroje vedle sebe** |
| `EcogCompare` | dvě hodnoty + rozdíl + data |
| `Timeline` | horizontální časová osa (dg., léčba, zobrazení, PROMs, MDT) |
| `TrendChart` | Hb, onkomarkery, skóre PROMs v čase (doporučení: `recharts`) |
| `RoleTabs` | záložky podle přítomných rolí |
| `TreatmentOptions` / `TrialScreening` | B2: možnosti s citací guidelines; tabulka kritérií met / not_met / unknown |
| `SectionConfigurator` | zap/vyp sekce, drag & drop pořadí, role, detail; uložit preset |
| `DecisionEditor` | rozhodnutí, zdůvodnění, úkoly (owner, termín), re-review; AI předvyplnění odlišené |
| `ConfirmDialog` | potvrzení: kdo potvrzuje, co se zapíše (výpis FHIR resources) |
| `JobProgress` | průběh generování (polling `/api/jobs/{id}`) |

### 7.3 UX principy

1. **30 sekund:** `CaseHeader` a 3–5 odrážek souhrnu nad ohybem stránky, bez scrollování.
2. **Každé tvrzení je ověřitelné jedním klikem.** Citace jsou čísla, ne dlouhé odkazy.
3. **AI vs. člověk je vidět na první pohled** (barva, badge, stav).
4. **Prezentační režim** pro projektor: velké písmo, tmavé téma (theme toggle je v templatu).
5. Ovládání klávesnicí: Ctrl+K (command palette z templatu) pro přepínání pacientů v agendě.
6. Typy `src/types/mdt.ts` přesně odpovídají [§8](#8-datové-kontrakty-fe--be). Pro vývoj UI bez backendu existují fixtures `data/fixtures/*.json`.

---

## 8. Datové kontrakty (FE ↔ BE)

> **Zdroj pravdy:** backend `apps/copilot/schemas.py` (pydantic) ↔ frontend `src/types/mdt.ts`. Při změně uprav obojí + tuto sekci + fixtures.

### 8.1 Společné typy

```ts
type EvidenceId = string;                       // "Observation/p01-hb-20260312" | "DocumentReference/p01-dr-03#2"
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
```

### 8.2 Brief (podklad)

```ts
interface Brief {
  case_id: string;
  patient_id: string;
  generated_at: string;                         // ISO 8601
  model: string;
  config: BriefConfig;                          // snapshot
  status: "draft" | "confirmed";
  header: {
    display_name: string;                       // pseudonym / iniciály
    age: number;
    sex: "male" | "female" | "other" | "unknown";
    diagnosis: { text: string; icd10: string; citation: EvidenceId };
    tnm?: { t: string; n: string; m: string; stage?: string; citation: EvidenceId };
    ecog: {
      physician?: { value: number; date: string; citation: EvidenceId };
      patient?:   { value: number; date: string; citation: EvidenceId };
    };
    mdt_question: { text: string; citation: EvidenceId };   // z ServiceRequest
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
}

interface RedFlag {
  id: string;
  rule: string;                                 // "RF-ECOG" | "RF-HB-FATIGUE" | "RF-LLM" …
  severity: Severity;
  title: string;
  description: string;
  citations: EvidenceId[];                      // ≥ 2 (oba zdroje)
  verification: Verification;
}

interface TimelineEvent {                       // GET /api/patients/{pid}/timeline/
  date: string;
  type: "diagnosis" | "procedure" | "medication" | "imaging" | "lab" | "proms" | "mdt" | "document";
  label: string;
  citation: EvidenceId;
}
```

### 8.3 DecisionSupport (B2)

```ts
interface DecisionSupport {
  treatment_options: {
    id: string;
    title: string;                              // např. "Neoadjuvantní chemoradioterapie → resekce"
    rationale: Claim[];                         // vazba na fakta pacienta
    guideline_citations: EvidenceId[];          // "Guideline/esmo-crc#s4.2-1"
    considerations: string[];                   // rizika, kontraindikace (citované v rationale)
  }[];
  trials: {
    study_id: string;                           // "ResearchStudy/rs-02"
    title: string;
    overall: "eligible" | "potentially_eligible" | "not_eligible";
    criteria: {
      criterion_id: EvidenceId;                 // "ResearchStudy/rs-02#inc-3"
      kind: "inclusion" | "exclusion";
      text: string;
      status: "met" | "not_met" | "unknown";
      citations: EvidenceId[];                  // fakta pacienta
      missing?: string;                         // u unknown: co dodat
    }[];
  }[];
  discussion_questions: { text: string; citations: EvidenceId[] }[];   // 2–3
  disclaimer: string;                           // "AI předkládá možnosti, nerozhoduje."
}
```

### 8.4 Decision (závěr komise)

```ts
interface Decision {
  case_id: string;
  status: "draft" | "confirmed";
  attendees: { user_id: string; name: string; role: RoleId | "chair" }[];
  decision: { text: string; source: "ai" | "human" | "ai_edited" };
  rationale: { text: string; source: "ai" | "human" | "ai_edited"; citations: EvidenceId[] };
  tasks: {
    id: string;
    description: string;
    owner: string;                              // jméno / role
    due_date: string;                           // YYYY-MM-DD
    status: "requested" | "in-progress" | "completed";
    source: "ai" | "human" | "ai_edited";
  }[];
  re_review?: { date: string; reason: string };
  trial_candidates: string[];                   // ResearchStudy ID potvrzené komisí
  red_flags_acknowledged: string[];             // RedFlag.id
  confirmed_by?: { user_id: string; name: string };
  confirmed_at?: string;
  fhir_ids?: {                                  // po potvrzení
    careplan: string; tasks: string[]; detected_issues: string[];
    provenance: string; composition: string; document_reference_pdf?: string;
  };
}
```

### 8.5 BriefConfig

```ts
interface BriefConfig {
  id?: string;
  name: string;
  sections: { id: SectionId; enabled: boolean; order: number; detail?: "brief" | "standard" | "detailed" }[];
  roles_present: RoleId[];                      // ovlivní role_views i záložky
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
| `IRIS_USER` / `IRIS_PASSWORD` | backend | dev `SuperUser` / `SYS`, **prod jiné** |
| `FHIR_BASE_URL` | backend | `http://iris:52773/fhir/r4` |
| `AI_PROVIDER` | backend | `mock` (testy) / `openai` / `gemini` / `ollama` |
| `AI_MODEL` | backend | rozhodne W3 |
| `EMBEDDING_MODEL` | backend | `text-embedding-3-small` (dim 1536) |
| `OPENAI_API_KEY` (případně jiné) | backend | **nikdy do gitu ani do frontendu** |
| `CSRF_TRUSTED_ORIGINS` / `CORS_ALLOWED_ORIGINS` | backend | Vercel doména(y) |

---

## 10. Lokální vývoj

```powershell
# celý stack (Next.js, Django, Postgres, Redis, Mailhog, Traefik) + IRIS (po T-002)
cd WEB_Template
.\dev.ps1 up                       # nebo: make dev
docker compose -f docker-compose.dev.yml exec backend python manage.py iris_init
docker compose -f docker-compose.dev.yml exec backend python manage.py ingest_dataset /data/raw
```

- **Jen frontend** (doporučeno pro UI lane): `cd WEB_Template/frontend && npm run dev`. Pak buď `BACKEND_URL` na nasazený backend, nebo práce nad fixtures v `data/fixtures/`.
- **Kontrola IRIS:** `curl -u SuperUser:SYS http://localhost:52773/fhir/r4/metadata` vrátí 200.
- **Reset dat:** `docker compose -f docker-compose.dev.yml down -v`. Smaže **i** Postgres volume.
- Porty: FE 3000, BE 8000, Postgres 5432, Redis 6379, Mailhog 8025, Traefik 8080, IRIS 1972 / 52773.

### Navrhovaná struktura repa

```
Rakhaton2026/
├── AGENTS.md / CLAUDE.md      # pravidla pro AI agenty
├── ARCHITEKTURA.md            # tento dokument
├── PROGRESS.md                # roadmapa, úkoly, stav, deník
├── docs/
│   ├── zadani/                # pptx zadání (přesunout z WEB_Template/)
│   └── EVAL.md                # výsledky evaluace
├── data/
│   ├── raw/                   # dataset od Asseco (ověřit, zda smí do gitu)
│   ├── fhir/                  # vygenerované FHIR bundly
│   ├── guidelines/  trials/
│   ├── ground_truth/
│   └── fixtures/              # JSON pro FE vývoj (Brief, Decision…)
├── .claude/skills/            # IRIS skills z FHIR-AI-Hackathon-Kit
└── WEB_Template/
    ├── frontend/              # → Vercel
    ├── backend/               # → server
    ├── iris/            ★     # Dockerfile + merge.cpf (z kitu)
    └── docker-compose*.yml    # + služba iris
```

---

## 11. Otevřené otázky

| # | Otázka | Kdo / kde |
|---|---|---|
| Q1 | Formát a doručení datasetu (JSON? PDF? CSV?), včetně ground truth a přepisu | Ľ. Piljan (Asseco) |
| Q2 | LLM provider a API klíč: kdo platí, EU region? | tým |
| Q3 | Server a doména pro backend (VPS? VZP Azure s IRIS?) | tým / VZP |
| Q4 | Pravidla odevzdání (repo, video, délka pitche) a zda lze po So 12:00 commitovat pro národní finále | organizátoři |
| Q5 | Je repo veřejné? Smí dataset do gitu? | tým / Asseco |
| Q6 | Klinické prahy red flags a obsah rolí: připomínky onkologů | mentoři |
| Q7 | Podpora `Patient/$everything` a import mCODE IG ve verzi IRIS v kontejneru | O. Hoferek / test |

---

## 12. Zdroje

- Zadání: `WEB_Template/MDT_Copilot_zadani_upravené_2026_v02.pptx` (Asseco CE)
- [InterSystems Challenge at Rakathon 2026](https://developer.intersystems.com/intersystems-challenge-at-rakathon-2026/)
- [FHIR-AI-Hackathon-Kit (V2)](https://github.com/intersystems-community/FHIR-AI-Hackathon-Kit): tutoriály 3.x FHIR, 3.5 FHIR SQL Builder, 4.1 Vector Search, 5.1 agenti, 5.2 MCP; `skills/`
- [iris-agentic-dev](https://github.com/intersystems-community/iris-agentic-dev): MCP pro AI coding agenty nad IRIS
- [Rakathon 2026](https://www.rakathon.cz/eng): harmonogram
- HL7 [FHIR R4](https://hl7.org/fhir/R4/) · [mCODE](https://hl7.org/fhir/us/mcode/) · HL7 Europe Common Cancer Model (ECCDM, 1.0.0-ballot) · [IPS](https://hl7.org/fhir/uv/ips/) · [Patient $everything](https://www.hl7.org/fhir/R4/operation-patient-everything.html)
- Klinika: ESMO guidelines · RECIST 1.1 · EORTC QLQ-C30 · PRO-CTCAE
