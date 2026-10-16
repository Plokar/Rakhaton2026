# AGENTS.md — pravidla pro AI agenty (a lidi)

Projekt **MDT Copilot** vzniká na hackathonu Rakathon 2026 (zadání Asseco CE + výzva InterSystems). Paralelně na něm pracuje víc lidí a víc AI agentů, proto drž tento protokol.

## Než začneš

1. Spusť `git pull --rebase origin master`.
2. Přečti **[PROGRESS.md](PROGRESS.md)**: protokol (§1), task board (§4) a blokery.
3. Přečti v **[ARCHITEKTURA.md](ARCHITEKTURA.md)** sekce, na které odkazuje tvůj úkol. Je to zdroj pravdy pro architekturu, FHIR model a kontrakty (§8).
4. Vezmi si úkol podle protokolu: stav ⬜, závislosti ✅. Udělej **claim commit** a pak pracuj ve větvi `t-xxx-…`.

## Mapa repa

- `WEB_Template/frontend/`: Next.js 16 (→ Vercel). **Před psaním frontend kódu přečti `WEB_Template/frontend/AGENTS.md`**, protože Next 16 má breaking changes.
- `WEB_Template/backend/`: Django 4.2 + DRF (→ externí server). Je to modulární monolit: `apps/` (HTTP vrstva), `services/` (logika).
- IRIS for Health (FHIR R4 + Vector Search): služba `iris` v docker-compose, viz ARCHITEKTURA §4.
- `data/`: dataset, vygenerované FHIR bundly, fixtures pro UI.
- `.claude/skills/` (po T-011): IRIS skills z FHIR-AI-Hackathon-Kit. Použij je pro FHIR, vektory a IRIS SQL.

## Příkazy

```powershell
cd WEB_Template; .\dev.ps1 up          # celý dev stack (Linux/macOS: ./dev.sh up nebo make dev)
.\dev.ps1 test                         # backend testy (pytest)
cd WEB_Template/frontend; npm run lint; npm run build
curl -u SuperUser:SYS http://localhost:52773/fhir/r4/metadata   # IRIS FHIR běží?
```

## Pravidla

- **Commit:** `T-xxx: co se změnilo`. Commituj malé kroky a často. Nikdy `push --force` do `master`.
- **Secrets:** nikdy necommituj `.env`, API klíče ani hesla. Ve frontendu nesmí být žádné LLM klíče.
- **LLM v testech:** jen `AI_PROVIDER=mock`.
- **Kontrakty** (API §6.3, JSON §8): změna jde nejdřív do ARCHITEKTURA.md, ve stejném PR jako kód, a do Deníku v PROGRESS.md jako `⚠️ KONTRAKT`.
- **FHIR:**
  - používej stabilní ID a `PUT` v transaction bundlu (žádné duplikáty);
  - reference piš ve tvaru `ResourceType/id`;
  - text v `attachment.data` kóduj jako base64;
  - neznámé search parametry IRIS tiše ignoruje, proto filtry ověř.
- **IRIS DB-API:** spojení vždy zavírej (Community Edition má limit spojení). SQL parametry předávej přes `?`. Používej `SELECT TOP n`, ne `LIMIT`.
- **AI výstupy:** každé tvrzení musí mít citaci (Evidence ID) a chybějící údaj se hlásí jako `missing`, nikdy se nedomýšlí. AI text musí být v UI odlišený a nic se nestane oficiálním záznamem bez potvrzení lékařem.
- **Rozsah:** neupravuj soubory cizí lane bez domluvy a neformátuj hromadně. Template moduly (`projects`, `items`, `ws`) nemaž, jen je skryj z UI.
- **Hotovo** znamená: DoD z task boardu je splněné, lint a testy projdou, stav v PROGRESS.md je ✅ a v Deníku přibyl jeden řádek.
- Když něco nevíš nebo jsi zablokovaný, zapiš to do Blokerů v PROGRESS.md a nehádej.
