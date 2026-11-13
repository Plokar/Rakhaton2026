# Pilotní provoz MDTcore

> Stav: připraveno k nasazení (T-355, 9. 11. 2026). Nasazení na VPS dělá Claude podle
> [UKOL_VPS_CLAUDE.md](UKOL_VPS_CLAUDE.md), úkol 4.

## 1. Co pilot je a co není

- **Je:** lékaři onkologických komisí zkoušejí MDTcore na **fiktivních pacientech** (P01–P72, později P73–P172)
  a říkají nám, co jim pomáhá, co chybí a co je špatně.
- **Není:** péče o skutečné pacienty. MDTcore v pilotu **není zdravotnický prostředek** a jeho výstupy se
  **nepoužívají k rozhodování o léčbě**. Do aplikace se nezadávají ani nenahrávají skutečné údaje pacientů
  (jména, rodná čísla, zprávy). Aplikace to připomíná pruhem „Pilotní provoz“ a u zakládání pacienta.
- AI v pilotu běží na free tieru NVIDIA (D-021): smí jen nad syntetickými daty. I kdyby se do aplikace dostal
  skutečný pacient (bez tagu `fiktivni-data`), jeho data do LLM neodejdou (`AI_REAL_PATIENT_DATA=False`).

Ostrý provoz se skutečnými pacienty je samostatný projekt: AI v EU s DPA (Vertex AI EU), DPIA, klasifikace podle
AI Act, souhlas etické komise a smlouva s nemocnicí. Nic z toho pilot nenahrazuje.

## 2. Kontrola před spuštěním (go / no-go)

Pilot se spustí, až je všechno zaškrtnuté. Ověřuje koordinátor pilotu.

**Bezpečnost**
- [ ] `DJANGO_SECRET_KEY` náhodný, aspoň 50 znaků (jinak backend nenaběhne).
- [ ] `MDT_DEMO_PASSWORD` vlastní, aspoň 12 znaků, a hesla už založených demo účtů změněná
      (`seed_mdt --reset-demo-passwords`).
- [ ] `IRIS_PASSWORD`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD` nejsou výchozí.
- [ ] Vercel: `NEXT_PUBLIC_PILOT_MODE=true` (žádné 1-click demo účty), `NEXT_PUBLIC_PILOT_FEEDBACK_URL` vyplněné,
      **ne** `NEXT_PUBLIC_DEMO_PASSWORD`.
- [ ] `AI_REAL_PATIENT_DATA=False`.
- [ ] Samoregistrace vypnutá: `MDT_ALLOW_REGISTRATION` nenastavené nebo `False` (registrovaný účet by viděl
      všechny pacienty). `/register` v pilotu jen odkáže na koordinátora.
- [ ] Portál IRIS (52773) a Postgres nejsou dostupné z internetu (jen `127.0.0.1` / síť Dockeru).

**Provoz**
- [ ] `https://<API_DOMAIN>/api/health/` → 200, přihlášení na produkční doméně projde.
- [ ] Denní záloha běží (`scripts/backup.sh` v cronu) a jedna obnova je vyzkoušená (§6).
- [ ] Volitelně `SENTRY_DSN` (hlášení chyb backendu; bez těla požadavků, cookies a query, `core/monitoring.py`).
- [ ] Monitoring dostupnosti hlídá `/api/health/?strict=1` (503 i při výpadku IRIS) a frontend (např. UptimeRobot,
      každých 5 min, e-mail koordinátorovi).

**Lidé a data**
- [ ] Každý lékař pilotu má **vlastní účet** (Tým → Přidat lékaře): jméno, odbornost, role. Sdílené demo účty
      jen pro koordinátora.
- [ ] Zasedání a pacienti pro pilot jsou připravení (`seed_mdt`), termíny odpovídají plánu pilotu.
- [ ] Lékaři dostali tento dokument (§3–§5) a kontakt na koordinátora.

## 3. Pro lékaře: jak se zapojit

1. Přihlaste se účtem od koordinátora a hned si v Nastavení změňte heslo.
2. Projděte aspoň jednou celý postup (§4) na pacientovi svého zasedání.
3. Co vás zarazí, nahlaste hned odkazem **Nahlásit problém nebo nápad** v pruhu nahoře. Stačí pár vět.

