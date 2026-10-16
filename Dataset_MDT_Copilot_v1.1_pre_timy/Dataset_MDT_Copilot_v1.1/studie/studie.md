# Otevřené klinické studie (fiktivní)

> **Fiktivní studie vytvořené pro hackathon Rakathon 2026.** Neexistují – nevyhledávejte je v registrech. Slouží pro předběžný screening v Decision Support Panelu: u každého kritéria vyhodnoťte „splněno / nesplněno / chybí údaj“ s odkazem na zdroj v datech pacienta.

Strojově čitelně: `studie.json`, FHIR: `studie_ResearchStudy_bundle.json` (ResearchStudy + Group s kritérii).

## RKT-01 MERIDIAN-B (fáze II)

**Perorální selektivní degradátor estrogenového receptoru (RKT-SERD) vs. fulvestrant u ESR1-mutovaného HR+/HER2− metastatického karcinomu prsu po progresi na inhibitoru CDK4/6**

- **Diagnóza:** Karcinom prsu, HR+/HER2−, metastatický
- **Ramena:** RKT-SERD 400 mg p. o. denně · fulvestrant 500 mg i.m. (D1, D15, D29, pak á 28 dní)

| Kritérium zařazení | |
|---|---|
| Z1 | Histologicky ověřený karcinom prsu, ER ≥ 10 %, HER2 negativní (IHC 0, 1+ nebo 2+ s negativní ISH) |
| Z2 | Mutace ESR1 prokázaná v cirkulující nádorové DNA (ctDNA) ne starší než 3 měsíce |
| Z3 | Progrese během nebo po 1. linii inhibitor aromatázy + inhibitor CDK4/6 v metastatickém stadiu |
| Z4 | Nejvýše 1 linie chemoterapie v metastatickém stadiu |
| Z5 | ECOG 0–1 |

| Kritérium vyřazení | |
|---|---|
| V1 | Viscerální krize |
| V2 | Neléčené nebo symptomatické mozkové metastázy |
| V3 | Bilirubin > 1,5× horní hranice normy |
| V4 | Předchozí léčba fulvestrantem nebo jiným SERD |

## RKT-02 HELIX-2 (fáze III)

**Nový anti-HER2 protilátkový konjugát (RKT-ADC2) vs. léčba dle výběru lékaře u HER2+ metastatického karcinomu prsu po trastuzumabu a taxanu, včetně pacientek s mozkovými metastázami**

- **Diagnóza:** Karcinom prsu, HER2+, metastatický
- **Ramena:** RKT-ADC2 i.v. á 3 týdny · léčba dle výběru lékaře (trastuzumab deruxtekan nebo tukatinib + trastuzumab + kapecitabin)

| Kritérium zařazení | |
|---|---|
| Z1 | HER2 pozitivní karcinom prsu (IHC 3+ nebo ISH pozitivní) z primárního nádoru nebo metastázy |
| Z2 | Progrese po předchozí léčbě trastuzumabem a taxanem v metastatickém stadiu |
| Z3 | Mozkové metastázy povoleny: léčené a stabilní, nebo neléčené asymptomatické nevyžadující kortikoidy v dávce > 2 mg dexametazonu denně |
| Z4 | ECOG 0–1 |
| Z5 | LVEF ≥ 50 % |

| Kritérium vyřazení | |
|---|---|
| V1 | Intersticiální plicní onemocnění nebo pneumonitida v anamnéze |
| V2 | Předchozí léčba trastuzumab deruxtekanem |
| V3 | Leptomeningeální postižení |

## RKT-03 COLUMBA-LM (fáze III)

**Resekce jater s peroperační ultrazvukovou navigací a ablací drobných ložisek vs. standardní resekce u kolorektálních jaterních metastáz po indukční chemoterapii**

- **Diagnóza:** Kolorektální karcinom s jaterními metastázami
- **Ramena:** resekce + navigace + ablace ložisek ≤ 15 mm · standardní resekce

| Kritérium zařazení | |
|---|---|
| Z1 | Metastázy kolorektálního karcinomu omezené na játra |
| Z2 | Odpověď nebo stabilizace po ≥ 6 cyklech indukční chemoterapie s oxaliplatinou nebo irinotekanem |
| Z3 | ECOG 0–1 |
| Z4 | Resekabilita potvrzená MDT s hepatobiliárním chirurgem |

