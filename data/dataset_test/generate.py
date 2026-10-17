"""
Testovací pacienti P07–P12 ve formátu datasetu Asseco (bundle `collection`, `pacienti/Pxx/Pxx_bundle.json`).

Každý pacient míří na jednu hranu výběru guidelines podle MKN-10 (`services/rules/guideline_sets.py`):
konečník C20, prostata C61 (bez sady), malobuněčný karcinom plic, dva primární nádory, anus C21 a nádor
bez kategorie „onkologická diagnóza“. Očekávání jsou v `expected.json` (generuje se odsud).

Fiktivní data jen pro testy, nikdy pro péči o pacienty. Původní dataset se nemění.

    python data/dataset_test/generate.py
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
TAG = {"system": "https://rakathon.example.org/fhir/tag", "code": "fiktivni-data",
       "display": "Fiktivní data – Rakathon 2026"}
ICD10 = "http://hl7.org/fhir/sid/icd-10"
ICDO3 = "http://terminology.hl7.org/CodeSystem/icd-o-3"
LOINC = "http://loinc.org"
SD = "https://rakathon.example.org/fhir/StructureDefinition"
CS = "https://rakathon.example.org/fhir/CodeSystem"
OBS_CAT = "http://terminology.hl7.org/CodeSystem/observation-category"

LABS = [  # (klíč, LOINC, název, jednotka, sekce)
    ("hb", "718-7", "Hemoglobin", "g/l", "Hematologie"),
    ("neu", "751-8", "Neutrofily absolutně", "10^9/l", "Hematologie"),
    ("plt", "777-3", "Trombocyty", "10^9/l", "Hematologie"),
    ("krea", "14682-9", "Kreatinin", "µmol/l", "Biochemie"),
    ("bili", "14631-6", "Bilirubin celkový", "µmol/l", "Biochemie"),
]

PATIENTS: dict[str, dict] = {
    "P07": {
        "gender": "female", "age": 59, "focus": "GIT – kolorektum",
        "question": "Karcinom rekta se synchronními jaterními metastázami (RAS/BRAF wt, pMMR): pořadí léčby – "
                    "systémová léčba, radioterapie rekta a resekce jater?",
        "dx": [
            {"code": "C20", "display": "Zhoubný novotvar konečníku", "morph": ("8140/3", "Adenokarcinom NOS"),
             "site": "rektum, 8 cm od anu", "onset": "2026-08-20",
             "stage": "cT3 cN1 cM1a, stadium IVA (TNM 8. vyd.)"},
            {"code": "C78.7", "display": "Sekundární zhoubný novotvar jater a intrahepatálních žlučovodů",
             "site": "jaterní segmenty S6 a S7", "onset": "2026-09-02"},
        ],
        "comorb": [("E11.9", "Diabetes mellitus 2. typu bez komplikací", "2018-03")],
        "meds": [("A10BA02", "metformin", "1000 mg p.o. 2× denně")],
        "biomarkers": [("KRAS", "bez mutace (wild-type)"), ("NRAS", "bez mutace (wild-type)"),
                       ("BRAF V600E", "neprokázána (wild-type)"),
                       ("MMR (IHC)", "zachovalá exprese MLH1, PMS2, MSH2, MSH6 (pMMR)")],
        "labs": {"hb": 124, "neu": 4.2, "plt": 268, "krea": 71, "bili": 14},
        "ecog": 1, "weight": 71,
        "histology": "Biopsie z rekta: středně diferencovaný adenokarcinom (G2). Imunohistochemicky zachovalá "
                     "exprese MMR proteinů. Molekulárně KRAS, NRAS a BRAF bez mutace.",
        "imaging": "CT hrudníku, břicha a pánve: tumor rekta 8 cm od anu, perirektální uzliny do 9 mm. "
                   "V játrech 2 ložiska v S6 (24 mm) a S7 (18 mm) charakteru metastáz. Plíce bez ložisek.",
        "consult": "Pacientka 59 let, diabetička na metforminu. Od června enteroragie, kolonoskopicky tumor rekta. "
                   "ECOG 1. Hmotnost stabilní. Přeje si léčbu s kurativním záměrem, pokud je možná.",
        "expected": {"sets": ["KRC", "OBC"], "trials": ["RKT-03", "RKT-05", "RKT-06"], "role_question": True,
                     "options_include": ["Totální neoadjuvance"],
                     "tests": "C20 (konečník) musí spadnout do KRC stejně jako C18 a C19."},
    },
    "P08": {
        "gender": "male", "age": 72, "focus": "Urologie – prostata",
        "question": "Metastatický hormonálně senzitivní karcinom prostaty s kostními metastázami: ADT + ARPI, "
                    "nebo trojkombinace ADT + docetaxel + darolutamid?",
        "dx": [
            {"code": "C61", "display": "Zhoubný novotvar předstojné žlázy (prostaty)",
             "morph": ("8140/3", "Adenokarcinom NOS"), "site": "oba laloky prostaty", "onset": "2026-09-10",
             "stage": "cT3a cN1 cM1b, stadium IVB (TNM 8. vyd.), Gleason 4+4 = 8 (ISUP 4)"},
            {"code": "C79.5", "display": "Sekundární zhoubný novotvar kosti a kostní dřeně",
             "site": "páteř L2–L4, pánev", "onset": "2026-09-24"},
        ],
        "comorb": [("I10", "Esenciální hypertenze", "2012-01"), ("I48.0", "Paroxysmální fibrilace síní", "2020-06")],
        "meds": [("C09AA05", "ramipril", "5 mg p.o. 1× denně"), ("B01AF02", "apixaban", "5 mg p.o. 2× denně")],
        "biomarkers": [("PSA", "148 µg/l")],
        "labs": {"hb": 131, "neu": 3.8, "plt": 221, "krea": 96, "bili": 9},
        "ecog": 1, "weight": 84,
        "histology": "Biopsie prostaty (12 vzorků): acinární adenokarcinom, Gleason 4+4 = 8 (ISUP 4) "
                     "v 9 z 12 vzorků.",
        "imaging": "PSMA PET/CT: primární tumor prostaty, pánevní uzliny vpravo, osteoblastická ložiska L2–L4 "
                   "a v pánvi (celkem 5 ložisek). Viscerální metastázy nejsou.",
        "consult": "Pacient 72 let, hypertonik s paroxysmální fibrilací síní na apixabanu. Bolesti zad VAS 3. "
                   "PSA 148 µg/l. Nově zjištěné, hormonálně senzitivní onemocnění, dosud bez androgenní "
                   "deprivace. ECOG 1. Chce zůstat aktivní, jezdí na kole.",
        "expected": {"sets": ["OBC"], "trials": ["RKT-05", "RKT-06"], "role_question": False,
                     "options_include": ["ADT + ARPI", "ADT + docetaxel"], "options_exclude": ["Radium-223"],
                     "tests": "C61 nemá v datasetu sadu guidelines: AI dostane jen OBC, semafor jede z báze data/onko."},
    },
    "P09": {
        "gender": "male", "age": 64, "focus": "Hrudní – karcinom plic",
        "question": "Malobuněčný karcinom plic, limitované stadium: konkomitantní chemoradioterapie a "
                    "profylaktické ozáření mozku?",
        "dx": [
            {"code": "C34.3", "display": "Zhoubný novotvar dolního laloku, průdušky nebo plíce",
             "morph": ("8041/3", "Malobuněčný karcinom NOS"), "site": "levý dolní plicní lalok",
             "onset": "2026-09-18", "stage": "cT2b cN2 cM0, stadium IIIA (TNM 8. vyd.), limitované stadium"},
            {"code": "C77.1", "display": "Sekundární a neurčený zhoubný novotvar nitrohrudních mízních uzlin",
             "site": "mediastinální uzliny 7 a 4L", "onset": "2026-09-18"},
        ],
        "comorb": [("J44.9", "Chronická obstrukční plicní nemoc (GOLD 2)", "2017-02"),
                   ("F17.2", "Závislost na tabáku – aktivní kuřák (45 balíčkoroků)", None)],
        "meds": [("R03BB04", "tiotropium", "18 µg inh. 1× denně")],
        "biomarkers": [("TTF-1 (IHC)", "pozitivní"), ("Synaptofyzin, chromogranin (IHC)", "pozitivní"),
                       ("Ki-67", "85 %")],
        "labs": {"hb": 139, "neu": 6.1, "plt": 302, "krea": 82, "bili": 11},
        "ecog": 1, "weight": 76,
        "histology": "Bronchoskopická biopsie levého dolního laloku: malobuněčný karcinom plic, "
                     "TTF-1+, synaptofyzin+, chromogranin+, Ki-67 85 %.",
        "imaging": "PET/CT: tumor levého dolního laloku 48 mm, metabolicky aktivní mediastinální uzliny 7 a 4L. "
                   "MR mozku bez metastáz. Vzdálené metastázy nejsou.",
        "consult": "Pacient 64 let, aktivní kuřák s CHOPN. Kašel a úbytek 3 kg za 2 měsíce. ECOG 1. "
                   "Malobuněčný karcinom, limitované stadium.",
        "expected": {"sets": ["PLI", "OBC"], "trials": ["RKT-04", "RKT-05", "RKT-06"], "role_question": True,
                     "options_include": ["cisplatina + etoposid"],
                     "options_exclude": ["Neoadjuvantní chemoimunoterapie"],
                     "tests": "C34 vede na PLI, i když PLI je výtah pro NEmalobuněčný karcinom (mezera mapy).",
                     "gap": "AI dostane guidelines PLI a studii RKT-04, obojí pro nemalobuněčný karcinom "
                            "(semafor už SCLC rozlišuje, výběr guidelines podle MKN-10 ne)."},
    },
    "P10": {
        "gender": "female", "age": 66, "focus": "Duplicita malignit – prs a plíce",
        "question": "Metastatický karcinom prsu (HR+/HER2−, kosti) a nově primární adenokarcinom plic cT1b N0: "
                    "priorita léčby a resekce plicního ložiska?",
        "dx": [
            {"code": "C50.4", "display": "Zhoubný novotvar horního zevního kvadrantu prsu",
             "morph": ("8500/3", "Invazivní karcinom NST"), "site": "levý prs, horní zevní kvadrant",
             "onset": "2025-11-03", "stage": "pT2 pN1 M1 (kosti), stadium IV (TNM 8. vyd.)"},
            {"code": "C79.5", "display": "Sekundární zhoubný novotvar kosti a kostní dřeně",
             "site": "Th8, levá kyčelní kost", "onset": "2026-02-10"},
            {"code": "C34.1", "display": "Zhoubný novotvar horního laloku, průdušky nebo plíce",
             "morph": ("8140/3", "Adenokarcinom NOS"), "site": "pravý horní plicní lalok",
             "onset": "2026-09-30", "stage": "cT1b cN0 cM0, stadium IA2 (TNM 8. vyd.)"},
        ],
        "comorb": [("E03.9", "Hypotyreóza", "2010-05")],
        "meds": [("H03AA01", "levothyroxin", "75 µg p.o. 1× denně"),
                 ("L02BG03", "letrozol", "2,5 mg p.o. 1× denně")],
        "biomarkers": [("ER", "95 %"), ("PR", "40 %"), ("HER2", "IHC 1+ (HER2-low)"),
                       ("TTF-1 (plicní ložisko)", "pozitivní"), ("EGFR (plicní ložisko)", "bez mutace"),
                       ("ALK (plicní ložisko)", "negativní")],
        "labs": {"hb": 127, "neu": 2.9, "plt": 198, "krea": 68, "bili": 10},
        "ecog": 0, "weight": 63,
        "histology": "Transtorakální biopsie ložiska pravého horního laloku: adenokarcinom plic, TTF-1+, "
                     "GATA3−, ER−. Morfologie i imunoprofil odpovídají primárnímu plicnímu nádoru, ne metastáze prsu.",
        "imaging": "CT hrudníku a břicha: v pravém horním laloku solidní ložisko 17 mm (dříve 9 mm), "
                   "mediastinum bez zvětšených uzlin. Kostní metastázy Th8 a kyčelní kosti stacionární.",
        "consult": "Pacientka 66 let s metastatickým karcinomem prsu na letrozolu + ribociklibu, kostní nemoc "
                   "stabilní. Nově rostoucí plicní ložisko, histologicky primární adenokarcinom plic. ECOG 0.",
        "expected": {"sets": ["PRS", "PLI", "OBC"], "trials": ["RKT-01", "RKT-02", "RKT-04", "RKT-05", "RKT-06"],
                     "role_question": True,
                     "tests": "Dva primární nádory (C50 + C34) = dvě sady guidelines najednou."},
    },
    "P11": {
        "gender": "male", "age": 61, "focus": "GIT – anus",
        "question": "Spinocelulární karcinom anu cT2 N0 M0: definitivní chemoradioterapie (5-FU/mitomycin)?",
        "dx": [
            {"code": "C21.1", "display": "Zhoubný novotvar řitního kanálu",
             "morph": ("8070/3", "Spinocelulární karcinom NOS"), "site": "anální kanál", "onset": "2026-09-25",
             "stage": "cT2 cN0 cM0, stadium IIA (TNM 8. vyd.)"},
        ],
        "comorb": [("B20", "HIV infekce na antiretrovirové léčbě, nedetekovatelná virémie", "2009-04")],
        "meds": [("J05AR24", "lamivudin + dolutegravir", "1 tbl. p.o. 1× denně")],
        "biomarkers": [("p16 (IHC)", "pozitivní (HPV asociovaný)")],
        "labs": {"hb": 142, "neu": 3.4, "plt": 240, "krea": 88, "bili": 8},
        "ecog": 0, "weight": 80,
        "histology": "Biopsie z análního kanálu: nerohovějící spinocelulární karcinom, p16 difuzně pozitivní.",
        "imaging": "MR pánve: tumor análního kanálu 32 mm bez infiltrace svěračů, uzliny nezvětšené. "
                   "CT hrudníku a břicha bez vzdálených metastáz.",
        "consult": "Pacient 61 let, HIV pozitivní na ART s nedetekovatelnou virémií, CD4 620. Krvácení z konečníku "
                   "a bolest při defekaci. ECOG 0.",
        "expected": {"sets": ["OBC"], "trials": ["RKT-05", "RKT-06"], "role_question": False,
                     "tests": "C21 (anus) NESMÍ spadnout do KRC: jiná nemoc, jiná léčba."},
    },
    "P12": {
        "gender": "male", "age": 68, "focus": "GIT – kolorektum",
        "question": "Karcinom sigmatu s jaterními metastázami po 6 cyklech FOLFOX: resekabilita jater?",
        "dx": [
            {"code": "C18.7", "display": "Zhoubný novotvar esovité kličky tlustého střeva (sigmatu)",
             "morph": ("8140/3", "Adenokarcinom NOS"), "site": "colon sigmoideum", "onset": "2026-04-02",
             "stage": "cT3 cN1 cM1a, stadium IVA (TNM 8. vyd.)", "category": "hlavní diagnóza"},
            {"code": "C78.7", "display": "Sekundární zhoubný novotvar jater a intrahepatálních žlučovodů",
             "site": "játra, 3 ložiska v pravém laloku", "onset": "2026-04-10", "category": "hlavní diagnóza"},
        ],
        "comorb": [("I10", "Esenciální hypertenze", "2016-09")],
        "meds": [("C08CA01", "amlodipin", "5 mg p.o. 1× denně")],
        "biomarkers": [("KRAS", "mutace G12V"), ("BRAF V600E", "neprokázána (wild-type)"),
                       ("MMR (IHC)", "zachovalá exprese (pMMR)")],
        "labs": {"hb": 119, "neu": 2.4, "plt": 176, "krea": 90, "bili": 13},
        "ecog": 1, "weight": 82,
        "histology": "Biopsie sigmatu: adenokarcinom G2, pMMR, KRAS G12V.",
        "imaging": "CT břicha po 6 cyklech FOLFOX: jaterní metastázy v pravém laloku zmenšené o 35 %, "
                   "nová ložiska nejsou. Odhadovaný FLR po pravostranné hepatektomii 34 %.",
        "consult": "Pacient 68 let po 6 cyklech FOLFOX. Neuropatie G1. ECOG 1. Zvažována resekce jater.",
        "expected": {"sets": ["KRC", "OBC"], "trials": ["RKT-03", "RKT-05", "RKT-06"], "role_question": True,
                     "options_include": ["FOLFOX"], "header_dx": "C18.7",
                     "tests": "Diagnóza s kategorií „hlavní diagnóza“ místo „onkologická diagnóza“ "
                              "(jiný zdrojový systém). Kolorektum musí dostat KRC."},
    },
}


def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def ref(rtype: str, rid: str) -> dict:
    return {"reference": f"{rtype}/{rid}"}


def condition(pid: str, rid: str, dx: dict, category: str) -> dict:
    out = {
        "resourceType": "Condition", "id": rid,
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                       "code": "active"}]},
        "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                                           "code": "confirmed"}]},
        "category": [{"text": dx.get("category", category)}],
        "code": {"coding": [{"system": ICD10, "code": dx["code"], "display": dx["display"]}], "text": dx["display"]},
        "subject": ref("Patient", pid),
    }
    if dx.get("onset"):
        out["onsetDateTime"] = dx["onset"]
    if dx.get("site"):
        out["bodySite"] = [{"text": dx["site"]}]
    if dx.get("morph"):
        out["extension"] = [
            {"url": f"{SD}/icd-o-3-morfologie",
             "valueCodeableConcept": {"coding": [{"system": ICDO3, "code": dx["morph"][0], "display": dx["morph"][1]}]}},
            {"url": f"{SD}/icd-o-3-topografie",
             "valueCodeableConcept": {"coding": [{"system": ICDO3, "code": dx["code"]}]}},
        ]
    if dx.get("stage"):
        out["stage"] = [{"summary": {"text": dx["stage"]}, "type": {"text": "klinické"}}]
    return out


def text_report(pid: str, rid: str, kind: str, title: str, date: str, text: str, author: str) -> dict:
    if kind == "RAD":
        cat = [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "RAD",
                            "display": "Radiology"}], "text": "Zobrazovací metody"}]
        code = {"coding": [{"system": LOINC, "code": "18748-4", "display": "Diagnostic imaging study"}], "text": title}
    else:
        cat = [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "SP",
                            "display": "Surgical Pathology"}], "text": "Patologie"}]
        code = {"coding": [{"system": LOINC, "code": "22637-3", "display": "Pathology report"}], "text": title}
    return {
        "resourceType": "DiagnosticReport", "id": rid, "status": "final", "category": cat, "code": code,
        "subject": ref("Patient", pid), "effectiveDateTime": date, "issued": f"{date}T15:00:00+02:00",
        "performer": [ref("Practitioner", author)], "conclusion": text.split(". ")[0] + ".",
        "presentedForm": [{"contentType": "text/plain; charset=utf-8", "language": "cs", "data": b64(text),
                           "title": title, "creation": date}],
    }


def bundle(pid: str, p: dict, mdt: str = "2026-10-28") -> dict:
    lek = [f"LEK-{pid}-0{i}" for i in (1, 2, 3)]
    res: list[dict] = [
        {"resourceType": "Patient", "id": pid,
         "identifier": [{"system": "https://rakathon.example.org/fhir/sid/pacient", "value": pid}],
         "name": [{"text": f"Pacient {pid} (fiktivní)"}], "gender": p["gender"], "birthDate": str(2026 - p["age"]),
         "extension": [{"url": f"{SD}/vek-k-datu-mdt", "valueInteger": p["age"]}]},
        {"resourceType": "Organization", "id": "ORG-FN",
         "name": "Fiktivní fakultní nemocnice – Komplexní onkologické centrum"},
    ]
    for rid, role in zip(lek, ("klinický onkolog (ošetřující lékař)", "radiolog", "patolog")):
        res.append({"resourceType": "Practitioner", "id": rid,
                    "identifier": [{"system": "https://rakathon.example.org/fhir/sid/lekar", "value": rid}],
                    "name": [{"text": f"{rid} (fiktivní lékař) – {role}"}],
                    "qualification": [{"code": {"text": role}}]})
    for i, dx in enumerate(p["dx"], 1):
        res.append(condition(pid, f"{pid}-dg{i}", dx, "onkologická diagnóza"))
    for i, (code, display, onset) in enumerate(p["comorb"], 1):
        res.append(condition(pid, f"{pid}-kom{i}", {"code": code, "display": display, "onset": onset}, "komorbidita"))
    for i, (atc, name, dose) in enumerate(p["meds"], 1):
        res.append({"resourceType": "MedicationRequest", "id": f"{pid}-med{i:02d}", "status": "active",
                    "intent": "order", "category": [{"text": "chronická medikace"}],
                    "medicationCodeableConcept": {"coding": [{"system": "http://www.whocc.no/atc", "code": atc,
                                                              "display": name}], "text": name},
                    "subject": ref("Patient", pid), "authoredOn": "2026-01-15",
                    "dosageInstruction": [{"text": dose}], "requester": ref("Practitioner", lek[0])})

    res.append(text_report(pid, f"{pid}-pat01", "SP", "Histologie – bioptický vzorek", p["dx"][0]["onset"],
                           p["histology"], lek[2]))
    res.append(text_report(pid, f"{pid}-img01", "RAD", "Restagingové zobrazení", "2026-10-12", p["imaging"], lek[1]))
    res.append({
        "resourceType": "DocumentReference", "id": f"{pid}-doc01", "status": "current",
        "type": {"coding": [{"system": LOINC, "code": "11488-4", "display": "Consult note"}],
                 "text": "Onkologické vyšetření před MDT"},
        "category": [{"text": "A-ONK – Onkologická ambulance"}], "subject": ref("Patient", pid),
        "date": "2026-10-14T10:00:00+02:00", "author": [ref("Practitioner", lek[0])],
        "description": "Onkologické vyšetření před MDT",
        "content": [{"attachment": {"contentType": "text/plain; charset=utf-8", "language": "cs",
                                    "data": b64(p["consult"]), "title": "Onkologické vyšetření před MDT",
                                    "creation": "2026-10-14"}}],
    })

    stage = next(dx["stage"] for dx in p["dx"] if dx.get("stage"))
    res.append({"resourceType": "Observation", "id": f"{pid}-tnm01", "status": "final",
                "subject": ref("Patient", pid), "effectiveDateTime": "2026-10-12",
                "derivedFrom": [ref("DocumentReference", f"{pid}-doc01")], "category": [{"text": "Staging"}],
                "code": {"text": "TNM (klinické)"}, "valueString": stage, "focus": [ref("Condition", f"{pid}-dg1")]})
    res.append({"resourceType": "Observation", "id": f"{pid}-ecog01", "status": "final",
                "subject": ref("Patient", pid), "effectiveDateTime": "2026-10-14",
                "derivedFrom": [ref("DocumentReference", f"{pid}-doc01")],
                "category": [{"coding": [{"system": OBS_CAT, "code": "survey"}]}],
                "code": {"coding": [{"system": LOINC, "code": "89247-1", "display": "ECOG Performance Status score"}],
                         "text": "ECOG – hodnoceno lékařem"},
                "valueInteger": p["ecog"], "performer": [ref("Practitioner", lek[0])]})
    res.append({"resourceType": "Observation", "id": f"{pid}-vaha01", "status": "final",
                "subject": ref("Patient", pid), "effectiveDateTime": "2026-10-14",
                "category": [{"coding": [{"system": OBS_CAT, "code": "vital-signs"}]}],
                "code": {"coding": [{"system": LOINC, "code": "29463-7", "display": "Body weight"}], "text": "Hmotnost"},
                "valueQuantity": {"value": p["weight"], "unit": "kg", "system": "http://unitsofmeasure.org",
                                  "code": "kg"}})
    for i, (name, value) in enumerate(p["biomarkers"], 1):
        res.append({"resourceType": "Observation", "id": f"{pid}-bm{i:02d}", "status": "final",
                    "subject": ref("Patient", pid), "effectiveDateTime": p["dx"][0]["onset"],
                    "derivedFrom": [ref("DiagnosticReport", f"{pid}-pat01")],
                    "category": [{"coding": [{"system": OBS_CAT, "code": "laboratory"}]},
                                 {"text": "Biomarker / molekulární patologie"}],
                    "code": {"text": name}, "valueString": value})
    for key, loinc, name, unit, section in LABS:
        res.append({"resourceType": "Observation", "id": f"{pid}-lab01-{key}", "status": "final",
                    "category": [{"coding": [{"system": OBS_CAT, "code": "laboratory"}]}, {"text": section}],
                    "code": {"coding": [{"system": LOINC, "code": loinc, "display": name}], "text": name},
                    "subject": ref("Patient", pid), "effectiveDateTime": "2026-10-13T07:30:00+02:00",
                    "valueQuantity": {"value": p["labs"][key], "unit": unit}})

    res.append({
        "resourceType": "ServiceRequest", "id": f"{pid}-zad01",
        "identifier": [{"system": "https://rakathon.example.org/fhir/sid/mdt-zadanka", "value": f"{pid}-zad01"}],
        "status": "active", "intent": "order", "category": [{"text": f"Požadované zaměření MDT: {p['focus']}"}],
        "code": {"coding": [{"system": f"{CS}/mdt-typ-projednani", "code": "primarni",
                             "display": "Primární projednání"}]},
        "priority": "routine", "subject": ref("Patient", pid), "authoredOn": "2026-10-15T11:00:00+02:00",
        "requester": ref("Practitioner", lek[0]), "performer": [ref("Organization", "ORG-FN")],
        "reasonCode": [{"coding": [{"system": f"{CS}/mdt-typ-otazky", "code": "lecebny-plan",
                                    "display": "Léčebný plán"}], "text": p["question"]}],
    })
    res.append({
        "resourceType": "Task", "id": f"{pid}-zad01-task", "status": "accepted",
        "businessStatus": {"coding": [{"system": f"{CS}/mdt-stav-zadanky", "code": "naplanovana",
                                       "display": "Naplánovaná"}]},
        "intent": "order", "focus": ref("ServiceRequest", f"{pid}-zad01"), "for": ref("Patient", pid),
        "authoredOn": "2026-10-15T11:00:00+02:00", "requester": ref("Practitioner", lek[0]),
        "owner": ref("Organization", "ORG-FN"), "restriction": {"period": {"start": f"{mdt}T14:00:00+02:00"}},
    })
    return {"resourceType": "Bundle", "id": f"{pid}-bundle", "type": "collection", "meta": {"tag": [TAG]},
            "entry": [{"fullUrl": f"urn:uuid:{r['resourceType']}-{r['id']}", "resource": r} for r in res]}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for pid, p in PATIENTS.items():
        out = HERE / "pacienti" / pid / f"{pid}_bundle.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(bundle(pid, p), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    expected = {pid: {"dx": [d["code"] for d in p["dx"]], **p["expected"]} for pid, p in PATIENTS.items()}
    (HERE / "expected.json").write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Vygenerováno {len(PATIENTS)} pacientů do {HERE / 'pacienti'}")


if __name__ == "__main__":
    main()
