# Pacientka P06 – HER2+ karcinom prsu se smíšenou odpovědí – rostoucí dominantní plicní ložisko nejasného původu a neřešený nádor ledviny

> **Fiktivní pacient.** Vytvořeno pro hackathon Rakathon 2026 (MDT Copilot). Neodpovídá žádné skutečné osobě. Klinicky neověřeno – nepoužívat pro péči o pacienty.

- **Pohlaví:** žena · **rok narození:** 1950 · **věk k datu MDT:** 76
- **Identifikátor ve FHIR:** `Patient/P06` · každý záznam níže nese ID zdroje v hranatých závorkách, např. `[P06-doc01]`.

## Diagnózy
- `[P06-dg1]` **C50.4** Zhoubný novotvar horního zevního kvadrantu prsu (levý prs) · morfologie ICD-O-3 8500/3 Invazivní karcinom prsu NST (duktální) · od 2025-10-07
  - klinické TNM: cT3 cN1 cM1, stadium IV (2025-11-12)
- `[P06-dg2]` **C78.0** Sekundární zhoubný novotvar plic (předpoklad – původ histologicky neurčen) · od 2025-11-10
- `[P06-dg3]` **D41.0** Novotvar nejistého chování ledviny – suspektní renální karcinom pravé ledviny (cT1b) · od 2025-10-17
- `[P06-kom1]` **I10** Esenciální hypertenze
- `[P06-kom2]` **N18.3** Chronické onemocnění ledvin, stadium 3 (G3a)
- `[P06-kom3]` **M15.9** Polyartróza (kyčle, kolena)

## Nominace na MDT (žádanka)

`[P06-zad01]` · stav **Naplánovaná** · plánovaný termín MDT **2026-10-21**

| Položka | Obsah |
|---|---|
| Datum vytvoření | 2026-10-07 |
| Žádající lékař / pracoviště | LEK-P06-01 (klinický onkolog (ošetřující lékař)), Onkologická klinika – ambulance klinické onkologie |
| Požadované zaměření MDT | Mamární komise s účastí hrudní komise (hrudní chirurg, pneumolog) a urologa |
| Typ projednání | Restaging / hodnocení odpovědi |
| Priorita | běžná |
| Požadovaný termín (nejpozději) | 2026-10-23 |
| Typ klinické otázky | Diagnostická nejasnost, Léčebný plán, Systémová léčba |
| **Otázka pro MDT** | **Smíšená odpověď na 1. linii pertuzumab + trastuzumab: prs, axila a ostatní plicní ložiska regredují nebo jsou stabilní, ale dominantní plicní ložisko v pravém horním laloku roste (nadir 30 → 46 mm) a zvětšuje se uzlina 4R. Jde o metastázu karcinomu prsu, nebo o druhý primární nádor plic? Indikovat rebiopsii (CT-navigovaná biopsie / EBUS z 4R) s vyšetřením HER2, ER a IHC původu? Pokračovat do výsledku v udržovací PH, nebo změnit linii? Kdy a jak řešit suspektní nádor pravé ledviny (cT1b, 54 → 57 mm)?** |
| Diagnózy | `P06-dg1`, `P06-dg2`, `P06-dg3` |
| Histologie a grade | Prs: invazivní karcinom NST G2, ER 15 %, PR 0 %, HER2 3+, Ki-67 12 % (core biopsie 7. 10. 2025). Plíce PHL: málo diferencovaný karcinom, TTF-1−, GATA3−, původ neurčen, HER2 nevyšetřen (10. 11. 2025). Ledvina: neověřeno. |
| Relevantní komorbidity a současný stav | Hypertenze, CKD G3a (kreatinin 106 µmol/l), polyartróza – chůze s holí, neuropatie G2 po paklitaxelu. ECOG 1. Echokardiografie: LVEF 61 % (1/2026), kardiálně kompenzovaná. |
| Preference pacienta | Prioritou je kvalita života a soběstačnost (žije sama). Po pneumotoraxu při první biopsii má obavy z další biopsie plic; operaci ledviny si nepřeje, pokud nebude nezbytná. |
| Pacient informován o projednání | ano |
| Předchozí MDT | `P06-mdt01` |

**Předchozí onkologická léčba**
- [Cílená léčba] pertuzumab + trastuzumab + paklitaxel, 6 cyklů (paklitaxel týdně 18×, redukovaně 64 → 48 mg/m², ukončen pro neuropatii G2) (2025-11-17 – 2026-03-16)
- [Cílená léčba] udržovací pertuzumab + trastuzumab á 3 týdny (2026-03-23 – dosud)

**Podklady (odkazy):** `P06-pat01`, `P06-pat02`, `P06-img02`, `P06-img04`, `P06-img05`, `P06-doc02`, `P06-doc03`, `P06-doc11`, `P06-lab07`, `P06-bm03`, `P06-bm07`, `P06-ecog04`

## Chronologie dokumentace

### 2025-10-03 · RDG · Mamografie a UZ prsů a axil  `[P06-img01]`
*Zobrazení · Radiodiagnostické oddělení – mamodiagnostika · autor LEK-P06-04 (radiolog)*

Indikace: hmatná rezistence levého prsu, poslední screeningová mamografie před 3 lety.

Mamografie oboustranně (CC, MLO), doplněna UZ obou prsů a axil.
Levý prs: V horním zevním kvadrantu nepravidelné, neostře ohraničené ložisko 55 × 44 mm, sonograficky hypoechogenní s nepravidelným okrajem. Kůže a bradavka bez známek infiltrace.
Levá axila: uzlina se ztluštělým kortexem a setřelým hilem, 21 mm v krátké ose, další 2 uzliny do 9 mm.
Pravý prs a pravá axila: bez ložiskových změn.

Závěr: Levý prs HZK – suspektní malignita, BI-RADS 5. Suspektní uzlina levé axily. Pravý prs BI-RADS 1.
Doporučení: core biopsie ložiska levého prsu pod UZ kontrolou.

