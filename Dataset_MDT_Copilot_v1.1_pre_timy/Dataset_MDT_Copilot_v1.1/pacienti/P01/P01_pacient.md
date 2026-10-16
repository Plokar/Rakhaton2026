# Pacientka P01 – metastatický HR+/HER2− karcinom prsu – progrese po 1. linii inhibitor aromatázy + CDK4/6

> **Fiktivní pacient.** Vytvořeno pro hackathon Rakathon 2026 (MDT Copilot). Neodpovídá žádné skutečné osobě. Klinicky neověřeno – nepoužívat pro péči o pacienty.

- **Pohlaví:** žena · **rok narození:** 1963 · **věk k datu MDT:** 63
- **Identifikátor ve FHIR:** `Patient/P01` · každý záznam níže nese ID zdroje v hranatých závorkách, např. `[P01-doc01]`.

## Diagnózy
- `[P01-dg1]` **C50.4** Zhoubný novotvar horního zevního kvadrantu prsu · morfologie ICD-O-3 8500/3 Invazivní karcinom NST (duktální) · od 2017-01-10
  - patologické TNM: pT2 pN1a cM0, stadium IIB (2017-02-02)
- `[P01-dg2]` **C78.7** Sekundární zhoubný novotvar jater a intrahepatálních žlučovodů · od 2023-04-12
- `[P01-dg3]` **C79.5** Sekundární zhoubný novotvar kosti a kostní dřeně · od 2023-04-12
- `[P01-kom1]` **E03.9** Hypotyreóza, substituovaná · od 2014
- `[P01-kom2]` **I10** Esenciální hypertenze · od 2016

## Nominace na MDT (žádanka)

`[P01-zad01]` · stav **Naplánovaná** · plánovaný termín MDT **2026-10-21**

| Položka | Obsah |
|---|---|
| Datum vytvoření | 2026-10-07 |
| Žádající lékař / pracoviště | LEK-P01-01 (klinický onkolog (ošetřující lékař)), Onkologická klinika – ambulance klinické onkologie |
| Požadované zaměření MDT | Mamární komise – karcinom prsu |
| Typ projednání | Progrese / recidiva |
| Priorita | běžná |
| Požadovaný termín (nejpozději) | 2026-10-23 |
| Typ klinické otázky | Systémová léčba, Klinická studie |
| **Otázka pro MDT** | **Progrese jaterních metastáz po 1. linii letrozol + ribociklib (40 měsíců). Jaká další linie – endokrinní léčba podle biomarkerů, trastuzumab deruxtekan (HER2-low v primáru, HER2 0 v metastáze), nebo chemoterapie? Je pacientka kandidátkou studie RKT-01?** |
| Diagnózy | `P01-dg1`, `P01-dg2`, `P01-dg3` |
| Histologie a grade | Invazivní karcinom NST levého prsu G2 (mastektomie 2017): ER 90 %, PR 20 %, HER2 1+, Ki-67 25 %. Metastáza v játrech (biopsie 20. 4. 2023): ER 80 %, PR 0 %, HER2 0, Ki-67 40 %. |
| Relevantní komorbidity a současný stav | Hypotyreóza (substituce), hypertenze. Elevace transamináz G1, bilirubin v normě. Anémie lehkého stupně (Hb 104). ECOG 1. |
| Preference pacienta | Nepřeje si znovu chemoterapii s vypadáváním vlasů, pokud existuje jiná možnost. |
| Pacient informován o projednání | ano |
| Předchozí MDT | `P01-mdt01` |

**Předchozí onkologická léčba**
- [Chirurgie] Mastektomie vlevo s disekcí axily (2017-01-26 – 2017-01-26)
- [Chemoterapie] Adjuvantní AC 4× → paklitaxel týdně 12× (2017-03 – 2017-08)
- [Radioterapie] Adjuvantní RT hrudní stěny a supraklavikulární oblasti vlevo, 50 Gy / 25 frakcí (2017-09-04 – 2017-10-06)
- [Hormonální léčba] Adjuvantní tamoxifen → letrozol (ukončeno po 4,5 letech pro artralgie) (2017-08 – 2022-01-31)
- [Hormonální léčba] 1. linie letrozol + ribociklib (od 3. cyklu 400 mg pro neutropenii G3) (2023-05-22 – dosud)
- [Jiná systémová léčba] Denosumab 120 mg s. c. á 4 týdny + kalcium a vitamin D (2023-05-22 – dosud)

**Podklady (odkazy):** `P01-pat01`, `P01-pat02`, `P01-img01`, `P01-img04`, `P01-img05`, `P01-img06`, `P01-doc06`, `P01-doc07`, `P01-lab06`, `P01-bm03`, `P01-bm07`, `P01-ecog05`

