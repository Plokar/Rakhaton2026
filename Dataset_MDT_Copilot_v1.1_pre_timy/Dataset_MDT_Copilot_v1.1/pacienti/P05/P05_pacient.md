# Pacientka P05 – metastatický HR+/HER2-low karcinom prsu s variantou BRCA2 – PARP inhibitor ve studii, opakovaná anémie G3

> **Fiktivní pacient.** Vytvořeno pro hackathon Rakathon 2026 (MDT Copilot). Neodpovídá žádné skutečné osobě. Klinicky neověřeno – nepoužívat pro péči o pacienty.

- **Pohlaví:** žena · **rok narození:** 1958 · **věk k datu MDT:** 68
- **Identifikátor ve FHIR:** `Patient/P05` · každý záznam níže nese ID zdroje v hranatých závorkách, např. `[P05-doc01]`.

## Diagnózy
- `[P05-dg1]` **C50.4** Zhoubný novotvar horního zevního kvadrantu prsu · morfologie ICD-O-3 8500/3 Invazivní karcinom NST (duktální)
  - klinické TNM: cT2 cN2a cM0, stadium IIIA (cca před 12 lety, dle dokumentace)
- `[P05-dg2]` **C78.7** Sekundární zhoubný novotvar jater a intrahepatálních žlučovodů · od 2019-05
- `[P05-dg3]` **C79.5** Sekundární zhoubný novotvar kosti a kostní dřeně · od 2019-05
- `[P05-dg4]` **C77.8** Sekundární zhoubný novotvar mízních uzlin více oblastí · od 2026-02-19
- `[P05-ae1]` **D64.8** Jiné určené anémie – anémie při léčbě PARP inhibitorem (CTCAE G3) · od 2026-08-17

## Nominace na MDT (žádanka)

`[P05-zad01]` · stav **Naplánovaná** · plánovaný termín MDT **2026-10-21**

| Položka | Obsah |
|---|---|
| Datum vytvoření | 2026-10-08 |
| Žádající lékař / pracoviště | LEK-P05-01 (klinický onkolog – studijní ambulance KOC (ošetřující lékař)), Komplexní onkologické centrum – studijní ambulance (klinická hodnocení) |
| Požadované zaměření MDT | Mamární komise – karcinom prsu, s účastí molekulárního tumor boardu |
| Typ projednání | Restaging / hodnocení odpovědi |
| Priorita | běžná |
| Požadovaný termín (nejpozději) | 2026-10-23 |
| Typ klinické otázky | Systémová léčba, Klinická studie |
| **Otázka pro MDT** | **Pacientka ve studii RKT-06 ORION-HRR (PARP inhibitor – indikace podle patogenní varianty BRCA2 nalezené v nádoru, původ somatický/zárodečný neurčen) má po 3 cyklech parciální odpověď, ale opakovanou anémii G3 vyžadující transfuze (17. 8. a 28. 9. 2026), léčba je přerušena. Pokračovat ve studijní léčbě ve 2. redukci dávky (200 mg 2× denně, nejnižší úroveň protokolu), nebo léčbu změnit (jiná linie podle biomarkerů a předchozí léčby)? Zárodečný původ varianty BRCA2 dosud neověřen – doporučit genetické vyšetření?** |
| Diagnózy | `P05-dg1`, `P05-dg2`, `P05-dg3`, `P05-dg4`, `P05-ae1` |
| Histologie a grade | Invazivní karcinom NST pravého prsu; metastáza jater S4b (10. 3. 2026): G2, ER 100 %, PR 10 %, HER2 1+ (HER2-low), Ki-67 60 % |
| Relevantní komorbidity a současný stav | Bez chronických interních onemocnění. Opakovaná anémie G3 při PARP inhibitoru (2× transfuze 2 TU). Kostní metastáza sterna – kyselina zoledronová. ECOG 1. |
| Preference pacienta | Hodnotí léčbu jako účinnou, ale únavu špatně snáší; přeje si probrat jiné možnosti. Zvažuje genetické vyšetření kvůli dceři. |
| Pacient informován o projednání | ano |
| Předchozí MDT | `P05-mdt02` |

**Předchozí onkologická léčba**
- [Chemoterapie] Primární léčba: neoadjuvantní chemoterapie, mastektomie vpravo s disekcí pravé axily, adjuvantní chemoterapie, radioterapie hrudní stěny vpravo, krátce inhibitor aromatázy (cca před 12 lety – cca před 11 lety)
- [Hormonální léčba] 1. linie: letrozol + palbociklib (2019-06 – 2022-03)
- [Hormonální léčba] 2. linie: fulvestrant (2022-04 – 2023-02)
- [Chemoterapie] 3. linie: paklitaxel týdně (2023-03 – 2024-07)
- [Hormonální léčba] 4. linie: everolimus + exemestan (progrese – vícečetné jaterní metastázy, uzliny) (2024-08 – 2026-02-26)
- [Cílená léčba] 5. linie: RKT-PARPi ve studii RKT-06 ORION-HRR – 300 mg 2× denně, od 31. 8. 2026 250 mg 2× denně; přerušeno 17.–31. 8. a od 28. 9. 2026 pro anémii G3 (2026-05-11 – dosud)

**Podklady (odkazy):** `P05-pat01`, `P05-pat02`, `P05-img03`, `P05-img04`, `P05-doc09`, `P05-doc10`, `P05-lab07`, `P05-bm07`, `P05-bm09`, `P05-bm14`, `P05-ecog05`

## Chronologie dokumentace