### 2025-10-07 · PAT-B · Core biopsie ložiska levého prsu  `[P06-pat01]`
*Patologie · Patologie – bioptická laboratoř · autor LEK-P06-03 (patolog)*

Materiál: 4 válečky z ložiska levého prsu, horní zevní kvadrant (core biopsie pod UZ kontrolou).

Mikroskopicky: Infiltrace invazivním karcinomem bez zvláštního typu (NST) s trámčitou a solidní stavbou, středně výrazná jaderná pleomorfie, ojedinělé mitózy. Nottingham skóre 2 + 2 + 2 = 6 (G2). Zastižena lymfovaskulární invaze.

Imunohistochemie:
- estrogenové receptory (ER): pozitivní v 15 % nádorových buněk, slabá intenzita
- progesteronové receptory (PR): 0 %
- HER2: IHC 3+ (kompletní silné membránové barvení ve více než 10 % buněk) – HER2 pozitivní
- Ki-67: 12 %

Závěr: Invazivní karcinom levého prsu NST, G2, ER 15 % (slabě pozitivní), PR 0 %, HER2 pozitivní (IHC 3+), Ki-67 12 %.

KLASIFIKACE: Topografie (ICD-O-3) C50.4, Morfologie (ICD-O-3) 8500/3

### 2025-10-13 · A-MAM · Vstupní vyšetření v mamární poradně  `[P06-doc01]`
*Zpráva · Mamární poradna · autor LEK-P06-02 (chirurg – mamární chirurgie)*

Důvod: došetření nově zjištěné rezistence levého prsu, histologie z core biopsie k dispozici.

NO: Pravidelně chodila na screeningovou mamografii, naposledy asi před 3 lety. Na podzim si sama nahmatala tuhou nebolestivou bulku v horním zevním kvadrantu levého prsu, poslední týdny vnímá pnutí a občasné pobolívání. Praktický lékař ji odeslal na mamografii.
Subjektivně: Mírné pobolívání levého prsu, dlouhodobé bolesti kyčlí a kolen. Nehubne, teploty nemá, dušnost jen při větší námaze. Chuť k jídlu dobrá.

Objektivně: ECOG 1. Výška 160 cm, hmotnost 68 kg. Orientovaná, kardiopulmonálně kompenzovaná. Srdce – systolický šelest nad aortou. Dýchání sklípkové. Břicho měkké, nebolestivé. DKK bez otoků.
Stav místní: Prsy asymetrické, levý zvětšený. Vlevo tuhá nepravidelná rezistence v horních a dolních vnitřních kvadrantech cca 5,5 × 5 cm, kůže nad ní bez infiltrace, bradavka bez retrakce. V levé axile hmatná uzlina cca 2 × 1 cm. Vpravo prs i axila bez patologie. Nadklíčky volné.

Dosavadní vyšetření: MG + UZ 3. 10. – ložisko levého prsu 55 mm, BI-RADS 5, suspektní uzlina levé axily. Core biopsie 7. 10. – invazivní karcinom NST G2, ER 15 %, PR 0 %, HER2 3+, Ki-67 12 %.
Laboratoř dnes: Hb 114 g/l, Tr 432, kreatinin 98 µmol/l, CA 15-3 68 kU/l, CEA 7,9 µg/l.

Závěr: Karcinom levého prsu NST G2, ER slabě pozitivní, PR negativní, HER2 pozitivní, cT3 N1 Mx. Postmenopauzální pacientka.
Plán: CT hrudníku, břicha a pánve, echokardiografie před anti-HER2 léčbou, projednání na mamární komisi.

### 2025-10-17 · RDG · CT hrudníku, břicha a pánve s k. l. – staging  `[P06-img02]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P06-04 (radiolog)*

Technika: CT hrudníku, břicha a pánve po i.v. aplikaci k. l.

Hrudník: Levý prs – nepravidelné ložisko 55 mm (cílová léze 1), kůže bez infiltrace. Levá axila – uzlina 21 mm v krátké ose (cílová léze 2).
Plíce: V pravém horním laloku (S1) dominantní spikulované ložisko 31 mm s pleurální retrakcí (cílová léze 3) – morfologicky může odpovídat i primárnímu plicnímu nádoru. V levém dolním laloku (S10) okrouhlé ložisko 14 mm (cílová léze 4). Dále vícečetná okrouhlá ložiska oboustranně do 6 mm charakteru metastáz (necílové léze).
Mediastinum: zvětšená pravostranná paratracheální uzlina (4R) 16 mm v krátké ose (cílová léze 5), hilové uzliny do 9 mm. Malý fluidothorax vpravo (necílový nález).
Břicho a pánev: Játra, slezina, slinivka a nadledviny bez ložisek. Pravá ledvina menší, se sníženým sycením parenchymu; v dolním pólu solidně-cystický útvar 54 × 48 mm se sytící se solidní složkou – suspektní renální karcinom (cT1b), bez trombu v renální žíle, bez lymfadenopatie. Levá ledvina bez patologie. Bez ascitu.
Skelet: degenerativní změny páteře, bez ložisek metastatického vzhledu.

Závěr: Tumor levého prsu (cT3) s metastatickou uzlinou levé axily (cN1). Mnohočetná plicní ložiska oboustranně – dominantní ložisko pravého horního laloku suspektní z primárního plicního nádoru, ostatní spíše metastázy. Mediastinální lymfadenopatie. Suspektní nádor pravé ledviny 54 mm.
Cílové léze (RECIST 1.1): prs 55 mm, axilární uzlina 21 mm, ložisko PHL 31 mm, ložisko LDL 14 mm, uzlina 4R 16 mm – součet 137 mm. Útvar ledviny hodnocen samostatně (suspektní další primární nádor).

### 2025-10-22 · MDT · Záznam MDT – Mamární komise – karcinom prsu  `[P06-mdt01]`
*Předsedající LEK-P06-07 · účastníci: klinický onkolog, klinický onkolog, mamární chirurg, radiolog, radiační onkolog, patolog · pacient přítomen: ne*