## Chronologie dokumentace

### 2017-02-02 · PAT-B · Definitivní histologie – mastektomie vlevo s disekcí axily  `[P01-pat01]`
*Patologie · Patologie – bioptická laboratoř · autor LEK-P01-02 (patolog)*

Materiál: levý prs (mastektomie) a obsah levé axily (disekce I. a II. etáže). Klinicky: st. p. core-cut biopsii 10. 1. 2017 – invazivní karcinom.

Makroskopicky: V horním zevním kvadrantu tuhý šedobílý tumor 28 × 24 × 20 mm, vzdálenost od dorzálního okraje 12 mm, od kůže 15 mm. Bradavka bez makroskopických změn.

Mikroskopicky: Invazivní karcinom NST (duktální), Nottingham grade 2 (tubuly 3, pleomorfie 2, mitózy 1 – 6 bodů). Lymfovaskulární invaze neprokázána. Okolní DCIS nízkého stupně do 10 % objemu. Resekční okraje volné, nejbližší dorzální 12 mm.
Lymfatické uzliny: 2 ze 14 s metastázou (makrometastázy 6 mm a 4 mm), bez extranodálního šíření.

Imunohistochemie:
ER pozitivní 90 % (silná intenzita)
PR pozitivní 20 % (střední intenzita)
HER2 IHC 1+ (slabá neúplná membránová reaktivita ve > 10 % buněk) – HER2-low, ISH není indikována
Ki-67 25 %

Závěr: Invazivní karcinom NST levého prsu, G2, velikost 28 mm, metastázy ve 2/14 axilárních uzlinách.
pT2 pN1a (2/14), R0. Luminální B (HER2 negativní).

KLASIFIKACE: Topografie (ICD-O-3) C50.4, Morfologie (ICD-O-3) 8500/3

### 2022-01-31 · A-ONK · Dispenzární kontrola – ukončení adjuvantní endokrinní léčby (souhrn léčby 2017–2022)  `[P01-doc01]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P01-01 (klinický onkolog (ošetřující lékař))*

Dg.: Invazivní karcinom NST levého prsu, G2, pT2 (28 mm) pN1a (2/14) cM0, st. IIB, ER 90 %, PR 20 %, HER2 1+ (HER2-low), Ki-67 25 %.

Souhrn léčby:
- 01/2017 core-cut biopsie, 26. 1. 2017 mastektomie vlevo s disekcí axily (R0)
- 03–08/2017 adjuvantní chemoterapie: AC (doxorubicin 60 mg/m² + cyklofosfamid 600 mg/m²) 4× á 21 dní, poté paklitaxel 80 mg/m² týdně 12×; bez závažné toxicity
- 09–10/2017 adjuvantní RT hrudní stěny a supraklavikulární oblasti vlevo, 50 Gy / 25 frakcí
- 08/2017–08/2019 tamoxifen 20 mg denně; po potvrzení postmenopauzálního stavu převedena na letrozol 2,5 mg denně (08/2019–01/2022)

OA: hypotyreóza na substituci (od 2014), arteriální hypertenze (od 2016).
FA: levothyroxin 75 µg 1-0-0, amlodipin 5 mg 1-0-0, letrozol 2,5 mg 1-0-0 – dnes ukončen.
GA: menarche 13 let, 2 porody, menopauza (po chemoterapii trvalá amenorea) potvrzena 2019.
RA: matka karcinom prsu v 60 letech.
SA: úřednice, vdaná, 2 dospělé děti.

Subjektivně: Při letrozolu artralgie drobných kloubů rukou a kolen (G2) zhoršující kvalitu života, analgetika jen s částečným efektem.
Objektivně: ECOG 0. Jizva po mastektomii vlevo klidná, hrudní stěna bez rezistence, lymfedém levé HK neguje. Pravý prs a obě axily palpačně bez nálezu.
Mamografie pravého prsu (11/2021): bez známek malignity (BI-RADS 1).

Závěr: Po 4,5 letech adjuvantní endokrinní léčby (plánováno 5 let) ukončen letrozol pro artralgie G2 – po poučení na přání pacientky. Bez známek recidivy.
Plán: dispenzarizace á 6 měsíců, mamografie pravého prsu 1× ročně.

### 2023-04-12 · RDG · CT hrudníku, břicha a pánve s k. l. – podezření na relaps  `[P01-img01]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P01-03 (radiolog)*

Indikace: st. p. léčbě karcinomu levého prsu (2017), 2 měsíce bolest dolní hrudní páteře, při dispenzární kontrole vzestup ALP a CA 15-3.

Technika: CT hrudníku, břicha a pánve v portální fázi po i.v. aplikaci k. l.

