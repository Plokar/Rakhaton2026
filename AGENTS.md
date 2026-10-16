# AGENTS.md — pravidla pro AI agenty (a lidi)

Projekt **MDT Copilot** vzniká na hackathonu Rakathon 2026 (zadání Asseco CE + výzva InterSystems). Paralelně na něm pracuje víc lidí a víc AI agentů, proto drž tento protokol.

## Než začneš

1. Spusť `git pull --rebase origin master`.
2. Přečti **[PROGRESS.md](PROGRESS.md)**: protokol (§1), task board (§4) a blokery.
3. Přečti v **[ARCHITEKTURA.md](ARCHITEKTURA.md)** sekce, na které odkazuje tvůj úkol. Je to zdroj pravdy pro architekturu, FHIR model a kontrakty (§8).
4. U všeho, co sahá na data nebo AI, přečti **[DATASET.md](DATASET.md)**: struktura datasetu, ID, sanitizace, kde co ve FHIR je a hypotézy nesrovnalostí.
5. U obrazovek, semaforu, varování a zařazení pacienta přečti **[docs/POZADAVKY_LEKARE.md](docs/POZADAVKY_LEKARE.md)**: požadavky lékaře sladěné se zadáním, katalog pravidel, škály a zkratky.
6. Vezmi si úkol podle protokolu: stav ⬜, závislosti ✅. Udělej **claim commit** a pak pracuj ve větvi `t-xxx-…`. Když na jednom stroji pracuje víc agentů, má každý vlastní `git worktree` (PROGRESS §1, „Sprinty a paralelní práce“).

## Mapa repa

- `WEB_Template/frontend/`: Next.js 16 (→ Vercel). **Před psaním frontend kódu přečti `WEB_Template/frontend/AGENTS.md`**, protože Next 16 má breaking changes.
- `WEB_Template/backend/`: Django 5.2 + DRF (→ VPS). Je to modulární monolit: `apps/` (HTTP vrstva), `services/` (logika).
- IRIS for Health (FHIR R4 + Vector Search): služba `iris` v docker-compose, viz ARCHITEKTURA §4.
- `Dataset_MDT_Copilot_v1.1_pre_timy/Dataset_MDT_Copilot_v1.1/`: dataset od Asseco (= `DATASET_DIR`). **Neměnit**, opravy patří do sanitizace v ingestu.
- `data/`: dev ground truth, fixtures pro UI, audio pro zapisovatele.
- `docs/`: požadavky lékaře (`POZADAVKY_LEKARE.md`), později `EVAL.md` a `DEMO.md`.
- `.claude/skills/` (po T-011): IRIS skills z FHIR-AI-Hackathon-Kit. Použij je pro FHIR, vektory a IRIS SQL, ale **místo OpenAI volej Gemini**.

## Příkazy

```powershell
cd WEB_Template; .\dev.ps1 up          # celý dev stack (Linux/macOS: ./dev.sh up nebo make dev)
.\dev.ps1 test                         # backend testy (pytest)
cd WEB_Template/frontend; npm run lint; npm run build
curl -u SuperUser:SYS http://localhost:52773/fhir/r4/metadata   # IRIS FHIR běží?
docker compose -f docker-compose.dev.yml exec backend python manage.py ingest_dataset --patients P03 --skip-vectors
```

- **Windows:** před prvním checkoutem `git config --global core.autocrlf input`. Jinak dostane `entrypoint.sh` konce řádků CRLF a backend nenaběhne (do vyřešení T-001, Q12).
- **Bez Node na stroji:** lint a build pusť v kontejneru: `docker compose -f docker-compose.dev.yml exec frontend npm run lint`.

## Pravidla

- **Commit:** `T-xxx: co se změnilo`. Commituj malé kroky a často. Nikdy `push --force` do `master`. Před claimem i před každým push `git pull --rebase origin master`. Jeden agent = jeden úkol = jedna větev.
- **Secrets:** nikdy necommituj `.env`, API klíče ani hesla. Ve frontendu nesmí být žádné LLM klíče.
- **LLM:** Google AI Studio (Gemini API).
  - V testech a CI jen `AI_PROVIDER=mock`.
  - Reálná volání: **free tier jen nad syntetickým datasetem hackathonu** (D-021, Q9); skutečná pacientská data nikdy, ta jen placený tier / Vertex AI EU.
  - Model ID drž v env (`AI_MODEL`…), nehardcoduj je. Výchozí `AI_MODEL=gemini-3.8-flash` (nejlepší poměr ceny a výkonu), `gemini-4-argon` jen pro srovnání v evalu.
- **Kontrakty** (API §6.3, JSON §8): změna jde nejdřív do ARCHITEKTURA.md, ve stejném PR jako kód, a do Deníku v PROGRESS.md jako `⚠️ KONTRAKT`.
- **Dataset → FHIR:**
  - bundly jsou `collection` a do IRIS se nahrávají jako `transaction` s `PUT Type/id`;
  - **sanitizace je povinná**: `_` v ID se mění na `-` (`P01-lab01-hb_f` → `P01-lab01-hb-f`) a prázdné stringy se odstraňují;
  - reference piš ve tvaru `ResourceType/id`;
  - text je v `attachment.data` / `presentedForm.data` jako base64;
  - neznámé search parametry IRIS tiše ignoruje, proto filtry ověř.
- **Za běhu čti data jen z IRIS**, nikdy z JSON nebo `.md` souborů datasetu (ty jsou jen pro ingest, testy a čtení člověkem).
- **Citace (Evidence ID) = ID z datasetu:** `P03-img03`, `P03-img03#2` (odstavec), `KRC-2.4` (guidelines), `RKT-03/V3` (kritérium studie). Jediná výjimka je `EXT-…` pro externí zdroj prahu u pravidel semaforu (D-016), nikdy pro fakta pacienta. Nevymýšlej jiné formáty.
- **IRIS DB-API:** spojení vždy zavírej (Community Edition má limit spojení). SQL parametry předávej přes `?`. Používej `SELECT TOP n`, ne `LIMIT`.
- **AI výstupy:** každé tvrzení musí mít citaci a chybějící údaj se hlásí jako `missing`, nikdy se nedomýšlí. AI text musí být v UI odlišený a nic se nestane oficiálním záznamem bez potvrzení lékařem.
  - **Semafor** u léčebných postupů počítá jen kód, s citací faktu pacienta i pravidla (D-015). LLM barvu nepřiřazuje. Vždy se zobrazí všechny možnosti, i červené, a nikdy se nepíše „doporučujeme“.
  - **Z podkladu se nic neztratí:** odkliknuté varování ani přeskočený údaj („Chybí (přeskočeno lékařem)“) nezmizí (D-019).
  - **Hlavička bez jména a RČ:** `P03 · muž · 67 let`, diagnóza + TNM, hlavní otázka, ECOG lékaře i pacienta, záměr C/P (D-018).
  - **Když si AI není jistá** (rozmezí, nejednoznačná zkratka, rozpor), vyhodí varování NEJISTOTA AI. Nikdy neodhaduje.
- **Rozsah:** neupravuj soubory cizí lane bez domluvy a neformátuj hromadně. Template moduly (`projects`, `items`, `ws`) nemaž, jen je skryj z UI.
- **Hotovo** znamená: DoD z task boardu je splněné, lint a testy projdou, stav v PROGRESS.md je ✅ a v Deníku přibyl jeden řádek.
- Když něco nevíš nebo jsi zablokovaný, zapiš to do Blokerů v PROGRESS.md a nehádej. Nový nález v datech připiš do DATASET.md §9.
