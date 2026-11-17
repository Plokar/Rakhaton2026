# Zadání: příprava MDTcore na použití (T-367 až T-378)

> Stav k 10. 11. 2026, větev `claude/gifted-cori-jryrib` (= `master` po T-366). Tento soubor je **jen zadání**.
> V kódu se při jeho přípravě nic nezměnilo. Implementuje jiný agent, kontrolu dělá autor zadání.

## 0. Pro agenta, který to implementuje

1. Drž [AGENTS.md](../AGENTS.md) a protokol v [PROGRESS.md](../PROGRESS.md) §1. Úkoly níže **nejsou** zatím
   v task boardu: nejdřív je tam zapiš (PROGRESS §4, jeden řádek na úkol, stav ⬜), pak teprve claim.
2. Pořadí: **T-367 jako první** (bez něj nejde nic ověřit v prohlížeči na stroji bez Dockeru), pak P0, P1, P2.
3. Jeden úkol = jeden commit `T-xxx: …` (malé kroky). Po každém úkolu: `pytest` jen dotčených modulů,
   `npx tsc --noEmit`, `npm run lint`. Na konci celé `pytest` a `npm run build`.
4. Kde zadání říká **„ověř“**, nejdřív zjisti skutečný stav. Když už to funguje, nic neměň a napiš to do Deníku.
5. Nedělej nic mimo tento seznam. Nápady navíc zapiš na konec tohoto souboru do oddílu „Další nápady“.
6. Změna kontraktu (T-369, T-375): nejdřív ARCHITEKTURA.md §6.3, ve stejném commitu jako kód, a `⚠️ KONTRAKT`
   v Deníku.

## 1. Co bylo ověřeno a jak

Prostředí bez Dockeru: Django (`settings_dev`) + lokální Postgres 16 a Redis, FHIR a IRIS SQL v paměti
(`services/fhir/testing.py`, `services/iris/testing.py`), `AI_PROVIDER=mock`, frontend `next dev`, Playwright.

| Co | Výsledek |
|---|---|
| Ingest + seed do paměťového FHIR | 4 740 záznamů, 40 zasedání, 166 případů, vektory (mock) v pořádku |
| 17 obrazovek za předsedu, 1440 px | načtou se, žádná výjimka JS, žádná chyba 5xx, žádné vodorovné posouvání |
| 9 obrazovek za chirurga (člen komise), 390 px | totéž |
| `npx tsc --noEmit` | bez chyb |
| `npm run lint` | 0 chyb, 28 varování (26× nepoužitá proměnná) |
| `pytest` (celé) | **nedoběhlo** během přípravy zadání (prvních ~200 testů zelených); spusť celé před začátkem |
| Skutečné IRIS, NVIDIA / Gemini, nasazení na VPS a Vercel | **neověřeno** (bez Dockeru a bez klíčů) |

Neproklikané toky (jen načtení obrazovek): generování podkladu, potvrzení závěru, exporty, pozvánka, chat.
Ty kryjí backendové testy a dřívější [AUDIT_FUNKCI.md](AUDIT_FUNKCI.md); T-378 je má pokrýt automaticky.

## 2. Nálezy (proč ty úkoly)

