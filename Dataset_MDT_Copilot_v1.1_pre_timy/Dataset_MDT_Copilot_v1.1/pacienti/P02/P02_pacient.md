# Pacientka P02 – HER2+ metastatický karcinom prsu – nové mozkové metastázy na udržovací léčbě pertuzumab + trastuzumab

> **Fiktivní pacient.** Vytvořeno pro hackathon Rakathon 2026 (MDT Copilot). Neodpovídá žádné skutečné osobě. Klinicky neověřeno – nepoužívat pro péči o pacienty.

- **Pohlaví:** žena · **rok narození:** 1958 · **věk k datu MDT:** 68
- **Identifikátor ve FHIR:** `Patient/P02` · každý záznam níže nese ID zdroje v hranatých závorkách, např. `[P02-doc01]`.

## Diagnózy
- `[P02-dg1]` **C50.4** Zhoubný novotvar horního zevního kvadrantu prsu (pravý prs) · morfologie ICD-O-3 8500/3 Invazivní karcinom prsu NST (duktální) · od 2025-01-14
  - klinické TNM: cT4b cN1 cM1, stadium IV (2025-01-20)
- `[P02-dg2]` **C78.0** Sekundární zhoubný novotvar plic · od 2025-01-20
- `[P02-dg3]` **C79.3** Sekundární zhoubný novotvar mozku a mozkových plen · od 2026-09-22
- `[P02-kom1]` **E11.9** Diabetes mellitus 2. typu bez komplikací · od 2016
- `[P02-kom2]` **I10** Esenciální hypertenze · od 2012

## Nominace na MDT (žádanka)

`[P02-zad01]` · stav **Naplánovaná** · plánovaný termín MDT **2026-10-14**

| Položka | Obsah |
|---|---|
| Datum vytvoření | 2026-10-02 |
| Žádající lékař / pracoviště | LEK-P02-01 (klinický onkolog (ošetřující lékař)), Onkologická klinika – ambulance klinické onkologie |
| Požadované zaměření MDT | Mamární komise – karcinom prsu |
| Typ projednání | Progrese / recidiva |
| Priorita | urgentní |
| Požadovaný termín (nejpozději) | 2026-10-16 |
| Typ klinické otázky | Indikace radioterapie, Systémová léčba, Klinická studie |
| **Otázka pro MDT** | **Nově 2 mozkové metastázy (14 a 9 mm) při stabilní extrakraniální nemoci na udržovací léčbě pertuzumab + trastuzumab. Lokální léčba (stereotaktická radioterapie) a pokračování PH, nebo změna systémové léčby (trastuzumab deruxtekan / studie RKT-02)?** |
| Diagnózy | `P02-dg1`, `P02-dg2`, `P02-dg3` |
| Histologie a grade | Invazivní karcinom pravého prsu NST, G3, ER 10 %, PR 0 %, HER2 3+, Ki-67 35 % (core biopsie 14. 1. 2025) |
| Relevantní komorbidity a současný stav | DM 2. typu na metforminu, hypertenze. Dexametazon 4 mg/den od 23. 9. 2026. Neuropatie G1 po paklitaxelu. ECOG 1. |
| Preference pacienta | Obává se ozařování hlavy kvůli paměti; přeje si zachovat soběstačnost a kontakt s rodinou (vnučka). |
| Pacient informován o projednání | ano |
| Předchozí MDT | `P02-mdt01` |

**Předchozí onkologická léčba**
- [Cílená léčba] Pertuzumab + trastuzumab + paklitaxel weekly (21 podání paklitaxelu), parciální odpověď (2025-02-10 – 2025-06-30)
- [Cílená léčba] Udržovací pertuzumab + trastuzumab á 3 týdny (poslední podání 8. 9. 2026) (2025-07-07 – dosud)

**Podklady (odkazy):** `P02-pat01`, `P02-img02`, `P02-img05`, `P02-img06`, `P02-doc08`, `P02-doc11`, `P02-lab06`, `P02-bm03`, `P02-tnm01`, `P02-ecog04`

## Chronologie dokumentace

### 2025-01-08 · A-MCH · Vyšetření pro rezistenci pravého prsu  `[P02-doc01]`
*Zpráva · Ambulance mamární chirurgie · autor LEK-P02-02 (chirurg – mamární chirurgie)*

Důvod: Pacientka odeslána praktickým lékařem pro bulku v pravém prsu, kterou si nahmatala asi před 3 měsíci, poslední týdny se zvětšuje a kůže nad ní zarudla.

OA: DM 2. typu na PAD, hypertenze. Gynekologicky: 2 porody, kojila, menopauza v 51 letech, HRT neužívala.
FA: metformin 1000 mg 1-0-1, perindopril 5 mg 1-0-0.
RA: bez nádorů prsu a vaječníků v rodině.
SA: učitelka v důchodu, žije s manželem.