Hrudník: St. p. mastektomii vlevo, hrudní stěna bez známek recidivy. Plicní parenchym bez ložiskových změn, postradiační fibróza apexu levé plíce. Uzliny axilární, supraklavikulární a mediastinální nezvětšené. Bez fluidothoraxu.

Břicho a pánev: Játra normální velikosti, 2 hypodenzní ložiska s periferním sycením charakteru metastáz:
- S6: 31 mm (cílová léze 1)
- S4: 24 mm (cílová léze 2)
Žlučové cesty nerozšířené, portální žíla průchodná. Slezina, slinivka, nadledviny a ledviny bez patologie. Bez ascitu, uzliny retroperitonea nezvětšené.

Skelet: Sklerotická ložiska v obratlovém těle Th10 (bez komprese, zadní hrana intaktní), v obratlovém těle L2, v pravé kosti kyčelní periacetabulárně (cca 18 mm) a v levém os ilium. Bez patologické fraktury. Kostní ložiska nehodnotitelná jako cílová (necílové léze).

Závěr: Metastatický relaps karcinomu prsu – 2 metastázy jater (S6, S4) a sklerotické metastázy skeletu (Th10, L2, pánev). Hrudník bez metastáz.
Součet cílových lézí (RECIST 1.1): 55 mm.

### 2023-04-20 · PAT-B · Core-cut biopsie ložiska jater S6  `[P01-pat02]`
*Patologie · Patologie – bioptická laboratoř · autor LEK-P01-02 (patolog)*

Materiál: 3 válečky jaterní tkáně z UZ navigované biopsie ložiska v S6, délka 8–14 mm.

Mikroskopicky: Infiltrace jaterního parenchymu nízce až středně diferencovaným karcinomem solidní a trabekulární stavby. Morfologie odpovídá metastáze invazivního karcinomu NST.

Imunohistochemie:
GATA3 pozitivní, CK7 pozitivní, CK20 negativní
ER pozitivní 80 % (střední až silná intenzita)
PR negativní (0 %)
HER2 IHC 0 (bez membránové reaktivity)
Ki-67 40 %

Závěr: Metastáza karcinomu prsu v játrech, ER+ (80 %), PR−, HER2 0, Ki-67 40 %.
Ve srovnání s primárním nádorem (2017) ztráta exprese PR a vyšší proliferační aktivita.

KLASIFIKACE: Topografie (ICD-O-3) C22.0, Morfologie (ICD-O-3) 8500/6

### 2023-05-03 · NM · Scintigrafie skeletu (99mTc-HDP), celotělová  `[P01-img02]`
*Zobrazení · Oddělení nukleární medicíny · autor LEK-P01-04 (lékař nukleární medicíny)*

Indikace: relaps karcinomu prsu, sklerotická ložiska skeletu na CT 12. 4. 2023.

Nález: Celotělová scintigrafie 3 h po i.v. aplikaci radiofarmaka. Ložiskově zvýšená akumulace v obratlovém těle Th10, v obratlovém těle L2, v pravé kosti kyčelní v oblasti stropu acetabula a v levém os ilium. Lebka, žebra, hrudní kost, lopatky a dlouhé kosti bez ložiskových změn. Degenerativní změny obou kolen.

Závěr: Mnohočetné osteoblastické metastázy skeletu (4 ložiska – Th10, L2, pravé acetabulum, levé os ilium), odpovídají nálezu na CT. Jiná ložiska nezjištěna.

### 2023-05-10 · MDT · Záznam MDT – Mamární komise – karcinom prsu  `[P01-mdt01]`
*Předsedající LEK-P01-05 · účastníci: klinický onkolog, klinický onkolog, mamární chirurg, radiolog, radiační onkolog, lékař nukleární medicíny, patolog · pacient přítomen: ne*

**Typ projednání:** Progrese / recidiva  
**Projednaná otázka:** Léčebný plán u metastatického relapsu karcinomu levého prsu (játra, skelet).  
**Klinické zhodnocení:** Relaps HR+ karcinomu levého prsu (2017, pT2 pN1a, st. IIB) 14 měsíců po ukončení adjuvantní endokrinní léčby – endokrinně senzitivní onemocnění. CT 12. 4. 2023: metastázy jater S6 31 mm a S4 24 mm, sklerotické metastázy Th10, L2, pravé kosti kyčelní a levého os ilium bez fraktury a bez neurologického deficitu; scintigrafie 3. 5. 2023 bez dalších ložisek. Biopsie jater: metastáza karcinomu prsu, ER 80 %, PR 0 %, HER2 0, Ki-67 40 %. Jaterní testy a bilirubin v normě – bez viscerální krize. Postmenopauzální, ECOG 0.  
**Léčebný záměr:** Paliativní  
**Doporučený postup:**
1. [Hormonální léčba] Letrozol 2,5 mg denně + ribociklib 600 mg D1–21 á 28 dní – do progrese nebo nepřijatelné toxicity; CT á 3 měsíce
2. [Jiná systémová léčba] Denosumab 120 mg s. c. á 4 týdny + kalcium a vitamin D; před zahájením stomatologické vyšetření
3. [Radioterapie] Paliativní RT skeletu při bolesti nebo hrozící fraktuře – dle klinického vývoje