| # | Nález | Kde | Úkol |
|---|---|---|---|
| N1 | Bez Dockeru nejde aplikaci spustit jedním příkazem; ruční skript vznikl už potřetí | — | T-367 |
| N2 | Job generování, který běžel při restartu backendu, zůstane navždy `running`; UI na něj čeká | `apps/copilot/jobs.py:21` (přiznaný komentář) | T-368 |
| N3 | `/api/health/` hlásí `healthy`, i když IRIS neběží (kontroluje jen Postgres, Redis, disk) | `config/urls.py:40` | T-369 |
| N4 | Neexistuje záznam, kdo si kdy otevřel kterého pacienta nebo stáhl export | žádný model | T-370 |
| N5 | Zásady soukromí a Podmínky mají text šablony („Kanban“, „hackathon kód“) | `app/privacy/page.tsx`, `app/terms/page.tsx` | T-371 |
| N6 | Lišta cookies nabízí „analytické cookies“, žádná analytika v aplikaci není. Na mobilu zakrývá spodní třetinu obrazovky, na počítači položku „Okno pro projektor“ v postranním panelu | `components/cookies/*`, `app/layout.tsx:44` | T-371 |
| N7 | Přihlášení ukazuje „Nemáte účet? Zaregistrujte se“, přitom se účty zakládají jen pozvánkou | `app/login/page.tsx` | T-372 |
| N8 | Žádné odhlášení při nečinnosti (sdílené počítače na oddělení); refresh token drží přihlášení 7 dní | frontend | T-373 |
| N9 | Chybí `error.tsx` a `global-error.tsx`: pád komponenty = bílá stránka Next.js anglicky | `src/app/` | T-374 |
| N10 | Každý případ bez podkladu nebo závěru vyhodí v konzoli 404 (`GET …/brief/`, `…/decision/`); skutečné chyby se v tom ztrácí | `apps/mdt/views.py:739` | T-375 |
| N11 | Zasedání po termínu, které nikdo neukončil (P03, board 21. 10., 0 / 1 projednáno), vypadá stejně jako běžné | `components/mdt/SessionList.tsx` | T-376 |
| N12 | E-mail: funkce `send_hackathon_email`, výchozí odesílatel `noreply@hackathon.local`, SMTP výchozí `smtp.gmail.com` | `services/email_service.py:12`, `settings_prod.py` | T-371 |
| N13 | Sentry jen zakomentovaný; chyby v pilotu uvidí jen ten, kdo čte log na VPS | `settings_prod.py` (konec) | T-377 |
| N14 | CI nepouští žádný test v prohlížeči; každý audit se dělá ručně | `.github/workflows/ci.yml` | T-378 |

## 3. Úkoly

### P0: bez toho pilot nespouštět

#### T-367 · Lokální běh bez Dockeru
- **Co:** `WEB_Template/backend/scripts/run_local.py` a příkaz `./dev.sh local` (+ `dev.ps1 local`).
- **Jak:** skript nastaví env (`settings_dev`, `AI_PROVIDER=mock`, `VERIFIER_PROVIDER=off`, Postgres a Redis
  z env s výchozím `127.0.0.1`), po `django.setup()` nahradí `services.fhir.client.request` instancí
  `FakeFhirServer().request` a `services.iris.db.connect` instancí `FakeIris().connect`, pak ve **stejném procesu**
  zavolá `migrate`, `ingest_dataset`, `seed_mdt` a `runserver 0.0.0.0:8000 --noreload` (stav je v paměti, proto
  jeden proces a bez reloadu).
- **Pojistka:** skript odmítne běžet, když `DJANGO_SETTINGS_MODULE` není `config.settings_dev`.
- **Dokumentace:** krátký oddíl v `WEB_Template/README.md` a řádek v AGENTS.md → Příkazy.
- **DoD:** na čistém stroji s Postgres + Redis `./dev.sh local` → `GET /api/health/` 200, přihlášení `predseda`,
  kalendář ukáže zasedání. Výpis končí počtem záznamů FHIR (dnes 4 740).

#### T-368 · Zaseknuté joby generování
- **Co:** job nesmí zůstat `queued` / `running` navždy.
- **Jak:**
  1. `apps/copilot/jobs.py`: funkce `fail_stale(max_age_minutes=15)`: joby ve stavu `queued` / `running`
     s `updated_at` starším než limit → `status='error'`, `error='Generování přerušil restart serveru. Spusťte ho znovu.'`
  2. Volat ji při čtení stavu jobu (`GET /api/jobs/{id}/`) a před založením nového jobu pro stejný případ.
     Limit z `settings.MDT_JOB_TIMEOUT_MINUTES` (výchozí 15).
  3. `progress()` už `updated_at` neposouvá (`.update()` obchází `auto_now`): do obou `update(...)` v `run`
     přidej `updated_at=timezone.now()`.
  4. Frontend: **ověř**, že stav `error` ukáže hlášku z `error` a tlačítko pro nové spuštění; když ne, doplň.
