# Šablony lékaře, kategorie údajů a Modrá kniha v semaforu

> Návrh a odůvodnění pro T-338 až T-341 (17. 10. 2026). Vychází z rozhovoru s lékařem (pneumolog, plicní
> onkologie) a z jeho seznamu údajů, které chce při rozhodování o karcinomu plic vidět. Kontrakty jsou
> v ARCHITEKTURA.md §6.3 a §8.6, rozhodnutí D-024 až D-026.

## 1. Co lékař řekl a co z toho plyne

Lékař si v okně pro projektor (T-333) u pacienta s karcinomem plic sám vybral, co chce vidět, a seznam
rozdělil do tří skupin. Zbytek označil jako skrytý:

| Jeho skupina | Údaje |
|---|---|
| 1) Hlavní diagnóza a staging | TNM, histologie |
| 2) Molekulární genetika | EGFR, ALK, PD-L1 |
| 3) Vyšetření a stav | PET/CT, MR mozku, zobrazení ≤ 6 týdnů, EBUS, FEV1, DLCO, hmotnost, G8, kouření, dosavadní léčba, Hb |
| Skryté | všechna upozornění (chybí, doporučeno, mimo normu), Na, CRP, CEA, Leu, Neu, Tr, symptomová zátěž z dotazníku, VO2max, ppoFEV1, ppoDLCO, komorbidity, alergie |

Z rozhovoru a ze seznamu vyplývají čtyři požadavky:

1. **Údaje ve skupinách podle toho, co jsou.** Výsledky vyšetření se nemají plést s výstupy dotazníků.
   Lékař hledá EGFR vždy na stejném místě, ne podle toho, jestli zrovna „svítí“.
2. **Výběr si systém pamatuje u lékaře.** Lékař si šablonu nastaví jednou, a ne u každého pacienta znovu,
   jako dnes v T-333. U konkrétního pacienta ji může upravit.
3. **Šablona vzniká už při zakládání uživatele:** jméno, tituly, profese a hned i předvolený seznam.
4. **Hmotnost ideálně jako BMI.**

Ze stejné schůzky jsou ještě dvě úpravy: **dokončení rozpracovaného zařazení** z agendy a **Modrá kniha
v semaforu** (prahy pravidel opřené o oddíly knihy, kontrola závěru i proti nim).

## 2. Principy, podle kterých jsme rozhodovali

- **P1 Stejný údaj na stejném místě.** Kategorie určuje systém, ne lékař. Na projektoru se dívá celá
  komise a každý potřebuje najít EGFR stejně rychle u pacienta kteréhokoli kolegy.
- **P2 Nic se neztratí (D-019).** Skrytý údaj je sbalený, ne smazaný. V osobním přehledu je pod
  „Skryté podle mé šablony (n)“, na projektoru je vidět počet skrytých. Šablona nikdy nemění podklad, export ani
  kontrolu úplnosti.
- **P3 Závažné se neskrývá.** Údaj se stavem *závažné* (červený) se ukáže, i když ho šablona skrývá, a je
  označený „ukázáno, protože je závažné“. Šablona je pohodlí, ne filtr bezpečnosti.
- **P4 Nastavit jednou, upravit kdykoli.** Šablona lékaře platí pro všechny jeho pacienty dané oblasti.
  Úprava u jednoho pacienta platí jen pro něj a dá se vrátit „podle mé šablony“.
- **P5 Nic se neodhaduje.** BMI jen ze změřené výšky. Odkaz na Modrou knihu jen tam, kde text oddílu
  doslova obsahuje parametr a hodnotu prahu nebo kritérium, s citací, kterou ověřuje test.

## 3. Rozhodnutí

### R1 Pevné kategorie údajů (D-024)

Osm kategorií v pořadí, v jakém se o pacientovi rozhoduje: *co to je → co to řídí → jak je to rozsáhlé
→ zvládne pacient léčbu → co už měl → laboratoř → co říká pacient → co chybí*.

