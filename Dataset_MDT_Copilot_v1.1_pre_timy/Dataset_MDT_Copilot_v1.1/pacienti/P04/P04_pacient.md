# Pacient P04 – adenokarcinom pravého horního laloku plíce st. III (N2) – operabilita a volba radikální léčby

> **Fiktivní pacient.** Vytvořeno pro hackathon Rakathon 2026 (MDT Copilot). Neodpovídá žádné skutečné osobě. Klinicky neověřeno – nepoužívat pro péči o pacienty.

- **Pohlaví:** muž · **rok narození:** 1956 · **věk k datu MDT:** 70
- **Identifikátor ve FHIR:** `Patient/P04` · každý záznam níže nese ID zdroje v hranatých závorkách, např. `[P04-doc01]`.

## Diagnózy
- `[P04-dg1]` **C34.1** Zhoubný novotvar horního laloku, průdušky nebo plíce · morfologie ICD-O-3 8140/3 Adenokarcinom NOS · od 2026-08-14
  - klinické TNM: cT3 cN2 cM0, stadium IIIB (2026-10-06)
- `[P04-dg2]` **C77.1** Sekundární a neurčený zhoubný novotvar nitrohrudních mízních uzlin · od 2026-10-05
- `[P04-kom1]` **J44.9** Chronická obstrukční plicní nemoc (GOLD 2) · od 2019-05
- `[P04-kom2]` **I10** Esenciální hypertenze · od 2015-06
- `[P04-kom3]` **F17.2** Závislost na tabáku – aktivní kuřák (40 balíčkoroků)

## Nominace na MDT (žádanka)

`[P04-zad01]` · stav **Naplánovaná** · plánovaný termín MDT **2026-10-21**

| Položka | Obsah |
|---|---|
| Datum vytvoření | 2026-10-08 |
| Žádající lékař / pracoviště | LEK-P04-01 (pneumolog (ošetřující lékař)), Pneumologická klinika – pneumologická ambulance |
| Požadované zaměření MDT | Hrudní – karcinom plic |
| Typ projednání | Primární projednání |
| Priorita | běžná |
| Požadovaný termín (nejpozději) | 2026-10-21 |
| Typ klinické otázky | Indikace operace, Léčebný plán, Klinická studie |
| **Otázka pro MDT** | **Adenokarcinom PHL cT3 N2 (single-station 4R) M0?, PD-L1 60 %. Resekce po neoadjuvantní chemoimunoterapii, nebo definitivní chemoradioterapie s konsolidační imunoterapií? Je pacient funkčně operabilní?** |
| Diagnózy | `P04-dg1`, `P04-dg2` |
| Histologie a grade | Adenokarcinom plic G3 (solidní složka), TTF-1 pozitivní (bronchoskopická biopsie 12. 8. 2026); EBUS-TBNA 4R – metastáza adenokarcinomu (1. 10. 2026) |
| Relevantní komorbidity a současný stav | CHOPN GOLD 2 (FEV1 58 %, DLCO 45 %), hypertenze. Aktivní kuřák, 40 balíčkoroků. ECOG 0. |
| Preference pacienta | Přeje si operaci, pokud bude možná; obává se dušnosti po odstranění části plíce. |
| Pacient informován o projednání | ano |
| Předchozí MDT | `P04-mdt01` |

**Podklady (odkazy):** `P04-pat01`, `P04-pat02`, `P04-pat03`, `P04-img02`, `P04-img03`, `P04-img04`, `P04-doc03`, `P04-doc05`, `P04-doc06`, `P04-lab05`, `P04-bm01`, `P04-bm05`, `P04-ecog02`, `P04-tnm01`

## Chronologie dokumentace

### 2026-07-28 · A-PNEU · Vstupní pneumologické vyšetření – hemoptoe, stín na RTG  `[P04-doc01]`
*Zpráva · Pneumologická ambulance · autor LEK-P04-01 (pneumolog (ošetřující lékař))*

Důvod: odeslán praktickým lékařem pro kašel trvající 2 měsíce a 2× hemoptoe (drobné příměsi krve ve sputu).