**Klinická studie:** Nezvažována – vhodná studie pro 1. linii není k dispozici.

**Závěr MDT:** Metastatický HR+/HER2− karcinom prsu, endokrinně senzitivní – 1. linie letrozol + ribociklib, denosumab s kalciem a vitaminem D.

**Rozhodnutí o léčbě** `[P01-mdt01-rozhodnuti]` (2023-05-15, LEK-P01-01): Zahájení letrozol + ribociklib 600 mg D1–21 á 28 dní a denosumab 120 mg á 4 týdny od 22. 5. 2023 · stanovisko pacienta: Souhlasí

### 2023-05-22 · A-ONK · Zahájení 1. linie paliativní léčby – letrozol + ribociklib, denosumab  `[P01-doc02]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P01-01 (klinický onkolog (ošetřující lékař))*

Pacientka po projednání na mamární komisi 10. 5. 2023 – indikována 1. linie letrozol + ribociklib a denosumab. Pacientka s léčbou souhlasí.

Subjektivně: Bolest dolní hrudní páteře při zátěži, na paracetamolu 500 mg dle potřeby (1–2× denně) zvládnutelná. Chuť k jídlu dobrá, pracuje.
Objektivně: ECOG 0. Hrudní stěna vlevo bez rezistence, játra nehmatná, bez ikteru, bez otoků. Poklep na trny Th–L páteře lehce citlivý v oblasti Th10, neurologicky bez deficitu.
Laboratoř: krevní obraz, jaterní testy, bilirubin, kreatinin a kalcium v normě.
EKG: sinusový rytmus 72/min, QTc 420 ms.
Stomatologické vyšetření 17. 5. 2023: bez kontraindikace léčby denosumabem.

Zahájeno (1. cyklus):
- letrozol 2,5 mg p. o. 1× denně kontinuálně
- ribociklib 600 mg p. o. 1× denně D1–21, cyklus 28 dní
- denosumab 120 mg s. c. á 4 týdny
- kalcium + cholekalciferol 1 tbl. denně
Edukace o nežádoucích účincích (neutropenie, hepatotoxicita, prodloužení QT, lékové interakce, osteonekróza čelisti, hypokalcémie).

Plán: KO a jaterní testy á 2 týdny během prvních 2 cyklů, EKG 14. den, CT á 3 měsíce, scintigrafie skeletu dle klinického stavu.

### 2023-07-17 · A-ONK · Kontrola před 3. cyklem – neutropenie G3, redukce ribociklibu  `[P01-doc03]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P01-01 (klinický onkolog (ošetřující lékař))*

Subjektivně: Léčbu snáší dobře, mírná únava. Bolest zad ustupuje, analgetika užívá jen výjimečně. Bez teplot.
Objektivně: ECOG 0, afebrilní, bez známek infekce.
Laboratoř: neutrofily 0,8 × 10^9/l (neutropenie G3), Hb a trombocyty v normě, jaterní testy v normě.

Závěr: Neutropenie G3 bez febrilní neutropenie. 3. cyklus ribociklibu odložen o 1 týden, letrozol a denosumab pokračují.
Od 3. cyklu (24. 7. 2023, po kontrole KO) redukce ribociklibu na 400 mg D1–21 á 28 dní (1. stupeň redukce).

### 2025-03-18 · NM · Scintigrafie skeletu (99mTc-HDP) – kontrolní  `[P01-img03]`
*Zobrazení · Oddělení nukleární medicíny · autor LEK-P01-04 (lékař nukleární medicíny)*

Indikace: kontrola kostních metastáz při léčbě letrozol + ribociklib + denosumab.

Nález: Srovnání se scintigrafií z 3. 5. 2023. Známá ložiska v obratlových tělech Th10 a L2, v pravé kosti kyčelní v oblasti stropu acetabula a v levém os ilium s mírně nižší akumulací radiofarmaka. Nová ložiska v ostatním skeletu nezjištěna. Degenerativní změny obou kolen beze změny.

Závěr: Stacionární nález, bez známek progrese kostních metastáz.

### 2025-11-05 · RDG · CT hrudníku, břicha a pánve s k. l. – kontrolní  `[P01-img04]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P01-03 (radiolog)*

Srovnání s CT z 12. 4. 2023 (výchozí vyšetření před léčbou).

