# Pacient P03 – karcinom sigmatu s jaterními metastázami – resekabilita po konverzní chemoterapii

> **Fiktivní pacient.** Vytvořeno pro hackathon Rakathon 2026 (MDT Copilot). Neodpovídá žádné skutečné osobě. Klinicky neověřeno – nepoužívat pro péči o pacienty.

- **Pohlaví:** muž · **rok narození:** 1959 · **věk k datu MDT:** 67
- **Identifikátor ve FHIR:** `Patient/P03` · každý záznam níže nese ID zdroje v hranatých závorkách, např. `[P03-doc01]`.

## Diagnózy
- `[P03-dg1]` **C18.7** Zhoubný novotvar esovité kličky tlustého střeva (sigmatu) · morfologie ICD-O-3 8140/3 Adenokarcinom NOS · od 2026-04-24
  - klinické TNM: cT3 cN1 cM1a, stadium IVA (2026-05-20)
- `[P03-dg2]` **C78.7** Sekundární zhoubný novotvar jater a intrahepatálních žlučovodů · od 2026-04-28
- `[P03-kom1]` **I25.2** Starý infarkt myokardu (2019, st. p. PCI RIA) · od 2019-03
- `[P03-kom2]` **I10** Esenciální hypertenze
- `[P03-kom3]` **E78.0** Hypercholesterolémie

## Nominace na MDT (žádanka)

`[P03-zad01]` · stav **Naplánovaná** · plánovaný termín MDT **2026-10-21**

| Položka | Obsah |
|---|---|
| Datum vytvoření | 2026-10-06 |
| Žádající lékař / pracoviště | LEK-P03-01 (klinický onkolog (ošetřující lékař)), Onkologická klinika – ambulance klinické onkologie |
| Požadované zaměření MDT | GIT – kolorektální karcinom / hepatobiliární |
| Typ projednání | Restaging / hodnocení odpovědi |
| Priorita | běžná |
| Požadovaný termín (nejpozději) | 2026-10-31 |
| Typ klinické otázky | Indikace operace, Léčebný plán |
| **Otázka pro MDT** | **Jsou jaterní metastázy po 8 cyklech FOLFOX + bevacizumab resekabilní (jednodobě, nebo dvoudobě vč. ložiska S3) a v jakém pořadí řešit primární tumor sigmatu? Pokud ne, jak pokračovat v systémové léčbě?** |
| Diagnózy | `P03-dg1`, `P03-dg2` |
| Histologie a grade | Adenokarcinom sigmatu G2 (biopsie 24. 4. 2026) |
| Relevantní komorbidity a současný stav | IM 2019, st. p. PCI RIA, užívá kyselinu acetylsalicylovou; hypertenze (zhoršená při bevacizumabu); neuropatie G1 po oxaliplatině. ECOG 0. |
| Preference pacienta | Přeje si operaci, pokud je možná; obává se dlouhé pracovní neschopnosti (profesionální řidič). |
| Pacient informován o projednání | ano |
| Předchozí MDT | `P03-mdt01` |

**Předchozí onkologická léčba**
- [Chemoterapie] FOLFOX + bevacizumab, 8 cyklů (8. cyklus s redukcí oxaliplatiny na 75 %) (2026-06-01 – 2026-09-07)

**Podklady (odkazy):** `P03-pat01`, `P03-pat02`, `P03-img01`, `P03-img02`, `P03-img03`, `P03-img04`, `P03-doc07`, `P03-lab06`, `P03-bm01`, `P03-bm04`, `P03-ecog03`

## Chronologie dokumentace

### 2026-04-21 · A-GAST · Koloskopie s biopsií  `[P03-doc01]`
*Zpráva · Gastroenterologická ambulance – endoskopie · autor LEK-P03-02 (gastroenterolog)*

Indikace: pozitivní test na okultní krvácení (screening), anémie lehkého stupně, změna defekace posledních 3 měsíců.