**Typ projednání:** Primární projednání  
**Projednaná otázka:** Léčebný plán u nově diagnostikovaného HER2+ karcinomu levého prsu cT3 N1 s mnohočetnými plicními ložisky, mediastinální lymfadenopatií a suspektním nádorem pravé ledviny.  
**Klinické zhodnocení:** Invazivní karcinom levého prsu NST G2, ER 15 %, PR 0 %, HER2 3+, Ki-67 12 %, cT3 N1. CT 17. 10.: mnohočetná plicní ložiska, dominantní ložisko PHL 31 mm suspektní z primárního plicního nádoru, uzlina 4R 16 mm, solidně-cystický útvar pravé ledviny 54 mm. Nelze vyloučit duplicitu až triplicitu malignit. Pravděpodobně dominuje generalizovaný HER2+ karcinom prsu. ECOG 1, hypertenze, CKD G3a.  
**Léčebný záměr:** Paliativní  
**Doporučený postup:**
1. [Diagnostika] Histologická verifikace dominantního ložiska pravého horního laloku (biopsie pod CT) s imunohistochemií k určení původu – po stanovisku hrudní komise
2. [Cílená léčba] Při potvrzení metastáz karcinomu prsu pertuzumab + trastuzumab + taxan, poté udržovací pertuzumab + trastuzumab – restaging CT po 3 cyklech
3. [Diagnostika] Echokardiografie (LVEF) před zahájením a á 3 měsíce během anti-HER2 léčby
4. [Sledování] Suspektní nádor pravé ledviny – stanovisko uroonkologické komise, sledování

**Doplnit:** Hrudní komise – posouzení dominantního plicního ložiska a způsobu biopsie; Uroonkologická komise – stanovisko k nádoru pravé ledviny

**Klinická studie:** Nezvažována.

**Závěr MDT:** Pravděpodobně generalizovaný HER2+ karcinom levého prsu – nejprve histologicky ověřit dominantní plicní ložisko (metastáza vs. primární plicní nádor). Při potvrzení metastatického karcinomu prsu zahájit pertuzumab + trastuzumab + taxan. Nádor ledviny zatím sledovat.

**Rozhodnutí o léčbě** `[P06-mdt01-rozhodnuti]` (2025-11-12, LEK-P06-01): Zahájení pertuzumab + trastuzumab á 21 dní + paklitaxel týdně, od počátku s redukcí paklitaxelu na 80 % (64 mg/m²) · stanovisko pacienta: Souhlasí – na aplikace požaduje převoz sanitou pro omezenou mobilitu

### 2025-10-27 · A-HCH · Stanovisko hrudní indikační komise  `[P06-doc02]`
*Zpráva · Hrudní chirurgie – hrudní indikační komise · autor LEK-P06-06 (hrudní chirurg)*

Přítomni: hrudní chirurg, pneumolog, radiolog, radiační onkolog, klinický onkolog.

Podklady: HER2 pozitivní karcinom levého prsu cT3 N1, CT 17. 10. 2025 – mnohočetná plicní ložiska oboustranně, dominantní spikulované ložisko pravého horního laloku 31 mm, mediastinální uzlina 4R 16 mm, suspektní nádor pravé ledviny.

Diskuse: Dominantní ložisko pravého horního laloku má morfologii možného primárního plicního nádoru, ostatní ložiska odpovídají spíše metastázám. Rozsah nálezu radikální chirurgický výkon neumožňuje.

Závěr: Doporučena histologická verifikace ložiska pravého horního laloku – perkutánní transtorakální biopsie pod CT kontrolou, při nediagnostickém výsledku EBUS z uzliny 4R, event. VATS biopsie. Materiál vyšetřit imunohistochemicky k určení původu. Výsledek předložit mamární komisi.

### 2025-10-27 · A-URO · Stanovisko uroonkologické komise  `[P06-doc03]`
*Zpráva · Urologie – uroonkologická komise · autor LEK-P06-09 (urolog)*

Podklady: CT 17. 10. 2025 – solidně-cystický útvar dolního pólu pravé ledviny 54 × 48 mm se sytící se solidní složkou, pravá ledvina menší se sníženým sycením parenchymu. Současně HER2 pozitivní karcinom levého prsu s mnohočetnými plicními ložisky a suspektním primárním ložiskem pravé plíce. Kreatinin 98 µmol/l.

Rozvaha: Nález odpovídá suspektnímu renálnímu karcinomu cT1b N0, bez známek šíření z této lokalizace. Prognózu nyní určuje generalizované onemocnění prsu a plic; radikální výkon na ledvině by ji neovlivnil a při snížené funkci ledvin nese riziko dalšího zhoršení.

Závěr: Nádor ledviny nyní není prioritou. Prioritou je verifikace plicního ložiska a systémová léčba.
Doporučení: velikost útvaru sledovat na restagingových CT; po stabilizaci karcinomu prsu (orientačně do 6 měsíců) znovu předložit uroonkologické komisi – zvážit biopsii, ablaci nebo aktivní sledování.

### 2025-10-29 · A-KARD · Echokardiografie před zahájením anti-HER2 léčby  `[P06-doc04]`
*Zpráva · Kardiologická ambulance · autor LEK-P06-10 (kardiolog)*

Indikace: vstupní vyšetření před léčbou trastuzumabem a pertuzumabem.

Sinusový rytmus 70/min. Vyšetření částečně limitováno horší vyšetřitelností, základní parametry hodnotitelné.
Levá komora normální velikosti, bez hypertrofie, bez poruchy kinetiky. LVEF 65 % (biplane Simpson). Pravá komora normální. Chlopně bez hemodynamicky významné vady, fyziologická trikuspidální regurgitace. Odhad tlaku v plicnici lehce zvýšený. Perikard bez výpotku.

Závěr: Zachovaná systolická funkce LK, LVEF 65 %.
Doporučení: Bez kontraindikace anti-HER2 léčby. Kontrolní echokardiografie á 3 měsíce během léčby.

### 2025-11-06 · L-PNEU · Propouštěcí zpráva – biopsie plicního ložiska  `[P06-doc05]`
*Zpráva · Pneumologické oddělení – lůžková část · autor LEK-P06-05 (pneumolog)*