Co uvést do hlášení: pacient (`Pxx`), obrazovka, co jste dělali, co jste čekali a co se stalo. Snímek obrazovky
pomůže. Žádné skutečné údaje pacientů.

## 4. Scénáře k vyzkoušení

| # | Kdo | Scénář | Na co se díváme |
|---|-----|--------|-----------------|
| 1 | zadávající lékař | Zařadit pacienta na zasedání, doplnit chybějící údaje, ECOG a záměr C/P | Je jasné, co chybí? Kolik to trvá? |
| 2 | zadávající lékař | Kontrola před zasedáním: co přibylo od zařazení | Všiml jsem si nových výsledků? |
| 3 | předseda | Podklad: přehled za 30 s, varovné signály, citace (klik na zdroj) | Odpovídá podklad dokumentaci? Je něco špatně citované? |
| 4 | předseda | Jednání: okno projektoru, přepínání pacientů, chat a chatbot | Čte se projektor z dálky? Chybí tam něco důležitého? |
| 5 | předseda | Závěr komise: zvolit postup, záměr, úkoly, potvrdit | Odpovídá zápis tomu, jak komise opravdu rozhoduje? |
| 6 | všichni | Úkoly po zasedání, záznam boardu | Ví každý, co má udělat? |
| 7 | radiolog / patolog | Detail případu, „Pro vás“, odbornosti | Vidím to, co potřebuji pro svou odbornost? |

Každé tvrzení AI má citaci. Neověřené tvrzení je žluté a označené „Neověřeno“. Barvy léčebných postupů počítají
pravidla, ne AI, a šedá („nelze posoudit“) znamená, že k pravidlu chybí údaj.

## 5. Známá omezení pilotu

- AI se může mýlit. Proto má každé tvrzení citaci a nic se nestane záznamem bez potvrzení lékařem.
- Free tier AI má limity: generování podkladu může trvat desítky sekund, ve špičce i déle.
- Přepis diskuse (AI zapisovatel) jen se souhlasem všech přítomných a jen nad fiktivním případem.
- Aplikace je optimalizovaná pro počítač a projektor; mobil umí čtení a jednání, ne celé zakládání pacienta.

## 6. Provoz (pro správce VPS)

**Zálohy.** `WEB_Template/scripts/backup.sh` zálohuje Postgres (`pg_dump`) a IRIS (ExternalFreeze → kopie
`/durable` → ExternalThaw, zmrazení zápisů trvá kolem minuty). Výchozí cíl `/var/backups/mdtcore`, drží 14 dní.

```bash
crontab -e   # 15 3 * * * cd /cesta/k/repu/WEB_Template && scripts/backup.sh >> /var/log/mdtcore-backup.log 2>&1
```

**Obnova ze zálohy** (vyzkoušet jednou před spuštěním pilotu):

```bash
cd WEB_Template && Z=/var/backups/mdtcore/<datum>
(cd "$Z" && sha256sum -c SHA256SUMS)
docker compose stop backend iris
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$Z/postgres.dump"
docker run --rm --volumes-from "$(docker compose ps -aq iris)" -v "$Z:/backup" alpine \
  sh -c 'rm -rf /durable/* && tar xzf /backup/iris_durable.tgz -C /'
docker compose up -d iris backend
```

**Aktualizace během pilotu:** jen po domluvě s koordinátorem, mimo termíny zasedání. Před aktualizací záloha,
po ní `/api/health/` a přihlášení.

**Záznam přístupů:** kdo kdy otevřel kterého pacienta, stáhl export nebo zapsal, vidí správce MDT v aplikaci (Tým a
účty → Přístupy) a v Django adminu (MDT → Access logs, jen pro čtení). Ukládají se jen ID pacientů (Pxx), ne jména.

**Hlášení chyb:** odkaz v aplikaci → koordinátor → záznam do Blokerů v [PROGRESS.md](../PROGRESS.md) nebo úkol na
task boardu.

## 7. Konec pilotu

- Vyhodnocení: počet projednaných pacientů, čas přípravy podkladu, hlášené chyby a nápady, rozhovory s lékaři.
- Účty lékařů deaktivovat (Django admin → Users → Active), zálohy smazat podle dohody.