Průběh: Přístroj zaveden do céka, ileocékální chlopeň identifikována. Příprava střeva dobrá (BBPS 8).
V sigmatu ve vzdálenosti cca 25 cm od anu cirkulární exofytický, snadno krvácivý tumor zužující lumen asi na 2/3, endoskop prochází. Odebrány biopsie (6×).
Ve zbytku tračníku 2 drobné polypy do 4 mm v transverzu, odstraněny kleštěmi.

Závěr: Tumor sigmatu suspektní z malignity – histologie odeslána. Polypy transverza odstraněny.
Doporučení: CT hrudníku a břicha s k. l., CEA, kontrola v onkologické ambulanci po výsledku histologie.

### 2026-04-24 · PAT-B · Biopsie tumoru sigmatu  `[P03-pat01]`
*Patologie · Patologie – bioptická laboratoř · autor LEK-P03-03 (patolog)*

Makroskopicky: 6 drobných fragmentů sliznice do 3 mm.

Mikroskopicky: Ve všech fragmentech infiltrace středně diferencovaným adenokarcinomem s tubulární stavbou, s ložisky nekrózy. Zastižena invaze do submukózy; hloubku invaze nelze v bioptickém vzorku plně hodnotit.

Závěr: Adenokarcinom tlustého střeva, středně diferencovaný (G2).
Polypy transverza: tubulární adenomy s low-grade dysplazií.

Doporučení: molekulárně-genetické vyšetření (RAS, BRAF) bude provedeno na žádost onkologa.

KLASIFIKACE: Topografie (ICD-O-3) C18.7, Morfologie (ICD-O-3) 8140/3

### 2026-04-28 · RDG · CT hrudníku, břicha a pánve s k. l. – staging  `[P03-img01]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P03-04 (radiolog)*

Technika: CT hrudníku, břicha a pánve v portální fázi po i.v. aplikaci k. l.

Hrudník: Plicní parenchym bez ložiskových změn. Mediastinální a hilové uzliny nezvětšené. Bez fluidothoraxu.

Břicho a pánev: V sigmatu cirkulární ztluštění stěny v délce cca 5 cm s mírnou infiltrací perikolického tuku, bez známek perforace. V mezosigmatu 3 uzliny do 9 mm v krátké ose, suspektní.
Játra normální velikosti, v pravém laloku 4 hypodenzní ložiska charakteru metastáz:
- S7: 48 mm (cílová léze 1)
- S8: 35 mm (cílová léze 2), naléhá na pravou jaterní žílu
- S6: 12 mm
- S5: 10 mm
Levý jaterní lalok bez ložiskových změn. Portální žíla průchodná. Žlučník, slinivka, slezina, nadledviny a ledviny bez patologie. Bez ascitu.

Závěr: Tumor sigmatu (cT3 N1), 4 jaterní metastázy v pravém laloku (S5–S8), levý lalok bez ložisek. Hrudník bez metastáz.
Součet cílových lézí (RECIST 1.1): 83 mm.

### 2026-05-06 · RDG · MR jater s hepatospecifickou k. l.  `[P03-img02]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P03-04 (radiolog)*

Indikace: zpřesnění rozsahu jaterního postižení před MDT.

Nález: V pravém jaterním laloku potvrzena 4 ložiska popsaná na CT (S7 47 mm, S8 36 mm, S6 12 mm, S5 11 mm) s restrikcí difuze a defektem v hepatobiliární fázi.
Nově v levém laloku v segmentu S3 subkapsulárně ložisko 7 mm se stejnými charakteristikami – vysoce suspektní z metastázy, na CT nezachyceno.
Ložisko S8 naléhá na pravou jaterní žílu v délce cca 15 mm, střední jaterní žíla volná.

Závěr: Celkem 5 jaterních metastáz (S5, S6, S7, S8 a S3). Postižení obou laloků.

### 2026-05-12 · PAT-B · Molekulárně-genetické vyšetření (RAS, BRAF)  `[P03-pat02]`
*Patologie · Patologie – molekulární patologie · autor LEK-P03-03 (patolog)*