Objektivně: Pravý prs – v horním zevním kvadrantu tuhá, nebolestivá rezistence cca 6 cm, fixovaná ke kůži, kůže nad ní infiltrovaná s obrazem pomerančové kůže, bez ulcerace. Bradavka bez sekrece.
Pravá axila: hmatné zvětšené, pohyblivé uzliny. Levý prs a levá axila bez hmatné patologie. Nadklíčky volné.

Závěr: Rezistence pravého prsu s infiltrací kůže, suspektní malignita, suspektní axilární uzliny vpravo.
Doporučení: MG a UZ obou prsů a axil, následně core biopsie.

### 2025-01-10 · RDG · Mamografie a UZ prsů a axil  `[P02-img01]`
*Zobrazení · Radiodiagnostické oddělení – mamodiagnostika · autor LEK-P02-04 (radiolog)*

Mamografie oboustranně (CC, MLO), doplněna UZ obou prsů a axil.

Pravý prs: V horním zevním kvadrantu nepravidelné spikulované ložisko s mikrokalcifikacemi, sonograficky hypoechogenní, s nepravidelným okrajem, velikost 58 × 42 mm. Zesílená kůže nad ložiskem, edém podkoží.
Pravá axila: 3 zvětšené uzliny se ztluštělým kortexem a setřelým hilem, největší 22 mm v krátké ose.
Levý prs a levá axila: bez ložiskových změn.

Závěr: Pravý prs – suspektní malignita, BI-RADS 5. Suspektní metastatické uzliny pravé axily. Levý prs BI-RADS 1.
Doporučení: core biopsie ložiska pravého prsu pod UZ kontrolou.

### 2025-01-14 · PAT-B · Core biopsie ložiska pravého prsu  `[P02-pat01]`
*Patologie · Patologie – bioptická laboratoř · autor LEK-P02-03 (patolog)*

Materiál: 4 válečky z ložiska pravého prsu (HZK), core biopsie pod UZ kontrolou.

Mikroskopicky: Ve všech válečcích infiltrace invazivním karcinomem bez zvláštního typu (NST), solidní a trabekulární stavba, výrazná jaderná pleomorfie, četné mitózy. Tubulární struktury chybí. Nottingham skóre 3 + 3 + 2 = 8 (G3). Lymfangioinvaze přítomna.

Imunohistochemie:
- estrogenové receptory (ER): pozitivní v 10 % nádorových buněk, slabá až středně silná intenzita
- progesteronové receptory (PR): 0 %
- HER2: IHC 3+ (kompletní silné membránové barvení ve více než 10 % buněk) – HER2 pozitivní, ISH není nutná
- Ki-67: 35 %

Závěr: Invazivní karcinom pravého prsu NST, G3, ER 10 %, PR 0 %, HER2 pozitivní (IHC 3+), Ki-67 35 %.

KLASIFIKACE: Topografie (ICD-O-3) C50.4, Morfologie (ICD-O-3) 8500/3

### 2025-01-20 · RDG · CT hrudníku, břicha a pánve s k. l. – staging  `[P02-img02]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P02-04 (radiolog)*

Technika: CT hrudníku, břicha a pánve po i.v. aplikaci k. l.

Hrudník: V pravém prsu v horním zevním kvadrantu nepravidelné ložisko 58 mm (cílová léze 1) se zesílením kůže a edémem podkoží. V pravé axile zvětšené uzliny, největší 22 mm v krátké ose (cílová léze 2), další do 12 mm. Levá axila, nadklíčky a mediastinum bez zvětšených uzlin.
Plíce: Ve dvou lalocích solidní okrouhlá ložiska charakteru metastáz:
- pravý dolní lalok (S9): 18 mm (cílová léze 3)
- levý horní lalok (S3): 14 mm (cílová léze 4)
Dále 2 drobná ložiska do 5 mm (pravý horní a levý dolní lalok) – necílové léze. Bez fluidothoraxu.

Břicho a pánev: Játra bez ložiskových změn. Nadledviny, slezina, slinivka a ledviny bez patologie. Bez ascitu, bez lymfadenopatie.
Skelet: bez osteolytických a osteoplastických ložisek.

Závěr: Tumor pravého prsu (cT4b) s metastatickou uzlinou pravé axily (cN1), plicní metastázy oboustranně (M1 PUL).
Součet cílových lézí (RECIST 1.1): 112 mm.

### 2025-01-24 · A-ONK · Vstupní onkologické vyšetření  `[P02-doc02]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P02-01 (klinický onkolog (ošetřující lékař))*

