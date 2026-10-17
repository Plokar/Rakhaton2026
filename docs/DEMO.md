# Demo scénář: 5 minut, pacient P03 (T-401)

> Pro toho, kdo předvádí na pitchi. Každý krok má **co kliknout**, **co říct** a **zálohu**, když něco nepůjde.
> Pořadí odpovídá [PROGRESS §7](../PROGRESS.md#7-demo-checklist-finále-5-min-pacient-p03).
> Data jsou fiktivní (dataset Asseco v1.1), demo pacient je **P03** (D-013), záloha **P05**.

## Před pitchem (10 min předem)

1. Stack běží: `cd WEB_Template; .\dev.ps1 up`. Kontrola: `curl -u SuperUser:SYS http://localhost:52773/fhir/r4/metadata` vrátí 200.
2. Čistý stav P03 (smaže zápisy z nácviku, vrátí P03 na původní board a načte uložený podklad):
   `docker compose -f docker-compose.dev.yml exec backend python manage.py demo reset P03`
3. **Rozhodni, jestli generovat živě:**
   - Výchozí LLM je **NVIDIA** (T-323): živý podklad P03 trvá **25–40 s** (hostované API, limit 40 požadavků za minutu). Na pitch je jistější **offline demo**: v `WEB_Template/.env` `MDT_DEMO_OFFLINE=True`, pak `docker compose -f docker-compose.dev.yml up -d backend`. Podklad se načte z `data/demo_cache/brief_P03.json` (předgenerovaný přes NVIDIA, stejný obsah).
   - Gemini free tier (20 požadavků za den) na živé demo nestačí, proto už není výchozí.
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
| 8 | 4:30–5:00 | — | slide s čísly z [EVAL.md](EVAL.md) | NVIDIA Nemotron (v ostrém provozu NIM on-prem, data neopustí nemocnici), IRIS FHIR + Vector Search s filtrem na pacienta, grounding validátor, pseudonymizace, AI Act / MDR |

## Kroky, které zatím nemají tlačítko v UI

Všechno je v UI (T-322, T-323):

- **AI zapisovatel (krok 6):** v Závěru komise „Importovat audio z diskuse“ = `data/audio/P03_mdt02.m4a` (předseda, zadávající nebo přizvaný lékař; ostatní vidí závěr jen pro čtení) (Groq Whisper + NVIDIA, ~30 s), nebo v jednání komise přepínač **„Nahrávat diskusi“** v boku agendy (po přepnutí pacienta se úsek sám odešle). Bez sítě: vložit přepis z `data/audio/P03_mdt02.md`.
- **Shrnutí pro pacienta:** po potvrzení v Závěru komise „Připravit shrnutí pro pacienta“; text je i v PDF exportu („Shrnutí pro pacienta [AI návrh]“).
- **Nový pacient a vložení zprávy (BON-7):** v zařazení „Nový pacient“ (pseudonym Pxx do IRIS), pak „Vložit zprávu“: text nebo PDF (parser, sken přes OCR) → návrh hodnot se zněním odstavce → zápis do IRIS → podklad cituje odstavce zprávy.

## Zálohy

| Problém | Záloha |
|---|---|
| NVIDIA / Groq nedostupné nebo limit | `MDT_DEMO_OFFLINE=True` (podklad z cache); zapisovatel s vloženým přepisem místo audia; přepnout `AI_PROVIDER=gemini` |
| IRIS nenaběhne | `docker compose -f docker-compose.dev.yml restart iris`, počkat na healthy (~1 min) |
| Rozbitý stav po nácviku | `python manage.py demo reset P03` |
| Nic nefunguje | záložní video (T-403) |
| P03 nejde | stejný průchod na **P05** (záloha D-013; třezalka × olaparib, RKT-06) |

## Kontrola po nácviku

- [ ] krok 0–8 pod 5:00 (3× se stopkami, T-401)
- [ ] `demo reset P03` po každém nácviku
- [ ] čísla na slidu 8 = aktuální běh v [EVAL.md](EVAL.md)