Materiál: parafinový blok z biopsie tumoru sigmatu (pat. č. viz biopsie z 24. 4.), podíl nádorových buněk cca 60 %.

Metoda: NGS panel (KRAS, NRAS exon 2–4, BRAF).

Výsledek:
KRAS: detekována patogenní varianta c.35G>A, p.(Gly12Asp) – G12D.
NRAS: bez patogenní varianty.
BRAF: varianta V600E neprokázána.

Interpretace: Nádor je RAS mutovaný – anti-EGFR léčba není indikována.

Pozn.: Vyšetření MMR/MSI nebylo požadováno.

### 2026-05-18 · A-ONK · Vstupní onkologické vyšetření  `[P03-doc02]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P03-01 (klinický onkolog (ošetřující lékař))*

Důvod: nově diagnostikovaný adenokarcinom sigmatu s jaterními metastázami.

Anamnéza: Pracuje jako řidič městské dopravy, nyní v pracovní neschopnosti. Kouřil do r. 2019 (cca 20 balíčkoroků), alkohol příležitostně.
OA: IM 2019, st. p. PCI RIA s implantací stentu, od té doby bez stenokardií. Hypertenze, hypercholesterolémie.
FA: kyselina acetylsalicylová 100 mg 0-1-0, ramipril 5 mg 1-0-0, atorvastatin 40 mg 0-0-1, bisoprolol 2,5 mg 1-0-0.
Alergie: neudává.
RA: otec karcinom tlustého střeva v 72 letech.

Subjektivně: Od zimy střídání zácpy a průjmu, občas příměs krve ve stolici. Za 3 měsíce zhubl cca 4 kg. Bolesti neudává.

Objektivně: Výška 178 cm, hmotnost 84 kg. ECOG 0. Břicho měkké, nebolestivé, játra nehmatná. Bez ikteru, bez otoků.

Laboratoř: Hb 121 g/l, CEA 86 µg/l, jaterní testy v normě.

Závěr: Adenokarcinom sigmatu G2, cT3 N1 M1a (jaterní metastázy), KRAS G12D, BRAF wt.
Plán: Projednat na GIT komisi – otázka resekability jaterních metastáz a pořadí léčby.

### 2026-05-20 · MDT · Záznam MDT – GIT – kolorektální karcinom  `[P03-mdt01]`
*Předsedající LEK-P03-06 · účastníci: klinický onkolog, klinický onkolog, hepatobiliární chirurg, radiolog, radiační onkolog, patolog · pacient přítomen: ne*

**Typ projednání:** Primární projednání  
**Projednaná otázka:** Léčebný plán u nově diagnostikovaného karcinomu sigmatu se synchronními jaterními metastázami.  
**Klinické zhodnocení:** Adenokarcinom sigmatu G2, cT3 N1 M1a, KRAS G12D, BRAF wt. Na CT 4 metastázy v pravém laloku, MR navíc ložisko S3 (7 mm). Ložisko S8 naléhá na pravou jaterní žílu. Primární tumor bez obstrukce a bez významného krvácení. ECOG 0, kardiálně kompenzován.  
**Léčebný záměr:** Kurativní  
**Doporučený postup:**
1. [Chemoterapie] Konverzní chemoterapie FOLFOX + bevacizumab – restaging CT a MR jater po 6–8 cyklech
2. [Chirurgie] Při dostatečné odpovědi zvážit resekci jater (event. dvoudobě) a resekci primárního tumoru – rozhodne re-MDT

**Klinická studie:** Nezvažována.

**Plánované re-MDT:** Po restagingu po 6–8 cyklech chemoterapie (do 2026-10-31)

**Závěr MDT:** Potenciálně resekabilní jaterní metastázy – zahájit konverzní chemoterapii FOLFOX + bevacizumab, re-MDT po restagingu.

**Rozhodnutí o léčbě** `[P03-mdt01-rozhodnuti]` (2026-05-25, LEK-P03-01): Zahájení FOLFOX + bevacizumab v 14denních cyklech · stanovisko pacienta: Souhlasí