Anamnéza: Bývalý zámečník, v důchodu. Žije s manželkou. Kouří od 17 let, dříve 20 cig./den, nyní cca 10 cig./den, celkem 40 balíčkoroků. Alkohol příležitostně.
OA: CHOPN od r. 2019 (GOLD 2), sledován v naší ambulanci, exacerbace bez hospitalizace. Hypertenze od r. 2015. DM neguje, arytmie neguje.
FA: tiotropium 18 µg inh. 1× denně, formoterol/budesonid 4,5/160 µg 2 vdechy 2× denně, amlodipin 5 mg 1-0-0.
Alergie: neudává.
RA: bez onkologické zátěže.

Subjektivně: Asi 2 měsíce kašel, nyní vlhký, 2× drobná příměs krve ve sputu. Námahová dušnost do schodů, dle pacienta beze změny proti loňsku. Bolesti na hrudi neudává. Teploty neměl.

Objektivně: Výška 176 cm, hmotnost 78 kg. ECOG 0. SpO2 94 % bez O2, TK 145/85, AS pravidelná 82/min. Dýchání vpravo nahoře oslabené, jinak sklípkové s prodlouženým exspiriem. Periferní uzliny nehmatné.

RTG hrudníku (dnes): stín v pravém horním plicním poli – viz popis.
Laboratoř: KO v normě (Hb 148 g/l, leukocyty 8,4), Na 136, K 4,3, kreatinin 82, CRP 12, CEA 8,2 µg/l.

Závěr: Suspektní tumor pravého horního laloku u kuřáka s CHOPN.
Plán: CT hrudníku a břicha s k. l., bronchoskopie s biopsií, spirometrie s DLCO. Kontrola po výsledcích.

### 2026-07-28 · RDG · RTG hrudníku PA a bočný  `[P04-img01]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P04-04 (radiolog)*

Indikace: kašel, hemoptoe, kuřák.

Nález: V pravém horním plicním poli nehomogenní zastínění s nepravidelnými okraji, velikosti cca 6 cm. Pravý hilus mírně rozšířen. Plíce jinak s emfyzematózními změnami, bez infiltrace. Bránice hladké, úhly volné. Srdce nezvětšené.

Závěr: Stín v pravém horním plicním poli suspektní z tumoru. Doporučeno CT hrudníku s k. l.

### 2026-08-04 · RDG · CT hrudníku a břicha s k. l. – staging  `[P04-img02]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P04-04 (radiolog)*

Technika: CT hrudníku a břicha po i.v. aplikaci k. l., hrudník v pozdní arteriální fázi, břicho v portální fázi.

Hrudník: V pravém horním laloku (segmenty S1/S2) solidní tumor s nepravidelnými, spikulovanými okraji, velikosti 62 × 48 mm (cílová léze 1), přiléhá k ústí segmentárních bronchů B1 a B2, horní lalokový bronchus průchodný. Tumor nepřesahuje interlobium, hrudní stěnu ani mediastinum neinfiltruje, bez satelitních ložisek ve stejném laloku.
Mediastinum: uzlina 4R 18 mm v krátké ose (cílová léze 2), subkarinální uzlina (st. 7) 11 mm v krátké ose, uzlina 10R 7 mm. Levostranné mediastinální uzliny nezvětšené.
Plíce oboustranně s centrilobulárním emfyzémem, v levé plíci bez ložisek. Bez fluidothoraxu.

Břicho: Játra bez ložiskových změn. V levé nadledvině ovoidní ložisko 14 mm s hladkými okraji, denzita v portální fázi 38 HU – charakter nelze spolehlivě určit, pravděpodobně adenom, k dořešení. Pravá nadledvina štíhlá. Ledviny, slezina a slinivka bez patologie. Retroperitoneální uzliny nezvětšené.

Závěr: Tumor pravého horního laloku 62 mm. Mediastinální lymfadenopatie 4R (18 mm), hraniční uzlina 7 (11 mm). Ložisko levé nadledviny 14 mm – pravděpodobně adenom, k dořešení.
Součet cílových lézí (RECIST 1.1, uzlina v krátké ose): 80 mm.