Důvod: nově diagnostikovaný karcinom pravého prsu s plicními metastázami.

Anamnéza: Učitelka v důchodu, žije s manželem, má dceru a vnučku. Nekouří, alkohol výjimečně.
OA: DM 2. typu od r. 2016 na metforminu, hypertenze od r. 2012. Jiná závažná onemocnění neudává.
FA: metformin 1000 mg 1-0-1, perindopril 5 mg 1-0-0.
Alergie: neudává.
RA: negativní pro karcinom prsu a ovaria.

Subjektivně: Bulka v pravém prsu asi 3 měsíce, bez bolesti. Kašel ani dušnost neudává. Hmotnost stabilní.

Objektivně: Výška 164 cm, hmotnost 72 kg. ECOG 0. Pravý prs: tumor HZK cca 6 cm s infiltrací kůže (pomerančová kůže). Pravá axila: pohyblivé zvětšené uzliny. Dýchání čisté, sklípkové.

Laboratoř (20. 1.): Hb 128 g/l, glykémie 7,4 mmol/l, jaterní testy v normě, CA 15-3 125 kU/l, CEA 6,8 µg/l.

Závěr: Invazivní karcinom pravého prsu NST G3, ER 10 %, PR 0 %, HER2 3+, Ki-67 35 %, cT4b N1 M1 (PUL), stadium IV.
Plán: Projednat na mamární komisi – 1. linie anti-HER2 léčby. Před zahájením echokardiografie a implantace portu.

### 2025-01-29 · MDT · Záznam MDT – Mamární komise – karcinom prsu  `[P02-mdt01]`
*Předsedající LEK-P02-07 · účastníci: klinický onkolog, klinický onkolog, mamární chirurg, radiolog, radiační onkolog, patolog · pacient přítomen: ne*

**Typ projednání:** Primární projednání  
**Projednaná otázka:** Léčebný plán u nově diagnostikovaného HER2+ karcinomu pravého prsu s plicními metastázami.  
**Klinické zhodnocení:** Invazivní karcinom pravého prsu NST G3, ER 10 %, PR 0 %, HER2 3+, Ki-67 35 %. cT4b N2 M1 (plicní metastázy oboustranně), stadium IV. Na CT tumor prsu 58 mm, axilární uzlina vpravo 22 mm, plicní ložiska 18 a 14 mm + 2 drobná. Játra a skelet bez metastáz. ECOG 0. DM 2. typu na metforminu, hypertenze.  
**Léčebný záměr:** Paliativní  
**Doporučený postup:**
1. [Cílená léčba] Pertuzumab + trastuzumab á 3 týdny + paklitaxel 80 mg/m² týdně do maximální odpovědi – restaging CT po cca 4 měsících
2. [Cílená léčba] Poté udržovací pertuzumab + trastuzumab do progrese nebo netolerance – CT á 3–6 měsíců
3. [Diagnostika] Echokardiografie (LVEF) před zahájením a á 3 měsíce během anti-HER2 léčby

**Doplnit:** Cévní přístup – implantace venózního portu před zahájením léčby

**Klinická studie:** Nezvažována.

**Závěr MDT:** HER2+ metastatický karcinom pravého prsu – 1. linie pertuzumab + trastuzumab + paklitaxel, poté udržovací PH; kontrola LVEF á 3 měsíce. Lokální léčba prsu nyní neindikována.

**Rozhodnutí o léčbě** `[P02-mdt01-rozhodnuti]` (2025-02-03, LEK-P02-01): Zahájení pertuzumab + trastuzumab + paklitaxel weekly po implantaci portu a vstupní echokardiografii · stanovisko pacienta: Souhlasí

### 2025-02-05 · A-KTPP · Implantace venózního portu  `[P02-doc03]`
*Zpráva · Chirurgická ambulance – cévní přístupy · autor LEK-P02-05 (chirurg – cévní přístupy)*

Indikace: zajištění žilního přístupu pro dlouhodobou systémovou léčbu (anti-HER2 léčba) u pacientky s karcinomem levého prsu.

Výkon: implantace venózního portu cestou v. jugularis interna l. sin. v lokální anestezii pod UZ a skiaskopickou kontrolou. Komůrka uložena podkožně v levé podklíčkové krajině.
Průběh bez komplikací, hrot katétru v úrovni kavoatriálního přechodu. Port funkční, propláchnut, uzavřen heparinovou zátkou.

Doporučení: stehy extrahovat za 10 dní, port lze používat ihned.

### 2025-02-07 · A-KARD · Echokardiografie před zahájením anti-HER2 léčby  `[P02-doc04]`
*Zpráva · Kardiologická ambulance · autor LEK-P02-06 (kardiolog)*