- **Testy:** `apps/copilot/test_jobs.py`: starý `running` job → po čtení `error`; čerstvý `running` zůstane.
- **DoD:** testy zelené; ručně: job v DB posunutý o 20 min zpět se v UI ukáže jako chyba s možností opakovat.

#### T-369 · Health check zná IRIS ⚠️ KONTRAKT
- **Co:** `config/urls.py:health_check` přidá `checks['iris_fhir']` (`GET metadata` přes `services.fhir.client`,
  timeout 3 s) a `checks['iris_sql']` (`services.iris.db.connect`, `SELECT 1`, spojení **vždy zavřít**).
  Obojí jen když je nastavené `IRIS_HOST`; jinak `'skipped'` (a `skipped` se nepočítá jako chyba).
- **Stavový kód:** výchozí odpověď zůstává 200 i při `degraded` (healthcheck Dockeru nesmí shazovat backend kvůli
  IRIS). Nový parametr `?strict=1` vrátí při `degraded` **503**; ten je pro externí monitoring.
- **Výkon:** výsledek kontrol IRIS drž v cache 20 s, monitoring nesmí vyčerpat limit spojení Community Edition.
- **Verze:** `version` čti z env `APP_VERSION` (výchozí `dev`), ne natvrdo `2.0.0`.
- **Dokumentace:** ARCH §6.3, `docs/PILOT.md` §2 (monitoring hlídá `/api/health/?strict=1`).
- **Testy:** IRIS dole → 200 + `degraded`; se `strict=1` → 503; bez `IRIS_HOST` → `healthy`.

#### T-370 · Záznam přístupů k pacientům
- **Co:** model `AccessLog` v `apps/mdt/models.py`: `user` (FK, `SET_NULL`), `username` (kopie textem),
  `patient_fhir_id`, `case` (FK, null, `SET_NULL`), `action` (`view` / `export` / `write` / `ai`), `path`,
  `method`, `status_code`, `ip`, `created_at` (index). Záznamy se neupravují ani nemažou z UI.
- **Jak:** middleware v `apps/mdt/` (za autentizací), který po odpovědi zapíše jeden řádek pro požadavky pod
  `/api/mdt/cases/{cid}/…`, `/api/mdt/patients/{pid}/…`, `/api/patients/…` a exporty
  (`export.pdf`, `export.fhir.json`, `sessions/{sid}/export.zip`). ID pacienta ber z URL (`resolver_match.kwargs`),
  u případu z `MdtCase`. Opakované čtení stejného pacienta stejným uživatelem do 5 min slouč (jinak polling
  zahltí tabulku): `view` loguj nejvýš jednou za 5 min na dvojici uživatel + pacient, `export`, `write` a `ai` vždy.
  Zápis nesmí shodit požadavek (chybu jen zaloguj).
- **Bez osobních údajů:** žádné jméno, RČ ani tělo požadavku; hledání podle RČ loguj jen jako `action='view'`
  s `patient_fhir_id` nalezeného pacienta, hledaný výraz ne.
- **Zobrazení:** Django admin jen pro čtení (filtry uživatel, pacient, akce, datum) a endpoint
  `GET /api/mdt/access-log/?patient=&user=&from=&to=` jen pro `mdt_manager`. Záložka „Přístupy“ v
  `/dashboard/tym` (tabulka, filtr podle pacienta a lékaře, stránkování po 50).
