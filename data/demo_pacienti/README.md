# Demo pacienti P13–P32

Dvacet fiktivních pacientů pro komise v listopadu 2026, ve formátu datasetu Asseco (`pacienti/Pxx/Pxx_bundle.json`,
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

Na čem jde co předvést:

- **Chybějící údaje** (doplnit, přeskočit, do úkolů): P15 je nejméně připravený (bez dotazníku pacienta, PET/CT,
  MR mozku, EBUS a geriatrického screeningu); P27 a P32 nemají dotazník pacienta (ECOG podle pacienta, preference,
  alergie); P19, P23 a P30 jsou nad 70 let bez G8; P13 má ppoFEV1 pod 60 % bez zátěžového testu.
- **Nové výsledky po zařazení** (nominace 15. 10., kontrola před zasedáním): P14 PET/CT, P17 BRCA1, P19 LVEF 48 %,
  P23 CEA 124 µg/l, P27 MR pánve, P30 kreatinin 138 µmol/l.