Indikace: vstupní vyšetření před léčbou trastuzumabem a pertuzumabem.

Nález: Levá komora nedilatovaná, normální tloušťka stěn, bez poruchy kinetiky. LVEF 63 % (biplane Simpson). Diastolická funkce: porucha relaxace (I. stupeň). Chlopně bez významné vady. Pravostranné oddíly normální. Perikard bez výpotku.

Závěr: Normální systolická funkce LK, LVEF 63 %.
Doporučení: Z kardiologického hlediska bez kontraindikace anti-HER2 léčby. Kontrolní echokardiografie á 3 měsíce po dobu léčby.

### 2025-02-10 · A-ONK · Zahájení 1. linie – pertuzumab + trastuzumab + paklitaxel  `[P02-doc05]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P02-01 (klinický onkolog (ošetřující lékař))*

Pacientka po projednání na mamární komisi (29. 1. 2025) – indikována 1. linie pertuzumab + trastuzumab + paklitaxel weekly, poté udržovací pertuzumab + trastuzumab.

Subjektivně: bez obtíží. Port klidný, bez známek infekce.
Objektivně: ECOG 0, TK 135/80, hmotnost 72 kg. Echokardiografie 7. 2.: LVEF 63 %.

Podáno: pertuzumab 840 mg i.v. (úvodní dávka), trastuzumab 8 mg/kg i.v. (úvodní dávka), paklitaxel 80 mg/m² i.v.
Dále: pertuzumab 420 mg + trastuzumab 6 mg/kg á 3 týdny, paklitaxel 80 mg/m² každý týden.
Edukace o nežádoucích účincích (neuropatie, alopecie, průjem, infuzní reakce, kardiotoxicita).

Restagingové CT po cca 4 měsících léčby, echokardiografie á 3 měsíce.

### 2025-06-24 · RDG · CT hrudníku, břicha a pánve s k. l. – restaging  `[P02-img03]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P02-04 (radiolog)*

Srovnání s CT z 20. 1. 2025.

Pravý prs: ložisko zmenšeno na 30 mm (dříve 58 mm), kůže méně zesílená.
Pravá axila: uzlina 9 mm v krátké ose (dříve 22 mm), ostatní uzliny nezvětšené.
Plíce:
- pravý dolní lalok: 9 mm (dříve 18 mm)
- levý horní lalok: 6 mm (dříve 14 mm)
Drobná necílová ložiska do 4 mm, beze změny nebo menší.
Břicho a skelet: bez nových ložisek.

Závěr: Parciální odpověď dle RECIST 1.1 – součet cílových lézí 54 mm (pokles o 52 %). Bez nových ložisek.

### 2025-06-30 · A-ONK · Ukončení paklitaxelu, přechod na udržovací PH  `[P02-doc06]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P02-01 (klinický onkolog (ošetřující lékař))*

Subjektivně: Léčbu snáší dobře, únava mírná. Brnění konečků prstů rukou a nohou posledních 6 týdnů, jemnou motoriku neomezuje. Alopecie.
Objektivně: ECOG 0, hmotnost 70 kg, TK 130/80. Kůže pravého prsu klidná, tumor hmatný cca 3 cm.
Laboratoř (23. 6.): Hb 116, neutrofily 3,0, Tr 228, glykémie 7,8, CA 15-3 48.
Echokardiografie 12. 5.: LVEF 62 %.
CT 24. 6.: parciální odpověď (součet cílových lézí 112 → 54 mm).

Toxicita: periferní senzitivní neuropatie G1, alopecie.
Podán 21. (poslední) paklitaxel – ukončení taxanu po dosažení parciální odpovědi.
Plán: udržovací pertuzumab + trastuzumab á 3 týdny (další podání 7. 7.), echokardiografie á 3 měsíce, CT á 3–4 měsíce.

### 2026-03-08 · Dotazník pacienta (PROMs)  `[P02-prom01]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 1 |
| Kde vás bolí? (vlastními slovy) | občas klouby |
| Únava za poslední týden (0–10) | 3 |
| Nevolnost nebo zvracení (0–10) | 0 |
| Dušnost (0–10) | 1 |
| Nechutenství (0–10) | 1 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 3 |
| Průjem (0–10) | 1 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 3 |
| Potíže se spánkem (0–10) | 2 |
| Jak zvládáte běžný den? | Těžší fyzickou práci nezvládám, lehčí činnosti a domácnost ano |
| Kolik zvládnete ujít? | Vyjdu jedno patro bez zastavení |
| Vaše současná hmotnost (kg) | 71 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | 0 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | nic nového, brnění konečků prstů trvá |
| Alergie nebo nesnášenlivost léků | nevím o žádné |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | vitamin D |
| Co je pro vás v léčbě nejdůležitější? | Obojí je pro mě stejně důležité |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Léčbu snáším dobře a chci v ní pokračovat. Hodně pro mě znamená, že můžu hlídat vnučku. |
| Podpora v domácnosti | Mám dostatečnou podporu blízkých |