- **Dokumentace:** ARCH §6.2 (model), §6.3 (endpoint), `docs/PILOT.md` §6 (kde to správce najde). ⚠️ KONTRAKT.
- **Testy:** otevření detailu případu vytvoří 1 řádek; druhé do 5 min žádný; export vždy; lékař bez role správce
  dostane na endpointu 403; externí lékař se v logu objeví i při odmítnutí (403).

#### T-371 · Texty a zbytky šablony
- **Zásady soukromí** (`app/privacy/page.tsx`) a **Podmínky** (`app/terms/page.tsx`): přepsat pro MDTcore v pilotu.
  Obsah vezmi z `docs/PILOT.md` §1 a §5: jen fiktivní pacienti, není zdravotnický prostředek, výstupy AI nejsou
  podkladem pro léčbu, AI běží u poskytovatele (NVIDIA, přepis Groq) jen nad syntetickými daty, jaké údaje účtu
  se ukládají (jméno, e-mail, odbornost, nemocnice, záznam přístupů z T-370), kontakt = koordinátor pilotu
  (z `NEXT_PUBLIC_PILOT_FEEDBACK_URL`). Žádný „Kanban“, „projekty“, „hackathon kód“. Nevymýšlej název provozovatele
  ani adresu: kde údaj chybí, napiš „doplní provozovatel pilotu“ a vypiš ta místa do Deníku.
- **Cookies:** aplikace používá jen nezbytné cookies (přihlášení, CSRF) a `localStorage` pro vzhled. Lištu
  `CookieConsentBanner` z `app/layout.tsx` odstraň, v Zásadách soukromí nech oddíl „Cookies“ s výčtem. Komponenty
  `components/cookies/*`, `contexts/CookieContext.tsx`, `lib/cookies.ts`, `types/cookies.ts` smaž, pokud je po
  odstranění lišty nic dalšího nepoužívá (ověř `grep`); jinak je nech.
- **E-mail:** `send_hackathon_email` → `send_email` (uprav všechna volání), výchozí odesílatel z
  `DEFAULT_FROM_EMAIL` bez záložního `hackathon.local`. V `settings_prod.py` nesmí být výchozí `smtp.gmail.com`:
  když `EMAIL_HOST` chybí, použij `django.core.mail.backends.console.EmailBackend` a do logu při startu varování
  „E-maily se neodesílají (EMAIL_HOST není nastaven), pozvánky předávejte odkazem.“
- **Ověř:** dialog pozvánky při `email_sent=false` jasně říká, že e-mail neodešel a odkaz je třeba zkopírovat
  (`components/mdt/team/InviteDoctorDialog.tsx:43`). Když to neříká, doplň.
- **DoD:** `grep -rniE "kanban|hackathon" WEB_Template/frontend/src WEB_Template/backend/services WEB_Template/backend/apps`
  vrací jen komentáře o původu dat („syntetická data hackathonu“ na přihlášení smí zůstat) a skryté moduly šablony.

### P1: výrazně zlepší použití

#### T-372 · Přihlášení bez odkazu na registraci
- **Co:** odkaz „Nemáte účet? Zaregistrujte se“ na `/login` ukaž jen když je registrace povolená. Jinak text
  „Účet vám založí správce MDT pozvánkou.“
- **Jak:** **ověř**, jestli backend stav registrace vrací (např. v `/api/auth/status/`). Když ne, přidej tam pole
  `registration_enabled` (z `MDT_ALLOW_REGISTRATION`; v dev `True`). Frontend se řídí tímto polem, ne jen
  `NEXT_PUBLIC_PILOT_MODE`.
- **DoD:** se `settings_prod` odkaz není, v dev je; test endpointu.

#### T-373 · Odhlášení při nečinnosti
- **Co:** po `NEXT_PUBLIC_IDLE_MINUTES` (výchozí 30) bez myši, klávesnice a dotyku dialog „Budete odhlášeni za
  60 s“ s tlačítkem „Zůstat přihlášen“, pak odhlášení a přesměrování na `/login?next=…`.