### 2026-05-28 · A-KTPP · Implantace venózního portu  `[P03-doc03]`
*Zpráva · Chirurgická ambulance – cévní přístupy · autor LEK-P03-05 (chirurg – hepatobiliární chirurgie)*

Výkon: implantace venózního portu cestou v. subclavia l. dx. v lokální anestezii pod skiaskopickou kontrolou.
Průběh bez komplikací, hrot katétru v úrovni kavoatriálního přechodu. Port funkční, propláchnut heparinovou zátkou.
Kyselinu acetylsalicylovou nebylo třeba vysadit.
Doporučení: stehy extrahovat za 10 dní, port lze používat ihned.

### 2026-06-01 · A-ONK · Zahájení chemoterapie – FOLFOX + bevacizumab, 1. cyklus  `[P03-doc04]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P03-01 (klinický onkolog (ošetřující lékař))*

Pacient po projednání na GIT komisi (20. 5. 2026) – indikována konverzní chemoterapie FOLFOX + bevacizumab, restaging po 6–8 cyklech.

Subjektivně: bez obtíží, občas tlak v podbřišku. Váha 83 kg.
Objektivně: ECOG 0, TK 135/85, port klidný.
Laboratoř: Hb 119, neutrofily 4,8, Tr 312, kreatinin 88, bilirubin 11, CEA 79.

Podán 1. cyklus: oxaliplatina 85 mg/m², leukovorin 400 mg/m², 5-FU 400 mg/m² bolus + 2400 mg/m² 46h infuze, bevacizumab 5 mg/kg. Interval 14 dní.
Edukace o nežádoucích účincích (chladová neuropatie, průjem, hypertenze, krvácení, proteinurie). Pacient vyplnil vstupní dotazník.

Další cyklus 15. 6. 2026.

### 2026-06-01 · Dotazník pacienta (PROMs)  `[P03-prom01]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 1 |
| Kde vás bolí? (vlastními slovy) | občas tlak v podbřišku |
| Únava za poslední týden (0–10) | 2 |
| Nevolnost nebo zvracení (0–10) | 0 |
| Dušnost (0–10) | 1 |
| Nechutenství (0–10) | 2 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 0 |
| Průjem (0–10) | 3 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 6 |
| Potíže se spánkem (0–10) | 4 |
| Jak zvládáte běžný den? | Zvládám vše jako před nemocí, i fyzicky náročné věci |
| Kolik zvládnete ujít? | Ujdu bez potíží delší vzdálenost i do schodů |
| Vaše současná hmotnost (kg) | 83 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | -4 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | nic nového |
| Alergie nebo nesnášenlivost léků | nevím o žádné |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | nic |
| Co je pro vás v léčbě nejdůležitější? | Nejdůležitější je pro mě co nejdelší život, i za cenu náročnější léčby |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Chci se vyléčit a vrátit se do práce. Operace se nebojím. |
| Podpora v domácnosti | Mám dostatečnou podporu blízkých |

### 2026-07-13 · A-ONK · Kontrola před 4. cyklem  `[P03-doc05]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P03-01 (klinický onkolog (ošetřující lékař))*

Subjektivně: Snáší léčbu dobře, 2–3 dny po infuzi únava a nechutenství. Chladová dysestezie prstů 2–3 dny po oxaliplatině, poté odezní. Stolice formovaná.
Objektivně: ECOG 0, TK 150/95 (domácí měření 140–150/90).
Laboratoř: Hb 118, neutrofily 2,1, Tr 180, CEA 31.
Moč chemicky: bílkovina negativní.

Závěr: Toxicita: neuropatie G1 (přechodná), hypertenze G2 – navýšen ramipril na 10 mg.
Podán 4. cyklus v plné dávce. CEA klesá.

### 2026-09-07 · A-ONK · Kontrola před 8. cyklem  `[P03-doc06]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P03-01 (klinický onkolog (ošetřující lékař))*