### 2026-03-10 · RDG · CT hrudníku, břicha a pánve s k. l. – kontrola  `[P02-img04]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P02-04 (radiolog)*

Srovnání s CT z 20. 1. 2025 a s předchozí kontrolou.

Pravý prs: ložisko 26 mm.
Pravá axila: uzlina 8 mm v krátké ose.
Plíce: pravý dolní lalok 8 mm, levý horní lalok 6 mm. Drobná necílová ložiska do 4 mm beze změny.
Břicho a skelet: bez ložiskových změn.

Závěr: Stacionární nález – součet cílových lézí 48 mm. Bez nových ložisek.

### 2026-03-24 · A-ONK · Kontrola na udržovací léčbě PH  `[P02-doc07]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P02-01 (klinický onkolog (ošetřující lékař))*

Udržovací pertuzumab + trastuzumab od 7/2025, celkově 1. linie od 10. 2. 2025.

Subjektivně: Cítí se dobře, stará se o domácnost, pravidelně hlídá vnučku. Brnění konečků prstů přetrvává, nezhoršuje se. Těžší práci na zahradě nezvládá kvůli únavě.
Objektivně: ECOG 1, hmotnost 71 kg, TK 140/85.
Laboratoř dnes: Hb 124, neutrofily 3,6, Tr 238, glykémie 7,6, CA 15-3 30.
Echokardiografie 9. 2.: LVEF 60 %.
CT 10. 3.: stacionární nález, trvá parciální odpověď.

Toxicita: neuropatie G1 po paklitaxelu.
Podán pertuzumab 420 mg + trastuzumab 6 mg/kg. Pacientka vyplnila dotazník (8. 3.).
Plán: pokračovat v PH á 3 týdny, echokardiografie á 3 měsíce, CT za 6 měsíců.

### 2026-08-20 · A-KARD · Kontrolní echokardiografie na anti-HER2 léčbě  `[P02-doc08]`
*Zpráva · Kardiologická ambulance · autor LEK-P02-06 (kardiolog)*

Indikace: pravidelná kontrola při léčbě trastuzumabem a pertuzumabem.

Subjektivně: bez dušnosti a otoků, bez palpitací.
Nález: Levá komora nedilatovaná, difuzní mírná hypokineze. LVEF 52 % (biplane Simpson). Diastolická funkce: porucha relaxace (I. stupeň). Chlopně bez významné vady. Perikard bez výpotku.
Srovnání: vstupně (7. 2. 2025) LVEF 63 %, v 2/2026 60 %, v 5/2026 60 %.

Závěr: Pokles LVEF na 52 % – o 11 procentních bodů proti vstupnímu vyšetření, mírně snížená systolická funkce LK.
Doporučení: Kontrolní echokardiografie za 3–4 týdny. Perindopril ponechat. O pokračování anti-HER2 léčby rozhodne onkolog podle kontrolního vyšetření.

### 2026-09-15 · A-ONK · Nepravidelná kontrola – bolesti hlavy  `[P02-doc09]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P02-01 (klinický onkolog (ošetřující lékař))*

Důvod: Pacientka přichází mimo plánovaný termín pro bolesti hlavy.

Subjektivně: Asi 2 týdny bolesti hlavy, převážně ráno po probuzení, tlakového charakteru, na paracetamol částečně ustupují. Ráno nauzea, nezvrací. Poruchy řeči ani slabost končetin neudává.
Objektivně: ECOG 1, TK 145/85. Orientovaná, řeč plynulá. Neurologicky bez ložiskového nálezu, bez meningeálních příznaků, stoj a chůze bez ataxie.

Závěr: Bolesti hlavy s ranní nauzeou u pacientky s HER2+ metastatickým karcinomem prsu – nutno vyloučit mozkové metastázy.
Doporučení: MR mozku s k. l. urgentně. Paracetamol 1 g při bolesti, max. 3× denně.

### 2026-09-22 · RDG · MR mozku s k. l.  `[P02-img05]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P02-04 (radiolog)*

Indikace: bolesti hlavy, ranní nauzea, HER2+ karcinom prsu.

Nález:
- Levý frontální lalok: kortiko-subkortikálně ložisko 14 mm s prstencovým sycením, perifokální vazogenní edém do 25 mm, bez přesunu středočarových struktur.
- Pravá hemisféra mozečku: ložisko 9 mm se sycením, bez edému, IV. komora volná.
Komorový systém nerozšířen, bez známek hydrocefalu. Leptomeningeální sycení není patrné. Bez krvácení.