Hrudník: Plíce bez ložiskových změn, postradiační fibróza apexu vlevo beze změny. Uzliny nezvětšené.

Játra:
- S6: 18 mm (výchozí 31 mm) – cílová léze 1
- S4: 12 mm (výchozí 24 mm) – cílová léze 2
Nová ložiska v játrech nejsou. Žlučové cesty nerozšířené, bez ascitu.

Skelet: Sklerotická ložiska Th10, L2, v pravé kosti kyčelní periacetabulárně a v levém os ilium beze změny, bez patologické fraktury.

Závěr: Parciální odpověď dle RECIST 1.1 trvá – součet cílových lézí 30 mm (výchozí 55 mm, pokles o 45 %). Bez nových ložisek. Skelet stacionární.

### 2026-02-02 · A-ONK · Kontrola před 36. cyklem letrozol + ribociklib  `[P01-doc04]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P01-01 (klinický onkolog (ošetřující lékař))*

Subjektivně: Bez nových obtíží, bolesti nemá. Pracuje na zkrácený úvazek.
Objektivně: ECOG 0, hmotnost 68 kg, TK 135/80. Játra nehmatná, bez ikteru, bez otoků.
Laboratoř: Hb 125, neutrofily 1,7, Tr 198, ALT 0,48, AST 0,47, ALP 1,82, bilirubin 9, albumin 41, kreatinin 69, CA 15-3 38, CEA 3,9.

Závěr: Neutropenie G1 při ribociklibu, jinak bez toxicity. CA 15-3 hraničně nad normou – sledovat.
Podán 36. cyklus ribociklibu 400 mg, letrozol pokračuje, denosumab aplikován.
Plán: kontrolní CT v 05/2026.

### 2026-05-12 · RDG · CT hrudníku, břicha a pánve s k. l. – kontrolní  `[P01-img05]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P01-03 (radiolog)*

Srovnání s CT z 5. 11. 2025.

Hrudník: Plíce bez ložiskových změn, postradiační fibróza apexu vlevo beze změny. Uzliny nezvětšené. Bez fluidothoraxu.

Játra:
- S6: 22 mm (předchozí 18 mm)
- S4: 15 mm (předchozí 12 mm)
Jiná ložiska v játrech nezjištěna. Žlučové cesty nerozšířené, bez ascitu.

Skelet: Sklerotická ložiska Th10, L2, v pravé kosti kyčelní periacetabulárně a v levém os ilium beze změny.

Závěr: Stacionární nález, bez známek progrese.

### 2026-05-25 · A-ONK · Kontrola po restagingovém CT, 40. cyklus  `[P01-doc05]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P01-01 (klinický onkolog (ošetřující lékař))*

Subjektivně: Občas unavenější, zvládá práci na zkrácený úvazek a domácnost. Bolesti neudává.
Objektivně: ECOG 1, TK 130/80, bez ikteru, játra nehmatná.
Laboratoř: Hb 123, neutrofily 1,6, Tr 201, ALT 0,61, AST 0,58, ALP 2,05, bilirubin 11, albumin 40, kreatinin 71, CA 15-3 52, CEA 4,6.
CT 12. 5. 2026: dle popisu stacionární nález, bez známek progrese.

Závěr: Stabilní onemocnění při 1. linii letrozol + ribociklib (3 roky léčby). CA 15-3 mírně stoupá – kontrola za 3 měsíce.
Podán 40. cyklus ribociklibu 400 mg, letrozol pokračuje, denosumab aplikován.
Plán: kontrolní CT za 3–4 měsíce.

### 2026-06-10 · Dotazník pacienta (PROMs)  `[P01-prom01]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 1 |
| Kde vás bolí? (vlastními slovy) | občas záda při delším sezení |
| Únava za poslední týden (0–10) | 3 |
| Nevolnost nebo zvracení (0–10) | 1 |
| Dušnost (0–10) | 0 |
| Nechutenství (0–10) | 1 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 0 |
| Průjem (0–10) | 1 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 3 |
| Potíže se spánkem (0–10) | 2 |
| Jak zvládáte běžný den? | Těžší fyzickou práci nezvládám, lehčí činnosti a domácnost ano |
| Kolik zvládnete ujít? | Ujdu bez potíží delší vzdálenost i do schodů |
| Vaše současná hmotnost (kg) | 68 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | 0 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | nic nového |
| Alergie nebo nesnášenlivost léků | nevím o žádné |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | nic |
| Co je pro vás v léčbě nejdůležitější? | Obojí je pro mě stejně důležité |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Prášky snáším dobře a chci v léčbě pokračovat. Chodím do práce na zkrácený úvazek a chci to tak udržet. |
| Podpora v domácnosti | Mám dostatečnou podporu blízkých |