Subjektivně: Únava větší než na začátku léčby, chuť k jídlu horší. Brnění prstů rukou přetrvává i mezi cykly, chodidla bez potíží.
Objektivně: ECOG 0–1, hmotnost 79 kg, TK 140/90.
Laboratoř (24. 8.): Hb 113, neutrofily 1,7, Tr 151, CEA 11,2.

Závěr: Neuropatie G1. Podán 8. cyklus s redukcí oxaliplatiny na 75 % (cca 64 mg/m²) pro přetrvávající parestezie prstů mezi cykly.
Bevacizumab podán (poslední dávka před restagingem).
Plán: restagingové CT za 2 týdny, poté MR jater, re-MDT.

### 2026-09-21 · RDG · CT břicha a pánve s k. l. – restaging po 8 cyklech  `[P03-img03]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P03-04 (radiolog)*

Srovnání s CT z 28. 4. 2026. Vyšetřeno břicho a pánev, hrudník nebyl požadován.

Játra: Ložiska v pravém laloku zmenšena:
- S7: 29 mm (dříve 48 mm) – cílová léze 1
- S8: 21 mm (dříve 35 mm) – cílová léze 2, stále naléhá na pravou jaterní žílu
- S6: 6 mm (dříve 12 mm)
- S5: nezřetelné (dříve 10 mm)
Levý lalok bez ložiskových změn.
Sigma: ztluštění stěny v délce cca 3 cm, perikolický tuk klidnější. Uzliny v mezosigmatu do 5 mm.
Bez ascitu, bez nových ložisek v břiše.

Závěr: Parciální odpověď dle RECIST 1.1 – součet cílových lézí 50 mm (pokles o 40 %). Bez nových ložisek.

### 2026-09-28 · RDG · MR jater s hepatospecifickou k. l. – restaging  `[P03-img04]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P03-04 (radiolog)*

Srovnání s MR z 6. 5. 2026.

Nález:
- S7: 28 mm (dříve 47 mm)
- S8: 22 mm (dříve 36 mm), kontakt s pravou jaterní žílou v délce cca 10 mm
- S6: 6 mm
- S5: v hepatobiliární fázi bez zřetelného ložiska – vymizelá metastáza (disappearing metastasis); pro plánování resekce je třeba počítat s původní lokalizací
- S3: 4 mm (dříve 7 mm), stále s restrikcí difuze

Objem levého laloku (S2–S4) odhadem 38 % celkového objemu jater.

Závěr: Výrazná regrese všech ložisek. Jaterní postižení obou laloků trvá (S3).

### 2026-10-04 · Dotazník pacienta (PROMs)  `[P03-prom02]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 1 |
| Kde vás bolí? (vlastními slovy) |  |
| Únava za poslední týden (0–10) | 4 |
| Nevolnost nebo zvracení (0–10) | 1 |
| Dušnost (0–10) | 1 |
| Nechutenství (0–10) | 3 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 6 |
| Průjem (0–10) | 1 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 4 |
| Potíže se spánkem (0–10) | 3 |
| Jak zvládáte běžný den? | Těžší fyzickou práci nezvládám, lehčí činnosti a domácnost ano |
| Kolik zvládnete ujít? | Vyjdu jedno patro bez zastavení |
| Vaše současná hmotnost (kg) | 78 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | -5 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | Brnění v prstech rukou nepřestává ani mezi cykly, špatně zapínám knoflíky a padají mi věci z ruky. V zimě je to horší. |
| Alergie nebo nesnášenlivost léků | nevím o žádné |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | hořčík, vitamin B (doporučila známá) |
| Co je pro vás v léčbě nejdůležitější? | Obojí je pro mě stejně důležité |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Operaci bych chtěl, pokud dává smysl. Potřebuji ale vědět, jak dlouho budu mimo práci – jsem řidič a s brněním rukou teď řídit nemůžu. |
| Podpora v domácnosti | Mám dostatečnou podporu blízkých |

### 2026-10-05 · A-ONK · Kontrola po restagingu, nominace na re-MDT  `[P03-doc07]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P03-01 (klinický onkolog (ošetřující lékař))*