Hospitalizace 3. 11. – 6. 11. 2025.
Důvod přijetí: transtorakální biopsie dominantního ložiska pravého horního laloku pod CT kontrolou k odlišení metastázy karcinomu prsu od primárního plicního nádoru (dle doporučení mamární a hrudní komise).

Anamnéza: Žije sama v bytě, soběstačná, mobilitu omezují bolesti kloubů, chodí s holí. V důchodu. Dříve dlouhodobě kouřila, nekouří řadu let. OA: hypertenze, chronické onemocnění ledvin, polyartróza kyčlí a kolen. Bez IM, CMP a diabetu. RA: nádory v rodině neudává. Alergie: lékové neudává, po některých doplňcích stravy otoky.
FA při přijetí: metoprolol 25 mg 1-0-0, perindopril/indapamid 5/1,25 mg 1-0-0, kyselina acetylsalicylová 100 mg 0-1-0, atorvastatin 20 mg 0-0-1, občas ibuprofen na klouby.

Průběh: 4. 11. provedena biopsie ložiska PHL pod CT kontrolou (radiolog). Po výkonu malý apikální pneumotorax vpravo, bez dušnosti, řešen konzervativně; kontrolní RTG 5. a 6. 11. stacionární až regredující nález, drenáž nebyla nutná. Afebrilní, oběhově stabilní.
Po konzultaci klinického farmaceuta snížena dávka perindoprilu/indapamidu na 2,5/0,625 mg vzhledem k renální funkci (kreatinin 98 µmol/l, eGFR cca 50 ml/min/1,73 m²); nesteroidní antirevmatika nahrazena paracetamolem.

Závěr: St. p. transtorakální biopsii ložiska pravého horního laloku, malý pneumotorax řešen konzervativně. Karcinom levého prsu HER2+, suspektní nádor pravé ledviny. Hypertenze, CKD G3a, polyartróza.
Doporučení: Výsledek histologie očekáván do týdne, sdělí ošetřující onkolog. Při náhlé dušnosti nebo bolesti na hrudi ihned vyhledat lékaře. Paracetamol 500–1000 mg při bolesti, max. 3 g/den. Vyhnout se NSA.

### 2025-11-10 · PAT-B · Transtorakální biopsie ložiska pravého horního laloku  `[P06-pat02]`
*Patologie · Patologie – bioptická laboratoř · autor LEK-P06-03 (patolog)*

Materiál: 3 drobné válečky plicní tkáně z ložiska pravého horního laloku (biopsie pod CT kontrolou 4. 11. 2025), zpracováno celé.

Mikroskopicky: Plicní parenchym s fibrózou a mírným zánětlivým infiltrátem. V tomto terénu ojedinělé nepravidelné trámce a čepy atypických buněk se zvětšenými hyperchromními jádry, místy s prominujícími jadérky, ojedinělé mitózy. Nádorové infiltráty tvoří méně než 10 % plochy vzorku.

Imunohistochemie: pankeratin AE1/AE3 pozitivní, CK7 pozitivní, TTF-1 negativní, napsin A negativní, GATA3 negativní, p40 negativní.
Pro minimální objem nádorové tkáně nebylo možné provést další vyšetření (ER, PR, HER2) – materiál vyčerpán.

Závěr: Málo diferencovaný karcinom v minimálním rozsahu. Imunoprofil neurčuje primární původ (TTF-1 a GATA3 negativní) – nelze spolehlivě odlišit metastázu karcinomu prsu od primárního plicního karcinomu. Nutno hodnotit v klinicko-radiologickém kontextu, při klinické potřebě rebiopsie.

KLASIFIKACE: Topografie (ICD-O-3) C34.1, Morfologie (ICD-O-3) 8010/3

### 2025-11-17 · A-ONK · Zahájení 1. linie – pertuzumab + trastuzumab + paklitaxel  `[P06-doc06]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P06-01 (klinický onkolog (ošetřující lékař))*

Shrnutí: Karcinom levého prsu NST G2, ER 15 %, PR 0 %, HER2 3+, Ki-67 12 %, cT3 N1. Na CT mnohočetná plicní ložiska, mediastinální lymfadenopatie, suspektní nádor pravé ledviny cT1b (uroonkologická komise: nyní není priorita).
Biopsie ložiska PHL (10. 11.): málo diferencovaný karcinom, TTF-1 a GATA3 negativní, původ neurčen; HER2 pro nedostatek materiálu nevyšetřen. Vzhledem k mnohočetnosti plicních ložisek a známému HER2+ karcinomu prsu hodnotím jako generalizovaný karcinom prsu (M1 – plíce, mediastinální uzliny), stadium IV.

Subjektivně: Námahová dušnost, občas noční pocení, bolesti zad a kloubů beze změny. Kašel minimální. Po biopsii bez potíží.
Objektivně: ECOG 1–2 (chůze s holí), hmotnost 67 kg, TK 140/85. Levý prs – tuhá rezistence cca 5 cm, kůže klidná. Dýchání oboustranně slyšné.
Laboratoř dnes: Hb 111 g/l, neutrofily 5,2, Tr 418, kreatinin 101 µmol/l, ALT a bilirubin v normě, CA 15-3 61 kU/l, CEA 7,4 µg/l.
Echokardiografie 29. 10.: LVEF 65 %.

Terapie: Zahájena 1. linie paliativní léčby – pertuzumab 840 mg i.v. (úvodní dávka), trastuzumab 8 mg/kg i.v. (úvodní dávka), paklitaxel 64 mg/m² i.v. (80 % standardní týdenní dávky 80 mg/m² vzhledem k věku a komorbiditám). Pertuzumab + trastuzumab á 21 dní, paklitaxel každý týden. Aplikace periferní kanylou.
Edukace o nežádoucích účincích (neuropatie, alopecie, průjem, infuzní reakce, kardiotoxicita). Pacientka s léčbou souhlasí, na aplikace dojíždí sanitou.
Plán: paklitaxel 24. 11., další podání PH 8. 12., restagingové CT po 3 cyklech, echokardiografie á 3 měsíce.