### 2026-08-05 · Dotazník pacienta (PROMs)  `[P04-prom01]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 1 |
| Kde vás bolí? (vlastními slovy) | občas píchne vpravo na hrudi při kašli |
| Únava za poslední týden (0–10) | 3 |
| Nevolnost nebo zvracení (0–10) | 0 |
| Dušnost (0–10) | 4 |
| Nechutenství (0–10) | 2 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 0 |
| Průjem (0–10) | 0 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 5 |
| Potíže se spánkem (0–10) | 4 |
| Jak zvládáte běžný den? | Těžší fyzickou práci nezvládám, lehčí činnosti a domácnost ano |
| Kolik zvládnete ujít? | Vyjdu jedno patro bez zastavení |
| Vaše současná hmotnost (kg) | 77 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | -1 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | Asi dva měsíce kašlu, dvakrát jsem vykašlal krev. V noci mě kašel budí. |
| Alergie nebo nesnášenlivost léků | nevím o žádné |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | nic |
| Co je pro vás v léčbě nejdůležitější? | Nevím / chci to probrat s lékařem |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Chci hlavně vědět, co to je, a pak to řešit. Manželka je se mnou. |
| Podpora v domácnosti | Mám dostatečnou podporu blízkých |

### 2026-08-12 · A-PNEU · Bronchoskopie s biopsií  `[P04-doc02]`
*Zpráva · Pneumologická ambulance – bronchoskopie · autor LEK-P04-02 (pneumolog – intervenční bronchologie)*

Indikace: tumor pravého horního laloku na CT, hemoptoe.

Průběh: Flexibilní bronchoskopie v lokální anestezii, přístupem nosem. Hlasivky symetricky pohyblivé. Trachea volná, hlavní karina ostrá, pohyblivá.
Vpravo: v ústí apikálního (B1) a zadního (B2) segmentárního bronchu pravého horního laloku exofytická, snadno krvácivá infiltrace. Horní lalokový bronchus průchodný, intermediální bronchus, střední a dolní lalok bez patologie.
Vlevo: bez endobronchiální patologie.
Odebráno: kleštové biopsie z B1/B2 (5×), kartáčková cytologie, BAL. Drobné krvácení z místa biopsie zastaveno lokálně (adrenalin).

Závěr: Endobronchiální tumor pravého horního laloku (B1/B2), odebrána histologie. Bez komplikací.
Doporučení: výsledek histologie a prediktivních markerů k pneumologovi.

### 2026-08-14 · PAT-B · Bronchoskopická biopsie tumoru pravého horního laloku  `[P04-pat01]`
*Patologie · Patologie – bioptická laboratoř · autor LEK-P04-03 (patolog)*

Makroskopicky: 5 drobných fragmentů tkáně do 2 mm.

Mikroskopicky: Ve 3 z 5 fragmentů infiltrace nízce diferencovaným adenokarcinomem s acinární a převážně solidní stavbou, s ložisky nekrózy. Podíl nádorových buněk cca 15 %, celkově malé množství nádorové tkáně.
Imunohistochemie: TTF-1 pozitivní, napsin A pozitivní, p40 negativní.

Závěr: Adenokarcinom plic, G3 (solidní složka), TTF-1 pozitivní.
Pozn.: Malý objem materiálu – parafinové bloky ponechány pro prediktivní vyšetření (PD-L1, ALK, ROS1, NGS).

KLASIFIKACE: Topografie (ICD-O-3) C34.1, Morfologie (ICD-O-3) 8140/3

### 2026-08-20 · PAT-B · Prediktivní vyšetření (PD-L1, ALK, ROS1, EGFR)  `[P04-pat02]`
*Patologie · Patologie – molekulární patologie · autor LEK-P04-03 (patolog)*

Materiál: parafinové bloky z bronchoskopické biopsie (12. 8. 2026), podíl nádorových buněk cca 15 %.

Výsledek:
PD-L1 (klon 22C3): TPS 60 %.
ALK (IHC, klon D5F3): negativní.
ROS1 (IHC, klon D4D6): negativní.
NGS (EGFR, KRAS, BRAF, MET, RET, ERBB2): po vyčerpání tkáně na imunohistochemii nedostatečné množství DNA – vyšetření neprovedeno.

Interpretace: Vzorek nedostatečný pro NGS, doporučeno opakovat z dalšího materiálu (např. EBUS-TBNA, rebiopsie) nebo zvážit tekutou biopsii.

### 2026-08-25 · A-PNEU · Spirometrie, bronchodilatační test a difuzní kapacita  `[P04-doc03]`
*Zpráva · Pneumologická ambulance – funkční vyšetření plic · autor LEK-P04-01 (pneumolog (ošetřující lékař))*

Výška 176 cm, hmotnost 76 kg. Vyšetření při stávající inhalační léčbě.

Spirometrie: FEV1 1,9 l (58 % náležité hodnoty), FVC 3,3 l (82 % NH), FEV1/FVC 0,58.
Bronchodilatační test (salbutamol 400 µg): FEV1 +4 % – nesignifikantní.
Difuzní kapacita: DLCO 45 % NH.

