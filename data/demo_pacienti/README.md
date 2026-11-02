# Demo pacienti P13–P72

Šedesát fiktivních pacientů pro 10 komisí s 24 zasedáními od 3. 11. do 4. 12. 2026, ve formátu datasetu Asseco (`pacienti/Pxx/Pxx_bundle.json`,
bundle `collection`, tag `fiktivni-data`). `ingest_dataset` je nahraje do IRIS spolu s datasetem
(env `DEMO_DATASET_DIR`, v Dockeru `/data/demo_pacienti`; vypnutí `DEMO_DATASET_DIR=off` nebo `--no-demo`)
a `seed_mdt` z jejich nominací založí zasedání. Jen pro demo, nikdy pro péči o pacienty. Dataset se nemění.

```bash
python data/demo_pacienti/generate.py      # znovu vygeneruje bundly (data jsou v PATIENTS v generate.py)
```

| Termín | Komise | Pacienti | Zadává |
|---|---|---|---|
| út 3. 11. 14:00 | Hrudní – karcinom plic | P13 NSCLC IIIA N2, P14 EGFR+ IA3, P15 SCC IIIA (74 let, CHOPN) | pneumolog |
| st 4. 11. 14:00 | Mamární komise | P17 TNBC, P18 lobulární po mastektomii, P19 HER2+ s hraniční LVEF | onkolog |
| čt 5. 11. 14:00 | GIT – kolorektální karcinom / hepatobiliární | P21 kolon pN2a, P22 dMMR rektum, P23 sigma M1 RAS wt | onkolog-git |
| pá 6. 11. 13:00 | Gynekoonkologická komise | P25 ovarium BRCA2, P26 endometrium dMMR, P27 cervix IIB | onkolog |
| po 9. 11. 14:00 | Uroonkologická komise | P28 prostata high-risk, P29 ledvina M1, P30 močový měchýř cT2 | onkolog |
| út 10. 11. 14:00 | Hrudní – karcinom plic | P16 ALK+ s mozkovými metastázami | pneumolog |
| st 11. 11. 13:30 | Komise nádorů hlavy a krku | P31 orofarynx HPV+, P32 hlasivka cT3 | onkolog |
| st 18. 11. 14:00 | Mamární komise | P20 HR+ progrese, PIK3CA | onkolog |
| čt 19. 11. 14:00 | GIT – kolorektální karcinom / hepatobiliární | P24 pankreas hraničně resekabilní | onkolog-git |

Druhá vlna (T-351, `pt()` v `generate.py`): data jsou zadaná k 4. 11. a posunou se k termínu zasedání (`shift`), aby
nominace, vyšetření a laboratoř byly vždy čerstvé.

| Termín | Komise | Pacienti |
|---|---|---|
| čt 12. 11. 13:00 | Neuroonkologická komise | P33 glioblastom, P34 oligodendrogliom, P35 metastáza ledviny v mozečku |
| čt 12. 11. 14:00 | GIT | P39 GEJ adenokarcinom, P40 HCC BCLC B |
| pá 13. 11. 13:00 | Hematoonkologická komise | P36 DLBCL, P37 Hodgkinův lymfom, P38 myelom |
| po 16. 11. 13:00 | Komise pro melanom a kožní nádory | P44 melanom IIIB BRAF+, P45 melanom M1c, P46 Merkelův karcinom |
| út 17. 11. 14:00 | Hrudní | P41 NSCLC PD-L1 80 %, P42 SCC IIIB, P43 mezoteliom |
| st 18. 11. 14:00 | Mamární | P50 HER2+ po pCR, P51 reziduum gBRCA2 |
| čt 19. 11. 14:00 | GIT | P52 cékum BRAF V600E s peritoneálními metastázami |
| pá 20. 11. 13:00 | Komise pro sarkomy a GIST | P47 liposarkom retroperitonea, P48 GIST žaludku, P49 osteosarkom |
| po 23. 11. 14:00 | Uroonkologická | P53 germinální nádor varlete, P54 mCRPC BRCA2, P55 uroteliální M1 |
| út 24. 11. 14:00 | Hrudní | P56 EGFR L858R, P57 SCLC extenzivní |
| st 25. 11. 13:30 | Hlava a krk | P63 jazyk, P64 nosohltan EBV+ |
| čt 26. 11. 13:00 | Neuroonkologická | P61 glioblastom 71 let, P62 astrocytom grade 3 |
| pá 27. 11. 13:00 | Gynekoonkologická | P58 ovarium relaps, P59 recidiva cervixu, P60 vulva |
| po 30. 11. 13:00 | Hematoonkologická | P65 folikulární lymfom, P66 CLL del(17p) |
| st 2. 12. 14:00 | Mamární | P67 ER+ 82 let, P68 karcinom prsu u muže |
| čt 3. 12. 14:00 | GIT | P69 cholangiokarcinom FGFR2, P70 jícen SCC |
| pá 4. 12. 13:00 | Komise pro melanom a kožní nádory | P71 melanom IIIC neoadjuvance, P72 uveální melanom |

Zadává pneumolog (hrudní), onkolog-git (GIT), ostatní klinický onkolog (`apps/mdt/roles.py`).

Na čem jde co předvést:

- **Chybějící údaje** (doplnit, přeskočit, do úkolů): P15 je nejméně připravený (bez dotazníku pacienta, PET/CT,
  MR mozku, EBUS a geriatrického screeningu); P27 a P32 nemají dotazník pacienta (ECOG podle pacienta, preference,
  alergie); P19, P23 a P30 jsou nad 70 let bez G8; P13 má ppoFEV1 pod 60 % bez zátěžového testu. Ve druhé vlně
  chybí dotazník u P40, P41, P46, P57, P60, P61, P67 a P70.
- **Nové výsledky po zařazení** (nominace 15. 10., kontrola před zasedáním): P14 PET/CT, P17 BRCA1, P19 LVEF 48 %,
  P23 CEA 124 µg/l, P27 MR pánve, P30 kreatinin 138 µmol/l; ve druhé vlně P36 a P45 LDH, P41 biopsie nadledviny,
  P48 PDGFRA, P54 PSA, P63 PET/CT, P69 NGS panel.

## Nasazení na VPS (docker compose)

```bash
cd <checkout repa> && git pull origin master
cd WEB_Template && docker compose up -d --build backend     # nový mount /data/demo_pacienti, migrace
docker compose logs backend | grep -E "P[3-7][0-9] |Boardy"  # ingest pacientů a „Boardy: … případy: …“
```

Při startu backend nahraje do IRIS, co chybí (`ingest_dataset --if-empty`), a `seed_mdt` založí zasedání
(`MDT_SEED=True`). Ručně: `docker compose exec backend python manage.py ingest_dataset --skip-vectors` a pak
`docker compose exec backend python manage.py seed_mdt`.