### 2026-01-12 · RDG · CT hrudníku, břicha a pánve s k. l. – restaging po 3 cyklech  `[P06-img03]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P06-04 (radiolog)*

Srovnání s CT z 17. 10. 2025.

Levý prs: ložisko 34 mm (dříve 55 mm).
Levá axila: uzlina 11 mm v krátké ose (dříve 21 mm).
Plíce: ložisko PHL 30 mm (dříve 31 mm), morfologie beze změny. Ložisko LDL 8 mm (dříve 14 mm). Drobná ložiska oboustranně menší, některá jen naznačená. Fluidothorax vpravo vymizel.
Mediastinum: uzlina 4R 11 mm v krátké ose (dříve 16 mm).
Pravá ledvina: solidně-cystický útvar 54 mm, beze změny.
Bez nových ložisek.

Závěr: Parciální odpověď dle RECIST 1.1 – součet cílových lézí 94 mm (pokles o 31 %). Dominantní plicní ložisko v pravém horním laloku na léčbu nereaguje (31 → 30 mm), ostatní léze včetně ostatních plicních ložisek regredují.

### 2026-01-19 · A-ONK · Kontrola před 4. cyklem – restaging, redukce paklitaxelu  `[P06-doc07]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P06-01 (klinický onkolog (ošetřující lékař))*

Subjektivně: Lokální nález na prsu se zlepšuje, bolest prsu minimální. Únava hlavně den až dva po infuzi. Brnění prstů rukou mezi podáními přetrvává, jemnou motoriku zatím neomezuje. Dušnost při námaze mírně menší.
Objektivně: ECOG 1–2, levý prs – rezistence menší, cca 3 cm. DKK bez otoků.
Laboratoř dnes: Hb 102 g/l, neutrofily 2,4, Tr 302, kreatinin 96 µmol/l, CA 15-3 33 kU/l, CEA 4,6 µg/l.
Echokardiografie 14. 1.: LVEF 61 %.
CT 12. 1.: parciální odpověď (137 → 94 mm), dominantní plicní ložisko PHL beze změny (30 mm).

Toxicita: periferní senzitivní neuropatie G1 s progresí, anémie G1.
Podán 4. cyklus: pertuzumab 420 mg, trastuzumab 6 mg/kg; paklitaxel od dneška redukován na 56 mg/m² týdně (70 % dávky) pro neuropatii.
Plán: pokračovat, při zhoršení neuropatie ukončit paklitaxel a přejít na udržovací PH. Dominantní plicní ložisko PHL sledovat na dalším CT.

### 2026-03-23 · A-ONK · Ukončení paklitaxelu, přechod na udržovací PH  `[P06-doc08]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P06-01 (klinický onkolog (ošetřující lékař))*

Paklitaxel týdně podán 18× (6 cyklů, poslední 16. 3.; od 2. 3. další redukce na 48 mg/m²).

Subjektivně: Brnění prstů rukou i nohou obtěžuje, hůře zapíná knoflíky, při chůzi nejistota. Únava. Dušnost při námaze stacionární.
Objektivně: ECOG 2 (chůze s holí, kratší vzdálenosti), hmotnost 67 kg, TK 135/80. Levý prs – reziduální rezistence.
Neurologicky: distální senzitivní polyneuropatie, bez motorického deficitu.
Laboratoř dnes: Hb 108 g/l, neutrofily 2,9, kreatinin 99 µmol/l, CA 15-3 26 kU/l, CEA 4,1 µg/l.

Toxicita: periferní neuropatie G2 – paklitaxel ukončen.
Endokrinní léčba k udržovací PH zvážena (ER 15 %), pro artralgie a nízkou expresi ER zatím nepřidána.
Terapie: zahájena udržovací léčba pertuzumab 420 mg + trastuzumab 6 mg/kg á 3 týdny.
Plán: CT za 3 měsíce, echokardiografie á 3 měsíce. Pro obtížný periferní žilní přístup odeslána k implantaci venózního portu.

### 2026-04-12 · Dotazník pacienta (PROMs)  `[P06-prom01]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 3 |
| Kde vás bolí? (vlastními slovy) | kyčle, kolena, záda |
| Únava za poslední týden (0–10) | 5 |
| Nevolnost nebo zvracení (0–10) | 1 |
| Dušnost (0–10) | 4 |
| Nechutenství (0–10) | 3 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 6 |
| Průjem (0–10) | 0 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 4 |
| Potíže se spánkem (0–10) | 4 |
| Jak zvládáte běžný den? | Postarám se o sebe, ale pracovat nemohu; přes den odpočívám méně než polovinu času |
| Kolik zvládnete ujít? | Jedno patro vyjdu jen se zastávkou |
| Vaše současná hmotnost (kg) | 67 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | -1 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | Brní mě prsty na rukou i na nohou, chodím nejistě, venku s holí. |
| Alergie nebo nesnášenlivost léků | po některých doplňcích stravy otoky |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | nic |
| Co je pro vás v léčbě nejdůležitější? | Nejdůležitější je pro mě kvalita života, i kdyby léčba byla méně účinná |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Chci zůstat doma a postarat se o sebe. Na velké operace se už necítím. |
| Podpora v domácnosti | Podporu mám jen částečně |

### 2026-04-20 · A-CHIR · Implantace venózního portu  `[P06-doc09]`
*Zpráva · Chirurgická ambulance – jednodenní chirurgie · autor LEK-P06-11 (chirurg – jednodenní chirurgie)*

Indikace: dlouhodobá udržovací anti-HER2 léčba, opakované obtíže s periferními kanylami, špatné periferní žíly.

Výkon: implantace venózního portu cestou v. subclavia l. dx. (kontralaterálně k postiženému levému prsu) v lokální anestezii a krátké analgosedaci, pod skiaskopickou kontrolou. Hrot katétru v úrovni kavoatriálního přechodu. Port funkční, propláchnut, uzavřen heparinovou zátkou. Krevní ztráta minimální, bez komplikací.