Závěr: Středně těžká obstrukční ventilační porucha (odpovídá GOLD 2), středně těžce snížená difuzní kapacita plic.
Zátěžový test (spiroergometrie) neproveden – indikace dle posouzení hrudního chirurga.

### 2026-09-16 · MDT · Záznam MDT – Hrudní – karcinom plic  `[P04-mdt01]`
*Předsedající LEK-P04-06 · účastníci: klinický onkolog, pneumolog, hrudní chirurg, radiolog, radiační onkolog, patolog · pacient přítomen: ne*

**Typ projednání:** Primární projednání  
**Projednaná otázka:** Léčebný plán u nově diagnostikovaného adenokarcinomu pravého horního laloku s mediastinální lymfadenopatií.  
**Klinické zhodnocení:** Adenokarcinom PHL G3, TTF-1+. PD-L1 TPS 60 %, ALK a ROS1 negativní, EGFR nevyšetřen (vzorek nedostatečný pro NGS). CT 4. 8.: tumor 62 mm, uzlina 4R 18 mm, uzlina 7 11 mm, ložisko levé nadledviny 14 mm nejasného charakteru. Klinicky cT3 N2? (neověřeno), M0? CHOPN GOLD 2 (FEV1 58 %, DLCO 45 %), aktivní kuřák. ECOG 0.  
**Léčebný záměr:** Rozhodnutí odloženo – doplnit diagnostiku  
**Doporučený postup:**
1. [Diagnostika] Dokončit staging a molekulární diagnostiku (viz Doplnit) – do 4 týdnů
2. [Diagnostika] Po doplnění re-MDT – rozhodnutí o radikální léčbě (resekce vs. chemoradioterapie) – re-MDT

**Doplnit:** PET-CT – celotělový staging; EBUS-TBNA – verifikace mediastinálních uzlin 4R a 7; MR mozku – vyloučení mozkových metastáz; NGS – EGFR a další prediktivní markery z materiálu EBUS; Hrudně chirurgické konzilium – posouzení resekability a funkční operability

**Klinická studie:** Po dokončení stagingu zvážit RKT-04 PULMO-NEO.

**Plánované re-MDT:** Po doplnění stagingu, NGS a chirurgického posouzení (do 2026-10-31)

**Závěr MDT:** Rozhodnutí o léčbě odloženo – doplnit PET-CT, EBUS-TBNA, MR mozku, NGS a hrudně chirurgické posouzení operability, poté re-MDT.

**Rozhodnutí o léčbě** `[P04-mdt01-rozhodnuti]` (2026-09-18, LEK-P04-01): Doplnění diagnostiky dle doporučení MDT (PET-CT, EBUS-TBNA, MR mozku, NGS, hrudně chirurgické konzilium) · stanovisko pacienta: Souhlasí

### 2026-09-25 · NM · PET-CT (18F-FDG) – staging  `[P04-img03]`
*Zobrazení · Oddělení nukleární medicíny – PET centrum · autor LEK-P04-09 (lékař nukleární medicíny)*

Indikace: staging adenokarcinomu pravého horního laloku. Srovnání s CT z 4. 8. 2026.

Nález:
- Tumor pravého horního laloku 62 mm, SUVmax 14,2.
- Uzlina 4R 18 mm v krátké ose, SUVmax 6,1 – suspektní metastáza.
- Subkarinální uzlina (st. 7) 11 mm, SUVmax 2,3 – nespecifická, nízká akumulace.
- Uzliny 10R a levostranné mediastinální uzliny bez zvýšené akumulace FDG.
- Levá nadledvina: ložisko 14 mm, SUVmax 4,1 (vyšší než akumulace v játrech) – nejasné, nelze vyloučit metastázu.
- Skelet, játra, ostatní orgány bez metabolicky aktivních ložisek.

Závěr: Metabolicky aktivní tumor PHL a uzlina 4R. Uzlina 7 nespecifická. Ložisko levé nadledviny 14 mm se zvýšenou akumulací FDG – nejasné, nelze vyloučit metastázu, doporučeno ověření (MR nadledvin / biopsie). Jinde bez ložisek.

### 2026-10-01 · A-PNEU · EBUS-TBNA mediastinálních uzlin  `[P04-doc04]`
*Zpráva · Pneumologická ambulance – bronchoskopie · autor LEK-P04-02 (pneumolog – intervenční bronchologie)*

