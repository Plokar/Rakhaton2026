# Úkol pro Claude na VPS serveru

> **Jak spustit:** na VPS v kořeni checkoutu repa spusť `claude` a napiš:
> „Přečti `docs/UKOL_VPS_CLAUDE.md` a udělej všechny úkoly v pořadí. Ptej se mě jen u kroků označených 🛑.“
>
> Zadal @Maty (9. 11. 2026). Platí `AGENTS.md` (pravidla repa) a `PROGRESS.md` (Deník na konci každého úkolu).

## Kontext

- Produkce: frontend Next.js na **Vercelu**, backend Django + Postgres + Redis + IRIS for Health na **této VPS**
  (`WEB_Template/docker-compose.yml`, D-001). Vercel posílá `/api/*` na backend přes `rewrites` (`BACKEND_URL`).
- **Problém:** přihlášení na produkci hlásí „Server vrátil chybu 500“. Na aktuálním `master` přihlášení lokálně
  funguje (ověřeno 9. 11.: `POST /api/auth/token/` → 200, `/api/health/` → 200, žádná chybějící migrace).
  Chyba je tedy skoro jistě v provozu: backend neběží nebo padá, je nedostupný z Vercelu, chybí migrace nebo je
  špatně `BACKEND_URL`.
- Demo účty (`apps/mdt/roles.py`, `seed_mdt`): `predseda`, `onkolog`, `pneumolog`, `onkolog-git`, `paliatr`,
  `chirurg`, `radiolog`, `patolog`, `radioterapeut`. Heslo: `MDT_DEMO_PASSWORD` z `.env` (výchozí `demo123456`).

## Pravidla pro práci na serveru

- **Nic nemaž** (volumes, databáze, IRIS data) bez 🛑 potvrzení. `docker compose down -v` je zakázané.
- Před změnou `.env` udělej zálohu: `cp .env .env.bak-$(date +%F-%H%M)`. Secrets nikdy necommituj ani nevypisuj do chatu.
- Kód měň v repu, commituj `T-xxx: …` a pushuj do `master` (`git pull --rebase origin master` před push).
  Změny jen na serveru bez commitu nedělej, další `git pull` by je přepsal.
- LLM na serveru jen nad syntetickými daty (D-021). Testy vždy s `AI_PROVIDER=mock`.

---

## Úkol 1: oprav chybu 500 při přihlášení (priorita)

1. Stav:
   ```bash
   cd WEB_Template && git -C .. pull --rebase origin master
   docker compose ps
   docker compose logs --tail 200 backend
   docker compose exec backend curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/health/   # port 8000 je jen uvnitř sítě (Traefik)
   ```
2. Podle logu oprav příčinu. Typické případy:
   - kontejner `backend` restartuje → chyba v logu (import, chybějící env, CRLF v `entrypoint.sh`), oprav a `docker compose up -d --build backend`;
   - neproběhlé migrace → `docker compose exec backend python manage.py migrate`;
   - Postgres / Redis / IRIS neběží → `docker compose up -d db redis iris` a zkontroluj healthcheck;
   - backend běží, ale zvenku nedostupný → Traefik (`traefik/`), firewall, certifikát; ověř `curl https://<doména backendu>/api/health/` z jiného stroje.
3. Ověř přihlášení přímo na backend:
   ```bash
   docker compose exec backend curl -s -X POST http://localhost:8000/api/auth/token/ -H 'Content-Type: application/json' \
     -d '{"username":"predseda","password":"<MDT_DEMO_PASSWORD>"}' | head -c 200
   ```
   Pokud účty chybí: `docker compose exec backend python manage.py seed_mdt`.
4. 🛑 Pokud je chyba v `BACKEND_URL` na Vercelu, napiš uživateli přesnou hodnotu, kterou má nastavit
   (Vercel → Project → Settings → Environment Variables), a po redeployi ověř přihlášení přes doménu frontendu.
5. **Hotovo:** přihlášení `predseda` na produkční doméně projde, `/dashboard` se načte bez 5xx.

## Úkol 2: 100 nových demo pacientů