Závěr: 2 metastázy mozku (frontálně vlevo 14 mm s perifokálním edémem, mozeček vpravo 9 mm). Bez hydrocefalu.

### 2026-09-23 · A-ONK · Výsledek MR mozku, zahájení kortikoidů  `[P02-doc10]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P02-01 (klinický onkolog (ošetřující lékař))*

Pacientka seznámena s výsledkem MR mozku z 22. 9. 2026: 2 metastázy (frontálně vlevo 14 mm s perifokálním edémem, mozeček vpravo 9 mm).

Subjektivně: Bolesti hlavy trvají, ráno nauzea.
Objektivně: ECOG 1, neurologicky bez ložiskového nálezu.

Zahájen dexametazon 4 mg p.o. 1-0-0 a pantoprazol 20 mg 1-0-0.
Plán: Doplnit restagingové CT hrudníku a břicha (24. 9.), poté nominace na mamární komisi k rozhodnutí o lokální a systémové léčbě.

### 2026-09-24 · RDG · CT hrudníku, břicha a pánve s k. l. – restaging  `[P02-img06]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P02-04 (radiolog)*

Srovnání s CT z 10. 3. 2026 a z 20. 1. 2025.

Pravý prs: ložisko 25 mm (dříve 26 mm).
Pravá axila: uzlina 8 mm v krátké ose.
Plíce: pravý dolní lalok 8 mm, levý horní lalok 5 mm (dříve 8 a 6 mm). Drobná necílová ložiska do 4 mm beze změny. Bez známek pneumonitidy.
Břicho a pánev: játra, nadledviny a ostatní orgány bez ložiskových změn. Skelet bez metastáz.

Závěr: Extrakraniálně stabilní nález, součet cílových lézí 46 mm (nadir). Bez nových ložisek v zobrazené oblasti. Mozek viz MR z 22. 9. 2026.

### 2026-09-30 · Dotazník pacienta (PROMs)  `[P02-prom02]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 7 |
| Kde vás bolí? (vlastními slovy) | hlava, hlavně ráno |
| Únava za poslední týden (0–10) | 6 |
| Nevolnost nebo zvracení (0–10) | 5 |
| Dušnost (0–10) | 1 |
| Nechutenství (0–10) | 4 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 4 |
| Průjem (0–10) | 0 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 8 |
| Potíže se spánkem (0–10) | 6 |
| Jak zvládáte běžný den? | Postarám se o sebe, ale pracovat nemohu; přes den odpočívám méně než polovinu času |
| Kolik zvládnete ujít? | Zvládnu jen chůzi po rovině |
| Vaše současná hmotnost (kg) | 71 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | 0 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | Bolí mě hlava, ráno je mi špatně od žaludku. Občas vidím rozmazaně, hlavně když čtu – trvá to pár minut a pak to přejde. Po nových prášcích hůř spím. |
| Alergie nebo nesnášenlivost léků | nevím o žádné |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | vitamin D |
| Co je pro vás v léčbě nejdůležitější? | Obojí je pro mě stejně důležité |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Bojím se ozařování hlavy, aby mi nepoškodilo paměť – celý život jsem učila a na hlavě mi záleží nejvíc. Chci dál jezdit za vnučkou a hlídat ji. |
| Podpora v domácnosti | Mám dostatečnou podporu blízkých |

### 2026-10-01 · A-ONK · Kontrola na dexametazonu, nominace na mamární komisi  `[P02-doc11]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P02-01 (klinický onkolog (ošetřující lékař))*

Subjektivně: Bolesti hlavy přetrvávají, ráno nauzea. Hůře spí. Je ustaraná z dalšího postupu.
Objektivně: ECOG 1, hmotnost 71 kg, TK 150/90. Neurologicky bez ložiskového nálezu. Kardiálně kompenzovaná, EF v normě.
Laboratoř (30. 9.): Hb 131, leukocyty 9,4, neutrofily 6,8, Tr 266, kreatinin 78, glykémie vyšší, CA 15-3 34.
Medikace: dexametazon 4 mg 1-0-0 (od 23. 9.), pantoprazol 20 mg, metformin 1000 mg 1-0-1, perindopril 5 mg 1-0-0.

Toxicita: neuropatie G1 po paklitaxelu.
Udržovací PH: poslední podání 8. 9. 2026, podání plánované na 29. 9. odloženo do rozhodnutí komise.