### 2026-09-01 · RDG · CT hrudníku, břicha a pánve s k. l. – kontrolní  `[P01-img06]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P01-03 (radiolog)*

Srovnání s CT z 12. 5. 2026 a z 5. 11. 2025.

Hrudník: Plíce bez ložiskových změn. Uzliny nezvětšené. Bez fluidothoraxu.

Játra:
- S6: 29 mm (12. 5. 2026: 22 mm; 5. 11. 2025: 18 mm) – cílová léze 1
- S4: 19 mm (15 mm; 12 mm) – cílová léze 2
- S7: nové ložisko 12 mm
Žlučové cesty nerozšířené, portální žíla průchodná, bez ascitu.

Skelet: Sklerotická ložiska Th10, L2, v pravé kosti kyčelní periacetabulárně a v levém os ilium bez zjevné změny. Nová osteolytická ložiska ani patologická fraktura v zobrazeném rozsahu nejsou patrné.

Závěr: Progrese jaterních metastáz dle RECIST 1.1 – součet cílových lézí 48 mm (nejnižší hodnota 30 mm 5. 11. 2025) a nové ložisko S7. Skelet bez zjevné změny.

### 2026-09-08 · A-ONK · Kontrola – progrese jaterních metastáz, plán MDT  `[P01-doc06]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P01-01 (klinický onkolog (ošetřující lékař))*

Důvod: výsledek kontrolního CT 1. 9. 2026.

Anamnéza: Dg. viz výše – metastatický relaps 04/2023, 1. linie letrozol + ribociklib (od 07/2023 400 mg) a denosumab od 22. 5. 2023.
OA: hypotyreóza na substituci, hypertenze. FA: levothyroxin 75 µg, amlodipin 5 mg, letrozol 2,5 mg, ribociklib 400 mg D1–21, kalcium + vitamin D, denosumab 120 mg s. c. á 4 týdny.
RA: matka karcinom prsu v 60 letech, sestra karcinom vaječníku ve 49 letech (diagnostikováno 2024). Genetické vyšetření dosud neprovedeno.
SA: úřednice, vdaná, 2 dospělé děti.

Subjektivně: Poslední týdny unavenější, chuť k jídlu zachována. Bolesti neudává.
Objektivně: ECOG 1, TK 135/85. Játra nehmatná, bez ikteru, bez ascitu, bez otoků.
Laboratoř: Hb 116, neutrofily 1,4, Tr 188, ALT 0,98, AST 0,95, ALP 2,61, bilirubin 12, albumin 38, kreatinin 72, CA 15-3 89, CEA 5,9.

Závěr: Progrese jaterních metastáz po 1. linii letrozol + ribociklib (CT 1. 9. 2026 – zvětšení S6, S4 a nové ložisko S7). Mírná elevace transamináz (G1), bilirubin v normě. Rostoucí CA 15-3 a CEA.
Pacientka informována o progresi. Přeje si pokračovat v léčbě, ale nechce znovu chemoterapii, po které by jí vypadaly vlasy, pokud existuje jiná možnost.
Plán: nominace na mamární komisi (další linie léčby). Do rozhodnutí komise letrozol + ribociklib ponechány, denosumab pokračuje.

### 2026-10-05 · Dotazník pacienta (PROMs)  `[P01-prom02]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 6 |
| Kde vás bolí? (vlastními slovy) | pravá kyčel a tříslo, hlavně při chůzi |
| Únava za poslední týden (0–10) | 8 |
| Nevolnost nebo zvracení (0–10) | 1 |
| Dušnost (0–10) | 2 |
| Nechutenství (0–10) | 3 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 0 |
| Průjem (0–10) | 1 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 6 |
| Potíže se spánkem (0–10) | 5 |
| Jak zvládáte běžný den? | Postarám se o sebe, ale pracovat nemohu; přes den odpočívám méně než polovinu času |
| Kolik zvládnete ujít? | Zvládnu jen chůzi po rovině |
| Vaše současná hmotnost (kg) | 67 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | -1 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | Asi 3 týdny mě bolí pravá kyčel a tříslo, když chodím. Do schodů to skoro nejde, chodím jen po rovině. Jsem pořád unavená, odpoledne musím ležet. Do práce od září nechodím. |
| Alergie nebo nesnášenlivost léků | nevím o žádné |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | paracetamol 500 mg 2–3× denně na bolest kyčle |
| Co je pro vás v léčbě nejdůležitější? | Nejdůležitější je pro mě kvalita života, i kdyby léčba byla méně účinná |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Nechci znovu klasickou chemoterapii, po které mi vypadají vlasy, pokud to jde jinak. Chci co nejdéle zvládat sama domácnost a být s rodinou. |
| Podpora v domácnosti | Mám dostatečnou podporu blízkých |

