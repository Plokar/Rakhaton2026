# Demo scénář: 5 minut, pacient P03 (T-401)

> Pro toho, kdo předvádí na pitchi. Každý krok má **co kliknout**, **co říct** a **zálohu**, když něco nepůjde.
> Pořadí odpovídá [PROGRESS §7](../PROGRESS.md#7-demo-checklist-finále-5-min-pacient-p03).
> Data jsou fiktivní (dataset Asseco v1.1), demo pacient je **P03** (D-013), záloha **P05**.

## Před pitchem (10 min předem)

1. Stack běží: `cd WEB_Template; .\dev.ps1 up`. Kontrola: `curl -u SuperUser:SYS http://localhost:52773/fhir/r4/metadata` vrátí 200.
2. Čistý stav P03 (smaže zápisy z nácviku, vrátí P03 na původní board a načte uložený podklad):
   `docker compose -f docker-compose.dev.yml exec backend python manage.py demo reset P03`
3. **Rozhodni, jestli generovat živě:**
   - Gemini free tier má limit **5 požadavků za minutu a 20 za den** (jeden podklad ≈ 9 volání). Živý podklad P03 trvá ~1,5 minuty a denně vyjdou jen ~2 podklady. Nácvik proto dělej s offline demem a na pitch ho nech zapnuté: **offline demo**: v `WEB_Template/.env` `MDT_DEMO_OFFLINE=True`, pak `docker compose -f docker-compose.dev.yml up -d backend`. Podklad se načte z `data/demo_cache/brief_P03.json` (předgenerovaný, stejný obsah).
   - S placeným tierem (Q9) podklad trvá < 20 s, offline režim pak není potřeba.
4. Otevři dvě okna: aplikaci (`http://localhost:3000`) a **úzké okno** podkladu (tlačítko „Úzké okno“ v agendě). Druhý panel: IRIS Management Portal (`http://localhost:52773/csp/sys/UtilHome.csp`, SuperUser / SYS) nebo Swagger (`http://localhost:8000/api/docs/`).
5. Heslo všech demo účtů: `demo123456` (na přihlášení jsou 1-click tlačítka).

## Scénář

| # | Čas | Účet | Klikni | Řekni |
|---|---|---|---|---|
| 0 | 0:00–0:30 | **onkolog** | Zasedání → board GIT → **Zařadit pacienta** → P03. Varování: chybí MMR, rozpor v neuropatii, „ECOG 0–1“. „Beru na vědomí“ → ECOG 0, záměr **C**, ✓ snímek < 3 měsíce → Zařadit | „Lékař zařadí pacienta za minutu. Systém sám najde, co chybí a co si odporuje. Odkliknuté varování nezmizí, komise ho uvidí.“ |
| 1 | 0:30–1:00 | **predseda** | Agenda GIT → **Nastavit podklad**: sekce, pořadí, přítomné role (onkolog, chirurg, radiolog, patolog, pacient) | „Předseda nastaví, co komise uvidí. Když chybí role, kterou guidelines vyžadují (hepatobiliární chirurg u resekability), upozorní ho to.“ |
| 2 | 1:00–1:20 | predseda | **Generovat podklad** (průběh v %) | „Všechna data jsou z IRIS FHIR, AI běží paralelně.“ |
| 3 | 1:20–1:50 | predseda | **Úzké okno:** hlavička `P03 · muž · 67 let`, C18.7 + jaterní metastázy, cT3 cN1 cM1a, **ECOG 0 (lékař) vs. 1 (pacient)**, velké **C**, otázka resekability, IM + stent | „Za 30 s víte, o koho jde. Bez jména a rodného čísla. Rozdíl ECOG lékaře a pacienta je varování.“ |
| 4 | 1:50–2:30 | predseda | Klik na citaci u restagingu → panel zdroje `P03-img03` („hrudník nebyl požadován“). Varovné signály → **neuropatie G1 vs. „padají mi věci z ruky“** → Porovnat zdroje + KRC-3.2 | „Každé tvrzení je ověřitelné jedním klikem. Rozpor ukazujeme z obou zdrojů. Co nemá zdroj, je označené jako neověřené, nebo jako ‚údaj chybí‘.“ |
| 5 | 2:30–3:20 | predseda | Sekce odborností: chirurg FLR 38 % a poslední bevacizumab, **RECIST PR 83 → 50 mm**, Lung-RADS / Fleischner „nelze použít“. B2: možnosti se **semaforem** (resekce 🟠, anti-EGFR 🔴 KRAS G12D), **RKT-03** po kritériích | „Semafor počítá kód, ne AI, a vždy ukáže všechny možnosti, i červené. AI předkládá, nerozhoduje.“ |
| 6 | 3:20–4:10 | predseda | Záznam → **AI zapisovatel** z nahrávky diskuse (viz níže) → draft s úkoly → **Potvrdit** → v Management Portalu / Swaggeru `Composition/P03-mdt02` + `Provenance` | „Z 3 minut diskuse vznikne návrh zápisu s úkoly a termíny. Oficiální je až po potvrzení předsedou, zapisuje se do nemocniční FHIR databáze.“ |
| 7 | 4:10–4:30 | predseda | **Export** PDF + FHIR (mCODE profily) · Úkoly po zasedání | „Standardní HL7 FHIR s mCODE profily. Úkoly komise mají vlastníka a termín, nic se neztratí.“ |
| 8 | 4:30–5:00 | — | slide s čísly z [EVAL.md](EVAL.md) | Gemini (placený tier / Vertex AI EU pro ostrý provoz), IRIS FHIR + Vector Search s filtrem na pacienta, grounding validátor, pseudonymizace, AI Act / MDR |

## Kroky, které zatím nemají tlačítko v UI

Backend je hotový, tlačítka doplní UI lane. Do té doby se ukazují přes Swagger (`/api/docs/`, přihlášení stejným účtem):

- **AI zapisovatel (krok 6):** `POST /api/mdt/cases/{id}/scribe/` → multipart `audio` = `data/audio/P03_mdt02.m4a`. S free tierem ~1 min, proto ho na pitch spusť **předem** (po `demo reset`, před pitchem) a v kroku 6 jen otevři Záznam: draft už tam je. Bez Gemini lze poslat JSON `{"segments": …}` z `data/audio/P03_mdt02_transcript.json`.
- **Shrnutí pro pacienta:** po potvrzení `POST /api/mdt/cases/{id}/patient-summary/` → text je v PDF exportu („Shrnutí pro pacienta [AI návrh]“).
- **Vložení zprávy (BON-7):** `POST /api/mdt/patients/P03/import/` `{"text": "…"}` → návrh hodnot s citací → `…/import/confirm/`.

## Zálohy

| Problém | Záloha |
|---|---|
| Gemini nedostupný / limit | `MDT_DEMO_OFFLINE=True` (podklad z cache); zapisovatel s `segments` místo audia |
| IRIS nenaběhne | `docker compose -f docker-compose.dev.yml restart iris`, počkat na healthy (~1 min) |
| Rozbitý stav po nácviku | `python manage.py demo reset P03` |
| Nic nefunguje | záložní video (T-403) |
| P03 nejde | stejný průchod na **P05** (záloha D-013; třezalka × olaparib, RKT-06) |

## Kontrola po nácviku

- [ ] krok 0–8 pod 5:00 (3× se stopkami, T-401)
- [ ] `demo reset P03` po každém nácviku
- [ ] čísla na slidu 8 = aktuální běh v [EVAL.md](EVAL.md)