Pacient 4 týdny po 8. cyklu FOLFOX + bevacizumab, další cyklus odložen do rozhodnutí komise.

Subjektivně: Cítí se lépe než během léčby, chodí na procházky. Neuropatie dle pacienta přetrvává, ale je mírná.
Objektivně: ECOG 0, hmotnost 78 kg, TK 135/85, bez ikteru, břicho klidné.
Laboratoř: Hb 114, neutrofily 2,9, Tr 168, bilirubin 13, ALT 0,62, ALP 1,9, albumin 37, CEA 13,9.

Toxicita: neuropatie G1, hypertenze kompenzovaná.

Závěr: Parciální odpověď jaterních metastáz po 8 cyklech konverzní chemoterapie (CT 21. 9., MR 28. 9.).
Nominován na re-MDT GIT s otázkou resekability. Pacient si přeje operaci, pokud bude možná; obává se dlouhé pracovní neschopnosti.

## Laboratoř

ID výsledku: `P03-labNN-<parametr>`, NN = pořadí odběru (sloupec).

| Parametr | Jednotka | Norma | 01: 2026-04-28 | 02: 2026-06-01 | 03: 2026-07-13 | 04: 2026-08-24 | 05: 2026-09-21 | 06: 2026-10-05 |
|---|---|---|---|---|---|---|---|---|
| Hemoglobin (LOINC 718-7) | g/l | 135–175 | 121 ↓ | 119 ↓ | 118 ↓ | 113 ↓ | 112 ↓ | 114 ↓ |
| Leukocyty (LOINC 6690-2) | 10^9/l | 4.0–10.0 | 7.9 | 7.4 | 4.6 | 3.9 ↓ | 4.1 | 5.2 |
| Neutrofily absolutně (LOINC 751-8) | 10^9/l | 2.0–7.0 | 5.1 | 4.8 | 2.1 | 1.7 ↓ | 1.8 ↓ | 2.9 |
| Trombocyty (LOINC 777-3) | 10^9/l | 150–400 | 338 | 312 | 180 | 151 | 145 ↓ | 168 |
| Kreatinin (LOINC 14682-9) | µmol/l | 44–104 | 86 | 88 | 91 | 90 | 92 | 89 |
| Bilirubin celkový (LOINC 14631-6) | µmol/l | 2–21 | 10 | 11 | 12 | 14 | 13 | 13 |
| ALT (LOINC 1742-6) | µkat/l | 0.1–0.78 | 0.41 | 0.45 | 0.58 | 0.71 | 0.66 | 0.62 |
| AST (LOINC 1920-8) | µkat/l | 0.1–0.72 | 0.39 | 0.4 | 0.52 | 0.63 | 0.6 | 0.55 |
| ALP (LOINC 6768-6) | µkat/l | 0.66–2.2 | 1.6 | 1.7 | 2.0 | 2.3 ↑ | 2.1 | 1.9 |
| Albumin (LOINC 1751-7) | g/l | 35–52 | 41 | 40 | 38 | 37 | 36 | 37 |
| CEA (LOINC 2039-6) | µg/l | 0–5.0 | 86.0 ↑ | 79.0 ↑ | 31.0 ↑ | 11.2 ↑ | 9.1 ↑ | 13.9 ↑ |
| CA 19-9 (LOINC 24108-3) | kU/l | 0–37 | 64 ↑ | 58 ↑ | 30 | 22 | 19 | 21 |

## Strukturované nálezy (ECOG, biomarkery, staging, hmotnost)

