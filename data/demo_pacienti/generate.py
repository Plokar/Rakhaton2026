"""
Demo pacienti P13–P32 pro komise v listopadu 2026 (bundle `collection`, `pacienti/Pxx/Pxx_bundle.json`).

Rozšiřuje generátor testovacích pacientů (`data/dataset_test/generate.py`): nominace s poznámkami jako v datasetu
(histologie, předchozí léčba, komorbidity, preference), PROMs pacienta, dosavadní léčba a u některých pacientů
nové výsledky, které přišly až po zařazení (kontrola před zasedáním). Část pacientů má záměrně mezery
(chybí PROMs, preference, geriatrický screening), aby šlo předvést doplnění, přeskočení a úkoly.

`ingest_dataset` je nahraje do IRIS vedle datasetu (env `DEMO_DATASET_DIR`, výchozí tato složka).
Fiktivní data jen pro demo, nikdy pro péči o pacienty. Původní dataset se nemění.

    python data/demo_pacienti/generate.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
# pomocné funkce bundle, ref, text_report z generátoru testovacích pacientů (stejný název souboru → načíst cestou)
_spec = importlib.util.spec_from_file_location("dataset_test_generate", HERE.parent / "dataset_test" / "generate.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

NOMINATED = "2026-10-15T11:00:00+02:00"      # authoredOn nominace v base.bundle; „nové výsledky“ jsou po něm
PROMS_SYSTEM = "https://rakathon.example.org/fhir/CodeSystem/proms-odpovedi"
ECOG_PATIENT = {
    0: "Zvládám všechno jako dřív, bez omezení",
    1: "Těžší fyzickou práci nezvládám, lehčí činnosti a domácnost ano",
    2: "O sebe se postarám, ale práci nezvládnu, přes den odpočívám méně než polovinu dne",
    3: "Většinu dne ležím nebo sedím, s péčí o sebe potřebuji pomoc",
}
PRIORITY = {
    "delka": "Co nejdelší život, i za cenu vedlejších účinků",
    "kvalita": "Kvalita života, i kdyby léčba byla kratší nebo méně účinná",
    "oboji": "Obojí je pro mě stejně důležité",
}

# Komise = text zaměření v ServiceRequest.category (board_title v services/mdt_seed.py) + termín
LUNG, BREAST, GIT = "Hrudní – karcinom plic", "Mamární komise", "GIT – kolorektální karcinom / hepatobiliární"
GYN, URO, HN = "Gynekoonkologická komise", "Uroonkologická komise", "Komise nádorů hlavy a krku"

LAB = {"hb": 132, "neu": 4.1, "plt": 245, "krea": 78, "bili": 11}


def labs(**over) -> dict:
    return {**LAB, **over}


PATIENTS: dict[str, dict] = {
    # ── Hrudní komise ──
    "P13": {
        "gender": "male", "age": 68, "focus": LUNG, "mdt": ("2026-11-03", "14:00"),
        "question": "Lokálně pokročilý NSCLC stadium IIIA (N2): neoadjuvantní chemoimunoterapie a lobektomie, "
                    "nebo definitivní chemoradioterapie s durvalumabem?",
        "dx": [{"code": "C34.1", "display": "Zhoubný novotvar horního laloku, průdušky nebo plíce",
                "morph": ("8140/3", "Adenokarcinom NOS"), "site": "pravý horní plicní lalok", "onset": "2026-09-22",
                "stage": "cT2a cN2 cM0, stadium IIIA (TNM 8. vyd.)"}],
        "comorb": [("I25.1", "Aterosklerotická choroba srdeční", "2019-05"),
                   ("J44.9", "Chronická obstrukční plicní nemoc (GOLD 2)", "2016-11")],
        "meds": [("C10AA05", "atorvastatin", "40 mg p.o. 1× denně"), ("R03AL03", "vilanterol + umeklidinium", "1 inh. denně")],
        "biomarkers": [("EGFR", "bez mutace"), ("ALK", "negativní"), ("ROS1", "negativní"),
                       ("KRAS", "mutace G12C"), ("PD-L1 (TPS)", "60 %")],
        "labs": labs(hb=138, krea=88), "ecog": 1, "weight": 79,
        "histology": "EBUS-TBNA uzliny 4R a biopsie tumoru: adenokarcinom plic, TTF-1 pozitivní. PD-L1 TPS 60 %.",
        "imaging": [("PET/CT – staging", "2026-10-06", "PET/CT: tumor pravého horního laloku 38 mm, metabolicky "
                     "aktivní uzliny 4R a 7, vzdálené metastázy nejsou."),
                    ("MR mozku s kontrastem", "2026-10-07", "MR mozku: bez metastáz, bez patologického sycení.")],
        "lung": {"fev1": "2,1 l (68 % náležité hodnoty)", "dlco": "64 % náležité hodnoty",
                 "ppo_fev1": "cca 55 %", "ppo_dlco": "cca 52 %", "smoking": "bývalý kuřák, 40 balíčkoroků, nekouří od 2024"},
        "consult": "Pacient 68 let, bývalý kuřák (40 balíčkoroků). Kašel 2 měsíce, úbytek 2 kg. ECOG 1. FEV1 68 %.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná, nově diagnostikované onemocnění.",
                  "comorb": "Relevantní komorbidity a současný stav: ICHS (PCI 2019), CHOPN GOLD 2. ECOG 1.",
                  "preference": "Preference a omezení pacienta: Operaci si přeje, pokud bude možná."},
        "proms": {"ecog": 1, "priority": "delka", "allergy": "penicilin – vyrážka"},
    },
    "P14": {
        "gender": "female", "age": 57, "focus": LUNG, "mdt": ("2026-11-03", "14:00"),
        "question": "Periferní adenokarcinom levého dolního laloku 28 mm, EGFR exon 19 delece: lobektomie a "
                    "adjuvantní osimertinib?",
        "dx": [{"code": "C34.3", "display": "Zhoubný novotvar dolního laloku, průdušky nebo plíce",
                "morph": ("8140/3", "Adenokarcinom NOS"), "site": "levý dolní plicní lalok", "onset": "2026-10-01",
                "stage": "cT1c cN0 cM0, stadium IA3 (TNM 8. vyd.)"}],
        "comorb": [("E03.9", "Hypotyreóza", "2014-02")],
        "meds": [("H03AA01", "levothyroxin", "50 µg p.o. 1× denně")],
        "biomarkers": [("EGFR", "delece exonu 19"), ("ALK", "negativní"), ("PD-L1 (TPS)", "5 %")],
        "labs": labs(hb=129, krea=64), "ecog": 0, "weight": 62,
        "histology": "CT navigovaná biopsie: adenokarcinom plic s lepidickou a acinární složkou, TTF-1 pozitivní.",
        "imaging": [("CT hrudníku a břicha s k. l.", "2026-10-02", "CT hrudníku: solidní ložisko levého dolního laloku "
                     "28 mm, mediastinum bez zvětšených uzlin. Břicho bez metastáz."),
                    ("MR mozku s kontrastem", "2026-10-09", "MR mozku: bez metastáz.")],
        "lung": {"fev1": "2,6 l (94 % náležité hodnoty)", "dlco": "88 % náležité hodnoty",
                 "ppo_fev1": "cca 74 %", "ppo_dlco": "cca 70 %", "smoking": "nekuřačka"},
        "consult": "Pacientka 57 let, nekuřačka. Ložisko náhodně při CT pro bolest zad. ECOG 0, plně aktivní.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: substituovaná hypotyreóza. ECOG 0.",
                  "preference": "Preference a omezení pacienta: Chce co nejrychlejší řešení, pracuje jako učitelka."},
        "proms": {"ecog": 0, "priority": "oboji", "allergy": "nevím o žádné"},
        "new": [{"kind": "img", "date": "2026-10-27", "title": "PET/CT – staging",
                 "text": "PET/CT: metabolicky aktivní ložisko levého dolního laloku 29 mm (SUVmax 7,4), mediastinální "
                         "a hilové uzliny bez zvýšené akumulace. Vzdálené metastázy nejsou."}],
    },
    "P15": {
        "gender": "male", "age": 74, "focus": LUNG, "mdt": ("2026-11-03", "14:00"),
        "question": "Spinocelulární karcinom plic stadium IIIA u 74letého pacienta s CHOPN GOLD 3: operabilita, "
                    "nebo definitivní chemoradioterapie?",
        "dx": [{"code": "C34.1", "display": "Zhoubný novotvar horního laloku, průdušky nebo plíce",
                "morph": ("8070/3", "Spinocelulární karcinom NOS"), "site": "levý horní plicní lalok",
                "onset": "2026-09-30", "stage": "cT3 cN1 cM0, stadium IIIA (TNM 8. vyd.)"}],
        "comorb": [("J44.1", "Chronická obstrukční plicní nemoc (GOLD 3) s exacerbacemi", "2012-01"),
                   ("I10", "Esenciální hypertenze", "2008-06"), ("E11.9", "Diabetes mellitus 2. typu", "2015-03")],
        "meds": [("R03AL03", "vilanterol + umeklidinium", "1 inh. denně"), ("A10BA02", "metformin", "850 mg 2× denně")],
        "biomarkers": [("PD-L1 (TPS)", "15 %"), ("p40 (IHC)", "pozitivní")],
        "labs": labs(hb=121, krea=104), "ecog": 1, "weight": 70,
        "histology": "Bronchoskopická biopsie: spinocelulární karcinom plic, p40 pozitivní, TTF-1 negativní.",
        "imaging": [("CT hrudníku a břicha s k. l.", "2026-10-01", "CT hrudníku: tumor levého horního laloku 62 mm "
                     "s kontaktem hrudní stěny, hilová uzlina vlevo 14 mm. Břicho bez metastáz.")],
        "lung": {"fev1": "1,3 l (46 % náležité hodnoty)", "dlco": "44 % náležité hodnoty",
                 "ppo_fev1": "cca 31 %", "ppo_dlco": "cca 30 %", "smoking": "aktivní kuřák, 50 balíčkoroků"},
        "consult": "Pacient 74 let, kuřák. Dušnost při chůzi do schodů. FEV1 46 %, DLCO 44 %. ECOG 1.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: CHOPN GOLD 3, hypertenze, DM 2. typu. ECOG 1."},
        "proms": None,
    },
    "P16": {
        "gender": "female", "age": 63, "focus": LUNG, "mdt": ("2026-11-10", "14:00"),
        "question": "Nově diagnostikovaný ALK pozitivní adenokarcinom plic s mozkovými metastázami: alektinib, nebo "
                    "lorlatinib, a je indikována radioterapie mozku?",
        "dx": [{"code": "C34.1", "display": "Zhoubný novotvar horního laloku, průdušky nebo plíce",
                "morph": ("8140/3", "Adenokarcinom NOS"), "site": "pravý horní plicní lalok", "onset": "2026-10-09",
                "stage": "cT2b cN2 cM1c, stadium IVB (TNM 8. vyd.), metastázy mozku a kostí"},
               {"code": "C79.3", "display": "Sekundární zhoubný novotvar mozku a mozkových plen",
                "site": "3 ložiska supratentoriálně, největší 11 mm", "onset": "2026-10-12"}],
        "comorb": [],
        "meds": [("H02AB02", "dexamethason", "4 mg p.o. 1× denně")],
        "biomarkers": [("ALK", "přestavba prokázána (IHC D5F3 pozitivní)"), ("EGFR", "bez mutace"),
                       ("PD-L1 (TPS)", "10 %")],
        "labs": labs(hb=127), "ecog": 1, "weight": 58,
        "histology": "EBUS-TBNA: adenokarcinom plic, ALK přestavba prokázána imunohistochemicky.",
        "imaging": [("MR mozku s kontrastem", "2026-10-12", "MR mozku: 3 metastázy supratentoriálně, největší 11 mm, "
                     "bez perifokálního edému."),
                    ("PET/CT – staging", "2026-10-13", "PET/CT: tumor pravého horního laloku 42 mm, uzliny 4R a 7, "
                     "kostní metastáza Th10.")],
        "lung": {"fev1": "2,4 l (90 % náležité hodnoty)", "dlco": "82 % náležité hodnoty", "smoking": "nekuřačka"},
        "consult": "Pacientka 63 let, nekuřačka. Bolesti hlavy 3 týdny, neurologicky bez ložiskového nálezu. ECOG 1.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: bez komorbidit. ECOG 1.",
                  "preference": "Preference a omezení pacienta: Přeje si léčbu tabletami, pokud je to možné."},
        "proms": {"ecog": 1, "priority": "delka", "allergy": "nevím o žádné"},
    },
    # ── Mamární komise ──
    "P17": {
        "gender": "female", "age": 45, "focus": BREAST, "mdt": ("2026-11-04", "14:00"),
        "question": "Triple-negativní karcinom prsu cT2 N1: neoadjuvantní chemoimunoterapie s pembrolizumabem a "
                    "výsledek genetického vyšetření BRCA?",
        "dx": [{"code": "C50.4", "display": "Zhoubný novotvar horního zevního kvadrantu prsu",
                "morph": ("8500/3", "Invazivní karcinom NST"), "site": "pravý prs, horní zevní kvadrant",
                "onset": "2026-09-28", "stage": "cT2 cN1 cM0, stadium IIB (TNM 8. vyd.)"}],
        "comorb": [],
        "meds": [],
        "biomarkers": [("ER", "0 %"), ("PR", "0 %"), ("HER2", "IHC 0"), ("Ki-67", "70 %")],
        "labs": labs(hb=134, krea=61), "ecog": 0, "weight": 66,
        "histology": "Core-cut biopsie: invazivní karcinom NST, G3, ER 0 %, PR 0 %, HER2 IHC 0, Ki-67 70 %. "
                     "Core-cut axilární uzliny: metastáza karcinomu.",
        "imaging": "Mamografie a UZ: tumor pravého prsu 34 mm, v axile 2 suspektní uzliny. CT hrudníku a břicha a "
                   "scintigrafie skeletu bez vzdálených metastáz.",
        "consult": "Pacientka 45 let, matka měla karcinom ovaria v 50 letech. Odeslána na genetické vyšetření. ECOG 0.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: bez komorbidit. ECOG 0.",
                  "preference": "Preference a omezení pacienta: Zvažuje oboustrannou mastektomii, pokud bude nosičkou mutace."},
        "proms": {"ecog": 0, "priority": "delka", "allergy": "nevím o žádné"},
        "new": [{"kind": "bm", "date": "2026-10-30", "name": "BRCA1 (zárodečná mutace)",
                 "value": "patogenní varianta c.5266dupC prokázána"}],
    },
    "P18": {
        "gender": "female", "age": 62, "focus": BREAST, "mdt": ("2026-11-04", "14:00"),
        "question": "Po mastektomii pT2 pN1a, luminální karcinom: adjuvantní radioterapie, hormonální léčba a "
                    "přidání abemaciclibu?",
        "dx": [{"code": "C50.1", "display": "Zhoubný novotvar centrální části prsu",
                "morph": ("8520/3", "Lobulární karcinom NOS"), "site": "levý prs, centrální část",
                "onset": "2026-08-25", "stage": "pT2 pN1a (2/14) cM0, stadium IIB (TNM 8. vyd.)"}],
        "comorb": [("M81.0", "Postmenopauzální osteoporóza", "2021-04")],
        "meds": [("M05BA04", "kyselina alendronová", "70 mg p.o. 1× týdně")],
        "biomarkers": [("ER", "95 %"), ("PR", "60 %"), ("HER2", "IHC 1+ (HER2-low)"), ("Ki-67", "22 %")],
        "labs": labs(hb=128), "ecog": 0, "weight": 71,
        "histology": "Mastektomie vlevo a disekce axily: invazivní lobulární karcinom 32 mm, G2, okraje negativní, "
                     "metastázy ve 2 ze 14 uzlin. ER 95 %, PR 60 %, HER2 IHC 1+, Ki-67 22 %.",
        "imaging": "CT hrudníku a břicha po operaci: bez vzdálených metastáz.",
        "consult": "Pacientka 62 let, 4 týdny po mastektomii, hojení bez komplikací. ECOG 0.",
        "notes": {"treatment": "Předchozí onkologická léčba:\n- [Operace] mastektomie vlevo s disekcí axily (2026-09-29)",
                  "comorb": "Relevantní komorbidity a současný stav: osteoporóza na alendronátu. ECOG 0.",
                  "preference": "Preference a omezení pacienta: Obává se únavy z radioterapie, stará se o vnoučata."},
        "proms": {"ecog": 0, "priority": "kvalita", "allergy": "nevím o žádné"},
        "procedures": [("2026-09-29", "chirurgie", "Mastektomie vlevo s disekcí axily")],
    },
    "P19": {
        "gender": "female", "age": 71, "focus": BREAST, "mdt": ("2026-11-04", "14:00"),
        "question": "HER2 pozitivní karcinom prsu cT3 N1 u 71leté pacientky s hraniční LVEF: neoadjuvance s "
                    "trastuzumabem a pertuzumabem?",
        "dx": [{"code": "C50.8", "display": "Zhoubný novotvar prsu přesahující více oblastí",
                "morph": ("8500/3", "Invazivní karcinom NST"), "site": "levý prs, horní kvadranty",
                "onset": "2026-09-15", "stage": "cT3 cN1 cM0, stadium IIIA (TNM 8. vyd.)"}],
        "comorb": [("I42.0", "Dilatační kardiomyopatie", "2020-10"), ("I10", "Esenciální hypertenze", "2010-01")],
        "meds": [("C07AB07", "bisoprolol", "5 mg p.o. 1× denně"), ("C09AA05", "ramipril", "2,5 mg p.o. 1× denně")],
        "biomarkers": [("ER", "10 %"), ("PR", "0 %"), ("HER2", "IHC 3+"), ("Ki-67", "45 %")],
        "labs": labs(hb=122, krea=92), "ecog": 1, "weight": 74,
        "histology": "Core-cut biopsie: invazivní karcinom NST, G3, ER 10 %, PR 0 %, HER2 IHC 3+, Ki-67 45 %.",
        "imaging": "Mamografie a UZ: tumor levého prsu 56 mm, suspektní axilární uzlina 18 mm. CT bez metastáz. "
                   "Echokardiografie 2026-09-20: LVEF 52 %.",
        "consult": "Pacientka 71 let s dilatační kardiomyopatií, kompenzovaná. ECOG 1. Žije sama, soběstačná.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: dilatační kardiomyopatie (LVEF 52 %), hypertenze. "
                            "ECOG 1.",
                  "preference": "Preference a omezení pacienta: Chce se vyhnout dlouhým pobytům v nemocnici."},
        "proms": {"ecog": 1, "priority": "kvalita", "allergy": "jód – kopřivka"},
        "new": [{"kind": "lvef", "date": "2026-10-28", "value": 48}],
    },
    "P20": {
        "gender": "female", "age": 53, "focus": BREAST, "mdt": ("2026-11-18", "14:00"),
        "question": "Progrese jaterních metastáz na letrozolu s palbociklibem, PIK3CA H1047R: fulvestrant s "
                    "alpelisibem, nebo kapivasertib?",
        "dx": [{"code": "C50.4", "display": "Zhoubný novotvar horního zevního kvadrantu prsu",
                "morph": ("8500/3", "Invazivní karcinom NST"), "site": "pravý prs", "onset": "2023-05-10",
                "stage": "pT2 pN0 M1 (játra, od 2025), stadium IV (TNM 8. vyd.)"},
               {"code": "C78.7", "display": "Sekundární zhoubný novotvar jater a intrahepatálních žlučovodů",
                "site": "játra, 4 ložiska", "onset": "2025-03-14"}],
        "comorb": [],
        "meds": [("L02BG03", "letrozol", "2,5 mg p.o. 1× denně"), ("L01EF01", "palbociklib", "125 mg p.o. D1–21")],
        "biomarkers": [("ER", "90 %"), ("PR", "20 %"), ("HER2", "IHC 0"), ("PIK3CA", "mutace H1047R"),
                       ("ESR1", "bez mutace")],
        "labs": labs(hb=118, neu=1.6, bili=19), "ecog": 1, "weight": 64,
        "histology": "Biopsie jaterní metastázy 2025: karcinom prsu, ER 90 %, PR 20 %, HER2 0. NGS: PIK3CA H1047R.",
        "imaging": "CT břicha: progrese jaterních metastáz, největší 41 mm (dříve 26 mm), nové ložisko v S8.",
        "consult": "Pacientka 53 let, metastatické onemocnění od 2025 na letrozolu a palbociklibu 18 měsíců. ECOG 1.",
        "notes": {"treatment": "Předchozí onkologická léčba:\n- [Operace] parciální mastektomie a sentinelová biopsie (2023)\n"
                               "- [Hormonální léčba] letrozol + palbociklib (2025-04 – dosud)",
                  "comorb": "Relevantní komorbidity a současný stav: bez komorbidit. ECOG 1.",
                  "preference": "Preference a omezení pacienta: Chce pokračovat v práci na zkrácený úvazek."},
        "proms": {"ecog": 1, "priority": "oboji", "allergy": "nevím o žádné"},
        "treatment": [("2026-09-01", "palb", "L01EF01", "palbociklib", "hormonální léčba – letrozol + palbociklib"),
                      ("2026-10-01", "palb", "L01EF01", "palbociklib", "hormonální léčba – letrozol + palbociklib")],
    },
    # ── GIT komise ──
    "P21": {
        "gender": "male", "age": 61, "focus": GIT, "mdt": ("2026-11-05", "14:00"),
        "question": "Po pravostranné hemikolektomii pT3 pN2a: adjuvantní CAPOX 3, nebo 6 měsíců?",
        "dx": [{"code": "C18.2", "display": "Zhoubný novotvar vzestupného tračníku",
                "morph": ("8140/3", "Adenokarcinom NOS"), "site": "colon ascendens", "onset": "2026-09-02",
                "stage": "pT3 pN2a (5/22) cM0, stadium IIIB (TNM 8. vyd.)"}],
        "comorb": [("I10", "Esenciální hypertenze", "2017-04")],
        "meds": [("C08CA01", "amlodipin", "5 mg p.o. 1× denně")],
        "biomarkers": [("KRAS", "mutace G12D"), ("BRAF V600E", "neprokázána (wild-type)"),
                       ("MMR (IHC)", "zachovalá exprese (pMMR)")],
        "labs": labs(hb=119), "ecog": 0, "weight": 88,
        "histology": "Pravostranná hemikolektomie: adenokarcinom G2, pT3, metastázy v 5 z 22 uzlin, R0, pMMR.",
        "imaging": "CT hrudníku a břicha před operací: bez vzdálených metastáz.",
        "consult": "Pacient 61 let, 3 týdny po laparoskopické hemikolektomii, zotavený. ECOG 0. CEA po operaci 2,1 µg/l.",
        "notes": {"treatment": "Předchozí onkologická léčba:\n- [Operace] laparoskopická pravostranná hemikolektomie (2026-10-08)",
                  "comorb": "Relevantní komorbidity a současný stav: hypertenze. ECOG 0.",
                  "preference": "Preference a omezení pacienta: Hraje na kytaru, bojí se neuropatie prstů."},
        "proms": {"ecog": 0, "priority": "kvalita", "allergy": "nevím o žádné"},
        "procedures": [("2026-10-08", "chirurgie", "Laparoskopická pravostranná hemikolektomie")],
    },
    "P22": {
        "gender": "female", "age": 49, "focus": GIT, "mdt": ("2026-11-05", "14:00"),
        "question": "dMMR karcinom rekta cT3 N1: imunoterapie dostarlimabem s cílem zachování orgánu, nebo totální "
                    "neoadjuvance?",
        "dx": [{"code": "C20", "display": "Zhoubný novotvar konečníku", "morph": ("8140/3", "Adenokarcinom NOS"),
                "site": "rektum, 6 cm od anu", "onset": "2026-09-24",
                "stage": "cT3 cN1 cM0, stadium IIIB (TNM 8. vyd.)"}],
        "comorb": [],
        "meds": [],
        "biomarkers": [("MMR (IHC)", "ztráta exprese MLH1 a PMS2 (dMMR)"), ("MSI", "MSI-H"),
                       ("KRAS", "bez mutace (wild-type)"), ("BRAF V600E", "neprokázána (wild-type)")],
        "labs": labs(hb=112), "ecog": 0, "weight": 59,
        "histology": "Biopsie rekta: adenokarcinom G2, ztráta exprese MLH1 a PMS2, MSI-H.",
        "imaging": "MR pánve: tumor rekta 6 cm od anu, T3c, 2 mezorektální uzliny, MRF negativní. CT bez metastáz.",
        "consult": "Pacientka 49 let, enteroragie půl roku. Chce zachovat konečník. Genetické vyšetření (Lynch) objednáno.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: bez komorbidit. ECOG 0.",
                  "preference": "Preference a omezení pacienta: Zásadně si nepřeje trvalou stomii."},
        "proms": {"ecog": 0, "priority": "kvalita", "allergy": "nevím o žádné"},
    },
    "P23": {
        "gender": "male", "age": 70, "focus": GIT, "mdt": ("2026-11-05", "14:00"),
        "question": "Levostranný karcinom sigmatu RAS/BRAF wt s neresekabilními jaterními metastázami: FOLFOX s "
                    "panitumumabem a konverzní záměr?",
        "dx": [{"code": "C18.7", "display": "Zhoubný novotvar esovité kličky tlustého střeva (sigmatu)",
                "morph": ("8140/3", "Adenokarcinom NOS"), "site": "colon sigmoideum", "onset": "2026-09-08",
                "stage": "cT3 cN1 cM1a, stadium IVA (TNM 8. vyd.)"},
               {"code": "C78.7", "display": "Sekundární zhoubný novotvar jater a intrahepatálních žlučovodů",
                "site": "játra, 7 ložisek v obou lalocích", "onset": "2026-09-15"}],
        "comorb": [("E11.9", "Diabetes mellitus 2. typu", "2011-08"), ("N18.3", "Chronické onemocnění ledvin, stadium 3", "2022-02")],
        "meds": [("A10BJ06", "semaglutid", "1 mg s.c. 1× týdně")],
        "biomarkers": [("KRAS", "bez mutace (wild-type)"), ("NRAS", "bez mutace (wild-type)"),
                       ("BRAF V600E", "neprokázána (wild-type)"), ("MMR (IHC)", "zachovalá exprese (pMMR)")],
        "labs": labs(hb=115, krea=128), "ecog": 1, "weight": 92,
        "histology": "Biopsie sigmatu: adenokarcinom G2, pMMR, RAS a BRAF bez mutace.",
        "imaging": "CT břicha: 7 jaterních metastáz v obou lalocích, největší 52 mm, odhad FLR nedostatečný. "
                   "Plíce bez ložisek.",
        "consult": "Pacient 70 let, diabetik s CKD 3. ECOG 1. CEA 86 µg/l.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: DM 2. typu, CKD 3 (kreatinin 128 µmol/l). ECOG 1.",
                  "preference": "Preference a omezení pacienta: Přeje si léčbu ambulantně, dojíždí 60 km."},
        "proms": {"ecog": 2, "priority": "oboji", "allergy": "nevím o žádné"},
        "new": [{"kind": "lab", "date": "2026-10-29", "key": "cea", "loinc": "2039-6", "name": "CEA",
                 "unit": "µg/l", "value": 124, "section": "Nádorové markery"}],
    },
    "P24": {
        "gender": "male", "age": 66, "focus": GIT, "mdt": ("2026-11-19", "14:00"),
        "question": "Hraničně resekabilní karcinom hlavy pankreatu: neoadjuvantní mFOLFIRINOX a restaging?",
        "dx": [{"code": "C25.0", "display": "Zhoubný novotvar hlavy pankreatu",
                "morph": ("8500/3", "Duktální adenokarcinom"), "site": "hlava pankreatu", "onset": "2026-10-06",
                "stage": "cT2 cN1 cM0, stadium IIB (TNM 8. vyd.), hraničně resekabilní (kontakt VMS 180°)"}],
        "comorb": [("E11.9", "Diabetes mellitus 2. typu – nově zjištěný", "2026-09")],
        "meds": [("A10AE04", "inzulin glargin", "14 j. s.c. večer"), ("A09AA02", "pankreatin", "25 000 j. k jídlu")],
        "biomarkers": [("CA 19-9", "820 kU/l"), ("BRCA1/2 (zárodečné)", "vyšetření probíhá")],
        "labs": labs(hb=126, bili=38), "ecog": 1, "weight": 69,
        "histology": "EUS-FNB: duktální adenokarcinom pankreatu.",
        "imaging": "CT pankreatický protokol: tumor hlavy pankreatu 31 mm, kontakt s VMS 180°, bez kontaktu s AMS. "
                   "Játra bez metastáz.",
        "consult": "Pacient 66 let, obstrukční ikterus řešen stentem při ERCP. Úbytek 6 kg za 2 měsíce. ECOG 1.",
        "notes": {"treatment": "Předchozí onkologická léčba:\n- [Endoskopie] ERCP se zavedením metalického stentu (2026-10-04)",
                  "comorb": "Relevantní komorbidity a současný stav: nově zjištěný diabetes. ECOG 1.",
                  "preference": "Preference a omezení pacienta: Chce vědět všechny možnosti včetně studií."},
        "proms": {"ecog": 1, "priority": "delka", "allergy": "nevím o žádné"},
        "procedures": [("2026-10-04", "endoskopie", "ERCP se zavedením metalického biliárního stentu")],
    },
    # ── Gynekoonkologická komise ──
    "P25": {
        "gender": "female", "age": 58, "focus": GYN, "mdt": ("2026-11-06", "13:00"),
        "question": "High-grade serózní karcinom ovaria FIGO IIIC po R0 cytoredukci, BRCA2 mutace: adjuvantní "
                    "karboplatina s paklitaxelem a udržovací olaparib?",
        "dx": [{"code": "C56", "display": "Zhoubný novotvar vaječníku",
                "morph": ("8461/3", "Serózní karcinom high-grade"), "site": "oba vaječníky, peritoneum",
                "onset": "2026-09-10", "stage": "pT3c pN1 M0, FIGO IIIC"}],
        "comorb": [],
        "meds": [("B01AB05", "enoxaparin", "40 mg s.c. 1× denně")],
        "biomarkers": [("BRCA2 (zárodečná mutace)", "patogenní varianta prokázána"), ("HRD", "pozitivní"),
                       ("CA-125", "1 240 kU/l před operací")],
        "labs": labs(hb=108), "ecog": 1, "weight": 61,
        "histology": "Cytoredukce: high-grade serózní karcinom obou ovarií, peritoneální implantáty, R0.",
        "imaging": "CT před operací: ascites, peritoneální karcinomatóza, bez metastáz v parenchymu orgánů.",
        "consult": "Pacientka 58 let, 3 týdny po primární cytoredukci, zotavuje se. ECOG 1.",
        "notes": {"treatment": "Předchozí onkologická léčba:\n- [Operace] primární cytoredukce, R0 (2026-10-06)",
                  "comorb": "Relevantní komorbidity a současný stav: bez komorbidit, pooperačně anémie. ECOG 1.",
                  "preference": "Preference a omezení pacienta: Sestra má karcinom prsu, chce genetické poradenství pro dcery."},
        "proms": {"ecog": 1, "priority": "delka", "allergy": "nevím o žádné"},
        "procedures": [("2026-10-06", "chirurgie", "Primární cytoredukce, R0")],
    },
    "P26": {
        "gender": "female", "age": 66, "focus": GYN, "mdt": ("2026-11-06", "13:00"),
        "question": "Endometrioidní karcinom endometria G3 FIGO II, dMMR: adjuvantní brachyterapie, nebo zevní "
                    "radioterapie?",
        "dx": [{"code": "C54.1", "display": "Zhoubný novotvar endometria",
                "morph": ("8380/3", "Endometrioidní adenokarcinom"), "site": "děložní tělo s přechodem na hrdlo",
                "onset": "2026-09-01", "stage": "pT2 pN0 (0/18) M0, FIGO II"}],
        "comorb": [("E66.0", "Obezita (BMI 36)", None), ("I10", "Esenciální hypertenze", "2009-02")],
        "meds": [("C09DA01", "losartan + hydrochlorothiazid", "1 tbl. p.o. denně")],
        "biomarkers": [("MMR (IHC)", "ztráta exprese MLH1 a PMS2 (dMMR)"), ("p53 (IHC)", "wild-type"),
                       ("POLE", "bez mutace")],
        "labs": labs(hb=131), "ecog": 1, "weight": 98,
        "histology": "Hysterektomie s adnexy a lymfadenektomií: endometrioidní karcinom G3, invaze do stromatu hrdla, "
                     "LVSI fokálně, uzliny 0/18, dMMR.",
        "imaging": "MR pánve před operací: tumor endometria s přechodem na hrdlo, bez extrauterinního šíření.",
        "consult": "Pacientka 66 let, obézní hypertonička, 4 týdny po operaci. ECOG 1.",
        "notes": {"treatment": "Předchozí onkologická léčba:\n- [Operace] hysterektomie s adnexy a lymfadenektomií (2026-10-01)",
                  "comorb": "Relevantní komorbidity a současný stav: obezita BMI 36, hypertenze. ECOG 1."},
        "proms": {"ecog": 1, "priority": "kvalita", "allergy": "nevím o žádné"},
        "procedures": [("2026-10-01", "chirurgie", "Hysterektomie s adnexy a pánevní lymfadenektomií")],
    },
    "P27": {
        "gender": "female", "age": 41, "focus": GYN, "mdt": ("2026-11-06", "13:00"),
        "question": "Spinocelulární karcinom děložního hrdla FIGO IIB: konkomitantní chemoradioterapie s cisplatinou, "
                    "brachyterapie a přidání pembrolizumabu?",
        "dx": [{"code": "C53.0", "display": "Zhoubný novotvar endocervixu",
                "morph": ("8070/3", "Spinocelulární karcinom NOS"), "site": "děložní hrdlo, levé parametrium",
                "onset": "2026-10-02", "stage": "cT2b cN0 cM0, FIGO IIB"}],
        "comorb": [],
        "meds": [],
        "biomarkers": [("HPV (PCR)", "HPV 16 pozitivní"), ("PD-L1 (CPS)", "12")],
        "labs": labs(hb=104), "ecog": 0, "weight": 57,
        "histology": "Biopsie čípku: nerohovějící spinocelulární karcinom, HPV 16 pozitivní.",
        "imaging": "CT hrudníku a břicha: bez vzdálených metastáz, uzliny nezvětšené.",
        "consult": "Pacientka 41 let, krvácení po styku. Anemizace Hb 104 g/l. ECOG 0. Matka dvou dětí.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: bez komorbidit, sideropenická anémie. ECOG 0."},
        "proms": None,
        "new": [{"kind": "img", "date": "2026-10-29", "title": "MR pánve – staging",
                 "text": "MR pánve: tumor děložního hrdla 46 mm s infiltrací levého parametria, bez infiltrace stěny "
                         "pánevní a močového měchýře. Pánevní uzliny do 8 mm."}],
    },
    # ── Uroonkologická komise ──
    "P28": {
        "gender": "male", "age": 67, "focus": URO, "mdt": ("2026-11-09", "14:00"),
        "question": "Vysoce rizikový lokalizovaný karcinom prostaty: radikální prostatektomie, nebo radioterapie s "
                    "dlouhodobou ADT?",
        "dx": [{"code": "C61", "display": "Zhoubný novotvar předstojné žlázy (prostaty)",
                "morph": ("8140/3", "Adenokarcinom NOS"), "site": "pravý lalok prostaty", "onset": "2026-09-18",
                "stage": "cT3a cN0 cM0, stadium IIIB (TNM 8. vyd.), Gleason 4+5 = 9 (ISUP 5)"}],
        "comorb": [("I10", "Esenciální hypertenze", "2013-07")],
        "meds": [("C09AA05", "ramipril", "5 mg p.o. 1× denně")],
        "biomarkers": [("PSA", "38 µg/l")],
        "labs": labs(hb=141), "ecog": 0, "weight": 86,
        "histology": "Fúzní biopsie prostaty: acinární adenokarcinom, Gleason 4+5 = 9 (ISUP 5) v 6 z 14 vzorků.",
        "imaging": [("Multiparametrická MR prostaty", "2026-09-08", "MR prostaty: PI-RADS 5 v pravém laloku, "
                     "extrakapsulární šíření vpravo."),
                    ("PSMA PET/CT", "2026-10-06", "PSMA PET/CT: tumor pravého laloku s extrakapsulárním šířením, "
                     "uzliny a skelet bez metastáz.")],
        "consult": "Pacient 67 let, plně aktivní, sexuálně aktivní. IPSS 9. ECOG 0.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: hypertenze. ECOG 0.",
                  "preference": "Preference a omezení pacienta: Rozhoduje se mezi operací a ozářením, chce znát dopad na kontinenci."},
        "proms": {"ecog": 0, "priority": "oboji", "allergy": "nevím o žádné"},
    },
    "P29": {
        "gender": "male", "age": 59, "focus": URO, "mdt": ("2026-11-09", "14:00"),
        "question": "Světlobuněčný karcinom ledviny s plicními metastázami, IMDC intermediární riziko: cytoredukční "
                    "nefrektomie, nebo primárně nivolumab s ipilimumabem?",
        "dx": [{"code": "C64", "display": "Zhoubný novotvar ledviny kromě ledvinné pánvičky",
                "morph": ("8310/3", "Světlobuněčný renální karcinom"), "site": "levá ledvina", "onset": "2026-09-29",
                "stage": "cT3a cN0 cM1 (plíce), stadium IV (TNM 8. vyd.)"},
               {"code": "C78.0", "display": "Sekundární zhoubný novotvar plic", "site": "obě plíce, 6 ložisek do 14 mm",
                "onset": "2026-09-29"}],
        "comorb": [("E78.0", "Hypercholesterolemie", "2018-01")],
        "meds": [("C10AA07", "rosuvastatin", "10 mg p.o. 1× denně")],
        "biomarkers": [("IMDC skóre", "1 (anémie) – intermediární riziko")],
        "labs": labs(hb=118, plt=410), "ecog": 0, "weight": 91,
        "histology": "Biopsie tumoru levé ledviny: světlobuněčný renální karcinom, ISUP grade 3.",
        "imaging": [("CT hrudníku a břicha s k. l.", "2026-10-02", "CT hrudníku a břicha: tumor levé ledviny 84 mm "
                     "s propagací do perirenálního tuku, v plicích 6 metastáz do 14 mm. Uzliny a skelet bez metastáz.")],
        "consult": "Pacient 59 let, hematurie, jinak bez potíží. ECOG 0. Od diagnózy do léčby méně než rok.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: hypercholesterolemie. ECOG 0.",
                  "preference": "Preference a omezení pacienta: Podnikatel, chce co nejméně omezení v práci."},
        "proms": {"ecog": 0, "priority": "delka", "allergy": "nevím o žádné"},
    },
    "P30": {
        "gender": "male", "age": 72, "focus": URO, "mdt": ("2026-11-09", "14:00"),
        "question": "Svalovinu infiltrující uroteliální karcinom močového měchýře cT2 N0: neoadjuvantní chemoterapie "
                    "a radikální cystektomie, nebo trimodální léčba?",
        "dx": [{"code": "C67.2", "display": "Zhoubný novotvar boční stěny močového měchýře",
                "morph": ("8120/3", "Uroteliální karcinom"), "site": "pravá boční stěna močového měchýře",
                "onset": "2026-10-05", "stage": "cT2 cN0 cM0, stadium II (TNM 8. vyd.)"}],
        "comorb": [("I48.0", "Paroxysmální fibrilace síní", "2019-09"), ("H90.3", "Oboustranná nedoslýchavost", None)],
        "meds": [("B01AF02", "apixaban", "5 mg p.o. 2× denně")],
        "biomarkers": [("PD-L1 (CPS)", "8")],
        "labs": labs(hb=127, krea=102), "ecog": 1, "weight": 77,
        "histology": "TURBT: high-grade uroteliální karcinom s invazí do detrusoru, bez karcinomu in situ.",
        "imaging": "CT urografie: ztluštění pravé boční stěny 24 mm, horní cesty močové bez nálezu, uzliny nezvětšené.",
        "consult": "Pacient 72 let, makroskopická hematurie. Nedoslýchavost oboustranně (sluchadla). ECOG 1.",
        "notes": {"treatment": "Předchozí onkologická léčba:\n- [Operace] TURBT (2026-10-05)",
                  "comorb": "Relevantní komorbidity a současný stav: fibrilace síní na apixabanu, nedoslýchavost. ECOG 1.",
                  "preference": "Preference a omezení pacienta: Pokud možno chce zachovat močový měchýř."},
        "proms": {"ecog": 1, "priority": "kvalita", "allergy": "nevím o žádné"},
        "procedures": [("2026-10-05", "urologie", "Transuretrální resekce tumoru močového měchýře (TURBT)")],
        "new": [{"kind": "lab", "date": "2026-10-28", "key": "krea", "loinc": "14682-9", "name": "Kreatinin",
                 "unit": "µmol/l", "value": 138, "section": "Biochemie"}],
    },
    # ── Komise nádorů hlavy a krku ──
    "P31": {
        "gender": "male", "age": 55, "focus": HN, "mdt": ("2026-11-11", "13:30"),
        "question": "HPV pozitivní karcinom orofaryngu cT2 N1: transorální robotická resekce, nebo definitivní "
                    "chemoradioterapie?",
        "dx": [{"code": "C10.9", "display": "Zhoubný novotvar orofaryngu, neurčený",
                "morph": ("8070/3", "Spinocelulární karcinom NOS"), "site": "pravá patrová mandle",
                "onset": "2026-10-07", "stage": "cT2 cN1 cM0, stadium I (TNM 8. vyd., p16 pozitivní)"}],
        "comorb": [],
        "meds": [],
        "biomarkers": [("p16 (IHC)", "pozitivní (HPV asociovaný)"), ("PD-L1 (CPS)", "20")],
        "labs": labs(hb=148), "ecog": 0, "weight": 83,
        "histology": "Biopsie pravé tonzily: nerohovějící spinocelulární karcinom, p16 difuzně pozitivní.",
        "imaging": "MR krku: tumor pravé tonzily 28 mm, ipsilaterální uzlina II 22 mm. PET/CT bez vzdálených metastáz.",
        "consult": "Pacient 55 let, kuřák 10 balíčkoroků (přestal 2015). Bulka na krku 2 měsíce. ECOG 0.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: bez komorbidit. ECOG 0.",
                  "preference": "Preference a omezení pacienta: Učitel zpěvu, zachování hlasu a polykání je pro něj zásadní."},
        "proms": {"ecog": 0, "priority": "kvalita", "allergy": "nevím o žádné"},
    },
    "P32": {
        "gender": "female", "age": 63, "focus": HN, "mdt": ("2026-11-11", "13:30"),
        "question": "Karcinom hlasivek cT3 N0: zachování hrtanu (chemoradioterapie), nebo totální laryngektomie?",
        "dx": [{"code": "C32.0", "display": "Zhoubný novotvar hlasivky (glottis)",
                "morph": ("8070/3", "Spinocelulární karcinom NOS"), "site": "levá hlasivka s fixací",
                "onset": "2026-10-03", "stage": "cT3 cN0 cM0, stadium III (TNM 8. vyd.)"}],
        "comorb": [("J44.9", "Chronická obstrukční plicní nemoc (GOLD 2)", "2018-05"),
                   ("F17.2", "Závislost na tabáku – aktivní kuřačka (35 balíčkoroků)", None)],
        "meds": [("R03BB04", "tiotropium", "18 µg inh. 1× denně")],
        "biomarkers": [("PD-L1 (CPS)", "5")],
        "labs": labs(hb=136), "ecog": 1, "weight": 60,
        "histology": "Mikrolaryngoskopie s biopsií: středně diferencovaný rohovějící spinocelulární karcinom.",
        "imaging": "CT krku: tumor levé hlasivky s fixací, šíření do paraglotického prostoru, bez destrukce chrupavky. "
                   "Uzliny nezvětšené.",
        "consult": "Pacientka 63 let, chrapot 4 měsíce, aktivní kuřačka. ECOG 1.",
        "notes": {"treatment": "Předchozí onkologická léčba: žádná.",
                  "comorb": "Relevantní komorbidity a současný stav: CHOPN GOLD 2, aktivní kuřačka. ECOG 1."},
        "proms": None,
    },
}



# ── Druhá vlna (T-351): 4 nové komise a další termíny do 4. 12. 2026 ───────────────────────────────────────────
NEURO, HEMATO = "Neuroonkologická komise", "Hematoonkologická komise"
MEL, SARC = "Komise pro melanom a kožní nádory", "Komise pro sarkomy a GIST"
BASE_MDT = "2026-11-04"     # data v zadání pacientů jsou psaná k tomuto termínu, `shift` je posune k jeho zasedání


def pt(gender, age, focus, mdt, question, dx, *, histology, imaging, consult, comorb=(), meds=(), bm=(), ecog=1,
       weight=75, labs_over=None, treatment="Předchozí onkologická léčba: žádná.", preference=None,
       proms=(1, "oboji", "nevím o žádné"), procedures=(), therapy=(), new=(), lung=None) -> dict:
    """Pacient druhé vlny v kratším zápisu. `dx` = (MKN-10, název, (ICD-O-3, morfologie) | None, lokalita, vznik,
    stadium | None); `proms` = (ECOG podle pacienta, priorita, alergie) nebo None (dotazník chybí)."""
    comorb_text = ", ".join(c[1] for c in comorb) or "bez komorbidit"
    notes = {"treatment": treatment,
             "comorb": f"Relevantní komorbidity a současný stav: {comorb_text}. ECOG {ecog}."}
    if preference:
        notes["preference"] = f"Preference a omezení pacienta: {preference}"
    out = {
        "gender": gender, "age": age, "focus": focus, "mdt": mdt, "question": question, "shift": True,
        "dx": [{"code": c, "display": d, **({"morph": m} if m else {}), "site": site, "onset": onset,
                **({"stage": st} if st else {})} for c, d, m, site, onset, st in dx],
        "comorb": list(comorb), "meds": list(meds), "biomarkers": list(bm), "labs": labs(**(labs_over or {})),
        "ecog": ecog, "weight": weight, "histology": histology, "imaging": imaging, "consult": consult,
        "notes": notes, "proms": ({"ecog": proms[0], "priority": proms[1], "allergy": proms[2]} if proms else None),
        "procedures": list(procedures), "treatment": list(therapy), "new": list(new),
    }
    if lung:
        out["lung"] = lung
    if not any(d[5] for d in dx):                 # bez stadia (nádory bez TNM) aspoň popis rozsahu
        out["dx"][0]["stage"] = "rozsah viz zobrazení"
    return out


ADENO = ("8140/3", "Adenokarcinom NOS")
SCC = ("8070/3", "Spinocelulární karcinom NOS")
NST = ("8500/3", "Invazivní karcinom NST")

PATIENTS.update({
    # Neuroonkologická komise — čt 12. 11. a čt 26. 11.
    "P33": pt("male", 58, NEURO, ("2026-11-12", "13:00"),
              "Glioblastom IDH-wildtype po subtotální resekci, MGMT metylovaný: radioterapie 60 Gy s temozolomidem "
              "(Stupp), případně s TTFields?",
              [("C71.1", "Zhoubný novotvar čelního laloku", ("9440/3", "Glioblastom NOS"), "pravý frontální lalok",
                "2026-10-01", None)],
              bm=[("IDH1/2", "bez mutace (wild-type)"), ("MGMT promotor", "metylovaný"), ("EGFR amplifikace", "prokázána")],
              histology="Resekce tumoru pravého frontálního laloku: glioblastom, IDH-wildtype, CNS WHO grade 4.",
              imaging="MR mozku pooperačně: reziduum sytící se tkáně 6 mm podél dorzálního okraje resekční dutiny.",
              consult="Pacient 58 let, po subtotální resekci 3 týdny, mírná levostranná hemiparéza v regresi. ECOG 1.",
              treatment="Předchozí onkologická léčba:\n- [Operace] subtotální resekce tumoru (2026-10-08)",
              preference="Chce se vrátit do práce projektanta, řídí auto.",
              procedures=[("2026-10-08", "neurochirurgie", "Subtotální resekce tumoru pravého frontálního laloku")]),
    "P34": pt("female", 44, NEURO, ("2026-11-12", "13:00"),
              "Oligodendrogliom IDH mutovaný s 1p/19q kodelecí, CNS WHO grade 2, s reziduem po resekci: sledování, "
              "nebo radioterapie s PCV?",
              [("C71.0", "Zhoubný novotvar velkého mozku kromě laloků a komor", ("9450/3", "Oligodendrogliom NOS"),
                "levá inzula", "2026-09-20", None)],
              bm=[("IDH1", "mutace R132H"), ("1p/19q", "kodelece prokázána")], ecog=0, weight=64,
              histology="Resekce: oligodendrogliom, IDH-mutovaný a 1p/19q-kodeletovaný, CNS WHO grade 2.",
              imaging="MR mozku: T2/FLAIR reziduum v levé inzule 22 mm, bez sycení.",
              consult="Pacientka 44 let, epileptický záchvat jako první příznak, nyní bez záchvatů na levetiracetamu.",
              meds=[("N03AX14", "levetiracetam", "500 mg p.o. 2× denně")],
              treatment="Předchozí onkologická léčba:\n- [Operace] resekce tumoru levé inzuly (2026-10-02)",
              preference="Obává se kognitivních dopadů radioterapie, pracuje jako účetní.",
              proms=(0, "kvalita", "nevím o žádné"),
              procedures=[("2026-10-02", "neurochirurgie", "Resekce tumoru levé inzuly s neuromonitorací")]),
    "P35": pt("male", 66, NEURO, ("2026-11-12", "13:00"),
              "Solitární metastáza světlobuněčného karcinomu ledviny v mozečku 24 mm: neurochirurgická resekce, nebo "
              "stereotaktická radiochirurgie?",
              [("C79.3", "Sekundární zhoubný novotvar mozku a mozkových plen", None, "levá mozečková hemisféra",
                "2026-10-05", None),
               ("C64", "Zhoubný novotvar ledviny kromě ledvinné pánvičky", ("8310/3", "Světlobuněčný renální karcinom"),
                "pravá ledvina, st. p. nefrektomii 2023", "2023-04-12", "pT2a pN0 M1 (mozek), stadium IV")],
              comorb=[("I10", "Esenciální hypertenze", "2014-02")], meds=[("H02AB02", "dexamethason", "4 mg p.o. denně")],
              histology="Nefrektomie 2023: světlobuněčný renální karcinom ISUP 2.",
              imaging="MR mozku: solitární metastáza v levé mozečkové hemisféře 24 mm s edémem, IV. komora utlačena.",
              consult="Pacient 66 let, závratě a nestabilita chůze 3 týdny. ECOG 1. Jinak bez nádorové aktivity.",
              treatment="Předchozí onkologická léčba:\n- [Operace] nefrektomie vpravo (2023)",
              preference="Chce rychlé řešení, bojí se pádů."),
    "P61": pt("female", 71, NEURO, ("2026-11-26", "13:00"),
              "Glioblastom IDH-wildtype u 71leté pacientky, MGMT nemetylovaný, KPS 70: hypofrakcionovaná radioterapie "
              "40 Gy v 15 frakcích samostatně?",
              [("C71.2", "Zhoubný novotvar spánkového laloku", ("9440/3", "Glioblastom NOS"), "levý temporální lalok",
                "2026-10-06", None)],
              bm=[("IDH1/2", "bez mutace (wild-type)"), ("MGMT promotor", "nemetylovaný")], ecog=2, weight=61,
              comorb=[("E11.9", "Diabetes mellitus 2. typu", "2012-05")],
              histology="Stereotaktická biopsie: glioblastom, IDH-wildtype, CNS WHO grade 4.",
              imaging="MR mozku: sytící se léze levého temporálního laloku 41 mm s nekrózou a edémem.",
              consult="Pacientka 71 let, poruchy řeči a paměti. KPS 70, ECOG 2. Žije s manželem.",
              proms=None),
    "P62": pt("male", 38, NEURO, ("2026-11-26", "13:00"),
              "Astrocytom IDH mutovaný, CNS WHO grade 3, po resekci: radioterapie 59,4 Gy a adjuvantní temozolomid?",
              [("C71.1", "Zhoubný novotvar čelního laloku", ("9401/3", "Astrocytom anaplastický"), "levý frontální lalok",
                "2026-10-10", None)],
              bm=[("IDH1", "mutace R132H"), ("ATRX", "ztráta exprese"), ("1p/19q", "bez kodelece")], ecog=0, weight=82,
              histology="Resekce: astrocytom, IDH-mutovaný, CNS WHO grade 3, Ki-67 12 %.",
              imaging="MR mozku pooperačně: bez sytícího se rezidua, T2/FLAIR změny 15 mm.",
              consult="Pacient 38 let, otec dvou dětí, bolesti hlavy 2 měsíce. ECOG 0.",
              treatment="Předchozí onkologická léčba:\n- [Operace] resekce tumoru (2026-10-10)",
              preference="Plánuje další dítě, chce informace o kryokonzervaci spermatu.", proms=(0, "delka", "nevím o žádné"),
              procedures=[("2026-10-10", "neurochirurgie", "Resekce tumoru levého frontálního laloku")]),
    # Hematoonkologická komise — pá 13. 11. a po 30. 11.
    "P36": pt("male", 62, HEMATO, ("2026-11-13", "13:00"),
              "Difuzní velkobuněčný B-lymfom stadium III, IPI 2: R-CHOP, nebo Pola-R-CHP?",
              [("C83.3", "Difuzní velkobuněčný B-lymfom", ("9680/3", "Difuzní velkobuněčný B-lymfom NOS"),
                "krční, mediastinální a retroperitoneální uzliny", "2026-09-29", "Lugano stadium III, IPI 2")],
              bm=[("CD20 (IHC)", "pozitivní"), ("MYC přestavba (FISH)", "neprokázána"), ("Ki-67", "80 %")],
              labs_over={"hb": 121}, histology="Exstirpace krční uzliny: DLBCL, non-GCB typ, CD20+, Ki-67 80 %.",
              imaging="PET/CT: metabolicky aktivní uzliny krku, mediastina a retroperitonea, slezina bez postižení.",
              consult="Pacient 62 let, noční pocení a úbytek 6 kg. LDH 1,5× norma. ECOG 1.",
              preference="Chce léčbu ambulantně.",
              new=[{"kind": "lab", "date": "2026-10-30", "key": "ldh", "loinc": "14804-9", "name": "LDH",
                    "unit": "µkat/l", "value": 7.9, "section": "Biochemie"}]),
    "P37": pt("female", 27, HEMATO, ("2026-11-13", "13:00"),
              "Klasický Hodgkinův lymfom stadium IIB s velkou mediastinální masou: eskalovaný BEACOPP, nebo ABVD s "
              "PET řízenou léčbou, a zachování plodnosti?",
              [("C81.1", "Hodgkinův lymfom, nodulární skleróza", ("9663/3", "Hodgkinův lymfom, nodulární skleróza"),
                "mediastinum a krk vlevo", "2026-10-02", "Ann Arbor IIB, bulky mediastinum")],
              bm=[("CD30 (IHC)", "pozitivní"), ("CD15 (IHC)", "pozitivní")], ecog=0, weight=58,
              histology="Mediastinoskopická biopsie: klasický Hodgkinův lymfom, nodulární skleróza.",
              imaging="PET/CT: mediastinální masa 11 cm, uzliny krku vlevo, bez postižení pod bránicí.",
              consult="Pacientka 27 let, svědění kůže a teploty. Plánuje rodinu.",
              preference="Zachování plodnosti je pro ni zásadní, zájem o kryokonzervaci oocytů.",
              proms=(0, "delka", "nevím o žádné")),
    "P38": pt("male", 69, HEMATO, ("2026-11-13", "13:00"),
              "Mnohočetný myelom R-ISS II s t(4;14): indukce daratumumab-VRd a autologní transplantace?",
              [("C90.0", "Mnohočetný myelom", ("9732/3", "Mnohočetný myelom"), "kostní dřeň, osteolýzy páteře",
                "2026-09-25", "R-ISS II")],
              bm=[("t(4;14) (FISH)", "prokázána"), ("del(17p)", "neprokázána"), ("M-protein", "IgG kappa 38 g/l")],
              labs_over={"hb": 98, "krea": 140}, comorb=[("N18.3", "Chronické onemocnění ledvin, stadium 3", "2026-09")],
              histology="Trepanobiopsie: 45 % klonálních plazmatických buněk kappa.",
              imaging="Celotělové low-dose CT: osteolýzy Th9, L2 a pánve, bez patologické fraktury.",
              consult="Pacient 69 let, bolesti zad, anémie. ECOG 1, fit pro transplantaci podle hematologa."),
    "P65": pt("female", 74, HEMATO, ("2026-11-30", "13:00"),
              "Folikulární lymfom grade 1–2 stadium IV bez kritérií GELF: sledování, nebo rituximab?",
              [("C82.1", "Folikulární lymfom grade II", ("9691/3", "Folikulární lymfom grade 2"),
                "generalizovaná lymfadenopatie, kostní dřeň", "2026-10-08", "Ann Arbor IV, FLIPI 3")],
              bm=[("BCL2 přestavba", "prokázána")], ecog=0, weight=66,
              histology="Exstirpace tříselné uzliny: folikulární lymfom grade 1–2, CD20+, BCL2+.",
              imaging="PET/CT: uzliny do 4 cm nad i pod bránicí, bez bulky, slezina 12 cm.",
              consult="Pacientka 74 let, bez B-symptomů, náhodný nález. ECOG 0.",
              preference="Pokud léčba není nutná, nechce ji začínat.", proms=(0, "kvalita", "sulfonamidy – vyrážka")),
    "P66": pt("male", 55, HEMATO, ("2026-11-30", "13:00"),
              "Chronická lymfocytární leukémie s del(17p) a symptomatickou anémií: ibrutinib, nebo venetoklax s "
              "obinutuzumabem?",
              [("C91.1", "Chronická lymfocytární leukémie B-buněčného typu", ("9823/3", "CLL/SLL"), "periferní krev, uzliny",
                "2026-08-20", "Rai III, Binet C")],
              bm=[("del(17p) (FISH)", "prokázána"), ("TP53", "mutace"), ("IGHV", "nemutovaný")],
              labs_over={"hb": 94, "plt": 112}, ecog=1, weight=88,
              histology="Imunofenotypizace periferní krve: monoklonální B-lymfocyty CD5+ CD23+, 86 × 10^9/l.",
              imaging="CT: generalizovaná lymfadenopatie do 3 cm, splenomegalie 16 cm.",
              consult="Pacient 55 let, únava a anémie, infekce dýchacích cest 3× za půl roku.",
              comorb=[("I48.0", "Paroxysmální fibrilace síní", "2021-03")],
              meds=[("B01AF02", "apixaban", "5 mg p.o. 2× denně")],
              preference="Dává přednost léčbě s pevně danou délkou."),
    # Komise pro melanom a kožní nádory — po 16. 11. a pá 4. 12.
    "P44": pt("female", 52, MEL, ("2026-11-16", "13:00"),
              "Melanom zad pT3b pN1a (stadium IIIB), BRAF V600E, po excizi a biopsii sentinelové uzliny: adjuvantní "
              "anti-PD-1, nebo dabrafenib s trametinibem?",
              [("C43.5", "Zhoubný melanom trupu", ("8721/3", "Nodulární melanom"), "kůže zad", "2026-09-15",
                "pT3b pN1a cM0, stadium IIIB (AJCC 8)")],
              bm=[("BRAF", "mutace V600E"), ("Breslow", "3,2 mm, ulcerace")], ecog=0, weight=68,
              histology="Reexcize a sentinelová biopsie: nodulární melanom Breslow 3,2 mm s ulcerací, 1 z 2 uzlin "
                        "pozitivní (mikrometastáza 0,8 mm).",
              imaging="PET/CT: bez vzdálených metastáz. MR mozku bez metastáz.",
              consult="Pacientka 52 let, zdravotní sestra. Hojení jizev bez komplikací. ECOG 0.",
              treatment="Předchozí onkologická léčba:\n- [Operace] reexcize a biopsie sentinelové uzliny (2026-10-12)",
              preference="Chce léčbu s co nejméně návštěvami.", proms=(0, "oboji", "nevím o žádné"),
              procedures=[("2026-10-12", "chirurgie", "Reexcize jizvy a biopsie sentinelové uzliny axily")]),
    "P45": pt("male", 67, MEL, ("2026-11-16", "13:00"),
              "Metastatický melanom BRAF wild-type s jaterními a plicními metastázami, LDH 2× norma: ipilimumab s "
              "nivolumabem, nebo nivolumab s relatlimabem?",
              [("C43.7", "Zhoubný melanom dolní končetiny", ("8720/3", "Maligní melanom NOS"), "kůže lýtka vpravo",
                "2024-05-02", "M1c, stadium IV (AJCC 8)"),
               ("C78.7", "Sekundární zhoubný novotvar jater", None, "játra, 5 ložisek", "2026-10-01", None)],
              bm=[("BRAF", "bez mutace (wild-type)"), ("NRAS", "mutace Q61R")], labs_over={"bili": 21},
              comorb=[("I25.1", "Aterosklerotická choroba srdeční", "2018-04")],
              histology="Biopsie jaterního ložiska: metastáza melanomu, BRAF wild-type, NRAS Q61R.",
              imaging="CT: 5 jaterních metastáz do 35 mm, 3 plicní uzly do 12 mm. MR mozku bez metastáz.",
              consult="Pacient 67 let, 2 roky po excizi melanomu lýtka, nyní únava a tlak v pravém podžebří. ECOG 1.",
              treatment="Předchozí onkologická léčba:\n- [Operace] excize melanomu lýtka (2024)",
              new=[{"kind": "lab", "date": "2026-10-29", "key": "ldh", "loinc": "14804-9", "name": "LDH",
                    "unit": "µkat/l", "value": 9.4, "section": "Biochemie"}]),
    "P46": pt("female", 78, MEL, ("2026-11-16", "13:00"),
              "Karcinom z Merkelových buněk tváře 2,1 cm s pozitivní sentinelovou uzlinou: adjuvantní radioterapie "
              "lůžka a uzlin, nebo sledování?",
              [("C44.3", "Zhoubný novotvar kůže jiných a neurčených částí obličeje", ("8247/3", "Karcinom z Merkelových buněk"),
                "levá tvář", "2026-09-25", "pT2 pN1a(sn) M0, stadium IIIA")],
              bm=[("CK20 (IHC)", "pozitivní, perinukleární tečky"), ("MCPyV", "pozitivní")], ecog=1, weight=59,
              comorb=[("I10", "Esenciální hypertenze", "2001-01"), ("M15.0", "Polyartróza", None)],
              histology="Excize: karcinom z Merkelových buněk 21 mm, okraje volné, sentinelová uzlina pozitivní.",
              imaging="PET/CT: bez dalších ložisek.",
              consult="Pacientka 78 let, žije sama, do ambulance ji vozí syn.", proms=None),
    "P71": pt("male", 45, MEL, ("2026-12-04", "13:00"),
              "Melanom předloktí pT4b s klinicky postiženými axilárními uzlinami, BRAF V600K: neoadjuvantní "
              "pembrolizumab před disekcí uzlin?",
              [("C43.6", "Zhoubný melanom horní končetiny", ("8721/3", "Nodulární melanom"), "kůže levého předloktí",
                "2026-10-06", "pT4b cN2b M0, stadium IIIC (AJCC 8)")],
              bm=[("BRAF", "mutace V600K")], ecog=0, weight=86,
              histology="Excize: nodulární melanom Breslow 5,1 mm s ulcerací. FNA axilární uzliny: metastáza melanomu.",
              imaging="PET/CT: 2 metabolicky aktivní uzliny levé axily do 24 mm, bez vzdálených metastáz.",
              consult="Pacient 45 let, stavbyvedoucí, velký pracovní vytížení. ECOG 0.",
              preference="Chce co nejrychleji zpět do práce.", proms=(0, "delka", "nevím o žádné")),
    "P72": pt("female", 60, MEL, ("2026-12-04", "13:00"),
              "Uveální melanom s jaterními metastázami, HLA-A*02:01 pozitivní: tebentafusp, nebo jaterně cílená léčba?",
              [("C69.4", "Zhoubný novotvar řasnatého tělesa", ("8720/3", "Maligní melanom NOS"), "pravé oko",
                "2022-03-10", "M1b (játra)"),
               ("C78.7", "Sekundární zhoubný novotvar jater", None, "játra, 3 ložiska", "2026-10-02", None)],
              bm=[("HLA-A*02:01", "pozitivní"), ("GNAQ", "mutace Q209L")],
              histology="Biopsie jaterní metastázy: metastáza melanomu, GNAQ Q209L.",
              imaging="MR jater: 3 metastázy do 28 mm. CT hrudníku bez metastáz.",
              consult="Pacientka 60 let, 4 roky po brachyterapii uveálního melanomu. ECOG 1.",
              treatment="Předchozí onkologická léčba:\n- [Radioterapie] brachyterapie ruthenium (2022)"),
    # Komise pro sarkomy a GIST — pá 20. 11.
    "P47": pt("male", 49, SARC, ("2026-11-20", "13:00"),
              "Dediferencovaný liposarkom retroperitonea 18 cm: předoperační radioterapie, nebo primárně kompartmentová "
              "resekce?",
              [("C48.0", "Zhoubný novotvar retroperitonea", ("8858/3", "Dediferencovaný liposarkom"),
                "levý retroperitoneální prostor", "2026-09-30", "cT4 N0 M0")],
              bm=[("MDM2 amplifikace (FISH)", "prokázána")], weight=94,
              histology="Core biopsie: dediferencovaný liposarkom, FNCLCC grade 3, MDM2 amplifikace.",
              imaging="CT břicha: tumor 18 × 14 cm odtlačující levou ledvinu a sestupný tračník, bez metastáz.",
              consult="Pacient 49 let, zvětšování obvodu břicha. ECOG 1.",
              preference="Chce zachovat ledvinu, pokud to jde."),
    "P48": pt("female", 61, SARC, ("2026-11-20", "13:00"),
              "GIST žaludku 7 cm po R0 resekci, KIT exon 11, vysoké riziko recidivy: adjuvantní imatinib 3 roky?",
              [("C16.2", "Zhoubný novotvar těla žaludku", ("8936/3", "Gastrointestinální stromální tumor"),
                "tělo žaludku, velká kurvatura", "2026-09-10", "pT3 N0 M0, vysoké riziko (Miettinen)")],
              bm=[("KIT", "delece exonu 11"), ("Mitotický index", "8 / 5 mm²")], ecog=0, weight=70,
              histology="Parciální gastrektomie: GIST 70 mm, vřetenobuněčný, mitózy 8/5 mm², R0, bez ruptury.",
              imaging="CT po operaci: bez rezidua a metastáz.",
              consult="Pacientka 61 let, 4 týdny po operaci, dobře se zotavuje. ECOG 0.",
              treatment="Předchozí onkologická léčba:\n- [Operace] parciální gastrektomie (2026-10-05)",
              preference="Bojí se otoků a únavy z dlouhodobé léčby.", proms=(0, "oboji", "nevím o žádné"),
              procedures=[("2026-10-05", "chirurgie", "Laparoskopická parciální gastrektomie")],
              new=[{"kind": "bm", "date": "2026-10-28", "name": "PDGFRA", "value": "bez mutace"}]),
    "P49": pt("male", 19, SARC, ("2026-11-20", "13:00"),
              "Osteosarkom distálního femuru, high-grade, bez metastáz: neoadjuvantní MAP a záchovná resekce s "
              "endoprotézou?",
              [("C40.2", "Zhoubný novotvar dlouhých kostí dolní končetiny", ("9180/3", "Osteosarkom NOS"),
                "distální femur vpravo", "2026-10-07", "IIB (Enneking), bez metastáz")],
              ecog=1, weight=72, labs_over={"bili": 9},
              histology="Biopsie: konvenční osteoblastický osteosarkom, high-grade.",
              imaging="MR stehna: tumor distální metafýzy 9 cm s měkkotkáňovou složkou, nervově-cévní svazek volný. "
                      "CT plic bez metastáz.",
              consult="Pacient 19 let, student, bolesti kolene 3 měsíce. Hraje fotbal.",
              preference="Chce zachovat končetinu a vrátit se ke sportu.", proms=(1, "delka", "nevím o žádné")),
    # Hrudní komise — út 17. 11. a út 24. 11.
    "P41": pt("male", 71, LUNG, ("2026-11-17", "14:00"),
              "Metastatický adenokarcinom plic PD-L1 80 %, KRAS G12C: pembrolizumab v monoterapii, nebo "
              "chemoimunoterapie?",
              [("C34.1", "Zhoubný novotvar horního laloku, průdušky nebo plíce", ADENO, "pravý horní plicní lalok",
                "2026-10-05", "cT3 cN2 cM1b, stadium IVA (TNM 8. vyd.), metastáza nadledviny")],
              bm=[("EGFR", "bez mutace"), ("ALK", "negativní"), ("KRAS", "mutace G12C"), ("PD-L1 (TPS)", "80 %")],
              comorb=[("J44.9", "Chronická obstrukční plicní nemoc (GOLD 2)", "2015-06")], weight=73,
              histology="EBUS-TBNA: adenokarcinom plic, TTF-1 pozitivní, PD-L1 TPS 80 %.",
              imaging=[("PET/CT – staging", "2026-10-07", "PET/CT: tumor pravého horního laloku 52 mm, uzliny 4R a 7, "
                        "metastáza levé nadledviny 31 mm."),
                       ("MR mozku s kontrastem", "2026-10-09", "MR mozku: bez metastáz.")],
              lung={"fev1": "1,9 l (62 % náležité hodnoty)", "dlco": "58 % náležité hodnoty",
                    "smoking": "bývalý kuřák, 45 balíčkoroků"},
              consult="Pacient 71 let, bývalý kuřák. Kašel, úbytek 4 kg. ECOG 1.", proms=None,
              new=[{"kind": "img", "date": "2026-10-30", "title": "Biopsie nadledviny – výsledek",
                    "text": "CT navigovaná biopsie levé nadledviny: metastáza adenokarcinomu plic."}]),
    "P42": pt("female", 64, LUNG, ("2026-11-17", "14:00"),
              "Neresekabilní spinocelulární karcinom plic stadium IIIB: konkomitantní chemoradioterapie a "
              "konsolidační durvalumab?",
              [("C34.3", "Zhoubný novotvar dolního laloku, průdušky nebo plíce", SCC, "levý dolní plicní lalok",
                "2026-10-03", "cT3 cN3 cM0, stadium IIIB (TNM 8. vyd.)")],
              bm=[("PD-L1 (TPS)", "30 %"), ("EGFR", "bez mutace"), ("ALK", "negativní")], weight=66,
              histology="Bronchoskopická biopsie: spinocelulární karcinom, p40 pozitivní.",
              imaging=[("PET/CT – staging", "2026-10-06", "PET/CT: tumor levého dolního laloku 46 mm, kontralaterální "
                        "mediastinální uzlina 4R, bez vzdálených metastáz."),
                       ("MR mozku s kontrastem", "2026-10-08", "MR mozku: bez metastáz.")],
              lung={"fev1": "1,7 l (71 % náležité hodnoty)", "dlco": "60 % náležité hodnoty",
                    "smoking": "aktivní kuřačka, 30 balíčkoroků"},
              consult="Pacientka 64 let, hemoptýza. ECOG 1.", preference="Chce pokračovat v péči o vnoučata."),
    "P43": pt("male", 59, LUNG, ("2026-11-17", "14:00"),
              "Epitelioidní mezoteliom pleury: nivolumab s ipilimumabem, nebo chemoterapie s cisplatinou a "
              "pemetrexedem?",
              [("C45.0", "Mezoteliom pleury", ("9052/3", "Epitelioidní mezoteliom"), "pravá pleura", "2026-09-28",
                "cT3 N1 M0, stadium IIIA (IASLC)")],
              bm=[("BAP1 (IHC)", "ztráta exprese"), ("PD-L1 (TPS)", "5 %")], weight=80,
              histology="Torakoskopická biopsie pleury: epitelioidní mezoteliom, kalretinin+, WT1+, BAP1 ztráta.",
              imaging="CT hrudníku: difuzní ztluštění pravé pleury do 14 mm, fluidothorax, ipsilaterální hilové uzliny.",
              consult="Pacient 59 let, instalatér, expozice azbestu. Dušnost po evakuaci výpotku zlepšena. ECOG 1.",
              treatment="Předchozí onkologická léčba:\n- [Výkon] torakoskopie s talkáží (2026-09-28)",
              procedures=[("2026-09-28", "hrudní chirurgie", "Videotorakoskopie s biopsií a talkáží")]),
    "P56": pt("female", 69, LUNG, ("2026-11-24", "14:00"),
              "Adenokarcinom plic EGFR L858R s maligním pleurálním výpotkem: osimertinib, nebo osimertinib s "
              "chemoterapií?",
              [("C34.1", "Zhoubný novotvar horního laloku, průdušky nebo plíce", ADENO, "levý horní plicní lalok",
                "2026-10-12", "cT2a cN1 cM1a, stadium IVA (TNM 8. vyd.)")],
              bm=[("EGFR", "mutace L858R"), ("ALK", "negativní"), ("PD-L1 (TPS)", "1 %")], weight=57, ecog=1,
              histology="Cytologie pleurálního výpotku: adenokarcinom plic, EGFR L858R (PCR).",
              imaging=[("CT hrudníku a břicha s k. l.", "2026-10-10", "CT: tumor levého horního laloku 34 mm, "
                        "levostranný fluidothorax, hilová uzlina vlevo. Břicho bez metastáz."),
                       ("MR mozku s kontrastem", "2026-10-14", "MR mozku: bez metastáz.")],
              lung={"fev1": "1,6 l (75 % náležité hodnoty)", "dlco": "68 % náležité hodnoty", "smoking": "nekuřačka"},
              consult="Pacientka 69 let, nekuřačka, dušnost. Po hrudní punkci 1,2 l výpotku úleva.",
              preference="Preferuje léčbu tabletami.", proms=(1, "kvalita", "nevím o žádné")),
    "P57": pt("male", 76, LUNG, ("2026-11-24", "14:00"),
              "Malobuněčný karcinom plic, extenzivní stadium, u 76letého pacienta s ECOG 2: karboplatina s etoposidem "
              "a atezolizumabem?",
              [("C34.1", "Zhoubný novotvar horního laloku, průdušky nebo plíce", ("8041/3", "Malobuněčný karcinom NOS"),
                "pravý horní plicní lalok", "2026-10-09", "cT4 cN3 cM1c, extenzivní stadium")],
              bm=[("TTF-1 (IHC)", "pozitivní"), ("Ki-67", "90 %")], ecog=2, weight=64, labs_over={"hb": 117},
              comorb=[("I50.0", "Městnavé srdeční selhání (NYHA II)", "2020-01"), ("E11.9", "Diabetes mellitus 2. typu", "2010-03")],
              histology="Bronchoskopická biopsie: malobuněčný karcinom plic.",
              imaging=[("PET/CT – staging", "2026-10-12", "PET/CT: tumor pravého horního laloku 61 mm, mediastinální "
                        "uzliny, jaterní a kostní metastázy.")],
              lung={"fev1": "1,4 l (55 % náležité hodnoty)", "dlco": "48 % náležité hodnoty",
                    "smoking": "bývalý kuřák, 60 balíčkoroků"},
              consult="Pacient 76 let, výrazná únava, polovinu dne na lůžku. ECOG 2.", proms=None),
    # Mamární komise — st 18. 11. a st 2. 12.
    "P50": pt("female", 39, BREAST, ("2026-11-18", "14:00"),
              "HER2 pozitivní karcinom prsu cT2 N0 po neoadjuvanci s dosaženou pCR: pokračovat v trastuzumabu a "
              "pertuzumabu do 1 roku?",
              [("C50.4", "Zhoubný novotvar horního zevního kvadrantu prsu", NST, "levý prs", "2026-03-10",
                "ypT0 ypN0 (pCR), původně cT2 cN0")],
              bm=[("ER", "60 %"), ("PR", "20 %"), ("HER2", "IHC 3+"), ("Ki-67", "40 %")], ecog=0, weight=62,
              histology="Parciální mastektomie po neoadjuvanci: bez reziduálního invazivního karcinomu (pCR), sentinel 0/2.",
              imaging="Mamografie a UZ po neoadjuvanci: kompletní regrese tumoru.",
              consult="Pacientka 39 let, po 6 cyklech TCHP a operaci. ECOG 0.",
              treatment="Předchozí onkologická léčba:\n- [Chemoterapie] TCHP 6 cyklů (2026-04 – 2026-07)\n"
                        "- [Operace] parciální mastektomie a sentinelová biopsie (2026-09-01)",
              preference="Chce otěhotnět, ptá se na načasování hormonální léčby.", proms=(0, "oboji", "nevím o žádné"),
              procedures=[("2026-09-01", "chirurgie", "Parciální mastektomie a biopsie sentinelové uzliny")],
              therapy=[("2026-07-15", "tchp", "L01FD01", "trastuzumab", "protinádorová léčba – TCHP")]),
    "P51": pt("female", 58, BREAST, ("2026-11-18", "14:00"),
              "Reziduální nádor po neoadjuvantní chemoterapii u HR+/HER2− karcinomu prsu, zárodečná mutace BRCA2: "
              "adjuvantní olaparib?",
              [("C50.2", "Zhoubný novotvar horního vnitřního kvadrantu prsu", NST, "pravý prs", "2026-02-20",
                "ypT1c ypN1a, původně cT2 cN1")],
              bm=[("ER", "90 %"), ("PR", "50 %"), ("HER2", "IHC 1+"), ("Ki-67", "25 %"),
                  ("gBRCA2", "patogenní varianta prokázána")], weight=74,
              histology="Mastektomie po neoadjuvanci: reziduální karcinom 14 mm, 2 z 12 uzlin pozitivní, CPS+EG 3.",
              imaging="CT hrudníku a břicha: bez vzdálených metastáz.",
              consult="Pacientka 58 let, po neoadjuvanci AC-T a mastektomii. ECOG 1.",
              treatment="Předchozí onkologická léčba:\n- [Chemoterapie] AC-T (2026-03 – 2026-08)\n"
                        "- [Operace] mastektomie s disekcí axily (2026-09-20)",
              procedures=[("2026-09-20", "chirurgie", "Mastektomie vpravo s disekcí axily")]),
    "P67": pt("female", 82, BREAST, ("2026-12-02", "14:00"),
              "ER pozitivní karcinom prsu cT2 N0 u 82leté pacientky: primární endokrinní léčba letrozolem, nebo operace?",
              [("C50.8", "Zhoubný novotvar prsu přesahující více oblastí", NST, "levý prs", "2026-10-15",
                "cT2 cN0 cM0, stadium IIA")],
              bm=[("ER", "100 %"), ("PR", "80 %"), ("HER2", "IHC 0"), ("Ki-67", "8 %")], weight=55,
              comorb=[("I48.2", "Permanentní fibrilace síní", "2016-01"), ("N18.4", "Chronické onemocnění ledvin, stadium 4", "2022-06")],
              meds=[("B01AA03", "warfarin", "dle INR")],
              histology="Core-cut biopsie: invazivní karcinom NST G1, ER 100 %, HER2 0.",
              imaging="Mamografie a UZ: tumor 28 mm, axila bez suspektních uzlin.",
              consult="Pacientka 82 let, žije v domově pro seniory, chodí s holí. ECOG 2.", ecog=2, proms=None),
    "P68": pt("male", 66, BREAST, ("2026-12-02", "14:00"),
              "Karcinom prsu u muže pT1c pN0, ER 100 %: adjuvantní tamoxifen 5 let a genetické vyšetření?",
              [("C50.0", "Zhoubný novotvar bradavky a dvorce", NST, "pravý prs, retroareolárně", "2026-09-29",
                "pT1c pN0 (0/2), stadium IA")],
              bm=[("ER", "100 %"), ("PR", "70 %"), ("HER2", "IHC 1+"), ("Ki-67", "12 %")], ecog=0, weight=90,
              histology="Mastektomie a sentinelová biopsie: invazivní karcinom NST G2, 15 mm, sentinel 0/2.",
              imaging="CT hrudníku a břicha: bez metastáz.",
              consult="Pacient 66 let, hmatná rezistence za bradavkou. Sestra měla karcinom ovaria.",
              treatment="Předchozí onkologická léčba:\n- [Operace] mastektomie vpravo a sentinelová biopsie (2026-10-14)",
              preference="Bojí se vlivu tamoxifenu na sexuální funkce.", proms=(0, "kvalita", "nevím o žádné"),
              procedures=[("2026-10-14", "chirurgie", "Mastektomie vpravo a biopsie sentinelové uzliny")]),
    # GIT komise — čt 12. 11., čt 19. 11. a čt 3. 12.
    "P39": pt("male", 63, GIT, ("2026-11-12", "14:00"),
              "Adenokarcinom gastroezofageální junkce cT3 N1: perioperační FLOT, nebo neoadjuvantní chemoradioterapie?",
              [("C16.0", "Zhoubný novotvar kardie", ADENO, "gastroezofageální junkce, Siewert II", "2026-09-30",
                "cT3 cN1 cM0, stadium III (TNM 8. vyd.)")],
              bm=[("HER2", "IHC 1+ (negativní)"), ("MMR (IHC)", "zachovalá exprese (pMMR)"), ("PD-L1 (CPS)", "5")],
              comorb=[("K21.0", "Gastroezofageální reflux s ezofagitidou", "2010-01")], weight=78,
              histology="Gastroskopická biopsie: adenokarcinom intestinálního typu, G2.",
              imaging="CT a EUS: tumor GEJ 4 cm, T3, 2 periezofageální uzliny. PET/CT bez vzdálených metastáz.",
              consult="Pacient 63 let, dysfagie na tuhou stravu, úbytek 5 kg. ECOG 1.",
              preference="Chce léčbu s nejvyšší šancí na vyléčení."),
    "P40": pt("female", 71, GIT, ("2026-11-12", "14:00"),
              "Hepatocelulární karcinom BCLC B (4 ložiska do 4 cm), Child-Pugh A5: transarteriální chemoembolizace, "
              "nebo systémová léčba?",
              [("C22.0", "Hepatocelulární karcinom", ("8170/3", "Hepatocelulární karcinom NOS"), "pravý jaterní lalok",
                "2026-10-01", "BCLC B, Child-Pugh A5")],
              bm=[("AFP", "340 µg/l")], comorb=[("K74.6", "Jaterní cirhóza (MASH)", "2021-05"),
                                               ("E11.9", "Diabetes mellitus 2. typu", "2009-02")],
              weight=83, labs_over={"plt": 128, "bili": 22},
              histology="Diagnóza podle kritérií LI-RADS 5, biopsie neprovedena.",
              imaging="MR jater: 4 ložiska v pravém laloku 18–39 mm LI-RADS 5, portální žíla průchodná.",
              consult="Pacientka 71 let s cirhózou na podkladě MASH, bez ascitu a encefalopatie. ECOG 1.", proms=None),
    "P52": pt("male", 57, GIT, ("2026-11-19", "14:00"),
              "Karcinom céka s peritoneálními metastázami, BRAF V600E, pMMR: FOLFOXIRI s bevacizumabem, nebo "
              "cytoredukce s HIPEC?",
              [("C18.0", "Zhoubný novotvar céka", ADENO, "cékum", "2026-09-22", "cT4a cN2 cM1c, stadium IVC"),
               ("C78.6", "Sekundární zhoubný novotvar retroperitonea a peritonea", None, "peritoneum, PCI 9", "2026-09-28", None)],
              bm=[("BRAF", "mutace V600E"), ("KRAS", "bez mutace (wild-type)"), ("MMR (IHC)", "zachovalá exprese (pMMR)")],
              weight=71, labs_over={"hb": 108},
              histology="Kolonoskopická biopsie: adenokarcinom G3, BRAF V600E.",
              imaging="CT: tumor céka 6 cm, peritoneální implantáty v pravém hemiabdomenu, PCI 9, játra bez metastáz.",
              consult="Pacient 57 let, anémie a bolesti v pravém podbřišku. ECOG 1."),
    "P69": pt("female", 52, GIT, ("2026-12-03", "14:00"),
              "Neresekabilní intrahepatální cholangiokarcinom s FGFR2 fúzí: gemcitabin s cisplatinou a durvalumabem v "
              "první linii, pemigatinib při progresi?",
              [("C22.1", "Karcinom intrahepatálních žlučovodů", ("8160/3", "Cholangiokarcinom"), "levý jaterní lalok",
                "2026-10-10", "cT2 cN1 cM0, neresekabilní (cévní invaze)")],
              bm=[("FGFR2", "fúze FGFR2–BICC1"), ("IDH1", "bez mutace"), ("CA 19-9", "212 kU/l")], ecog=0, weight=63,
              histology="Biopsie jater: adenokarcinom pankreatobiliárního typu, CK7+, CK20−, odpovídá cholangiokarcinomu.",
              imaging="CT: tumor levého laloku 7 cm s infiltrací levé a střední jaterní žíly, hilové uzliny.",
              consult="Pacientka 52 let, náhodný nález při UZ pro bolest břicha. ECOG 0.",
              preference="Má zájem o klinickou studii.", proms=(0, "delka", "nevím o žádné"),
              new=[{"kind": "bm", "date": "2026-10-28", "name": "NGS panel", "value": "FGFR2 fúze potvrzena, TMB 3 mut/Mb"}]),
    "P70": pt("male", 68, GIT, ("2026-12-03", "14:00"),
              "Spinocelulární karcinom jícnu cT3 N1: neoadjuvantní chemoradioterapie a ezofagektomie, nebo definitivní "
              "chemoradioterapie?",
              [("C15.5", "Zhoubný novotvar dolní třetiny jícnu", SCC, "dolní třetina jícnu, 34 cm od řezáků",
                "2026-10-08", "cT3 cN1 cM0, stadium III")],
              bm=[("PD-L1 (CPS)", "12")], comorb=[("F10.2", "Závislost na alkoholu – abstinuje 2 roky", None)], weight=66,
              histology="Ezofagoskopická biopsie: středně diferencovaný spinocelulární karcinom.",
              imaging="CT a EUS: tumor dolní třetiny jícnu 5 cm, 2 periezofageální uzliny. PET/CT bez metastáz.",
              consult="Pacient 68 let, dysfagie, úbytek 8 kg. Nutriční podpora sondou. ECOG 1.", proms=None),
    # Uroonkologická komise — po 23. 11.
    "P53": pt("male", 31, URO, ("2026-11-23", "14:00"),
              "Neseminomový germinální nádor varlete po orchiektomii, stadium IIB, dobrá prognóza (IGCCCG): 3 cykly BEP?",
              [("C62.1", "Zhoubný novotvar sestouplého varlete", ("9085/3", "Smíšený germinální nádor"), "levé varle",
                "2026-10-01", "pT2 cN2 M0 S1, stadium IIB")],
              bm=[("AFP", "84 µg/l"), ("beta-hCG", "120 IU/l"), ("LDH", "1,2× norma")], ecog=0, weight=79,
              histology="Orchiektomie: smíšený germinální nádor (embryonální karcinom 60 %, teratom 40 %), LVI+.",
              imaging="CT: retroperitoneální paraaortální uzliny vlevo do 3,5 cm, plíce bez metastáz.",
              consult="Pacient 31 let, programátor, nekuřák. Po orchiektomii zotavený.",
              treatment="Předchozí onkologická léčba:\n- [Operace] orchiektomie vlevo (2026-10-03)",
              preference="Před léčbou chce kryokonzervaci spermatu.", proms=(0, "delka", "nevím o žádné"),
              procedures=[("2026-10-03", "urologie", "Inguinální orchiektomie vlevo")]),
    "P54": pt("male", 74, URO, ("2026-11-23", "14:00"),
              "Metastatický kastračně rezistentní karcinom prostaty s BRCA2 mutací, progrese na enzalutamidu: "
              "olaparib, nebo docetaxel?",
              [("C61", "Zhoubný novotvar předstojné žlázy (prostaty)", ADENO, "prostata, kosti", "2023-02-14",
                "cT3b cN1 cM1b, mCRPC, Gleason 4+4 = 8")],
              bm=[("PSA", "64 µg/l"), ("BRCA2 (NGS tkáně)", "patogenní varianta"), ("Testosteron", "0,3 nmol/l (kastrační)")],
              weight=81, ecog=1,
              histology="Biopsie prostaty 2023: acinární adenokarcinom Gleason 4+4 = 8.",
              imaging="PSMA PET/CT: progrese kostních metastáz (nová ložiska v žebrech a pánvi), uzliny stacionární.",
              consult="Pacient 74 let, na ADT a enzalutamidu 2 roky, nyní bolesti kostí. ECOG 1.",
              treatment="Předchozí onkologická léčba:\n- [Hormonální léčba] ADT + enzalutamid (2024 – dosud)",
              new=[{"kind": "lab", "date": "2026-10-29", "key": "psa", "loinc": "2857-1", "name": "PSA",
                    "unit": "µg/l", "value": 81, "section": "Nádorové markery"}]),
    "P55": pt("female", 66, URO, ("2026-11-23", "14:00"),
              "Metastatický uroteliální karcinom močového měchýře: enfortumab vedotin s pembrolizumabem v první linii?",
              [("C67.9", "Zhoubný novotvar močového měchýře, neurčený", ("8120/3", "Uroteliální karcinom"),
                "močový měchýř, uzliny a plíce", "2026-09-26", "cT3 cN2 cM1a, stadium IVA")],
              bm=[("PD-L1 (CPS)", "15"), ("FGFR3", "bez alterace")], labs_over={"krea": 112}, weight=69,
              comorb=[("E11.9", "Diabetes mellitus 2. typu s neuropatií", "2008-07")],
              histology="TURBT: high-grade uroteliální karcinom s invazí do detrusoru.",
              imaging="CT: tumor stěny měchýře, pánevní a paraaortální uzliny, 4 plicní metastázy do 15 mm.",
              consult="Pacientka 66 let, diabetička s periferní neuropatií G1. ECOG 1."),
    # Gynekoonkologická komise — pá 27. 11.
    "P58": pt("female", 62, GYN, ("2026-11-27", "13:00"),
              "Platina-senzitivní relaps high-grade serózního karcinomu ovaria (interval 18 měsíců), BRCA wild-type: "
              "karboplatina s pegylovaným liposomálním doxorubicinem a udržovací niraparib?",
              [("C56", "Zhoubný novotvar vaječníku", ("8461/3", "Serózní karcinom high-grade"), "peritoneum, uzliny",
                "2024-03-05", "relaps po FIGO IIIC")],
              bm=[("BRCA1/2", "bez patogenní varianty"), ("HRD", "negativní"), ("CA-125", "410 kU/l")], weight=64,
              histology="Primární cytoredukce 2024: high-grade serózní karcinom.",
              imaging="CT: peritoneální implantáty do 3 cm a paraaortální uzliny 18 mm.",
              consult="Pacientka 62 let, 18 měsíců po ukončení karboplatiny s paklitaxelem. ECOG 1.",
              treatment="Předchozí onkologická léčba:\n- [Operace] primární cytoredukce (2024)\n"
                        "- [Chemoterapie] karboplatina + paklitaxel 6 cyklů (2024)",
              preference="Chce pokračovat v práci učitelky, obává se ztráty vlasů."),
    "P59": pt("female", 48, GYN, ("2026-11-27", "13:00"),
              "Centrální recidiva karcinomu děložního hrdla v pánvi po chemoradioterapii: pánevní exenterace, nebo "
              "systémová léčba s pembrolizumabem?",
              [("C53.1", "Zhoubný novotvar exocervixu", SCC, "centrální recidiva v pánvi", "2024-01-12",
                "recidiva po FIGO IIIC1")],
              bm=[("PD-L1 (CPS)", "20"), ("HPV (PCR)", "HPV 18 pozitivní")], ecog=0, weight=60,
              histology="Biopsie z pochvy: recidiva spinocelulárního karcinomu.",
              imaging="MR pánve: centrální recidiva 38 mm bez infiltrace pánevní stěny. PET/CT bez vzdálených metastáz.",
              consult="Pacientka 48 let, 22 měsíců po chemoradioterapii. ECOG 0.",
              treatment="Předchozí onkologická léčba:\n- [Radioterapie] chemoradioterapie s cisplatinou a brachyterapií (2024)",
              preference="Je ochotná podstoupit rozsáhlou operaci, pokud dává šanci na vyléčení.", proms=(0, "delka", "jód – kopřivka")),
    "P60": pt("female", 71, GYN, ("2026-11-27", "13:00"),
              "Spinocelulární karcinom vulvy pT2 s pozitivní tříselnou sentinelovou uzlinou: inguinofemorální "
              "lymfadenektomie, nebo adjuvantní chemoradioterapie?",
              [("C51.9", "Zhoubný novotvar vulvy, neurčený", SCC, "levý velký pysk", "2026-09-30",
                "pT2 pN1a(sn), FIGO IIIA")],
              bm=[("p16 (IHC)", "negativní")], weight=78,
              comorb=[("I10", "Esenciální hypertenze", "2005-01"), ("E66.0", "Obezita (BMI 33)", None)],
              histology="Radikální lokální excize: spinocelulární karcinom 32 mm, okraje volné, sentinel 1 ze 3 pozitivní.",
              imaging="CT pánve: bez dalších zvětšených uzlin.",
              consult="Pacientka 71 let, hojení rány po excizi pomalé. ECOG 1.", proms=None),
    # Komise nádorů hlavy a krku — st 25. 11.
    "P63": pt("male", 64, HN, ("2026-11-25", "13:30"),
              "Spinocelulární karcinom okraje jazyka cT2 N1: hemiglosektomie s krční disekcí a rekonstrukcí, nebo "
              "primární chemoradioterapie?",
              [("C02.1", "Zhoubný novotvar okraje jazyka", SCC, "pravý okraj jazyka", "2026-10-06",
                "cT2 cN1 cM0, stadium III (TNM 8. vyd.)")],
              bm=[("p16 (IHC)", "negativní"), ("PD-L1 (CPS)", "25")],
              comorb=[("F17.2", "Závislost na tabáku – kuřák (40 balíčkoroků)", None)], weight=70,
              histology="Biopsie: středně diferencovaný spinocelulární karcinom, hloubka invaze 7 mm.",
              imaging="MR orofaciální oblasti: tumor pravého okraje jazyka 28 mm, uzlina IIA vpravo 18 mm.",
              consult="Pacient 64 let, kuřák, vřed na jazyku 2 měsíce. ECOG 1.",
              new=[{"kind": "img", "date": "2026-11-02", "title": "PET/CT – staging",
                    "text": "PET/CT: aktivita v tumoru jazyka a uzlině IIA vpravo, bez vzdálených metastáz."}]),
    "P64": pt("female", 57, HN, ("2026-11-25", "13:30"),
              "Nazofaryngeální karcinom EBV pozitivní, stadium III: indukční chemoterapie gemcitabin s cisplatinou a "
              "konkomitantní chemoradioterapie?",
              [("C11.9", "Zhoubný novotvar nosohltanu, neurčený", ("8072/3", "Nerohovějící spinocelulární karcinom"),
                "nosohltan, oboustranně", "2026-10-02", "cT2 cN2 cM0, stadium III (TNM 8. vyd.)")],
              bm=[("EBV DNA (plazma)", "4 800 kopií/ml"), ("EBER (ISH)", "pozitivní")], ecog=0, weight=58,
              histology="Biopsie nosohltanu: nerohovějící nediferencovaný karcinom, EBER pozitivní.",
              imaging="MR: tumor nosohltanu s šířením do parafaryngeálního prostoru, oboustranné krční uzliny.",
              consult="Pacientka 57 let, ucpaný nos a bulka na krku. ECOG 0.",
              preference="Obává se suchosti v ústech po ozáření, je zpěvačka ve sboru.", proms=(0, "kvalita", "nevím o žádné")),
})


def proms(pid: str, p: dict) -> dict:
    a = p["proms"]
    item = [
        {"linkId": "bolest", "text": "Bolest za poslední týden (0–10)", "answer": [{"valueInteger": 2}]},
        {"linkId": "unava", "text": "Únava za poslední týden (0–10)", "answer": [{"valueInteger": 3}]},
        {"linkId": "samostatnost", "text": "Jak zvládáte běžný den?",
         "answer": [{"valueCoding": {"system": PROMS_SYSTEM, "code": str(a["ecog"]), "display": ECOG_PATIENT[a["ecog"]]}}]},
        {"linkId": "hmotnost", "text": "Vaše současná hmotnost (kg)", "answer": [{"valueDecimal": p["weight"]}]},
        {"linkId": "alergie", "text": "Alergie nebo nesnášenlivost léků", "answer": [{"valueString": a["allergy"]}]},
        {"linkId": "priorita", "text": "Co je pro vás v léčbě nejdůležitější?",
         "answer": [{"valueCoding": {"system": PROMS_SYSTEM, "code": a["priority"], "display": PRIORITY[a["priority"]]}}]},
    ]
    return {"resourceType": "QuestionnaireResponse", "id": f"{pid}-prom01",
            "questionnaire": "https://rakathon.example.org/fhir/Questionnaire/MDT-PROMS-1", "status": "completed",
            "subject": base.ref("Patient", pid), "authored": "2026-10-13T18:00:00+02:00",
            "source": base.ref("Patient", pid), "item": item}


def new_results(pid: str, p: dict) -> list[dict]:
    """Výsledky, které přišly až po nominaci (kontrola před zasedáním)."""
    out = []
    first = 1 + (1 if isinstance(p["imaging"], str) else len(p["imaging"]))
    for i, n in enumerate(p.get("new", []), first):
        if n["kind"] == "img":
            out.append(base.text_report(pid, f"{pid}-img{i:02d}", "RAD", n["title"], n["date"], n["text"], f"LEK-{pid}-02"))
        elif n["kind"] == "bm":
            out.append({"resourceType": "Observation", "id": f"{pid}-bm{90 + i}", "status": "final",
                        "subject": base.ref("Patient", pid), "effectiveDateTime": n["date"],
                        "category": [{"coding": [{"system": base.OBS_CAT, "code": "laboratory"}]},
                                     {"text": "Biomarker / molekulární patologie"}],
                        "code": {"text": n["name"]}, "valueString": n["value"]})
        elif n["kind"] == "lvef":
            out.append({"resourceType": "Observation", "id": f"{pid}-lvef01", "status": "final",
                        "subject": base.ref("Patient", pid), "effectiveDateTime": n["date"],
                        "category": [{"coding": [{"system": base.OBS_CAT, "code": "exam"}]}, {"text": "Kardiologie"}],
                        "code": {"coding": [{"system": base.LOINC, "code": "10230-1",
                                             "display": "Left ventricular Ejection fraction"}],
                                 "text": "LVEF (echokardiografie)"},
                        "valueQuantity": {"value": n["value"], "unit": "%"}})
        elif n["kind"] == "lab":
            out.append({"resourceType": "Observation", "id": f"{pid}-lab{i:02d}-{n['key']}", "status": "final",
                        "category": [{"coding": [{"system": base.OBS_CAT, "code": "laboratory"}]}, {"text": n["section"]}],
                        "code": {"coding": [{"system": base.LOINC, "code": n["loinc"], "display": n["name"]}],
                                 "text": n["name"]},
                        "subject": base.ref("Patient", pid), "effectiveDateTime": f"{n['date']}T07:30:00+01:00",
                        "valueQuantity": {"value": n["value"], "unit": n["unit"]}})
    return out


def imaging_reports(pid: str, reports: list[tuple[str, str, str]]) -> list[dict]:
    """Zobrazení po jednotlivých zprávách s vlastním názvem (PET/CT, MR mozku…): podle názvu je hledá kontrola úplnosti."""
    return [base.text_report(pid, f"{pid}-img{i:02d}", "RAD", title, date, text, f"LEK-{pid}-02")
            for i, (title, date, text) in enumerate(reports, 1)]


def lung_function(pid: str, lung: dict) -> list[dict]:
    """Spirometrie, kouření a sodík (PLI-3.x) jako v datasetu u P04."""
    out = []
    labels = {"fev1": "FEV1", "dlco": "DLCO", "ppo_fev1": "ppoFEV1 (predikovaná pooperační hodnota po lobektomii)",
              "ppo_dlco": "ppoDLCO (predikovaná pooperační hodnota po lobektomii)"}
    for i, key in enumerate(k for k in labels if k in lung):
        out.append({"resourceType": "Observation", "id": f"{pid}-spiro{i + 1:02d}", "status": "final",
                    "subject": base.ref("Patient", pid), "effectiveDateTime": "2026-10-08",
                    "category": [{"text": "Funkční vyšetření plic"}], "code": {"text": labels[key]},
                    "valueString": lung[key]})
    out.append({"resourceType": "Observation", "id": f"{pid}-kour01", "status": "final",
                "subject": base.ref("Patient", pid), "effectiveDateTime": "2026-10-14",
                "category": [{"text": "Rizikové faktory"}], "code": {"text": "Kouření"}, "valueString": lung["smoking"]})
    out.append({"resourceType": "Observation", "id": f"{pid}-lab01-na", "status": "final",
                "category": [{"coding": [{"system": base.OBS_CAT, "code": "laboratory"}]}, {"text": "Biochemie"}],
                "code": {"coding": [{"system": base.LOINC, "code": "2951-2", "display": "Sodík"}], "text": "Sodík"},
                "subject": base.ref("Patient", pid), "effectiveDateTime": "2026-10-13T07:30:00+02:00",
                "valueQuantity": {"value": 139, "unit": "mmol/l"}})
    return out


def demo_bundle(pid: str, p: dict) -> dict:
    day, time = p["mdt"]
    imaging = p["imaging"]
    bundle = base.bundle(pid, {**p, "imaging": imaging if isinstance(imaging, str) else imaging[0][2]}, mdt=day)
    resources = [e["resource"] for e in bundle["entry"]]
    if not isinstance(imaging, str):
        resources = [r for r in resources if r["id"] != f"{pid}-img01"] + imaging_reports(pid, imaging)
    if p.get("lung"):
        resources += lung_function(pid, p["lung"])
    for r in resources:
        if r["resourceType"] == "Task":            # listopad = zimní čas (+01:00)
            r["restriction"] = {"period": {"start": f"{day}T{time}:00+01:00"}}
        if r["resourceType"] == "ServiceRequest":
            r["note"] = [{"text": f"Histologie a grade: {p['histology'].split(': ', 1)[-1]}"}] + \
                        [{"text": p["notes"][k]} for k in ("treatment", "comorb", "preference") if k in p["notes"]]
            r["reasonReference"] = [base.ref("Condition", f"{pid}-dg{i}") for i in range(1, len(p["dx"]) + 1)]
    if p.get("proms"):
        resources.append(proms(pid, p))
    for i, (when, category, title) in enumerate(p.get("procedures", []), 1):
        resources.append({"resourceType": "Procedure", "id": f"{pid}-proc{i:02d}", "status": "completed",
                          "code": {"text": title}, "subject": base.ref("Patient", pid), "category": {"text": category},
                          "performedDateTime": when})
    for i, (when, key, atc, name, regimen) in enumerate(p.get("treatment", []), 1):
        resources.append({"resourceType": "MedicationAdministration", "id": f"{pid}-tx-{key}-{i:02d}",
                          "status": "completed", "category": {"text": regimen},
                          "medicationCodeableConcept": {"coding": [{"system": "http://www.whocc.no/atc", "code": atc,
                                                                    "display": name}], "text": name},
                          "subject": base.ref("Patient", pid), "effectiveDateTime": when})
    resources += new_results(pid, p)
    if p.get("shift"):                  # druhá vlna: data zadaná k BASE_MDT posunout k termínu zasedání
        days = (date.fromisoformat(day) - date.fromisoformat(BASE_MDT)).days
        resources = [shift_dates(r, days) for r in resources] if days > 0 else resources
        for r in resources:             # termín zasedání posunout nesmí
            if r["resourceType"] == "Task":
                r["restriction"] = {"period": {"start": f"{day}T{time}:00+01:00"}}
    bundle["entry"] = [{"fullUrl": f"urn:uuid:{r['resourceType']}-{r['id']}", "resource": r} for r in resources]
    return bundle


RECENT_DATE = re.compile(r"(?<![\d-])2026-(?:0[89]|1[0-2])-\d{2}(?!\d)")


def shift_dates(node, days: int):
    """Data od srpna 2026 (nominace, vyšetření, laboratoř) o `days` dní později; starší anamnéza zůstává."""
    if isinstance(node, dict):
        return {k: shift_dates(v, days) for k, v in node.items()}
    if isinstance(node, list):
        return [shift_dates(v, days) for v in node]
    if isinstance(node, str):           # i data v textu nominace („resekce (2026-10-08)“); base64 je neobsahuje
        return RECENT_DATE.sub(lambda m: (date.fromisoformat(m[0]) + timedelta(days=days)).isoformat(), node)
    return node


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for pid, p in PATIENTS.items():
        out = HERE / "pacienti" / pid / f"{pid}_bundle.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(demo_bundle(pid, p), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    boards: dict[tuple, list[str]] = {}
    for pid, p in PATIENTS.items():
        boards.setdefault((p["mdt"][0], p["mdt"][1], p["focus"]), []).append(pid)
    for (day, time, focus), pids in sorted(boards.items()):
        print(f"{day} {time}  {focus}: {', '.join(pids)}")
    print(f"Vygenerováno {len(PATIENTS)} pacientů do {HERE / 'pacienti'}")


if __name__ == "__main__":
    main()