### 2026-02-02 · A-ONK · Ambulantní onkologická kontrola – vzestup CA 15-3, nové ložisko v játrech  `[P05-doc01]`
*Zpráva · Ambulance klinické onkologie – regionální pracoviště · autor LEK-P05-02 (klinický onkolog – regionální onkologické pracoviště)*

Dlouhodobě sledovaná pacientka s invazivním karcinomem NST pravého prsu, luminal B (ER 100 %, PR 10 %, HER2 negativní – IHC 1+, Ki-67 40 %), diagnostikovaným cca před 12 lety ve stadiu IIIA (cT2 N2a M0).
Primární léčba: neoadjuvantní chemoterapie, mastektomie vpravo s disekcí pravé axily, adjuvantní chemoterapie a radioterapie hrudní stěny a regionálních uzlin vpravo, adjuvantní inhibitor aromatázy podáván jen několik měsíců (ukončen pro artralgie).
Od 05/2019 metastatické onemocnění jater a skeletu (sternum). Paliativní léčba: 1. linie letrozol + palbociklib (06/2019–03/2022), 2. linie fulvestrant (04/2022–02/2023), 3. linie paklitaxel týdně (03/2023–07/2024), 4. linie everolimus + exemestan od 08/2024. Kyselina zoledronová á 12 týdnů.

Subjektivně: bez potíží, pracuje jako úřednice na zkrácený úvazek. Stomatologická kontrola před půl rokem bez nálezu.
Objektivně: ECOG 0, jizva po mastektomii vpravo klidná, bez známek lokální recidivy.
Laboratoř: CA 15-3 v posledních měsících postupně stoupá, nyní 72 kU/l, CEA 6,4 µg/l, KO a jaterní testy v normě.
CT hrudníku, břicha a pánve (26. 1. 2026, spádové pracoviště): nové subkapsulární ložisko v jaterním segmentu S4b cca 21 mm, ostatní drobná jaterní ložiska a sklerotické ložisko sterna beze změny.

Závěr: Progrese na 4. linii – nové dominantní ložisko S4b při známých jaterních a kostních metastázách, vzestup CA 15-3.
Plán: Projednat v digestivním onkologickém semináři KOC – možnost lokální léčby (SBRT, radiofrekvenční ablace). Před seminářem doplnit MR jater s hepatospecifickou k. l. a PET/CT k posouzení celkového rozsahu onemocnění – objednáno. Everolimus + exemestan zatím ponechán.

### 2026-02-16 · RDG · MR jater s hepatospecifickou k. l.  `[P05-img01]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P05-03 (radiolog)*

Indikace: nové ložisko S4b na CT, zvažována lokální léčba – upřesnit počet a charakter ložisek.

Nález: V játrech vícečetná ložiska s restrikcí difuze a defektem v hepatobiliární fázi, charakteru metastáz:
- S4b subkapsulárně 23 mm (dominantní)
- S7 12 mm
- S6 9 mm
- S2 8 mm
- dalších nejméně 5 ložisek do 5 mm v obou lalocích
Portální a jaterní žíly průchodné, žlučové cesty nedilatované. Bez ascitu.

Závěr: Vícečetné metastatické postižení obou jaterních laloků (nejméně 9 ložisek), nejde o solitární ložisko S4b.

### 2026-02-19 · NM · PET/CT s 18F-FDG – celotělové  `[P05-img02]`
*Zobrazení · Oddělení nukleární medicíny – PET centrum · autor LEK-P05-04 (lékař nukleární medicíny)*

Indikace: posouzení rozsahu onemocnění před rozhodnutím o lokální léčbě jaterní metastázy.

Nález: Zvýšená akumulace FDG v ložiscích obou jaterních laloků, nejvýrazněji S4b (SUVmax 9,8) a S7 (SUVmax 6,1).
Mediastinum: subkarinální uzlina, krátká osa 15 mm, SUVmax 5,4.
Retroperitoneum: paraaortální uzlina vlevo v úrovni L2, krátká osa 14 mm, SUVmax 4,9.
Skelet: sklerotické ložisko v těle sterna 18 mm bez zvýšené akumulace (metabolicky inaktivní, odpovídá léčené metastáze). Jiná ložiska ve skeletu nezobrazena.
Plíce bez ložisek. Mozek nehodnocen (fyziologická akumulace).

Závěr: Metabolicky aktivní metastázy jater, uzlin mediastina a retroperitonea. Sklerotická metastáza sterna stacionární, metabolicky neaktivní.

### 2026-02-26 · MDT · Záznam MDT – Digestivní onkologický seminář – jaterní metastázy  `[P05-mdt01]`
*Předsedající LEK-P05-07 · účastníci: klinický onkolog, klinický onkolog, hepatobiliární chirurg, radiolog, radiační onkolog, gastroenterolog · pacient přítomen: ne*

**Typ projednání:** Progrese / recidiva  
**Projednaná otázka:** Je u nového dominantního ložiska v jaterním segmentu S4b indikována lokální léčba (SBRT, radiofrekvenční ablace)?  
**Klinické zhodnocení:** Metastatický karcinom pravého prsu (luminal B) se známými jaterními a kostními metastázami, na 4. linii everolimus + exemestan. Na CT 26. 1. 2026 nové subkapsulární ložisko S4b 21 mm a vzestup CA 15-3. Doplněná MR jater (16. 2.) prokázala vícečetné metastázy v obou lalocích (S4b 23 mm, S7 12 mm, další menší), PET/CT (19. 2.) metabolicky aktivní uzliny subkarinálně a paraaortálně, sklerotické ložisko sterna bez akumulace. Asymptomatická, ECOG 0.  
**Léčebný záměr:** Paliativní  
**Doporučený postup:**
1. [Diagnostika] CT-navigovaná biopsie ložiska S4b – histologie, ER/PR/HER2, Ki-67 a rozšířené NGS – co nejdříve
2. [Jiná systémová léčba] Ukončit everolimus + exemestan pro progresi; další systémovou léčbu zvolit podle výsledku NGS – po výsledku NGS, molekulární tumor board