Závěr: HER2+ metastatický karcinom pravého prsu, nově 2 mozkové metastázy při stabilní extrakraniální nemoci na udržovací léčbě pertuzumab + trastuzumab.
Plán: Nominace na mamární komisi – lokální léčba mozkových metastáz a další systémová léčba. Dexametazon 4 mg pokračuje. Pacientka si přeje zachovat soběstačnost, obává se ozařování hlavy.

## Laboratoř

ID výsledku: `P02-labNN-<parametr>`, NN = pořadí odběru (sloupec).

| Parametr | Jednotka | Norma | 01: 2025-01-20 | 02: 2025-06-23 | 03: 2025-11-10 | 04: 2026-03-24 | 05: 2026-08-18 | 06: 2026-09-30 |
|---|---|---|---|---|---|---|---|---|
| Hemoglobin (LOINC 718-7) | g/l | 120–160 | 128 | 116 ↓ | 122 | 124 | 125 | 131 |
| Leukocyty (LOINC 6690-2) | 10^9/l | 4.0–10.0 | 7.8 | 5.1 | 6.2 | 6.0 | 6.4 | 9.4 |
| Neutrofily absolutně (LOINC 751-8) | 10^9/l | 2.0–7.0 | 4.9 | 3.0 | 3.8 | 3.6 | 3.9 | 6.8 |
| Trombocyty (LOINC 777-3) | 10^9/l | 150–400 | 312 | 228 | 245 | 238 | 251 | 266 |
| Kreatinin (LOINC 14682-9) | µmol/l | 44–104 | 68 | 72 | 70 | 74 | 76 | 78 |
| Sodík (LOINC 2951-2) | mmol/l | 136–145 | 140 | 139 | 141 | 140 | 139 | 138 |
| Draslík (LOINC 2823-3) | mmol/l | 3.5–5.1 | 4.3 | 4.1 | 4.4 | 4.2 | 4.5 | 3.9 |
| Glukóza (LOINC 15074-8) | mmol/l | 3.9–5.6 | 7.4 ↑ | 7.8 ↑ | 7.2 ↑ | 7.6 ↑ | 8.0 ↑ | 11.8 ↑ |
| Bilirubin celkový (LOINC 14631-6) | µmol/l | 2–21 | 8 | 9 | 8 | 9 | 10 | 9 |
| ALT (LOINC 1742-6) | µkat/l | 0.1–0.78 | 0.32 | 0.48 | 0.36 | 0.34 | 0.38 | 0.41 |
| AST (LOINC 1920-8) | µkat/l | 0.1–0.72 | 0.3 | 0.44 | 0.33 | 0.31 | 0.35 | 0.36 |
| Albumin (LOINC 1751-7) | g/l | 35–52 | 41 | 39 | 41 | 42 | 41 | 40 |
| CA 15-3 (LOINC 6875-3) | kU/l | 0–31 | 125 ↑ | 48 ↑ | 32 ↑ | 30 | 31 | 34 ↑ |
| CEA (LOINC 2039-6) | µg/l | 0–5.0 | 6.8 ↑ | 3.2 | 2.6 | 2.5 | 2.7 | 2.9 |

## Strukturované nálezy (ECOG, biomarkery, staging, hmotnost)

- 2025-01-14 `[P02-bm01]` Estrogenové receptory (ER): pozitivní 10 % (vzorek: core biopsie pravého prsu) · zdroj `P02-pat01`
- 2025-01-14 `[P02-bm02]` Progesteronové receptory (PR): 0 % (vzorek: core biopsie pravého prsu) · zdroj `P02-pat01`
- 2025-01-14 `[P02-bm03]` HER2: IHC 3+ – pozitivní (vzorek: core biopsie pravého prsu) · zdroj `P02-pat01`
- 2025-01-14 `[P02-bm04]` Ki-67: 35 % (vzorek: core biopsie pravého prsu) · zdroj `P02-pat01`
- 2025-01-20 `[P02-tnm01]` TNM (klinické): cT4b cN1 cM1 (PUL), stadium IV (TNM 8. vyd.) · zdroj `P02-img02`
- 2025-01-24 `[P02-ecog01]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P02-doc02`
- 2025-01-24 `[P02-vaha01]` Hmotnost 72 kg · zdroj `P02-doc02`
- 2025-02-07 `[P02-lvef01]` LVEF (echokardiografie): 63 % · zdroj `P02-doc04`
- 2025-05-12 `[P02-lvef02]` LVEF (echokardiografie): 62 % · zdroj `P02-doc06`
- 2025-06-30 `[P02-ecog02]` ECOG 0 (plně aktivní, bez omezení) – hodnotil lékař · zdroj `P02-doc06`
- 2025-06-30 `[P02-vaha02]` Hmotnost 70 kg · zdroj `P02-doc06`
- 2025-06-30 `[P02-neuro01]` Periferní neuropatie (CTCAE) – hodnocení lékařem: grade 1 · zdroj `P02-doc06`
- 2025-08-11 `[P02-lvef03]` LVEF (echokardiografie): 61 %
- 2025-11-10 `[P02-lvef04]` LVEF (echokardiografie): 62 %
- 2026-02-09 `[P02-lvef05]` LVEF (echokardiografie): 60 % · zdroj `P02-doc07`
- 2026-03-24 `[P02-ecog03]` ECOG 1 (omezen(a) při fyzicky náročné činnosti, zvládá lehkou práci) – hodnotil lékař · zdroj `P02-doc07`
- 2026-03-24 `[P02-vaha03]` Hmotnost 71 kg · zdroj `P02-doc07`
- 2026-05-11 `[P02-lvef06]` LVEF (echokardiografie): 60 %
- 2026-08-20 `[P02-lvef07]` LVEF (echokardiografie): 52 % · zdroj `P02-doc08`
- 2026-10-01 `[P02-ecog04]` ECOG 1 (omezen(a) při fyzicky náročné činnosti, zvládá lehkou práci) – hodnotil lékař · zdroj `P02-doc11`
- 2026-10-01 `[P02-vaha04]` Hmotnost 71 kg · zdroj `P02-doc11`
- 2026-10-01 `[P02-neuro02]` Periferní neuropatie (CTCAE) – hodnocení lékařem: grade 1 · zdroj `P02-doc11`