Doporučení: kontrola rány a extrakce stehů za 10 dní, port lze používat ihned. Při zarudnutí, otoku nebo bolesti v okolí portu ihned kontaktovat lékaře.

### 2026-06-22 · RDG · CT hrudníku, břicha a pánve s k. l. – kontrola na udržovací PH  `[P06-img04]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P06-04 (radiolog)*

Srovnání s CT z 12. 1. 2026 a z 17. 10. 2025.

Levý prs: ložisko 27 mm (dříve 34 mm).
Levá axila: uzlina 9 mm v krátké ose (dříve 11 mm).
Plíce: ložisko PHL 34 mm (dříve 30 mm). Ložisko LDL 7 mm (dříve 8 mm). Drobná ložiska oboustranně beze změny nebo menší.
Mediastinum: uzlina 4R 10 mm v krátké ose (dříve 11 mm).
Pravá ledvina: solidně-cystický útvar 55 mm (dříve 54 mm).
Játra, nadledviny, skelet bez nových ložisek.

Závěr: Trvá parciální odpověď dle RECIST 1.1 – součet cílových lézí 87 mm (pokles o 36,5 % proti výchozímu vyšetření). Dominantní plicní ložisko pravého horního laloku mírně větší (34 mm), doporučena kontrola za 3 měsíce.

### 2026-08-24 · A-KARD · Kontrolní echokardiografie na anti-HER2 léčbě  `[P06-doc10]`
*Zpráva · Kardiologická ambulance · autor LEK-P06-10 (kardiolog)*

Indikace: pravidelná kontrola při léčbě trastuzumabem a pertuzumabem.

Subjektivně: Námahová dušnost (přisuzuje plicnímu onemocnění a věku), bez otoků a palpitací.
Nález: Levá komora na horní hranici normy, bez segmentální poruchy kinetiky. LVEF 55 % (biplane Simpson). Lehká funkční trikuspidální regurgitace. Perikard bez výpotku.
Srovnání: vstupně 29. 10. 2025 LVEF 65 %, 14. 1. 2026 61 %, 4. 5. 2026 58 %.

Závěr: Pokles LVEF na 55 % – o 10 procentních bodů proti vstupnímu vyšetření, bez klinických známek srdečního selhání.
Doporučení: V anti-HER2 léčbě lze pokračovat se zvýšenou kardiologickou vigilancí. Kontrolní echokardiografie za 6 týdnů (začátkem října 2026). Medikaci (metoprolol, perindopril/indapamid) ponechat.

### 2026-09-21 · RDG · CT hrudníku, břicha a pánve s k. l. – restaging  `[P06-img05]`
*Zobrazení · Radiodiagnostické oddělení · autor LEK-P06-04 (radiolog)*

Srovnání s CT z 22. 6. 2026 a z 17. 10. 2025.

Levý prs: ložisko 25 mm (dříve 27 mm).
Levá axila: uzlina 8 mm v krátké ose (dříve 9 mm).
Plíce: dominantní plicní ložisko PHL 46 mm (dříve 34 mm, nadir 30 mm), nově širší kontakt s pleurou, bez destrukce žeber. Ložisko LDL 7 mm, beze změny. Drobná ložiska oboustranně beze změny. Bez fluidothoraxu.
Mediastinum: uzlina 4R 15 mm v krátké ose (dříve 10 mm).
Pravá ledvina: solidně-cystický útvar 57 mm (dříve 55 mm, výchozí 54 mm), bez známek lokálního šíření.
Játra, nadledviny, skelet: bez ložisek. Bez jednoznačně nových ložisek.

Závěr: Smíšená odpověď – další regrese v prsu a axile, disociovaný růst dominantního ložiska pravého horního laloku a zvětšení mediastinální uzliny 4R. Součet cílových lézí 101 mm (−26 % proti výchozímu vyšetření, +16 % proti nadiru 87 mm) – dle RECIST 1.1 stabilní onemocnění.
Diferenciálně diagnosticky: klon metastázy s odlišnou biologií vs. synchronní primární plicní nádor. Doporučena histologická verifikace.

### 2026-10-03 · Dotazník pacienta (PROMs)  `[P06-prom02]`

| Otázka | Odpověď |
|---|---|
| Bolest za poslední týden (0–10) | 4 |
| Kde vás bolí? (vlastními slovy) | záda a klouby |
| Únava za poslední týden (0–10) | 7 |
| Nevolnost nebo zvracení (0–10) | 1 |
| Dušnost (0–10) | 6 |
| Nechutenství (0–10) | 5 |
| Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | 5 |
| Průjem (0–10) | 0 |
| Psychická zátěž – úzkost, smutek, starosti (0–10) | 6 |
| Potíže se spánkem (0–10) | 5 |
| Jak zvládáte běžný den? | Postarám se o sebe, ale pracovat nemohu; přes den odpočívám méně než polovinu času |
| Kolik zvládnete ujít? | Zvládnu jen chůzi po rovině |
| Vaše současná hmotnost (kg) | 63 |
| Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | -3 |
| Objevily se od minulé návštěvy nové obtíže? Jaké? | Víc se zadýchám, do schodů musím odpočívat, častěji kašlu. Nemám chuť k jídlu. |
| Alergie nebo nesnášenlivost léků | po některých doplňcích stravy otoky |
| Léky, doplňky stravy nebo bylinky, které užíváte navíc | nic |
| Co je pro vás v léčbě nejdůležitější? | Nejdůležitější je pro mě kvalita života, i kdyby léčba byla méně účinná |
| Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | Léčbu chci, dokud ji zvládnu. Další odběr z plic ani operaci ledviny nechci, pokud to nebude opravdu nutné – po minulé biopsii mi splaskla plíce. |
| Podpora v domácnosti | Podporu mám jen částečně |

### 2026-10-05 · A-ONK · Kontrola po restagingu, nominace na komisi  `[P06-doc11]`
*Zpráva · Ambulance klinické onkologie · autor LEK-P06-01 (klinický onkolog (ošetřující lékař))*