**Klinická studie:** Zvážit podle výsledku NGS.

**Závěr MDT:** Vícečetné jaterní a uzlinové postižení – lokální léčba ložiska S4b není indikována. Biopsie S4b s NGS, změna systémové léčby podle výsledku.

**Rozhodnutí o léčbě** `[P05-mdt01-rozhodnuti]` (2026-03-02, LEK-P05-02): Ukončení everolimu a exemestanu (26. 2. 2026), objednána CT-navigovaná biopsie S4b na 10. 3. 2026 · stanovisko pacienta: Souhlasí

### 2026-03-10 · PAT-B · Biopsie jaterního ložiska S4b (CT-navigovaná) včetně receptorového profilu  `[P05-pat01]`
*Patologie · Patologie – bioptická laboratoř · autor LEK-P05-05 (patolog)*

Materiál: 3 válečky jaterní tkáně z CT-navigované biopsie ložiska S4b, délka 8–14 mm.

Mikroskopicky: Ve všech válečcích infiltrace karcinomem v solidních trámcích a hnízdech, morfologicky i imunofenotypově odpovídající metastáze invazivního karcinomu prsu nespecifického typu (NST), středního stupně (G2). GATA3 pozitivní, CK7 pozitivní, CK20 negativní.

Imunohistochemie:
ER pozitivní 100 % (silná intenzita)
PR pozitivní 10 % (slabá až střední intenzita)
HER2 IHC 1+ (slabá neúplná membránová reaktivita v části nádorových buněk) – kritéria HER2 pozitivity nesplněna; dle současné klasifikace HER2-low. ISH není indikována. Shodně s primárním nádorem (HER2 IHC 1+).
Ki-67 cca 60 %

Závěr: Metastáza hormonálně dependentního invazivního karcinomu prsu NST v játrech, G2, HER2-low. Materiál vhodný k rozšířenému molekulárnímu vyšetření (NGS) – předáno na molekulární patologii.

KLASIFIKACE: Topografie (ICD-O-3) C22.0, Morfologie (ICD-O-3) 8500/6

### 2026-04-08 · PAT-M · Komplexní molekulárně-genetické vyšetření nádoru (NGS panel)  `[P05-pat02]`
*Patologie · Patologie – molekulární patologie · autor LEK-P05-06 (molekulární patolog)*

Materiál: parafinový blok z biopsie jaterní metastázy S4b (10. 3. 2026), podíl nádorových buněk cca 50 %.
Metoda: NGS – rozšířený pan-nádorový panel (DNA + RNA), pouze nádorová tkáň (bez párového vzorku krve).

Výsledek:
BRCA2: patogenní frameshift varianta c.5946delT, p.(Ser1982Argfs*22), alelová frekvence (VAF) 47 %.
POLE: nonsense varianta mimo exonukleázovou doménu, klinický význam nejasný.
ESR1: detekováno několik fúzí zahrnujících gen ESR1 (RNA). Bodové mutace ESR1 v tkáni neprokázány.
Změny počtu kopií: amplifikace CCND1, FGF19, FGF3, MYC, MDM4.
PIK3CA, AKT1, PTEN: bez patogenní varianty.
Mikrosatelitová stabilita: MSS. Mutační nálož (TMB): 12,6 mut/Mb (zvýšená).

Interpretace: Varianta BRCA2 je prediktivní pro možnou citlivost k inhibitorům PARP. Vyšetření pouze nádorové tkáně nerozliší somatický a zárodečný původ – alelová frekvence kolem 50 % je slučitelná se zárodečnou variantou.
Doporučení: genetické poradenství a vyšetření zárodečné varianty BRCA2 z krve; interpretace na molekulárním tumor boardu.

### 2026-04-15 · MDT · Záznam MDT – Molekulární tumor board  `[P05-mdt02]`
*Předsedající LEK-P05-08 · účastníci: klinický onkolog, molekulární patolog, patolog, klinický onkolog, klinický genetik · pacient přítomen: ne*

**Typ projednání:** Progrese / recidiva  
**Projednaná otázka:** Interpretace NGS jaterní metastázy a návrh cílené léčby.  
**Klinické zhodnocení:** Postmenopauzální pacientka s luminálním karcinomem pravého prsu, po 4 liniích paliativní léčby pro metastázy jater, skeletu a uzlin, progrese 02/2026. Metastáza S4b: ER 100 %, PR 10 %, HER2 1+ (HER2-low), Ki-67 60 %. NGS: patogenní frameshift varianta BRCA2 nalezená v nádoru (původ somatický/zárodečný neurčen), VAF 47 %; MSS, TMB 12,6 mut/Mb, fúze ESR1, PIK3CA/AKT1/PTEN bez varianty. ECOG 0.  
**Léčebný záměr:** Paliativní  
**Doporučený postup:**
1. [Cílená léčba] PARP inhibitor v rámci klinické studie RKT-06 ORION-HRR (alterace HRR v nádoru) – odeslat do studijní ambulance KOC ke screeningu – co nejdříve
2. [Imunoterapie] Imunoterapii (zvýšená TMB) zvážit v některé z dalších linií

**Doplnit:** genetika – Genetické poradenství a vyšetření zárodečné varianty BRCA2 z krve – posouzení dědičnosti a rizika pro příbuzné

**Klinická studie:** RKT-06 ORION-HRR – doporučen screening.

