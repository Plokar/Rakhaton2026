# Audit funkcí (T-329)

> Stav k 17. 10. 2026, větev `dodelat` (master + T-322, T-329, T-330, T-332, T-333). Ověřeno bez Dockeru:
> skutečný Django backend nad in-memory FHIR s celým datasetem (`services/fhir/testing.py`, 1 098 resources),
> `AI_PROVIDER=mock`, frontend `next dev`, Playwright za předsedu, lékaře a člena komise.

| Oblast | Předseda | Lékař (onkolog) | Člen komise (chirurg) | Pozn. |
|---|---|---|---|---|
| Kalendář `/dashboard`, týden, rychlý přehled `?pacient=` | ✅ | ✅ | ✅ | |
| Zasedání `/dashboard/mdt`, jednání `/dashboard/mdt/2` | ✅ | ✅ | ✅ | |
| Zařazení pacienta `/dashboard/mdt/2/add` | ✅ | ✅ | ✅ (jen čtení) | 403 při zařazení lékařem opraveno (T-329) |
| Nastavení podkladu `/setup` | ✅ | ✅ | ✅ | |
| Detail pacienta `/dashboard/cases/3`, `/4`, demo | ✅ | ✅ | ✅ | |
| Závěr `/record` (přítomní a úkoly z popupu lékařů, zapisovatel, shrnutí) | ✅ | ✅ | ✅ (jen čtení) | výběr lékaře T-328 |
| Karta pacienta `/dashboard/patients/P03` (vložit zprávu) | ✅ | ✅ | ✅ | |
| Úkoly `/dashboard/tasks` (Moje / Všechny) | ✅ | ✅ | ✅ | |
| Tým `/dashboard/tym`, Záznam boardů `/dashboard/zaznamy` | ✅ | ✅ (hláška) | ✅ (hláška) | jen předseda |
| Okno projektoru `/projector`, úzké okno `/brief/3` | ✅ | ✅ | ✅ | nový vzhled T-330, pořadí T-332 |
| Ukončení boardu → stažení PDF / FHIR / ZIP | ✅ | — | — | T-333, testy backendu |

**Výsledek:** 19 obrazovek × 3 role se načte bez chyby konzole, pádu ani neočekávané HTTP chyby. Interakce (výběr lékaře v popupu, potvrzení závěru, moje úkoly, ukončení boardu a ZIP) jsou ověřené backendovými testy a dřívějším proklikáním nad mock API, tady znovu neproklikané. Backend 638 testů ✅, lint 0 chyb, tsc a `next build` OK.
**Neověřeno tady:** skutečné IRIS (Vector Search, transakce) a Gemini; ověřit na stroji s Dockerem (`dev.sh up`).

## Druhý průchod s interakcemi (17. 10. odpoledne, větev `astra-verifier` = `master` + T-331b, T-335, T-337)

Stejné prostředí (Django + paměťový FHIR s datasetem, `AI_PROVIDER=mock`), navíc **živá druhá AI na Azure**
(`gpt-6-1-sol-dz-eu`). Playwright proklikal celé toky, ne jen načtení obrazovek:

| Tok | Výsledek |
|---|---|
| Nový pacient z FHIR JSON (P07, P08, P01 + přepis `.md`, soubor se 2 pacienty) → návrh s náhledy → IRIS | ✅ |
| Zařazení: tlačítko zamčené, dokud není vše vyřešené (přeskočit, odkliknout, ECOG, C/P, snímek) | ✅ |
| Podklad (mock AI) + kontrola druhou AI na Azure: P08 10 tvrzení, P01 39 tvrzení | ✅ |
| Modrá kniha ČOS v podkladu (P01: kapitola 12), citace otevře oddíl a stránku PDF | ✅ |
| Citace ve všech sekcích detailu pacienta otevřou zdroj | ✅ po opravě (dřív jen rychlý přehled) |
| Jednání: pořadí agendy přetažením / Alt+↑↓ (předseda), chat dvou lékařů bez obnovení | ✅ |
| Okno projektoru podle zadávajícího lékaře (skrytá anamnéza a Hb, postupy nahoře) | ✅ |
| Závěr: výběr lékařů z popupu, úkol onkologovi, „Před potvrzením zbývá“, potvrzení → IRIS, úkol vidí onkolog | ✅ |
| Export PDF a FHIR document Bundle (50 záznamů), ukončení boardu, ZIP, záznam boardů | ✅ |
| Všechny obrazovky na 360 px bez vodorovného posouvání, světlý i tmavý režim | ✅ po opravě jednání a závěru |

**Neověřeno tady:** skutečné IRIS for Health (transakce, Vector Search s reálným embeddingem), hlavní LLM
NVIDIA / Gemini (bez klíče běží mock), nasazení (T-004, T-005, T-110, T-212).
