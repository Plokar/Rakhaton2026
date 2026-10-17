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

**Výsledek:** 19 obrazovek × 3 role bez chyby konzole, pádu ani neočekávané HTTP chyby. Backend 638 testů ✅, lint 0 chyb, tsc a `next build` OK.
**Neověřeno tady:** skutečné IRIS (Vector Search, transakce) a Gemini; ověřit na stroji s Dockerem (`dev.sh up`).