**Závěr MDT:** Patogenní varianta BRCA2 nalezená v nádoru (původ somatický/zárodečný neurčen) – pacientka je kandidátkou léčby PARP inhibitorem ve studii RKT-06 ORION-HRR. Současně genetické poradenství a germinální test BRCA2. Doporučení je podkladem pro ošetřujícího onkologa.

**Rozhodnutí o léčbě** `[P05-mdt02-rozhodnuti]` (2026-04-20, LEK-P05-02): Odeslání do studijní ambulance KOC ke screeningu RKT-06 ORION-HRR · stanovisko pacienta: Souhlasí – souhlasí se screeningem do studie, genetické vyšetření chce probrat s rodinou

### 2026-04-27 · A-ST · Vstupní vyšetření ve studijní ambulanci – screening do studie RKT-06 ORION-HRR  `[P05-doc02]`
*Zpráva · Studijní ambulance KOC – klinická hodnocení · autor LEK-P05-01 (klinický onkolog – studijní ambulance KOC (ošetřující lékař))*

Pacientka odeslána z regionálního pracoviště po doporučení molekulárního tumor boardu (15. 4. 2026) k posouzení zařazení do klinické studie RKT-06 ORION-HRR s perorálním inhibitorem PARP.

Revize dokumentace: invazivní karcinom NST pravého prsu, luminal B, diagnostikován cca před 12 lety ve stadiu IIIA, po neoadjuvantní chemoterapii, mastektomii vpravo s disekcí pravé axily, adjuvantní chemoterapii, radioterapii a krátké hormonální léčbě. Od 05/2019 metastázy jater a skeletu, vystřídány 4 linie paliativní léčby (letrozol + palbociklib, fulvestrant, paklitaxel, everolimus + exemestan). Poslední linie ukončena 26. 2. 2026 pro progresi, od té doby bez protinádorové léčby.
Biopsie S4b (10. 3. 2026): ER 100 %, PR 10 %, HER2 1+ (HER2-low), Ki-67 60 %. NGS: patogenní varianta BRCA2 nalezená v nádoru (původ somatický/zárodečný neurčen), VAF 47 %, MSS, TMB 12,6 mut/Mb.
OA: bez chronických interních onemocnění. FA: kyselina zoledronová 4 mg i.v. á 12 týdnů, kalcium + vitamin D, paracetamol při bolesti. Alergie neudává. Nekuřačka, alkohol příležitostně.
RA: matka zemřela v 58 letech na „nádor v břiše“, blíže neznámo; dcera zdravá.
Sociálně: úřednice, zkrácený úvazek, žije s manželem.

Subjektivně: bez obtíží. Objektivně: ECOG 0, hmotnost 74 kg, TK 148/88 (pacientka udává obavy z vyšetření), játra nehmatná, bez periferních otoků.
Laboratoř: Hb 121 g/l, neutrofily 3,4, trombocyty 232, ALT 0,84 a AST 0,81 µkat/l (lehce zvýšené), bilirubin 10, kreatinin 70, CA 15-3 104 kU/l, CEA 8,9 µg/l.

Závěr: Splňuje předběžná vstupní kritéria studie RKT-06 (varianta BRCA2 nalezená v nádoru (původ somatický/zárodečný neurčen), 4 předchozí linie, ECOG 0, KO v mezích protokolu). Po vysvětlení rizik a přínosů podepsán informovaný souhlas.
Plán: vstupní CT hrudníku, břicha a pánve, EKG (3× po sobě), konzultace klinického farmaceuta. Genetické poradenství doporučené tumor boardem – objednat do genetické ambulance.

### 2026-05-04 · A-KF · Klinicko-farmaceutické vyšetření před zahájením studijní léčby  `[P05-doc03]`
*Zpráva · Klinická farmacie · autor LEK-P05-10 (klinický farmaceut)*

Důvod: vstupní léková anamnéza před zahájením studijního PARP inhibitoru (metabolizován převážně jaterními cytochromy CYP3A).

Léková anamnéza: kyselina zoledronová 4 mg i.v. á 12 týdnů, kalcium + vitamin D 1-0-0, příležitostně paracetamol. Doplňky stravy ani bylinné přípravky dle pacientky neužívá.

Zhodnocení: Klinicky významné lékové interakce se studijním přípravkem nezjištěny. Riziko lékových problémů nízké, farmakoterapie nevyžaduje úpravu.
Doporučení: Vyhnout se samoléčbě, zejména přípravkům ovlivňujícím jaterní metabolismus (třezalka tečkovaná, grapefruitová šťáva). Každý nově užívaný lék, doplněk či bylinu konzultovat se studijním týmem.

### 2026-05-06 · RDG · CT hrudníku, břicha a pánve s k. l. – vstupní vyšetření (baseline studie)  `[P05-img03]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P05-03 (radiolog)*

Technika: CT hrudníku, břicha a pánve v portální fázi po i.v. aplikaci k. l. Srovnání s MR jater 16. 2. 2026 a PET/CT 19. 2. 2026.

Hrudník: Plicní parenchym bez ložisek. Subkarinální uzlina krátká osa 17 mm (dříve 15 mm). Bez fluidothoraxu.
Játra: vícečetná hypodenzní ložiska v obou lalocích:
- S4b: 26 mm (cílová léze 1)
- S7: 15 mm (cílová léze 2)
- S6 9 mm, S2 8 mm a další drobná ložiska do 5 mm (necílové)
Retroperitoneum: paraaortální uzlina vlevo v úrovni L2, krátká osa 16 mm.
Skelet: sklerotické ložisko těla sterna 18 mm, beze změny.
Mozek nevyšetřován.