| # | Kategorie | Co do ní patří (ID polí `IntakeField`, laboratoř `lab:<LOINC>`) |
|---|---|---|
| 1 | **Diagnóza a staging** | `dx.histology`, `dx.isup`, `dx.renal_histology`, `staging.tnm` |
| 2 | **Molekulární genetika a biomarkery** | `bm.*` (EGFR, ALK, PD-L1, RAS, BRAF, MMR, ER, PR, HER2, Ki-67, ESR1, PIK3CA, gBRCA, HRR) |
| 3 | **Zobrazení a invazivní vyšetření** | `staging.imaging`, `staging.pet`, `staging.brain_mr`, `staging.ebus`, `staging.chest_ct`, `staging.liver_mr`, `staging.prostate_mr`, `staging.renal_ct`, `liver.flr` |
| 4 | **Funkční stav a výkonnost** | `spiro.*` (FEV1, DLCO, ppoFEV1, ppoDLCO, VO2max), `lvef`, `weight` (s BMI), `geri.g8` |
| 5 | **Anamnéza a dosavadní léčba** | `smoking`, `comorbidities`, `treatment.*`, `tox.*`, `allergies` |
| 6 | **Laboratoř** | všechny laboratorní řady `lab:<LOINC>` a pole `lab.*` (Na, eGFR, PSA, testosteron) |
| 7 | **Pacient: dotazníky a preference** | `preferences` a varování odvozená z PROMs (`RF-PROMS`, `RF-NEWSYMPTOM`, `RF-MED`, `RF-PALIATIVE`) |
| 8 | **Upozornění a chybějící údaje** | varování pravidel, která nepatří k žádnému řádku (`CHYBI:`, `DOP:`, `RF-…`, `ai_uncertain`) |

ECOG a otázka pro MDT zůstávají v hlavičce a v dolním pásu (D-018), mezi údaji nejsou.

**Proč pevné kategorie, a ne skupiny podle lékaře:** Kdyby si každý lékař pojmenoval vlastní skupiny,
komise by na projektoru viděla u každého zadávajícího jinou strukturu a sloučení „Vyšetření a stav“ by
dál míchalo funkční vyšetření, laboratoř a anamnézu. Lékařovy tři skupiny se do kategorií promítnou beze
ztráty: 1 → *Diagnóza a staging*, 2 → *Molekulární genetika*, 3 se rozpadne na *Zobrazení*, *Funkční
stav*, *Anamnéza* a *Laboratoř* (Hb). Pořadí i viditelnost si lékař určuje sám.

**Proč přiřazuje backend:** Kategorie je vlastnost údaje (`IntakeField.category`), ne obrazovky. Jedno
místo (`services/rules/fact_categories.py`) zajistí, že se nové pole nikde neobjeví bez kategorie. Neznámé
pole spadne podle prefixu (`bm.` → molekulární, `spiro.` → funkční…) a jinak do Anamnézy.

**Pořadí uvnitř kategorie:** Bez šablony platí dosavadní priorita stavu (závažné, mimo normu, chybí,
zaznamenáno, v normě), takže to, co vyžaduje pozornost, je v kategorii nahoře. Se šablonou platí pořadí
lékaře. Stav je vidět vždy z ikony a barvy.

**Co to mění na projektoru:** Skupiny podle stavu z T-330 („Pozornost / Chybí / Zaznamenáno / V normě“)
nahrazují kategorie. Pozornost na projektoru nezmizí: počet varování je v hlavičce, závažný údaj je
podbarvený přes celý řádek a v kategorii je první. Lékař tím dostává stabilní místa, o která výslovně žádal.

### R2 Šablona lékaře (D-025)

- **Obsah:** pořadí a viditelnost kategorií a pořadí a viditelnost údajů. Ne hodnoty. Tvar je stejný
  jako u rozložení okna projektoru (T-333), rozšířený o `categories`:
  `{categories?: {order, hidden}, facts?: {order, hidden}, blocks?: {order, hidden}}`.