Indikace: invazivní staging mediastina dle doporučení MDT (16. 9. 2026), odběr materiálu na NGS.

Průběh: Endobronchiální ultrazvuk v analgosedaci. Systematicky zhodnoceny uzlinové stanice 4L, 4R, 7, 10R, 11R.
Punkce (22G): 4R – 3 vpichy, 7 – 2 vpichy, 10R – 2 vpichy. Rychlé cytologické hodnocení na sále (ROSE): ve 4R maligní buňky, 7 a 10R lymfoidní populace.
Z uzliny 4R odebrán další materiál do cell blocku pro histologii a NGS.
Výkon bez komplikací, bez krvácení.

Závěr: EBUS-TBNA 4R, 7, 10R. Předběžně (ROSE) pozitivní 4R. Definitivní výsledek a NGS z cell blocku – patologie.

### 2026-10-02 · RDG · MR mozku s k. l.  `[P04-img04]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P04-04 (radiolog)*

Indikace: staging NSCLC st. III.

Nález: Supra- i infratentoriálně bez ložiskových změn, po aplikaci k. l. bez patologického sycení. Ojedinělá drobná hyperintenzní ložiska v bílé hmotě frontálně oboustranně – nespecifická, vaskulární etiologie. Komorový systém přiměřené šíře, střední čára nedislokována.

Závěr: Bez známek metastatického postižení mozku.

### 2026-10-05 · PAT-B · Cytologie a cell block z EBUS-TBNA (4R, 7, 10R)  `[P04-pat03]`
*Patologie · Patologie – cytologie a molekulární patologie · autor LEK-P04-03 (patolog)*

Materiál: aspiráty a cell block z EBUS-TBNA ze dne 1. 10. 2026.

Výsledek:
4R: metastáza adenokarcinomu, TTF-1 pozitivní, morfologicky shodný s primárním nádorem plíce.
7: lymfoidní tkáň bez nádorových buněk, vzorek adekvátní (přítomna lymfoidní populace).
10R: lymfoidní tkáň bez nádorových buněk, vzorek adekvátní.

Cell block 4R: podíl nádorových buněk cca 40 %, materiál odeslán k NGS (EGFR, KRAS, BRAF, MET, RET, ERBB2). Výsledek bude doplněn dodatkem.

Závěr: Metastáza adenokarcinomu v uzlině 4R. Uzliny 7 a 10R negativní.

### 2026-10-05 · Dotazník pacienta (PROMs)  `[P04-prom02]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 2 |
| Kde vás bolí? (vlastními slovy) | vpravo na hrudi |
| Únava za poslední týden (0–10) | 6 |
| Nevolnost nebo zvracení (0–10) | 1 |
| Dušnost (0–10) | 7 |
| Nechutenství (0–10) | 6 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 0 |
| Průjem (0–10) | 0 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 6 |
| Potíže se spánkem (0–10) | 5 |
| Jak zvládáte běžný den? | Těžší fyzickou práci nezvládám, lehčí činnosti a domácnost ano |
| Kolik zvládnete ujít? | Jedno patro vyjdu jen se zastávkou |
| Vaše současná hmotnost (kg) | 71 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | -7 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | Hůř se mi dýchá, do prvního patra se musím zastavit. Nechutná mi jíst a hubnu. |
| Alergie nebo nesnášenlivost léků | nevím o žádné |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | nic |
| Co je pro vás v léčbě nejdůležitější? | Nejdůležitější je pro mě co nejdelší život, i za cenu náročnější léčby |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Operaci chci, když to půjde. Bojím se ale, že po vyndání plíce nebudu moct dýchat. Přestat kouřit zkouším, zatím kouřím asi 10 cigaret denně. |
| Podpora v domácnosti | Mám dostatečnou podporu blízkých |

### 2026-10-06 · A-PNEU · Kontrola po dokončení stagingu, nominace na hrudní komisi  `[P04-doc05]`
*Zpráva · Pneumologická ambulance · autor LEK-P04-01 (pneumolog (ošetřující lékař))*

Pacient po doplnění vyšetření dle MDT z 16. 9. 2026.

Subjektivně: Kašel přetrvává, hemoptoe se od srpna neopakovala. Únava. Stále kouří cca 10 cig./den.
Objektivně: ECOG 0. Hmotnost 71 kg, hmotnost stabilní. SpO2 94 %, TK 140/85, AS pravidelná. Poslechově oslabené dýchání vpravo nahoře.