Cílové léze (RECIST 1.1): S4b 26 mm, S7 15 mm, subkarinální uzlina 17 mm (krátká osa), paraaortální uzlina 16 mm (krátká osa).
Závěr: Součet cílových lézí 74 mm. Mírná progrese jaterních ložisek a uzlin oproti únoru (bez léčby).

### 2026-05-10 · Dotazník pacienta (PROMs)  `[P05-prom01]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 1 |
| Kde vás bolí? (vlastními slovy) | občas záda po delším sezení |
| Únava za poslední týden (0–10) | 2 |
| Nevolnost nebo zvracení (0–10) | 0 |
| Dušnost (0–10) | 0 |
| Nechutenství (0–10) | 1 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 2 |
| Průjem (0–10) | 0 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 6 |
| Potíže se spánkem (0–10) | 4 |
| Jak zvládáte běžný den? | Zvládám vše jako před nemocí, i fyzicky náročné věci |
| Kolik zvládnete ujít? | Ujdu bez potíží delší vzdálenost i do schodů |
| Vaše současná hmotnost (kg) | 74 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | -0.5 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | nic nového, jen trochu brní konečky prstů jako dřív |
| Alergie nebo nesnášenlivost léků | nevím o žádné |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | nic |
| Co je pro vás v léčbě nejdůležitější? | Obojí je pro mě stejně důležité |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Chci zkusit studii, pokud mi může pomoct. Ráda bych dál chodila do práce aspoň na zkrácený úvazek. |
| Podpora v domácnosti | Mám dostatečnou podporu blízkých |

### 2026-05-11 · ONK-L · Jednodenní hospitalizace – zahájení studijní léčby RKT-06 ORION-HRR (C1D1)  `[P05-doc04]`
*Zpráva · Onkologická klinika – jednodenní hospitalizace · autor LEK-P05-01 (klinický onkolog – studijní ambulance KOC (ošetřující lékař))*

Pacientka s metastatickým HR+/HER2-low karcinomem prsu a patogenní variantou BRCA2 nalezenou v nádoru (původ somatický/zárodečný neurčen) přijata k monitorovanému prvnímu podání studijního PARP inhibitoru (RKT-06 ORION-HRR), cyklus 1, den 1.

Při přijetí v dobrém stavu, bez známek infekce, ECOG 0. Laboratoř ze screeningu (27. 4.) v mezích protokolu, lehce zvýšené aminotransferázy (ALT 0,84 µkat/l) a nádorové markery. Vstupní CT (6. 5.): vícečetné jaterní metastázy s dominantním ložiskem S4b, uzliny mediastina a retroperitonea, stabilní sklerotické ložisko sterna.

Ráno nalačno podána první dávka RKT-PARPi 300 mg p. o., večer druhá dávka doma (300 mg 2× denně, cyklus 28 dní). Po podání opakovaně vitální funkce a EKG dle protokolu – bez klinicky významných změn. TK při přijetí 150/90, při opakovaných měřeních 132/80 – pravděpodobně syndrom bílého pláště; doporučeno domácí měření.
Během observace bez nežádoucích účinků, pouze nervozita ze zahájení léčby.

Edukace: hematologická toxicita (anémie, neutropenie, trombocytopenie), únava, nevolnost; při horečce, krvácení nebo dušnosti ihned kontaktovat pracoviště. Pacientka vede deník užívání.
Propuštěna domů ve stabilizovaném stavu. Kontroly dle protokolu (C1D8, C1D15, dále D1 každého cyklu).

### 2026-07-06 · A-ST · Kontrola ve studii – C3D1  `[P05-doc05]`
*Zpráva · Studijní ambulance KOC – klinická hodnocení · autor LEK-P05-01 (klinický onkolog – studijní ambulance KOC (ošetřující lékař))*

Zahájení 3. cyklu studijní léčby RKT-PARPi 300 mg 2× denně.

Subjektivně: na léčbu si zvykla, mírná únava odpoledne, občasná lehká nauzea bez zvracení, antiemetika nepotřebuje. Pracuje na zkrácený úvazek. Compliance dle deníku 100 %.
Objektivně: ECOG 0, hmotnost 73,5 kg, TK 130/80, bez krvácivých projevů.
Laboratoř: Hb 103 g/l (anémie G1), leukocyty 3,6 (G1), neutrofily 2,0, trombocyty 168, ALT 0,70, kreatinin 76. CA 15-3 69 kU/l (pokles ze 104), CEA 6,1 µg/l.

Závěr: Toxicita: anémie G1, leukopenie G1. Podmínky protokolu pro pokračování splněny, dávka beze změny.
Plán: restagingové CT po 3. cyklu (konec 7/2026).

### 2026-07-30 · RDG · CT hrudníku, břicha a pánve s k. l. – restaging po 3 cyklech  `[P05-img04]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P05-03 (radiolog)*

Srovnání s CT 6. 5. 2026 (baseline studie).

Hrudník: subkarinální uzlina krátká osa 11 mm (dříve 17 mm). Plíce bez ložisek.
Játra:
- S4b: 15 mm (dříve 26 mm) – cílová léze 1
- S7: 8 mm (dříve 15 mm) – cílová léze 2
- S6 není jednoznačně patrné, S2 5 mm, ostatní drobná ložiska nezřetelná
Retroperitoneum: paraaortální uzlina krátká osa 10 mm (dříve 16 mm).
Skelet: sklerotické ložisko sterna beze změny. Nová ložiska nezjištěna.

Závěr: Parciální odpověď dle RECIST 1.1 – součet cílových lézí 44 mm (baseline 74 mm, pokles o 41 %). Necílové léze regredují, bez nových ložisek.