## Léky

- `[P02-med01]` metformin (ATC A10BA02) – 1000 mg 1-0-1 · od 2016-05-10
- `[P02-med02]` perindopril (ATC C09AA04) – 5 mg 1-0-0 · od 2012-09-03
- `[P02-med03]` dexametazon (ATC H02AB02) – 4 mg p.o. 1-0-0 · od 2026-09-23 · pro perifokální edém mozkové metastázy
- `[P02-med04]` pantoprazol (ATC A02BC02) – 20 mg 1-0-0 · od 2026-09-23
- `[P02-med05]` paracetamol (ATC N02BE01) – 1 g p.o. při bolesti, max. 3× denně · od 2026-09-15
- `[P02-tx-pac-01…21]` paklitaxel (ATC L01CD01) – pertuzumab + trastuzumab + paklitaxel, 80 mg/m² i.v. každý týden · podání: 2025-02-10, 2025-02-17, 2025-02-24, 2025-03-03, 2025-03-10, 2025-03-17, 2025-03-24, 2025-03-31, 2025-04-07, 2025-04-14, 2025-04-21, 2025-04-28, 2025-05-05, 2025-05-12, 2025-05-19, 2025-05-26, 2025-06-02, 2025-06-09, 2025-06-16, 2025-06-23, 2025-06-30
  - 2025-06-30: 21. (poslední) podání – ukončení taxanu po dosažení parciální odpovědi; neuropatie G1
- `[P02-tx-per-01…12]` pertuzumab (ATC L01FD02) – udržovací pertuzumab + trastuzumab, 420 mg i.v. á 3 týdny · podání: 2026-01-20, 2026-02-10, 2026-03-03, 2026-03-24, 2026-04-14, 2026-05-05, 2026-05-26, 2026-06-16, 2026-07-07, 2026-07-28, 2026-08-18, 2026-09-08
  - 2026-01-20: pokračování udržovací léčby PH zahájené 10. 2. 2025 (úvodní dávky pertuzumab 840 mg, trastuzumab 8 mg/kg); přehled obsahuje podání od 1/2026
  - 2026-09-08: poslední podání před nominací; podání plánované na 29. 9. 2026 odloženo do rozhodnutí komise
- `[P02-tx-tra-01…12]` trastuzumab (ATC L01FD01) – udržovací pertuzumab + trastuzumab, 6 mg/kg i.v. á 3 týdny · podání: 2026-01-20, 2026-02-10, 2026-03-03, 2026-03-24, 2026-04-14, 2026-05-05, 2026-05-26, 2026-06-16, 2026-07-07, 2026-07-28, 2026-08-18, 2026-09-08
  - 2026-01-20: pokračování udržovací léčby PH zahájené 10. 2. 2025 (úvodní dávky pertuzumab 840 mg, trastuzumab 8 mg/kg); přehled obsahuje podání od 1/2026
  - 2026-09-08: poslední podání před nominací; podání plánované na 29. 9. 2026 odloženo do rozhodnutí komise

## Výkony a radioterapie

- `[P02-proc01]` 2025-01-14 · Core biopsie ložiska pravého prsu pod UZ kontrolou
- `[P02-proc02]` 2025-02-05 · Implantace venózního portu (v. jugularis interna l. sin.)