| Kritérium vyřazení | |
|---|---|
| V1 | Extrahepatální onemocnění |
| V2 | MSI-H / dMMR |
| V3 | Periferní neuropatie ≥ G2 |
| V4 | Předpokládaný budoucí jaterní remnant (FLR) < 30 % |

## RKT-04 PULMO-NEO (fáze III)

**Perioperační chemoimunoterapie s anti-PD-1 protilátkou (RKT-PD1) vs. standardní perioperační léčba u resekabilního NSCLC stadia II–IIIB**

- **Diagnóza:** Nemalobuněčný karcinom plic, stadium II–IIIB, resekabilní
- **Ramena:** 3 cykly chemoterapie + RKT-PD1, operace, adjuvantně RKT-PD1 1 rok · standardní perioperační chemoimunoterapie

| Kritérium zařazení | |
|---|---|
| Z1 | Histologicky ověřený NSCLC stadia II–IIIB (TNM 8), resekabilní dle hrudního chirurga; N2 jedné uzlinové stanice povoleno |
| Z2 | ECOG 0–1 |
| Z3 | ppoFEV1 a ppoDLCO ≥ 40 % náležité hodnoty, nebo vyhovující zátěžový test |
| Z4 | Známý stav EGFR a ALK |

| Kritérium vyřazení | |
|---|---|
| V1 | Mutace EGFR nebo přestavba ALK |
| V2 | Autoimunitní onemocnění vyžadující systémovou léčbu v posledních 2 letech |
| V3 | Vzdálené metastázy (M1) |

## RKT-05 VITALIS (fáze N/A (podpůrná intervence))

**Multimodální nutriční a pohybová intervence u onkologických pacientů s úbytkem hmotnosti během protinádorové léčby**

- **Diagnóza:** Solidní nádory
- **Ramena:** nutriční konzultace + perorální nutriční suplementace + řízený pohybový program 12 týdnů · standardní péče

| Kritérium zařazení | |
|---|---|
| Z1 | Solidní nádor, plánovaná nebo probíhající protinádorová léčba |
| Z2 | Nechtěný úbytek hmotnosti ≥ 5 % za posledních 6 měsíců |
| Z3 | ECOG 0–2 |

| Kritérium vyřazení | |
|---|---|
| V1 | Pouze symptomatická léčba (BSC) |
| V2 | Enterální nebo parenterální výživa |
| V3 | Neschopnost samostatné chůze |

## RKT-06 ORION-HRR (fáze II (basket))

**PARP inhibitor (RKT-PARPi) u pokročilých solidních nádorů s patogenní alterací genů homologní rekombinace (HRR) v nádoru**

- **Diagnóza:** Pokročilé solidní nádory s alterací BRCA1/2 nebo jiného HRR genu
- **Ramena:** RKT-PARPi 300 mg p. o. 2× denně, cyklus 28 dní (jediné rameno)

| Kritérium zařazení | |
|---|---|
| Z1 | Patogenní alterace BRCA1, BRCA2 nebo jiného HRR genu prokázaná NGS v nádoru (somatická nebo zárodečná) |
| Z2 | Alespoň 1 předchozí linie systémové léčby v metastatickém stadiu |
| Z3 | ECOG 0–1 |
| Z4 | Hemoglobin ≥ 90 g/l, neutrofily ≥ 1,5 × 10^9/l, trombocyty ≥ 100 × 10^9/l při zařazení |

| Kritérium vyřazení | |
|---|---|
| V1 | Předchozí léčba PARP inhibitorem |
| V2 | Myelodysplastický syndrom nebo akutní myeloidní leukémie v anamnéze |
| V3 | Neléčené mozkové metastázy |

**Pravidla protokolu:** Úprava dávky podle protokolu: hemoglobin < 80 g/l → přerušit podávání, transfuze dle potřeby, po úpravě na ≥ 90 g/l pokračovat se sníženou dávkou (250 mg 2× denně, další redukce 200 mg 2× denně). Anémie G3 při nejnižší dávce (200 mg 2× denně) → ukončení studijní léčby.

