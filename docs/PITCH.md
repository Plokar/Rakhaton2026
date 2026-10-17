# Pitch MDT Copilot (T-402)

> Pro toho, kdo pitch prezentuje: obsah slidů, co říct a kolik času. Demo samotné je v [DEMO.md](DEMO.md), čísla v [EVAL.md](EVAL.md).
> Pořadí podle zadání: problém → řešení → demo → technologie → InterSystems → dopad a cesta k MVP. Celkem **7 minut** (5 min demo + 2 min slidy), na lokální pitch lze zkrátit slidy 2, 6 a 7.

## Slide 1 · Problém (30 s)

**3–5 minut na pacienta, roky historie ve volném textu.**

- Onkologická komise (MDT) rozhoduje o operaci, ozařování a lécích. Každý obor vidí jen svou část.
- Lékaři dohledávají nálezy ručně, PROMs pacienta komise většinou nevidí.
- Rozpory v podkladech (ECOG lékaře vs. pacienta, zastaralý staging, chybějící biomarker) se najdou pozdě, nebo vůbec.

*Řekni:* „Komise má na pacienta pět minut. Za tu dobu se musí pět specialistů zorientovat v pacientovi, kterého často vidí poprvé.“

## Slide 2 · Řešení (30 s)

**MDT Copilot připraví podklad za pár sekund. Rozhoduje vždy lékař.**

- Celý cyklus komise: zařazení pacienta s kontrolou úplnosti → podklad → jednání → potvrzený zápis do nemocniční FHIR databáze → úkoly a re-MDT.
- Každé tvrzení AI má klikací citaci zdroje. Co v datech není, podklad řekne jako „údaj chybí“.
- Předseda si nastaví sekce, pořadí, přítomné role a podrobnost; každý lékař vidí nahoře to, co ho zajímá.

## Slide 3–4 · Demo (5 min)

Podle [DEMO.md](DEMO.md), pacient **P03** (kolorektum s jaterními metastázami, záloha P05):

1. zařazení s varováními (chybí MMR, rozpor neuropatie, „ECOG 0–1“);
2. podklad podle nastavení předsedy, orientace do 30 s v úzkém pásu (`P03 · muž · 67 let`, ECOG 0 lékař vs. 1 pacient, záměr C);
3. klik na citaci a varovný signál z obou zdrojů (neuropatie G1 vs. „padají mi věci z ruky“);
4. možnosti léčby se **semaforem souladu se stavem pacienta** (počítají pravidla, ne AI) a studie po kritériích;
5. AI zapisovatel → potvrzení předsedou → zápis do IRIS (`Composition`, `CarePlan`, `Provenance`);
6. export PDF a FHIR Bundle s mCODE profily.

*Volitelně (když zbude čas):* nový pacient jen z rodného čísla a vložené zprávy: návrh s citacemi, náhled podkladu a úzkého pásu, potvrzení do IRIS (T-323, API hotové).

## Slide 5 · Spolehlivost AI v číslech (30 s)

Deterministická vrstva bez LLM, 6 pacientů, porovnání s ručně sestavenou dev ground truth ([EVAL.md](EVAL.md)):

| | |
|---|---|
| Klíčové varovné signály | **90 %** (43/48) |
| Klíčová fakta s citací správného zdroje | **100 %** (81/81) |
| Kritéria klinických studií | **93 %** (98/105) |
| Chybějící povinné údaje nahlášené | **86 %** (18/21) |
| Barvy semaforu | **86 %** (43/50) |
| **Neověřená tvrzení** | **0 z 484** |

*Řekni:* „Tohle je spodní hranice bez jazykového modelu: opakovatelná a ověřitelná. Gemini přidává souhrn, pohledy odborníků a rozpory mezi texty, a každé jeho tvrzení prochází stejným validátorem.“
*Poctivě:* ground truth není oficiální (organizátor ji zveřejní po odevzdání); plný běh s Gemini a srovnání dvou modelů brzdí limit free tieru (Q24).

## Slide 6 · Technologie a ochrana dat (30 s)

- **Gemini** (Google AI Studio; pro ostrý provoz placený tier / Vertex AI v EU): souhrn, pohledy rolí, rozpory v textech, přepis diskuse. Model ID jen v konfiguraci.
- **RAG jen nad daty pacienta:** kontext z IRIS FHIR, vyhledávání v IRIS Vector Search vždy s filtrem na pacienta.
- **Grounding validátor:** každé tvrzení musí citovat existující zdroj, čísla a data musí být ve zdroji, u textů vektorová podobnost tvrzení a citovaného odstavce. Neprošlé tvrzení je viditelně „neověřeno“.
- **Ochrana údajů:** hlavička bez jména a RČ, pseudonymizace volného textu před LLM, RČ jen v `Patient.identifier` v IRIS. **Pojistka v kódu:** data skutečného pacienta do LLM ani embeddingů nejdou bez placeného tieru (D-021).
- V produkci vysoce rizikový systém podle AI Act a zdravotnický prostředek podle MDR: proto human-in-the-loop, `Provenance` u každého zápisu a odlišený AI text.

## Slide 7 · InterSystems IRIS for Health (30 s)

IRIS je v aplikaci **nemocniční databáze**, ne doplněk:

- **FHIR R4 server:** 1 091 resources datasetu, aplikace za běhu čte data jen odtud; potvrzený závěr komise se zapisuje zpět **jednou transakcí** ve struktuře předchozích záznamů MDT (+ `Task`, `DetectedIssue`, `Provenance`).
- **Vector Search:** odstavce zpráv, pasáže guidelines a kritéria studií (`VECTOR_COSINE`) pro řazení a ověřování citací.
- **SQL nad FHIR úložištěm:** pohled `MDT.ObservationSeries` (`JSON_TABLE`) pro trendy laboratoře a pravidla.
- **MCP server nad IRIS** (read-only): agent nebo Claude Code se ptá na kontext pacienta, guidelines a kritéria studií.
- **Interoperabilita:** export FHIR document Bundle s mCODE profily, který IRIS přijme zpět; LOINC, MKN-10, ICD-O-3, ATC.

## Slide 8 · Dopad a cesta k MVP (30 s)

- **Dopad:** kratší příprava komise, méně přehlédnutých rozporů a chybějících vyšetření, hlas pacienta (PROMs) u stolu, dohledatelný zápis.
- **Cesta k MVP:**
  1. pilot na jedné komisi nad FHIR rozhraním nemocnice (IRIS for Health / jiný FHIR server), syntetická data → pseudonymizovaná data;
  2. klinická validace pravidel a prahů s onkology (část prahů mimo dodané guidelines je označená „k ověření“);
  3. placený tier / Vertex AI EU, DPIA a cesta k certifikaci zdravotnického prostředku (MDR).
- **Tým:** Seb (infra, API), Maty (data, IRIS), Jarda (AI), Mira (UI, pitch).

## Kontrola před pitchem

- [ ] čísla na slidu 5 = poslední běh v [EVAL.md](EVAL.md)
- [ ] demo projde podle [DEMO.md](DEMO.md) pod 5:00 (T-401, nácvik 3×)
- [ ] záložní video (T-403)
- [ ] slidy vyrobené z tohoto textu (odkaz do Deníku v PROGRESS.md)