- **Klíče údajů jsou stabilní napříč pacienty:** ID pole (`bm.egfr`), laboratoř `lab:718-7`,
  upozornění `alert:<pravidlo>` (`alert:RF-LAB`, `alert:DOP:obc.hbv`, `alert:CHYBI:pli.siadh`). Proto
  šablona z jednoho pacienta platí u dalšího.
- **Oblasti:** šablona se ukládá zvlášť pro *Plíce* (C34), *Prs* (C50), *Kolorektum* (C18–C20) a
  *Ostatní*. Plicař potřebuje u plic jiné údaje než u prsu a jedna společná šablona by byla špatně pro
  lékaře, který pokrývá víc oblastí. Šablona podle jednotlivých kódů MKN-10 by byla zbytečně jemná.
  Oblast se určuje stejným pravidlem jako sada guidelines (`guideline_sets_for`). Když lékař pro oblast
  šablonu nemá, platí jeho šablona *Ostatní* a jinak výchozí pořadí.
- **Nové údaje, které lékař ještě neviděl,** jsou viditelné na konci své kategorie. Šablona nesmí potichu
  skrýt údaj, o kterém lékař nerozhodl.
- **Ukládá se na serveru** (`FactTemplate`: uživatel, oblast, rozložení), ne v prohlížeči. Lékař ji má na
  každém počítači a předseda ji vidí u případů svých kolegů.

### R3 Kde která šablona platí

| Obrazovka | Rozložení | Proč |
|---|---|---|
| Okno pro projektor | úprava u případu, jinak šablona **zadávajícího lékaře**, jinak výchozí | komise vidí, co připravil ten, kdo pacienta přinesl (T-333) |
| Jednání komise (široký přehled) | stejné jako projektor | předseda vidí totéž co komise |
| Detail pacienta, rychlý přehled v kalendáři, úzké okno vedle PACS | šablona **přihlášeného lékaře** | příprava, každý po svém |

Šablona zadávajícího se čte živě, ne jako kopie při zařazení. Když ji lékař vylepší, platí to i u jeho už
zařazených pacientů. Výjimkou jsou případy, které ručně upravil.

### R4 Výchozí šablona pneumologa = seznam lékaře

Preset *Plicní onkologie (výběr pneumologa)* je přesně jeho seznam: kategorie v pořadí Diagnóza →
Molekulární genetika → Zobrazení → Funkční stav → Anamnéza → Laboratoř → Pacient → Upozornění. Skryté jsou
VO2max, ppoFEV1, ppoDLCO, komorbidity, alergie, Na, CRP, CEA, Leu, Neu, Tr a celé kategorie *Pacient* a
*Upozornění*. Ostatní odbornosti začínají výchozím pořadím, kde je vše viditelné. Presety jsou data
(`services/rules/data/template_presets.yaml`), další odbornost se přidá bez kódu.

### R5 Zakládání uživatele: profil a šablona

Při registraci i když předseda zakládá kolegu v Týmu jsou dva kroky:

1. **Profil:** jméno, příjmení, **tituly před a za jménem** (MUDr., Ph.D.), **profese** (odbornost),
   u předsedy navíc role v komisi. Tituly se ukazují všude, kde je jméno lékaře (přítomní, úkoly, chat).
2. **Šablona:** podle profese se předvyplní preset a lékař ho hned upraví. Oči a šipky jsou stejné jako
   v editoru okna projektoru. Krok jde přeskočit, pak platí výchozí pořadí.

Šablonu lze později změnit v *Nastavení → Moje šablona údajů*, nebo z editoru okna projektoru
u pacienta volbou „uložit také jako moji šablonu“.

### R6 BMI místo holé hmotnosti