### 2026-10-06 · A-ONK · Kontrola před mamární komisí  `[P01-doc07]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P01-01 (klinický onkolog (ošetřující lékař))*

Pacientka s progresí jaterních metastáz (CT 1. 9. 2026), nominována na mamární komisi.

Subjektivně: Únava mírná, jinak bez nových obtíží.
Objektivně: ECOG 1, hmotnost 67 kg, TK 130/80. Bez ikteru, játra nehmatná, bez ascitu, bez otoků.
Laboratoř: Hb 104, neutrofily 1,7, Tr 176, ALT 1,46, AST 1,38, ALP 3,12, bilirubin 14, albumin 37, kreatinin 74, CA 15-3 121, CEA 6,8.

Závěr: Progrese jaterních metastáz po 1. linii letrozol + ribociklib (doba léčby cca 40 měsíců). Elevace transamináz G1 (do 2× ULN) – pravděpodobně při progresi jaterních metastáz, bilirubin v normě – bez známek viscerální krize. Anémie lehkého stupně.
Molekulární vyšetření z ctDNA (ESR1, PIK3CA, AKT1) dosud neprovedeno.
Plán: projednání na mamární komisi 21. 10. 2026. Další cyklus ribociklibu (45.) odložen do rozhodnutí komise, letrozol a denosumab pokračují.

## Laboratoř

ID výsledku: `P01-labNN-<parametr>`, NN = pořadí odběru (sloupec).

| Parametr | Jednotka | Norma | 01: 2025-03-31 | 02: 2025-11-10 | 03: 2026-02-02 | 04: 2026-05-25 | 05: 2026-09-08 | 06: 2026-10-06 |
|---|---|---|---|---|---|---|---|---|
| Hemoglobin (LOINC 718-7) | g/l | 120–160 | 128 | 127 | 125 | 123 | 116 ↓ | 104 ↓ |
| Neutrofily absolutně (LOINC 751-8) | 10^9/l | 2.0–7.0 | 1.6 ↓ | 1.5 ↓ | 1.7 ↓ | 1.6 ↓ | 1.4 ↓ | 1.7 ↓ |
| Trombocyty (LOINC 777-3) | 10^9/l | 150–400 | 210 | 205 | 198 | 201 | 188 | 176 |
| ALT (LOINC 1742-6) | µkat/l | 0.1–0.78 | 0.42 | 0.45 | 0.48 | 0.61 | 0.98 ↑ | 1.46 ↑ |
| AST (LOINC 1920-8) | µkat/l | 0.1–0.72 | 0.4 | 0.43 | 0.47 | 0.58 | 0.95 ↑ | 1.38 ↑ |
| ALP (LOINC 6768-6) | µkat/l | 0.66–2.2 | 1.65 | 1.7 | 1.82 | 2.05 | 2.61 ↑ | 3.12 ↑ |
| Bilirubin celkový (LOINC 14631-6) | µmol/l | 2–21 | 9 | 10 | 9 | 11 | 12 | 14 |
| Albumin (LOINC 1751-7) | g/l | 35–52 | 42 | 41 | 41 | 40 | 38 | 37 |
| Kreatinin (LOINC 14682-9) | µmol/l | 44–104 | 68 | 70 | 69 | 71 | 72 | 74 |
| CA 15-3 (LOINC 6875-3) | kU/l | 0–31 | 28 | 31 | 38 ↑ | 52 ↑ | 89 ↑ | 121 ↑ |
| CEA (LOINC 2039-6) | µg/l | 0–5.0 | 3.1 | 3.3 | 3.9 | 4.6 | 5.9 ↑ | 6.8 ↑ |

## Strukturované nálezy (ECOG, biomarkery, staging, hmotnost)