- 2026-05-12 `[P03-bm01]` KRAS: mutace c.35G>A p.(Gly12Asp) – G12D (vzorek: biopsie tumoru sigmatu) · zdroj `P03-pat02`
- 2026-05-12 `[P03-bm02]` NRAS: bez mutace (wild-type) · zdroj `P03-pat02`
- 2026-05-12 `[P03-bm03]` BRAF V600E: neprokázána (wild-type) · zdroj `P03-pat02`
- 2026-05-12 `[P03-bm04]` MMR / MSI: nevyšetřeno · zdroj `P03-pat02`
- 2026-05-18 `[P03-ecog01]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P03-doc02`
- 2026-05-18 `[P03-vaha01]` Hmotnost 84 kg · zdroj `P03-doc02`
- 2026-05-20 `[P03-tnm01]` TNM (klinické): cT3 cN1 cM1a, stadium IVA (TNM 8. vyd.) · zdroj `P03-img01`
- 2026-06-01 `[P03-vaha02]` Hmotnost 83 kg · zdroj `P03-doc04`
- 2026-09-07 `[P03-ecog02]` ECOG 1 (omezen(a) při fyzicky náročné činnosti, zvládá lehkou práci) – hodnotil lékař · zdroj `P03-doc06`
- 2026-09-07 `[P03-vaha03]` Hmotnost 79 kg · zdroj `P03-doc06`
- 2026-10-05 `[P03-ecog03]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P03-doc07`
- 2026-10-05 `[P03-vaha04]` Hmotnost 78 kg · zdroj `P03-doc07`
- 2026-10-05 `[P03-neuro01]` Periferní neuropatie (CTCAE) – hodnocení lékařem: grade 1 · zdroj `P03-doc07`

## Léky

- `[P03-med01]` kyselina acetylsalicylová (ATC B01AC06) – 100 mg 0-1-0 · od 2019-03-20
- `[P03-med02]` ramipril (ATC C09AA05) – 10 mg 1-0-0 (od 13. 7. 2026, dříve 5 mg) · od 2019-03-20
- `[P03-med03]` atorvastatin (ATC C10AA05) – 40 mg 0-0-1 · od 2019-03-20
- `[P03-med04]` bisoprolol (ATC C07AB07) – 2,5 mg 1-0-0 · od 2019-03-20
- `[P03-med05]` metoklopramid (ATC A03FA01) – 10 mg p. o. při nevolnosti, max. 3× denně · od 2026-06-01
- `[P03-tx-oxa-01…08]` oxaliplatina (ATC L01XA03) – FOLFOX + bevacizumab, 85 mg/m² i.v. D1 á 14 dní · podání: 2026-06-01, 2026-06-15, 2026-06-29, 2026-07-13, 2026-07-27, 2026-08-10, 2026-08-24, 2026-09-07
  - 2026-09-07: redukce na 75 % – cca 64 mg/m² (přetrvávající parestezie mezi cykly)
- `[P03-tx-5fu-01…08]` fluorouracil (ATC L01BC02) – FOLFOX + bevacizumab, 400 mg/m² bolus + 2400 mg/m² kontinuálně 46 h, D1 á 14 dní · podání: 2026-06-01, 2026-06-15, 2026-06-29, 2026-07-13, 2026-07-27, 2026-08-10, 2026-08-24, 2026-09-07
- `[P03-tx-lv-01…08]` kalcium-folinát (leukovorin) (ATC V03AF03) – FOLFOX + bevacizumab, 400 mg/m² i.v. D1 á 14 dní · podání: 2026-06-01, 2026-06-15, 2026-06-29, 2026-07-13, 2026-07-27, 2026-08-10, 2026-08-24, 2026-09-07
- `[P03-tx-bev-01…08]` bevacizumab (ATC L01FG01) – FOLFOX + bevacizumab, 5 mg/kg i.v. D1 á 14 dní · podání: 2026-06-01, 2026-06-15, 2026-06-29, 2026-07-13, 2026-07-27, 2026-08-10, 2026-08-24, 2026-09-07

## Výkony a radioterapie

- `[P03-proc01]` 2026-04-21 · Koloskopie s biopsií a polypektomií
- `[P03-proc02]` 2026-05-28 · Implantace venózního portu (v. subclavia l. dx.)
- `[P03-proc03]` 2019-03-20 · PCI RIA s implantací lékového stentu – akutní STEMI přední stěny