Udržovací pertuzumab + trastuzumab od 23. 3. 2026 (1. linie od 17. 11. 2025), poslední podání 28. 9., další plánováno 19. 10.

Subjektivně: Únava, dušnost při chůzi do schodů horší než v létě, častěji kašle, bez hemoptýzy. Bolesti zad a kloubů stacionární. Brnění prstů přetrvává. Hubne, chuť k jídlu horší.
Objektivně: ECOG 1, hmotnost 63 kg, TK 130/80, SpO2 95 %. Chůze s holí. Dýchání vpravo nahoře lehce oslabené. Levý prs – malá reziduální rezistence, kůže klidná. Port klidný.
Laboratoř dnes: Hb 113 g/l, neutrofily 4,3, Tr 301, kreatinin 106 µmol/l, ALT 0,34, bilirubin 10, albumin 34 g/l, LD 4,4 µkat/l, CA 15-3 52 kU/l (21. 9.: 41), CEA 8,6 µg/l (21. 9.: 6,4).
CT 21. 9.: smíšená odpověď – prs a axila regredují, dominantní plicní ložisko PHL roste (34 → 46 mm), ostatní plicní ložiska ne, uzlina 4R 15 mm; dle RECIST stabilní onemocnění. Útvar pravé ledviny 57 mm.

Závěr: HER2+ karcinom levého prsu stadium IV na udržovací PH se smíšenou odpovědí. Rostoucí dominantní plicní ložisko v pravém horním laloku (ostatní plicní ložiska regredovala) histologicky bez určení původu (HER2 nevyšetřen) – metastáza, nebo druhý primární nádor plic? Suspektní nádor pravé ledviny od 10/2025 bez dalšího urologického přehodnocení.
Plán: Nominace na mamární komisi s účastí hrudní komise a urologa. Do rozhodnutí pokračovat v udržovací PH. Pacientka si přeje zachovat soběstačnost, z další biopsie plic má obavy (po minulé biopsii pneumotorax).

## Laboratoř

ID výsledku: `P06-labNN-<parametr>`, NN = pořadí odběru (sloupec).

| Parametr | Jednotka | Norma | 01: 2025-10-13 | 02: 2025-11-17 | 03: 2026-01-19 | 04: 2026-03-23 | 05: 2026-06-22 | 06: 2026-09-21 | 07: 2026-10-05 |
|---|---|---|---|---|---|---|---|---|---|
| Hemoglobin (LOINC 718-7) | g/l | 120–160 | 114 ↓ | 111 ↓ | 102 ↓ | 108 ↓ | 117 ↓ | 115 ↓ | 113 ↓ |
| Neutrofily absolutně (LOINC 751-8) | 10^9/l | 2.0–7.0 | 5.8 | 5.2 | 2.4 | 2.9 | 3.8 | 4.1 | 4.3 |
| Trombocyty (LOINC 777-3) | 10^9/l | 150–400 | 432 ↑ | 418 ↑ | 302 | 288 | 276 | 290 | 301 |
| Kreatinin (LOINC 14682-9) | µmol/l | 44–104 | 98 | 101 | 96 | 99 | 102 | 104 | 106 ↑ |
| ALT (LOINC 1742-6) | µkat/l | 0.1–0.78 | 0.32 | 0.35 | 0.41 | 0.38 | 0.3 | 0.33 | 0.34 |
| AST (LOINC 1920-8) | µkat/l | 0.1–0.72 | 0.38 | 0.36 | 0.44 | 0.4 | 0.35 | 0.39 | 0.41 |
| Bilirubin celkový (LOINC 14631-6) | µmol/l | 2–21 | 9 | 8 | 10 | 9 | 8 | 9 | 10 |
| Albumin (LOINC 1751-7) | g/l | 35–52 | 38 | 37 | 35 | 36 | 37 | 35 | 34 ↓ |
| LD (LOINC 14804-9) | µkat/l | 2.25–3.75 | 4.1 ↑ | 3.9 ↑ | 3.4 | 3.3 | 3.2 | 3.9 ↑ | 4.4 ↑ |
| CA 15-3 (LOINC 6875-3) | kU/l | 0–31 | 68 ↑ | 61 ↑ | 33 ↑ | 26 | 24 | 41 ↑ | 52 ↑ |
| CEA (LOINC 2039-6) | µg/l | 0–5.0 | 7.9 ↑ | 7.4 ↑ | 4.6 | 4.1 | 3.8 | 6.4 ↑ | 8.6 ↑ |

## Strukturované nálezy (ECOG, biomarkery, staging, hmotnost)