- 2017-02-02 `[P01-bm01]` ER (primární nádor): pozitivní 90 % (vzorek: mastektomie vlevo) · zdroj `P01-pat01`
- 2017-02-02 `[P01-bm02]` PR (primární nádor): pozitivní 20 % (vzorek: mastektomie vlevo) · zdroj `P01-pat01`
- 2017-02-02 `[P01-bm03]` HER2 IHC (primární nádor): 1+ (HER2-low) (vzorek: mastektomie vlevo) · zdroj `P01-pat01`
- 2017-02-02 `[P01-bm04]` Ki-67 (primární nádor): 25 % (vzorek: mastektomie vlevo) · zdroj `P01-pat01`
- 2017-02-02 `[P01-tnm01]` TNM (patologické): pT2 pN1a (2/14) cM0, stadium IIB (TNM 8. vyd.) · zdroj `P01-pat01`
- 2023-04-12 `[P01-tnm02]` TNM (klinické): metastatický relaps – M1 (játra, skelet), stadium IV · zdroj `P01-img01`
- 2023-04-20 `[P01-bm05]` ER (metastáza): pozitivní 80 % (vzorek: biopsie jater S6) · zdroj `P01-pat02`
- 2023-04-20 `[P01-bm06]` PR (metastáza): negativní 0 % (vzorek: biopsie jater S6) · zdroj `P01-pat02`
- 2023-04-20 `[P01-bm07]` HER2 IHC (metastáza): 0 (vzorek: biopsie jater S6) · zdroj `P01-pat02`
- 2023-04-20 `[P01-bm08]` Ki-67 (metastáza): 40 % (vzorek: biopsie jater S6) · zdroj `P01-pat02`
- 2023-05-22 `[P01-ecog01]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P01-doc02`
- 2026-02-02 `[P01-ecog02]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P01-doc04`
- 2026-02-02 `[P01-vaha01]` Hmotnost 68 kg · zdroj `P01-doc04`
- 2026-05-25 `[P01-ecog03]` ECOG 1 (omezen(a) při fyzicky náročné činnosti, zvládá lehkou práci) – hodnotil lékař · zdroj `P01-doc05`
- 2026-09-08 `[P01-ecog04]` ECOG 1 (omezen(a) při fyzicky náročné činnosti, zvládá lehkou práci) – hodnotil lékař · zdroj `P01-doc06`
- 2026-09-08 `[P01-bm11]` Germinální BRCA1/2: nevyšetřeno · zdroj `P01-doc06`
- 2026-10-06 `[P01-ecog05]` ECOG 1 (omezen(a) při fyzicky náročné činnosti, zvládá lehkou práci) – hodnotil lékař · zdroj `P01-doc07`
- 2026-10-06 `[P01-vaha02]` Hmotnost 67 kg · zdroj `P01-doc07`
- 2026-10-06 `[P01-bm09]` ESR1 mutace (ctDNA): nevyšetřeno · zdroj `P01-doc07`
- 2026-10-06 `[P01-bm10]` PIK3CA / AKT1 / PTEN: nevyšetřeno · zdroj `P01-doc07`

## Léky

- `[P01-med01]` levothyroxin (ATC H03AA01) – 75 µg 1-0-0 nalačno · od 2014-06-10
- `[P01-med02]` amlodipin (ATC C08CA01) – 5 mg 1-0-0 · od 2016-03-15
- `[P01-med03]` kalcium + cholekalciferol (ATC A12AX) – 1 tbl. (kalcium 1000 mg + cholekalciferol 880 IU) 1× denně · od 2023-05-22 · při léčbě denosumabem
- `[P01-med04]` letrozol (ATC L02BG04) – 2,5 mg 1-0-0 kontinuálně · od 2023-05-22 · 1. linie metastatického onemocnění v kombinaci s ribociklibem; v adjuvanci užíván 08/2019–01/2022
- `[P01-tx-rib-01…10]` ribociklib (ATC L01EF02) – letrozol + ribociklib (1. linie), 400 mg p. o. 1× denně D1–21, cyklus 28 dní · podání: 2026-01-05, 2026-02-02, 2026-03-02, 2026-03-30, 2026-04-27, 2026-05-25, 2026-06-22, 2026-07-20, 2026-08-17, 2026-09-14
  - 2026-01-05: 35. cyklus od zahájení 22. 5. 2023; dávka 400 mg od 3. cyklu (24. 7. 2023) – redukce z 600 mg pro neutropenii G3
  - 2026-09-14: 44. cyklus – ponechán po progresi na CT 1. 9. 2026 do rozhodnutí MDT
- `[P01-tx-den-01…10]` denosumab (ATC M05BX04) – denosumab – kostní metastázy, 120 mg s. c. á 4 týdny · podání: 2026-01-05, 2026-02-02, 2026-03-02, 2026-03-30, 2026-04-27, 2026-05-25, 2026-06-22, 2026-07-20, 2026-08-17, 2026-09-14
  - 2026-01-05: léčba denosumabem od 22. 5. 2023, v datasetu uvedena jen podání v roce 2026

## Výkony a radioterapie

- `[P01-proc01]` 2017-01-10 · Core-cut biopsie tumoru levého prsu pod UZ kontrolou – histologie: invazivní karcinom NST – podrobně viz definitivní histologie
- `[P01-proc02]` 2017-01-26 · Mastektomie vlevo s disekcí axily (I. a II. etáž)
- `[P01-proc03]` 2017-09-04 – 2017-10-06 · Adjuvantní radioterapie hrudní stěny a supraklavikulární oblasti vlevo, 50 Gy / 25 frakcí
- `[P01-proc04]` 2023-04-20 · Core-cut biopsie ložiska jater S6 pod UZ kontrolou

