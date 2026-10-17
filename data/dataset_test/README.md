# Testovací pacienti P07–P12

Fiktivní pacienti ve formátu datasetu Asseco (`pacienti/Pxx/Pxx_bundle.json`, bundle `collection`). Testují
výběr guidelines podle MKN-10 (`services/rules/guideline_sets.py`) a navazující semafor na hranách, které
dataset P01–P06 nepokrývá. Jen pro testy, nikdy pro péči o pacienty. Původní dataset se nemění.

```powershell
pip install pydantic PyYAML                     # víc není potřeba (bez Dockeru, IRIS i Gemini)
python data/dataset_test/generate.py            # znovu vygeneruje bundly a expected.json
python data/dataset_test/run_checks.py          # P01–P12 + scénář „IRIS bez guidelines“
python data/dataset_test/run_checks.py P08 P12  # jen vybraní pacienti
```

`run_checks.py` pouští skutečný `services.ai.brief.generate_brief`. Podvržené jsou jen IRIS FHIR (bundly po
sanitizaci ingestem), IRIS SQL `MDT.GuidelineChunk` (pasáže z `guidelines/*.md`) a Gemini (mock, který si
zapíše každý prompt). Kontroluje, které sady se stáhly, co je v promptu pro AI, studie, otázky rolí a semafor.

| Pacient | Diagnóza | Co testuje | Očekávané sady |
|---|---|---|---|
| P07 | C20 rektum + C78.7 | konečník patří do KRC jako C18 a C19 | KRC, OBC |
| P08 | C61 prostata + C79.5 | diagnóza bez sady guidelines, semafor z báze `data/onko` | OBC |
| P09 | C34.3 malobuněčný karcinom | C34 vede na PLI, i když PLI je pro nemalobuněčný karcinom | PLI, OBC |
| P10 | C50.4 prs M1 + C34.1 plíce IA2 | dva primární nádory = dvě sady | PRS, PLI, OBC |
| P11 | C21.1 anus | anus nesmí spadnout do KRC | OBC |
| P12 | C18.7 sigma, kategorie „hlavní diagnóza“ | diagnóza z jiného systému bez kategorie „onkologická diagnóza“ | KRC, OBC |

## Stav

Všechny kontroly projdou od T-320. Před ní selhalo 8 kontrol, každá byla skutečný nález:

- **P12:** výběr sad bral jen diagnózy s kategorií „onkologická diagnóza“, kontext i ostatní. Prompt měl
  nadpis „KRC, OBC“ bez pasáží KRC, hlavička neměla diagnózu a semafor nenabídl nic. Oprava: jedno pravidlo
  `guideline_sets.is_oncologic` (kategorie, nebo kód novotvaru u diagnózy bez kategorie komorbidita / NÚ).
- **P08:** `onko_kb.M1_CONTEXT` nepoznal `mHSPC` a `mCRPC` jako metastatické. U metastatické prostaty vypadly
  hlavní postupy a zůstalo jen Radium-223 (patří ke kastračně rezistentnímu onemocnění). Oprava: obě zkratky
  jsou M1 a postupy HSPC / CRPC se dělí podle zmínky o kastrační rezistenci.
- **P09:** katalog semaforu nabízel malobuněčnému karcinomu neoadjuvantní chemoimunoterapii s lobektomií
  (NSCLC, PLI-2.x). Oprava: postupy PLI mají `requires: nsclc` (`compatibility.is_sclc`).

Zbývající známé mezery (runner je vypíše, nejsou to chyby kontrol):

- **P09:** AI dostane guidelines PLI a studii RKT-04, obojí pro nemalobuněčný karcinom. Výběr guidelines
  podle MKN-10 histologii nevidí.
- **Scénář „IRIS bez guidelines“:** podklad vznikne bez guidelines a v UI to není vidět (změna kontraktu).