Výsledky:
- PET-CT 25. 9.: aktivní tumor PHL 62 mm (SUVmax 14,2), uzlina 4R (SUVmax 6,1), jinde bez vzdálených metastáz.
- EBUS-TBNA 1. 10.: 4R metastáza adenokarcinomu, 7 a 10R negativní.
- MR mozku 2. 10.: bez metastáz.
- NGS (EGFR) z materiálu EBUS – výsledek se čeká.
- Levá nadledvina – ložisko 14 mm, dle CT pravděpodobně adenom.
Laboratoř 6. 10.: Hb 144, leukocyty 9,2, Na 129, K 4,2, kreatinin 80, albumin 39, CRP 18, CEA 11,5.

Závěr: Adenokarcinom pravého horního laloku G3, cT3 N2 (single-station 4R) M0, st. IIIB. PD-L1 TPS 60 %, ALK a ROS1 negativní, EGFR čeká se. CHOPN GOLD 2.
Plán: hrudně chirurgické konzilium (objednáno na 7. 10.), nominace na hrudní komisi.

### 2026-10-07 · A-HCH · Hrudně chirurgické konzilium – posouzení operability  `[P04-doc06]`
*Zpráva · Hrudně chirurgická ambulance · autor LEK-P04-05 (hrudní chirurg)*

Důvod: posouzení resekability a funkční operability dle doporučení MDT.

Nález: Adenokarcinom pravého horního laloku 62 mm, cT2b N2 (4R, single-station) M0, st. IIIA. Tumor dle CT nepřesahuje interlobium, bez infiltrace hrudní stěny a mediastina. Uzliny 7 a 10R na EBUS negativní.
Funkční vyšetření (25. 8.): FEV1 58 % (1,9 l), DLCO 45 %.
Predikované pooperační hodnoty po lobektomii (segmentová metoda, 16/19 segmentů): ppoFEV1 cca 49 %, ppoDLCO cca 38 %.
Objektivně: ECOG 0, EKG sinusový rytmus, bez známek ischemie.

Závěr: Technicky resekabilní lobektomií pravého horního laloku se systematickou lymfadenektomií. Funkčně hraniční (ppoFEV1 cca 49 %, ppoDLCO cca 38 %) – před definitivním rozhodnutím doporučena spiroergometrie (VO2max).
Důrazně doporučeno přestat kouřit nejméně 4 týdny před případnou operací.
Pacient by operaci chtěl, obává se pooperační dušnosti.

## Laboratoř

ID výsledku: `P04-labNN-<parametr>`, NN = pořadí odběru (sloupec).

| Parametr | Jednotka | Norma | 01: 2026-07-28 | 02: 2026-08-12 | 03: 2026-08-25 | 04: 2026-09-30 | 05: 2026-10-06 |
|---|---|---|---|---|---|---|---|
| Hemoglobin (LOINC 718-7) | g/l | 135–175 | 148 | 147 | 146 | 145 | 144 |
| Leukocyty (LOINC 6690-2) | 10^9/l | 4.0–10.0 | 8.4 | 8.1 | 8.6 | 8.9 | 9.2 |
| Neutrofily absolutně (LOINC 751-8) | 10^9/l | 2.0–7.0 | 5.6 | 5.3 | 5.8 | 6.0 | 6.2 |
| Trombocyty (LOINC 777-3) | 10^9/l | 150–400 | 312 | 305 | 318 | 326 | 334 |
| Kreatinin (LOINC 14682-9) | µmol/l | 44–104 | 82 | 84 | 83 | 81 | 80 |
| Sodík (LOINC 2951-2) | mmol/l | 136–145 | 136 | 135 ↓ | 133 ↓ | 131 ↓ | 129 ↓ |
| Draslík (LOINC 2823-3) | mmol/l | 3.5–5.1 | 4.3 | 4.4 | 4.2 | 4.1 | 4.2 |
| ALT (LOINC 1742-6) | µkat/l | 0.1–0.78 | 0.42 | 0.4 | 0.44 | 0.43 | 0.45 |
| AST (LOINC 1920-8) | µkat/l | 0.1–0.72 | 0.38 | 0.36 | 0.39 | 0.4 | 0.41 |
| ALP (LOINC 6768-6) | µkat/l | 0.66–2.2 | 1.32 | 1.35 | 1.38 | 1.41 | 1.44 |
| Bilirubin celkový (LOINC 14631-6) | µmol/l | 2–21 | 9 | 10 | 9 | 8 | 9 |
| Albumin (LOINC 1751-7) | g/l | 35–52 | 42 | 41 | 41 | 40 | 39 |
| CRP (LOINC 1988-5) | mg/l | 0–5 | 12 ↑ | 14 ↑ | 13 ↑ | 16 ↑ | 18 ↑ |
| LD (LOINC 14804-9) | µkat/l | 2.25–3.75 | 3.2 | 3.3 | 3.4 | 3.6 | 3.7 |
| CEA (LOINC 2039-6) | µg/l | 0–5.0 | 8.2 ↑ | — | 9.0 ↑ | — | 11.5 ↑ |