- 2025-10-07 `[P06-bm01]` Estrogenové receptory (ER): pozitivní 15 %, slabá intenzita (vzorek: core biopsie levého prsu) · zdroj `P06-pat01`
- 2025-10-07 `[P06-bm02]` Progesteronové receptory (PR): 0 % (vzorek: core biopsie levého prsu) · zdroj `P06-pat01`
- 2025-10-07 `[P06-bm03]` HER2: IHC 3+ – pozitivní (vzorek: core biopsie levého prsu) · zdroj `P06-pat01`
- 2025-10-07 `[P06-bm04]` Ki-67: 12 % (vzorek: core biopsie levého prsu) · zdroj `P06-pat01`
- 2025-10-13 `[P06-ecog01]` ECOG 1 (omezen(a) při fyzicky náročné činnosti, zvládá lehkou práci) – hodnotil lékař · zdroj `P06-doc01`
- 2025-10-13 `[P06-vaha01]` Hmotnost 68 kg · zdroj `P06-doc01`
- 2025-10-27 `[P06-tnm02]` TNM (klinické): suspektní renální karcinom pravé ledviny cT1b cN0 (TNM 8. vyd.), neověřeno histologicky · zdroj `P06-doc03`
- 2025-10-29 `[P06-lvef01]` LVEF (echokardiografie): 65 % · zdroj `P06-doc04`
- 2025-11-10 `[P06-bm05]` TTF-1 / napsin A: negativní / negativní (vzorek: biopsie ložiska pravého horního laloku) · zdroj `P06-pat02`
- 2025-11-10 `[P06-bm06]` GATA3: negativní (vzorek: biopsie ložiska pravého horního laloku) · zdroj `P06-pat02`
- 2025-11-10 `[P06-bm07]` HER2: nevyšetřeno – nedostatek materiálu (vzorek: biopsie ložiska pravého horního laloku) · zdroj `P06-pat02`
- 2025-11-10 `[P06-bm08]` ER / PR: nevyšetřeno – nedostatek materiálu (vzorek: biopsie ložiska pravého horního laloku) · zdroj `P06-pat02`
- 2025-11-12 `[P06-tnm01]` TNM (klinické): cT3 cN1 cM1 (plíce, mediastinální uzliny), stadium IV (TNM 8. vyd.) – M1 stanoveno klinicky, plicní ložisko histologicky bez určení původu · zdroj `P06-img02`
- 2025-11-17 `[P06-ecog02]` ECOG 2 (soběstačný(á), práce neschopen(a), mimo lůžko > 50 % dne) – hodnotil lékař · zdroj `P06-doc06`
- 2025-11-17 `[P06-vaha02]` Hmotnost 67 kg · zdroj `P06-doc06`
- 2026-01-14 `[P06-lvef02]` LVEF (echokardiografie): 61 % · zdroj `P06-doc07`
- 2026-03-23 `[P06-ecog03]` ECOG 2 (soběstačný(á), práce neschopen(a), mimo lůžko > 50 % dne) – hodnotil lékař · zdroj `P06-doc08`
- 2026-03-23 `[P06-vaha03]` Hmotnost 67 kg · zdroj `P06-doc08`
- 2026-03-23 `[P06-neuro01]` Periferní neuropatie (CTCAE) – hodnocení lékařem: grade 2 · zdroj `P06-doc08`
- 2026-05-04 `[P06-lvef03]` LVEF (echokardiografie): 58 % · zdroj `P06-doc10`
- 2026-08-24 `[P06-lvef04]` LVEF (echokardiografie): 55 % · zdroj `P06-doc10`
- 2026-10-05 `[P06-ecog04]` ECOG 1 (omezen(a) při fyzicky náročné činnosti, zvládá lehkou práci) – hodnotil lékař · zdroj `P06-doc11`
- 2026-10-05 `[P06-vaha04]` Hmotnost 63 kg · zdroj `P06-doc11`

## Léky

- `[P06-med01]` metoprolol (ATC C07AB02) – 25 mg 1-0-0 · od 2018-03-01
- `[P06-med02]` perindopril + indapamid (ATC C09BA04) – 2,5 mg/0,625 mg 1-0-0 (od 6. 11. 2025, dříve 5 mg/1,25 mg) · od 2015-06-01 · dávka snížena s ohledem na renální funkci
- `[P06-med03]` kyselina acetylsalicylová (ATC B01AC06) – 100 mg 0-1-0 · od 2018-03-01
- `[P06-med04]` atorvastatin (ATC C10AA05) – 20 mg 0-0-1 · od 2018-03-01
- `[P06-med05]` paracetamol (ATC N02BE01) – 500–1000 mg p. o. při bolesti, max. 3 g/den · od 2025-11-06 · místo nesteroidních antirevmatik
- `[P06-tx-pac-01…18]` paklitaxel (ATC L01CD01) – pertuzumab + trastuzumab + paklitaxel, 80 mg/m² i.v. každý týden (plná dávka; podávána redukovaně – viz poznámky) · podání: 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-02-02, 2026-02-09, 2026-02-16, 2026-02-23, 2026-03-02, 2026-03-09, 2026-03-16
  - 2025-11-17: 64 mg/m² (80 % – věk a komorbidity)
  - 2026-01-19: 56 mg/m² (70 %) – redukce pro progredující neuropatii
  - 2026-03-02: 48 mg/m² (60 %) – další redukce pro neuropatii
  - 2026-03-16: poslední podání – ukončeno pro neuropatii G2
- `[P06-tx-per-01…16]` pertuzumab (ATC L01FD02) – pertuzumab + trastuzumab (od 23. 3. 2026 udržovací), 420 mg i.v. á 3 týdny (úvodní dávka 840 mg) · podání: 2025-11-17, 2025-12-08, 2025-12-29, 2026-01-19, 2026-02-09, 2026-03-02, 2026-03-23, 2026-04-13, 2026-05-04, 2026-05-25, 2026-06-15, 2026-07-06, 2026-07-27, 2026-08-17, 2026-09-07, 2026-09-28
  - 2025-11-17: úvodní dávka 840 mg
  - 2026-03-23: zahájení udržovací léčby PH bez paklitaxelu
  - 2026-09-28: poslední podání před nominací; další plánováno 19. 10. 2026
- `[P06-tx-tra-01…16]` trastuzumab (ATC L01FD01) – pertuzumab + trastuzumab (od 23. 3. 2026 udržovací), 6 mg/kg i.v. á 3 týdny (úvodní dávka 8 mg/kg) · podání: 2025-11-17, 2025-12-08, 2025-12-29, 2026-01-19, 2026-02-09, 2026-03-02, 2026-03-23, 2026-04-13, 2026-05-04, 2026-05-25, 2026-06-15, 2026-07-06, 2026-07-27, 2026-08-17, 2026-09-07, 2026-09-28
  - 2025-11-17: úvodní dávka 8 mg/kg
  - 2026-03-23: zahájení udržovací léčby PH bez paklitaxelu
  - 2026-09-28: poslední podání před nominací; další plánováno 19. 10. 2026

## Výkony a radioterapie

- `[P06-proc01]` 2025-10-07 · Core biopsie ložiska levého prsu pod UZ kontrolou
- `[P06-proc02]` 2025-11-04 · Transtorakální biopsie ložiska pravého horního laloku pod CT kontrolou – komplikace: malý apikální pneumotorax vpravo, řešen konzervativně
- `[P06-proc03]` 2026-04-20 · Implantace venózního portu (v. subclavia l. dx.)