- **Výjimky:** `/projector`, `/brief/[caseId]` a obrazovka jednání, dokud je zasedání živé (promítá se celé
  zasedání bez dotyku). Aktivita v jedné záložce platí pro všechny (`BroadcastChannel` nebo `localStorage`).
- **Kde:** jeden hook `src/hooks/useIdleLogout.ts`, zapojený v `app/dashboard/layout.tsx`.
- **Rozepsaný text nesmí zmizet:** **ověř**, že závěr komise má draft uložený (tlačítko „Uložit draft“ existuje);
  před odhlášením draft ulož, nebo odhlášení na `/record` s neuloženými změnami odlož a ukaž jen dialog.
- **DoD:** Playwright s `NEXT_PUBLIC_IDLE_MINUTES=1`: po minutě dialog, po další odhlášení; na `/projector` nic.

#### T-374 · Chybové stránky
- **Co:** `src/app/error.tsx`, `src/app/global-error.tsx`, `src/app/dashboard/error.tsx`: česky „Něco se
  pokazilo“, tlačítka „Zkusit znovu“ (`reset()`) a „Zpět na přehled“, v pilotu odkaz „Nahlásit problém“
  (`NEXT_PUBLIC_PILOT_FEEDBACK_URL`). Bez technických detailů; `error.digest` malým písmem pro hlášení.
- **Pozor:** před psaním přečti `WEB_Template/frontend/AGENTS.md` (Next 16).
- **DoD:** uměle vyhozená chyba v komponentě detailu ukáže tuto stránku se shellem aplikace, ne bílou stránku.

#### T-375 · Konec 404 u chybějícího podkladu a závěru ⚠️ KONTRAKT
- **Co:** `GET /api/mdt/cases/{cid}/brief/` a `…/decision/` vrací při neexistujícím záznamu **204 No Content**
  místo 404. 404 zůstává jen pro neexistující případ.
- **Jak:** backend `apps/mdt/views.py` (`case_brief` ř. 739 a obdobně závěr). Frontend: všechna místa, která dnes
  berou 404 jako „ještě není“ (`src/lib/queries.ts`, `src/lib/api.ts`, `grep -rn "404" src`), přepni na 204;
  `api.ts` musí u 204 vracet `null` a neparsovat JSON.
- **Dokumentace:** ARCH §6.3; testy, které čekají 404, uprav.
- **DoD:** průchod `/dashboard/mdt/2`, `/dashboard/cases/3`, `/dashboard/cases/3/record`, `/brief/3` bez jediné
  chyby v konzoli prohlížeče.

#### T-376 · Zasedání po termínu
- **Co:** zasedání s datem v minulosti (víc než 12 h) a stavem jiným než `closed` označ „neukončeno“.
- **Kde:**
  - `components/mdt/SessionList.tsx`: nad „Nadcházející“ oddíl „Čeká na ukončení (n)“ (jen když n > 0), řádek
    s oranžovým štítkem a počtem neprojednaných pacientů.
  - Jednání takového zasedání: předsedovi pruh „Zasedání proběhlo 21. 10. a není ukončené. Neprojednaní pacienti:
    P03.“ s akcemi **Přesunout neprojednané na další zasedání** (stejná komise, nejbližší termín; **ověř**, že
    přesun případu už API umí, seed s ním počítá) a **Ukončit board** (existující akce).
- **Nic nedělej automaticky:** žádné samočinné ukončení ani přesun, vždy klik předsedy.
- **DoD:** seed má takové zasedání (GIT, 21. 10.); v seznamu je v novém oddílu, pruh se ukáže jen předsedovi.

#### T-377 · Hlášení chyb (volitelné, zapíná se env)
- **Co:** když je nastavené `SENTRY_DSN`, backend inicializuje `sentry-sdk` (`send_default_pii=False`,
  `traces_sample_rate=0`). Před odesláním (`before_send`) odstraň tělo požadavku, cookies, hlavičky a query string;
  v URL nech cestu (obsahuje jen `Pxx` a čísla případů).
