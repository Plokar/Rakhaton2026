# Demo pacienti P13–P172

160 fiktivních pacientů pro 10 komisí s 36 zasedáními od 3. 11. do 18. 12. 2026, ve formátu datasetu Asseco (`pacienti/Pxx/Pxx_bundle.json`,
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

Třetí vlna (T-355, `pt()`): 100 pacientů P73–P172. P73–P106 doplní zasedání druhé vlny od 10. 11. na 4–5 případů,
P107–P172 jsou v 12 nových zasedáních 7.–18. 12. Každé zasedání od 10. 11. má 4–8 případů. Pokrývají všechny diagnózy
katalogu postupů (`data/onko/postupy.tsv`: C00–C14/C32, C15, C16, C18–C20, C22, C25, C34, C43, C50, C53, C54, C56,
C61, C64, C67, C71, C78.2, C78.7, C79.3, C79.5, D41) a navíc lymfomy, myelom, CLL, sarkomy a desmoid. ECOG 0–3,
kurativní i paliativní situace.

| Termín | Komise | Pacienti |
|---|---|---|
| 10. 11.–4. 12. | doplnění 19 zasedání | P73–P106 |
| po 7. 12. 13:00 | Uroonkologická | P107–P112 (mHSPC, 177Lu-PSMA, biochemický relaps, ccRCC M1, MIBC, FGFR3) |
| út 8. 12. 14:00 | Hrudní | P113–P118 (adjuvance EGFR, unfit III, BRAF, MET, RET, SCLC ES) |
| st 9. 12. 14:00 | Mamární | P119–P124 (HER2+ neoadjuvance, T-DXd, HER2-low, TNBC M1, 72 let, WBRT) |
| čt 10. 12. 13:00 | Neuroonkologická | P125–P129 (relaps GBM, metastázy, PCNSL, komprese míchy) |
| čt 10. 12. 14:00 | GIT | P130–P135 (jícen po CROSS, CLDN18.2, kolon III, W&W rektum, jaterní metastázy, HCC) |
| pá 11. 12. 13:00 | Gynekoonkologická | P136–P141 (cervix IIIC1, endometrium p53abn a dMMR, ovarium) |
| po 14. 12. 13:00 | Hematoonkologická | P142–P146 (Hodgkin 71 let, FL, CLL, myelom, Burkitt) |
| út 15. 12. 14:00 | Hrudní | P147–P152 (PD-L1 85 %, skvamózní, KRAS G12C, ECOG 2, oligometastázy, nejasné ložisko) |
| st 16. 12. 13:30 | Hlava a krk | P153–P157 (ENE+, nezpůsobilá k cisplatině, R/M, parotis HER2+) |
| čt 17. 12. 14:00 | GIT | P158–P162 (KRAS G12C, rektum časné, pankreas gBRCA2, HCC BCLC C, jícen SCC M1) |
| pá 18. 12. 13:00 | Sarkomy a GIST | P163–P167 (liposarkom, Ewing, desmoid, synoviální sarkom, leiomyosarkom) |
| pá 18. 12. 14:00 | Melanom a kožní nádory | P168–P172 (neoadjuvance, IB, BRAF M1, mozkové metastázy, kožní SCC 81 let) |

Mezery ve třetí vlně (pětina): bez dotazníku pacienta P75, P84, P93, P100, P110, P117, P127, P140, P150, P161;
bez preferencí (dotazník bez priority, nominace bez preference) P77, P99, P115, P124, P146; bez laboratoře
(`no_labs`) P91, P109, P135, P154, P166. Nové výsledky po zařazení (desetina): P74, P86, P95, P107, P119, P131, P137,
P143, P149, P170.

**Fiktivní jméno a RČ** (T-355, pro hledání při zařazení, T-356) mají všichni demo pacienti P13–P172:
`Patient.name` = „Jméno Příjmení (fiktivní)“ z běžných českých jmen, `Patient.identifier` se systémem
`https://rakathon.example.org/fhir/sid/rc-fiktivni`. RČ je formálně platné (datum narození podle věku k datu komise
a pohlaví, ženy +50 k měsíci, desetimístné dělitelné 11, do roku 1953 devítimístné), ale z vymyšleného rozsahu:
koncovka začíná `99`. Jméno a RČ se ukážou jen v dialogu přidání pacienta, jinde dál `Pxx · pohlaví · věk` (D-018).

## Nasazení na VPS (docker compose)

```bash
cd <checkout repa> && git pull origin master
cd WEB_Template && docker compose -f docker-compose.vps.yml up -d --build backend   # mount /data/demo_pacienti, migrace
docker compose logs backend | grep -E "P[3-7][0-9] |Boardy"  # ingest pacientů a „Boardy: … případy: …“
```

Při startu backend nahraje do IRIS, co chybí (`ingest_dataset --if-empty`), a `seed_mdt` založí zasedání
(`MDT_SEED=True`). Ručně: `docker compose exec backend python manage.py ingest_dataset --skip-vectors` a pak
`docker compose exec backend python manage.py seed_mdt`.