## Strukturované nálezy (ECOG, biomarkery, staging, hmotnost)

- 2026-07-28 `[P04-ecog01]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P04-doc01`
- 2026-07-28 `[P04-vaha01]` Hmotnost 78 kg · zdroj `P04-doc01`
- 2026-08-20 `[P04-bm01]` PD-L1 (22C3): TPS 60 % (vzorek: bronchoskopická biopsie PHL) · zdroj `P04-pat02`
- 2026-08-20 `[P04-bm02]` ALK (IHC D5F3): negativní (vzorek: bronchoskopická biopsie PHL) · zdroj `P04-pat02`
- 2026-08-20 `[P04-bm03]` ROS1 (IHC D4D6): negativní (vzorek: bronchoskopická biopsie PHL) · zdroj `P04-pat02`
- 2026-08-20 `[P04-bm04]` EGFR (NGS): nevyšetřeno – vzorek nedostatečný pro NGS, doporučeno opakovat z dalšího materiálu (vzorek: bronchoskopická biopsie PHL) · zdroj `P04-pat02`
- 2026-08-25 `[P04-vaha02]` Hmotnost 76 kg · zdroj `P04-doc03`
- 2026-08-25 `[P04-spiro01]` FEV1: 1,9 l (58 % náležité hodnoty) · zdroj `P04-doc03`
- 2026-08-25 `[P04-spiro02]` DLCO: 45 % náležité hodnoty · zdroj `P04-doc03`
- 2026-10-05 `[P04-bm05]` EGFR (NGS): vyšetření probíhá – výsledek k datu nominace nedostupný (vzorek: cell block EBUS-TBNA 4R) · zdroj `P04-pat03`
- 2026-10-06 `[P04-ecog02]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P04-doc05`
- 2026-10-06 `[P04-vaha03]` Hmotnost 71 kg · zdroj `P04-doc05`
- 2026-10-06 `[P04-tnm01]` TNM (klinické): cT3 cN2 (single-station 4R) cM0, stadium IIIB (TNM 8. vyd.) · zdroj `P04-doc05`
- 2026-10-06 `[P04-kour01]` Kouření: aktivní kuřák, cca 10 cig./den, 40 balíčkoroků · zdroj `P04-doc05`
- 2026-10-07 `[P04-ecog03]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P04-doc06`
- 2026-10-07 `[P04-tnm02]` TNM (klinické): cT2b cN2 cM0, stadium IIIA (uvedeno v hrudně chirurgickém konziliu) · zdroj `P04-doc06`
- 2026-10-07 `[P04-spiro03]` ppoFEV1 (predikovaná pooperační hodnota po lobektomii): cca 49 % · zdroj `P04-doc06`
- 2026-10-07 `[P04-spiro04]` ppoDLCO (predikovaná pooperační hodnota po lobektomii): cca 38 % · zdroj `P04-doc06`

## Léky

- `[P04-med01]` tiotropium (ATC R03BB04) – 18 µg inh. 1× denně · od 2019-05-14
- `[P04-med02]` formoterol + budesonid (ATC R03AK07) – 4,5/160 µg 2 vdechy 2× denně · od 2021-03-02
- `[P04-med03]` amlodipin (ATC C08CA01) – 5 mg 1-0-0 · od 2015-06-10

## Výkony a radioterapie

- `[P04-proc01]` 2026-08-12 · Flexibilní bronchoskopie s kleštovou biopsií, kartáčkovou cytologií a BAL
- `[P04-proc02]` 2026-10-01 · EBUS-TBNA mediastinálních uzlin (4R, 7, 10R)