### 2026-08-03 · A-ST · Kontrola ve studii – C4D1, výsledek restagingu  `[P05-doc06]`
*Zpráva · Studijní ambulance KOC – klinická hodnocení · autor LEK-P05-01 (klinický onkolog – studijní ambulance KOC (ošetřující lékař))*

Restagingové CT 30. 7. 2026: parciální odpověď dle RECIST 1.1 (součet cílových lézí 74 → 44 mm), bez nových ložisek.

Subjektivně: únava mírná, přetrvává, jinak bez obtíží. Bolesti kostí ani dušnost neudává.
Objektivně: ECOG 0–1, bez krvácivých projevů.
Krevní obraz: lehká anémie, podmínky protokolu pro pokračování splněny.

Závěr: Parciální odpověď na studijní léčbu. Zahájen 4. cyklus v nezměněné dávce 300 mg 2× denně. Další restaging po 6. cyklu.

### 2026-08-17 · A-ST · Mimořádná kontrola ve studii – anémie G3, přerušení léčby  `[P05-doc07]`
*Zpráva · Studijní ambulance KOC – klinická hodnocení · autor LEK-P05-01 (klinický onkolog – studijní ambulance KOC (ošetřující lékař))*

Pacientka kontaktovala ambulanci pro výraznou únavu a námahovou dušnost (C4D15).

Objektivně: bledá, afebrilní, TK 115/70, TF 104/min, bez krvácivých projevů, ECOG 1.
Laboratoř: Hb 76 g/l, leukocyty 3,1, neutrofily 1,7, trombocyty 142, kreatinin 79, bilirubin 12.

Závěr: Anémie G3 (Hb < 80 g/l) při léčbě PARP inhibitorem, leukopenie a neutropenie G1, trombocytopenie G1.
Postup dle protokolu: studijní léčba přerušena od 17. 8. 2026. Podány 2 TU erytrocytů bez komplikací.
Plán: kontrola KO za 2 týdny; při Hb ≥ 90 g/l pokračovat v redukované dávce 250 mg 2× denně.

### 2026-08-31 · A-ST · Kontrola ve studii – obnovení léčby v redukované dávce (C5D1)  `[P05-doc08]`
*Zpráva · Studijní ambulance KOC – klinická hodnocení · autor LEK-P05-01 (klinický onkolog – studijní ambulance KOC (ošetřující lékař))*

Kontrola 2 týdny po přerušení studijní léčby a transfuzi.

Subjektivně: únava ustoupila, dušnost jen při rychlé chůzi do schodů.
Objektivně: ECOG 0–1, TF 82/min.
Laboratoř: Hb 98 g/l, leukocyty 3,9, neutrofily 2,3, trombocyty 175, CA 15-3 48 kU/l, CEA 5,0 µg/l.

Závěr: Hb ≥ 90 g/l – podmínka protokolu pro obnovení léčby splněna. Zahájen 5. cyklus v 1. redukci dávky: RKT-PARPi 250 mg 2× denně.

### 2026-09-28 · A-ST · Kontrola ve studii – C6D1, opakovaná anémie G3  `[P05-doc09]`
*Zpráva · Studijní ambulance KOC – klinická hodnocení · autor LEK-P05-01 (klinický onkolog – studijní ambulance KOC (ošetřující lékař))*

Plánovaná kontrola před 6. cyklem (dávka 250 mg 2× denně).

Subjektivně: opět větší únava, dušnost při chůzi do schodů. Bez krvácení, bez horečky.
Objektivně: ECOG 1, bledá, TF 98/min.
Laboratoř: Hb 77 g/l, leukocyty 3,3, neutrofily 1,8, trombocyty 151. CA 15-3 57 kU/l, CEA 5,6 µg/l.

Závěr: Opakovaná anémie G3 při redukované dávce. Studijní léčba přerušena od 28. 9. 2026, 6. cyklus nezahájen. Podány 2 TU erytrocytů.
Dle protokolu lze po úpravě Hb ≥ 90 g/l pokračovat ve 2. redukci (200 mg 2× denně, nejnižší úroveň); další anémie G3 při této dávce by znamenala ukončení studijní léčby.
Pacientka léčbu jinak toleruje dobře. Vzhledem k opakované toxicitě při parciální odpovědi navrženo projednání na MDT.

### 2026-10-05 · Dotazník pacienta (PROMs)  `[P05-prom02]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 2 |
| Kde vás bolí? (vlastními slovy) | záda |
| Únava za poslední týden (0–10) | 8 |
| Nevolnost nebo zvracení (0–10) | 2 |
| Dušnost (0–10) | 5 |
| Nechutenství (0–10) | 4 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 2 |
| Průjem (0–10) | 0 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 7 |
| Potíže se spánkem (0–10) | 6 |
| Jak zvládáte běžný den? | Těžší fyzickou práci nezvládám, lehčí činnosti a domácnost ano |
| Kolik zvládnete ujít? | Jedno patro vyjdu jen se zastávkou |
| Vaše současná hmotnost (kg) | 72 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | -1.5 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | Velká únava, při chůzi do schodů se zadýchám a buší mi srdce. Lehčí věci doma zvládnu, ale do práce teď chodím jen na pár hodin. Dvakrát jsem dostala krev. |
| Alergie nebo nesnášenlivost léků | nevím o žádné |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | každý večer třezalkový čaj na spaní, železo z lékárny |
| Co je pro vás v léčbě nejdůležitější? | Nejdůležitější je pro mě kvalita života, i kdyby léčba byla méně účinná |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Studie mi pomohla, nádory se zmenšily, ale takhle unavená to dlouho nevydržím. Chci vědět, jestli je jiná možnost. Nevím, jestli si mám nechat vyšetřit geny kvůli dceři – nikdo mi to zatím nevysvětlil. |
| Podpora v domácnosti | Mám dostatečnou podporu blízkých |