1. Rozšiř generátor `data/demo_pacienti/generate.py` (styl druhé vlny přes `pt()`, T-351) o **100 pacientů
   P73–P172**. Rozlož je do stávajících 10 komisí a na termíny zasedání od 10. 11. do 18. 12. 2026
   (doplň zasedání v `seed_mdt`, ať má každé 4–8 případů).
2. Pestrost: všechny diagnózy z katalogu (`data/onko/q.py`), různá stadia, ECOG 0–3, záměr C i P. Zhruba
   pětina pacientů má záměrně mezery (chybí PROMs, preference, laboratoř) a desetina „nové výsledky“ po zařazení.
3. **Data jsou fiktivní** (D-021): žádná skutečná jména ani rodná čísla. Pro úkol 3 dostane každý pacient:
   - jméno ve tvaru `Jméno Příjmení (fiktivní)` ze seznamu běžných českých jmen,
   - fiktivní RČ: formálně platné (datum narození podle věku a pohlaví, u žen +50 k měsíci, dělitelné 11), ale
     z vymyšleného rozsahu. `identifier.system` = `https://rakathon.example.org/fhir/sid/rc-fiktivni`.
4. Vygeneruj, nahraj a ověř:
   ```bash
   python3 data/demo_pacienti/generate.py
   cd WEB_Template && docker compose exec backend python manage.py ingest_dataset --skip-vectors
   docker compose exec backend python manage.py seed_mdt
   ```
   Vektory pusť zvlášť (`ingest_dataset` bez `--skip-vectors`) až po ověření, že FHIR část prošla.
5. Testy kohorty (`apps/copilot` / `services/tests`, podle T-347/T-351) uprav na nový počet, backend testy zelené.
6. Aktualizuj `data/demo_pacienti/README.md` (rozsah P13–P172, počty komisí a zasedání).

## Úkol 3: přidání pacienta podle rodného čísla nebo jména

Dnes se pacient do zasedání přidává výběrem ze seznamu `Pxx` (`components/mdt/AddPatientSheet.tsx`,
`usePatientsQuery`). Nově má jít pacienta najít podle **rodného čísla** i **jména**.

1. **Kontrakt nejdřív** (AGENTS.md): do ARCHITEKTURA §6.3 přidej hledání `GET /api/patients/?q=<text>`. `q`
   bere RČ s lomítkem i bez (`655315/1234` = `6553151234`), část jména bez ohledu na diakritiku a velikost
   písmen, nebo `Pxx`. Výsledek je nejvýš 20 pacientů. Zapiš to do Deníku jako `⚠️ KONTRAKT`.
2. **Backend:** hledání ve FHIR přes IRIS (`Patient?identifier=…`, `Patient?name=…`). Neznámé search
   parametry IRIS tiše ignoruje, proto filtr ověř testem, který vrátí jen správného pacienta. Testy s mock IRIS.
3. **Frontend** (`AddPatientSheet`): jedno pole „Rodné číslo, jméno nebo Pxx“. RČ se formátuje při psaní
   (`XXXXXX/XXXX`) a validuje (délka, dělitelnost 11, datum). U výsledku je jméno a RČ, aby lékař ověřil, že
   přidává správného člověka.
4. **Ochrana údajů zůstává (D-018):** jméno a RČ se ukážou **jen v dialogu přidání**. Hlavička případu,
   projektor, podklad, chat i export dál ukazují `Pxx · pohlaví · věk`. RČ nesmí do logů, URL ani do
   promptu LLM (hledání posílej v těle POST nebo jako query bez logování; zkontroluj `LOGGING`).
5. Lint, `tsc`, backend testy a build zelené. Ověř v prohlížeči: přidání pacienta podle RČ i podle jména.

## Na konci

- `docker compose ps` bez restartujících kontejnerů, `/api/health/` → 200, přihlášení na produkci funguje.
- Do `PROGRESS.md` zapiš úkoly (T-353 provoz VPS, T-354 100 pacientů, T-355 hledání podle RČ / jména) a jeden
  řádek do Deníku za každý.
- Uživateli napiš krátké shrnutí: co bylo špatně, co se změnilo, co zbývá.