- **Bez DSN se nic neimportuje** a nic neodchází ven. `sentry-sdk` do `requirements.txt`.
- **Frontend:** nic (žádný klíč ani SDK ve frontendu); chyby z prohlížeče řeší T-374 a odkaz na hlášení.
- **Dokumentace:** `.env.prod.example`, `docs/PILOT.md` §2.
- **Testy:** `before_send` nad ukázkovou událostí nevrátí tělo, cookies ani query.

### P2: údržba a jistota

#### T-378 · Test v prohlížeči v CI
- **Co:** `WEB_Template/frontend/e2e/smoke.spec.ts` (Playwright) proti `run_local.py` z T-367 a `next build && next start`.
- **Scénář (jeden test, předseda):** přihlášení → kalendář má aspoň jedno zasedání → `/dashboard/mdt/2` →
  detail případu → spustit generování podkladu (mock) a počkat na hotovo → otevřít citaci → `/record`: zvolit
  záměr, uložit draft → `/dashboard/tasks` → `/dashboard/tym` → `/projector` se načte.
  Po celou dobu: žádná `pageerror`, žádná odpověď 5xx, žádná chyba konzole (po T-375 ani 404).
- **Druhý test (člen komise, 390 px):** kalendář, jednání, detail, `/dashboard/live`; žádné vodorovné posouvání
  (`scrollWidth <= innerWidth`).
- **CI:** nový job `e2e` v `.github/workflows/ci.yml` (služby postgres + redis jako u `backend`), `--trace off`,
  při selhání nahraj snímky jako artefakt. Playwright jen jako `devDependency`.
- **Úklid ve stejném úkolu:** 28 varování lintu na 0 (26× `no-unused-vars`: smazat nepoužité; `avatar.tsx`:
  `alt` a případně výjimka pro `<img>` s komentářem proč).
- **DoD:** job `e2e` zelený na PR; `npm run lint` bez varování.

## 4. Co zůstává na lidech (agent to neudělá)

- **Nasazení:** T-004 (Vercel), T-110 a T-212 (VPS, ingest, smoke test) podle `docs/UKOL_VPS_CLAUDE.md`. Vyžaduje
  přístup na VPS a do Vercelu.
- **Go / no-go seznam** v `docs/PILOT.md` §2 (hesla, zálohy a jedna vyzkoušená obnova, monitoring, účty lékařů).
- **Skutečné IRIS a skutečná AI:** jeden průchod s Dockerem (`./dev.sh up`) a klíčem NVIDIA nad syntetickými daty.
- **Kontrola na skutečném projektoru** (T-310) a nácvik dema (T-401).
- **Údaje provozovatele** do Zásad soukromí a Podmínek (T-371 nechá označená místa).

## 5. Jak se bude kontrolovat

Ke každému úkolu: (1) DoD výše, (2) `pytest`, `tsc`, `lint`, `build` zelené, (3) průchod T-378 lokálně,
(4) řádek v Deníku a stav ✅ v task boardu, (5) u T-369, T-370, T-375 změna v ARCHITEKTURA.md ve stejném commitu.
Kontrola navíc projde: že `AccessLog` neobsahuje osobní údaje, že health check zavírá spojení do IRIS, že
odhlášení při nečinnosti nepřeruší promítání a že se nic z podkladu neztratilo (D-019).

## Další nápady (nezadáno, jen k rozhodnutí)

- Počet mých otevřených úkolů jako odznak u položky „Úkoly“ v postranním panelu.
- E-mail zadávajícímu lékaři den před zasedáním, když kontrola neproběhla (dnes je to jen pruh v aplikaci).
- Dvoufázové přihlášení pro roli správce MDT.
- Fronta jobů mimo proces (RQ nad existujícím Redisem), až bude víc než jeden worker backendu.