Řádek *Hmotnost* ukazuje `71 kg · BMI 24,6`, když je ve FHIR změřená výška (LOINC 8302-2) nebo přímo BMI
(39156-5). Bez výšky ukazuje `71 kg · BMI: chybí výška` a BMI neodhaduje (P5). Pod hranicí z Modré
knihy (GLIM, oddíl 31.3: BMI < 20 do 70 let, < 22 od 70 let) je hodnota *mimo normu* s citací
`EXT-MK-31.3-2`. Dataset hackathonu výšku nemá, u nových pacientů ji lze dodat ve FHIR JSON.

### R7 Modrá kniha v semaforu a v kontrole závěru (D-026)

- **Kurátorské mapování pravidel na oddíly knihy** (`data/onko/modra_kniha/pravidla.tsv`). Každé pravidlo
  semaforu má jeden ze tří stavů:
  - **práh:** oddíl doslova uvádí parametr a hodnotu nebo kritérium, například cisplatina „kreatininová
    clearance <60 ml/min“ (`EXT-MK-8.1.4.2-10`), durvalumab „PD-L1 ≥1 %“ (`EXT-MK-8.1.3.2-2`);
  - **téma:** oddíl pojednává o stejné věci bez čísla, například kouření, CYP3A;
  - **neuvádí:** v knize práh není a pravidlo stojí na guidelines datasetu nebo na `EXT-…`.
- **Proč ručně, ne vyhledáváním:** Automatické hledání podle slov vedlo u ECOG na kapitolu o sarkomech.
  Pro práh rozhodující o léčbě potřebujeme jistotu. U každého odkazu je doslovná citace a test ověří, že
  v textu oddílu opravdu je. „Neuvádí“ je také informace: lékař vidí, které prahy nemají oporu
  v národních doporučeních.
- **V semaforu:** u pravidla v „Proč“ je „Modrá kniha: práh / téma / neuvádí“ s citací, která otevře oddíl.
- **V kontrole závěru:** u zvolené možnosti se ukážou oddíly Modré knihy jejích pravidel a oddíly vybrané
  k pacientovi (T-337). Citace se uloží do „Soulad s doporučenými postupy“, takže jsou v záznamu MDT,
  v PDF i ve FHIR (`Composition`). Odchylka dál nic neblokuje, jen chce zdůvodnění (zadání B2).

### R8 Dokončit rozpracované zařazení

Případ, který vznikl potvrzením nového pacienta nebo nominací a nemá dokončené zařazení (ECOG, C/P, vše
vyřešené), je v agendě a v kalendáři označený **„Nedokončené zařazení“** s tlačítkem **Dokončit**.
Tlačítko otevře rovnou formulář zařazení s kontrolou úplnosti. Ve výběru pacienta je takový pacient dál
nabízený („dokončit zařazení“), dřív byl zašedlý jako „už je na tomto zasedání“.

## 4. Co se nemění

- **Podklad a export.** Šablona neovlivňuje obsah podkladu, PDF, FHIR export ani kontrolu úplnosti.
  Skrývá jen zobrazení.
- **Šablony podle diagnózy (T-317, `sablony.tsv`).** Dál určují, co musí být k diagnóze v podkladech.
  Šablona lékaře určuje, co chce lékař vidět a v jakém pořadí.
- **Úprava u případu (T-333).** Zůstává, jen má výchozí hodnotu ze šablony zadávajícího lékaře.

## 5. Rizika a další kroky

- **Lékař skryje údaj, který je u jiného pacienta důležitý.** Zmírňuje to P3 (závažné se ukáže) a P2
  (skryté je o klik dál, na projektoru je vidět počet).
- **Kategorie nesedí na nové pole.** Neznámé pole jde podle prefixu nebo do Anamnézy a test hlídá, že
  každé pole z `intake.py` má kategorii.
- **Mapování na Modrou knihu stárne s novým vydáním.** Test ověřuje citace proti `pasaze.jsonl`. Po novém
  vydání neplatné citace selžou a mapování se zkontroluje znovu.
- **Další kroky:** sdílení šablony mezi kolegy („převzít šablonu kolegy“), šablona podle typu komise,
  výška jako povinný údaj při zařazení u systémové léčby (dávkování podle povrchu těla).