### 2026-10-06 · A-ST · Kontrola v přerušení studijní léčby, nominace na MDT  `[P05-doc10]`
*Zpráva · Studijní ambulance KOC – klinická hodnocení · autor LEK-P05-01 (klinický onkolog – studijní ambulance KOC (ošetřující lékař))*

Pacientka 8 dní po transfuzi, studijní léčba přerušena od 28. 9. 2026.

Subjektivně: únava mírná, léčbu dobře toleruje, bez nevolnosti. Ptá se na další postup.
Objektivně: ECOG 1, hmotnost 72 kg, TK 128/78, TF 84/min, bez otoků, bez krvácivých projevů.
Laboratoř: Hb 92 g/l, leukocyty 3,8, neutrofily 2,2, trombocyty 170, ALT 0,61, bilirubin 10, albumin 37. CA 15-3 63 kU/l, CEA 6,3 µg/l – markery mírně kolísají.
Medikace: kyselina zoledronová á 12 týdnů (poslední 21. 9. 2026), kalcium + vitamin D, paracetamol při bolesti.

Shrnutí: Studijní léčba RKT-PARPi od 11. 5. 2026, po 3 cyklech parciální odpověď (CT 30. 7. 2026). Dvakrát anémie G3 vyžadující transfuzi (17. 8. a 28. 9. 2026), redukce na 250 mg 2× denně. Genetické vyšetření zárodečné varianty BRCA2 dosud neproběhlo.
Závěr: Nominována na mamární komisi s účastí molekulárního tumor boardu – pokračování ve studii v dávce 200 mg 2× denně, nebo změna léčby.

## Laboratoř

ID výsledku: `P05-labNN-<parametr>`, NN = pořadí odběru (sloupec).

| Parametr | Jednotka | Norma | 01: 2026-02-02 | 02: 2026-04-27 | 03: 2026-07-06 | 04: 2026-08-17 | 05: 2026-08-31 | 06: 2026-09-28 | 07: 2026-10-06 |
|---|---|---|---|---|---|---|---|---|---|
| Hemoglobin (LOINC 718-7) | g/l | 120–160 | 128 | 121 | 103 ↓ | 76 ↓ | 98 ↓ | 77 ↓ | 92 ↓ |
| Leukocyty (LOINC 6690-2) | 10^9/l | 4.0–10.0 | 5.8 | 5.4 | 3.6 ↓ | 3.1 ↓ | 3.9 ↓ | 3.3 ↓ | 3.8 ↓ |
| Neutrofily absolutně (LOINC 751-8) | 10^9/l | 2.0–7.0 | 3.6 | 3.4 | 2.0 | 1.7 ↓ | 2.3 | 1.8 ↓ | 2.2 |
| Trombocyty (LOINC 777-3) | 10^9/l | 150–400 | 245 | 232 | 168 | 142 ↓ | 175 | 151 | 170 |
| Kreatinin (LOINC 14682-9) | µmol/l | 44–104 | 72 | 70 | 76 | 79 | 74 | 78 | 75 |
| Bilirubin celkový (LOINC 14631-6) | µmol/l | 2–21 | 9 | 10 | 11 | 12 | 10 | 11 | 10 |
| ALT (LOINC 1742-6) | µkat/l | 0.1–0.78 | 0.62 | 0.84 ↑ | 0.7 | 0.58 | 0.55 | 0.6 | 0.61 |
| AST (LOINC 1920-8) | µkat/l | 0.1–0.72 | 0.55 | 0.81 ↑ | 0.66 | 0.52 | 0.5 | 0.56 | 0.57 |
| ALP (LOINC 6768-6) | µkat/l | 0.66–2.2 | 1.9 | 2.6 ↑ | 2.3 ↑ | 2.0 | 2.0 | 2.1 | 2.1 |
| Albumin (LOINC 1751-7) | g/l | 35–52 | 41 | 39 | 38 | 36 | 37 | 36 | 37 |
| CEA (LOINC 2039-6) | µg/l | 0–5.0 | 6.4 ↑ | 8.9 ↑ | 6.1 ↑ | 5.2 ↑ | 5.0 | 5.6 ↑ | 6.3 ↑ |
| CA 15-3 (LOINC 6875-3) | kU/l | 0–31 | 72 ↑ | 104 ↑ | 69 ↑ | 51 ↑ | 48 ↑ | 57 ↑ | 63 ↑ |

## Strukturované nálezy (ECOG, biomarkery, staging, hmotnost)

- 2026-02-02 `[P05-ecog01]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P05-doc01`
- 2026-02-02 `[P05-bm01]` ER (primární nádor): pozitivní 100 % (vzorek: primární nádor pravého prsu (dle dokumentace)) · zdroj `P05-doc01`
- 2026-02-02 `[P05-bm02]` PR (primární nádor): pozitivní 10 % (vzorek: primární nádor pravého prsu (dle dokumentace)) · zdroj `P05-doc01`
- 2026-02-02 `[P05-bm03]` HER2 IHC (primární nádor): 1+ (v dokumentaci „HER2 negativní“; dle současné klasifikace HER2-low) (vzorek: primární nádor pravého prsu (dle dokumentace)) · zdroj `P05-doc01`
- 2026-02-02 `[P05-bm04]` Ki-67 (primární nádor): 40 % (vzorek: primární nádor pravého prsu (dle dokumentace)) · zdroj `P05-doc01`
- 2026-02-02 `[P05-tnm01]` TNM (klinické): cT2 cN2a cM0, stadium IIIA (TNM 7. vyd.) – primární diagnóza cca před 12 lety, dle dokumentace · zdroj `P05-doc01`
- 2026-02-19 `[P05-tnm02]` TNM (klinické): M1 (játra, skelet, uzliny mediastina a retroperitonea), stadium IV · zdroj `P05-img02`
- 2026-03-10 `[P05-bm05]` ER (metastáza): pozitivní 100 % (vzorek: biopsie jater S4b) · zdroj `P05-pat01`
- 2026-03-10 `[P05-bm06]` PR (metastáza): pozitivní 10 % (vzorek: biopsie jater S4b) · zdroj `P05-pat01`
- 2026-03-10 `[P05-bm07]` HER2 IHC (metastáza): 1+ (HER2-low), ISH neindikována (vzorek: biopsie jater S4b) · zdroj `P05-pat01`
- 2026-03-10 `[P05-bm08]` Ki-67 (metastáza): 60 % (vzorek: biopsie jater S4b) · zdroj `P05-pat01`
- 2026-04-08 `[P05-bm09]` BRCA2 (NGS nádoru): patogenní frameshift varianta c.5946delT p.(Ser1982Argfs*22), VAF 47 % – varianta BRCA2 nalezená v nádoru (původ somatický/zárodečný neurčen) (vzorek: biopsie jater S4b) · zdroj `P05-pat02`
- 2026-04-08 `[P05-bm10]` MSI: MSS (mikrosatelitově stabilní) (vzorek: biopsie jater S4b) · zdroj `P05-pat02`
- 2026-04-08 `[P05-bm11]` TMB: 12,6 mut/Mb (zvýšená) (vzorek: biopsie jater S4b) · zdroj `P05-pat02`
- 2026-04-08 `[P05-bm12]` ESR1 (tkáň, NGS): fúze ESR1; bodové mutace ESR1 v tkáni neprokázány; ctDNA nevyšetřena (vzorek: biopsie jater S4b) · zdroj `P05-pat02`
- 2026-04-08 `[P05-bm13]` PIK3CA / AKT1 / PTEN: bez patogenní varianty (vzorek: biopsie jater S4b) · zdroj `P05-pat02`
- 2026-04-27 `[P05-ecog02]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P05-doc02`
- 2026-04-27 `[P05-vaha01]` Hmotnost 74 kg · zdroj `P05-doc02`
- 2026-07-06 `[P05-ecog03]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P05-doc05`
- 2026-07-06 `[P05-vaha02]` Hmotnost 73.5 kg · zdroj `P05-doc05`
- 2026-08-17 `[P05-anem01]` Anémie (CTCAE) – hodnoceno lékařem: grade 3 · zdroj `P05-doc07`
- 2026-09-28 `[P05-ecog04]` ECOG 1 (omezen(a) při fyzicky náročné činnosti, zvládá lehkou práci) – hodnotil lékař · zdroj `P05-doc09`
- 2026-09-28 `[P05-anem02]` Anémie (CTCAE) – hodnoceno lékařem: grade 3 (opakovaně, při dávce 250 mg 2× denně) · zdroj `P05-doc09`
- 2026-10-06 `[P05-ecog05]` ECOG 1 (omezen(a) při fyzicky náročné činnosti, zvládá lehkou práci) – hodnotil lékař · zdroj `P05-doc10`
- 2026-10-06 `[P05-vaha03]` Hmotnost 72 kg · zdroj `P05-doc10`
- 2026-10-06 `[P05-bm14]` Zárodečná (germinální) varianta BRCA1/2: nevyšetřeno – genetické poradenství doporučené 15. 4. 2026 neproběhlo · zdroj `P05-doc10`

## Léky

- `[P05-med01]` kyselina zoledronová (ATC M05BA08) – 4 mg i.v. á 12 týdnů · od 2019-06-10
- `[P05-med02]` kalcium + cholekalciferol (ATC A12AX) – 500 mg / 400 IU 1-0-0 · od 2019-06-10
- `[P05-med03]` paracetamol (ATC N02BE01) – 500 mg p. o. při bolesti, max. 3 g denně · od 2026-04-27
- `[P05-tx-parp-01…04]` RKT-PARPi (studijní PARP inhibitor) (ATC L01XK) – klinická studie RKT-06 ORION-HRR, 300 mg p. o. 2× denně, cyklus 28 dní (záznam = D1 cyklu, vydání studijní medikace) · podání: 2026-05-11, 2026-06-08, 2026-07-06, 2026-08-03
  - 2026-08-03: C4; podávání přerušeno 17. 8. 2026 – anémie G3 (Hb 76 g/l), transfuze 2 TU
- `[P05-tx-parpred-01…01]` RKT-PARPi (studijní PARP inhibitor) (ATC L01XK) – klinická studie RKT-06 ORION-HRR, 250 mg p. o. 2× denně (1. redukce dávky dle protokolu), cyklus 28 dní · podání: 2026-08-31
  - 2026-08-31: C5 v redukované dávce; přerušeno 28. 9. 2026 – opakovaná anémie G3 (Hb 77 g/l), transfuze 2 TU; C6 nezahájen

## Výkony a radioterapie

- `[P05-proc01]` 2026-03-10 · CT-navigovaná core-cut biopsie jaterního ložiska S4b – provedl LEK-P05-09, bez komplikací
- `[P05-proc02]` 2026-08-17 · Transfuze erytrocytů – 2 TU – anémie G3 (Hb 76 g/l) při léčbě PARP inhibitorem
- `[P05-proc03]` 2026-09-28 · Transfuze erytrocytů – 2 TU – opakovaná anémie G3 (Hb 77 g/l) při redukované dávce PARP inhibitoru

