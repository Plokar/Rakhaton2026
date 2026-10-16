"""Testy semaforu souladu postupů se stavem pacienta (T-503, D-015, docs/POZADAVKY_LEKARE.md §5.4)."""
import copy
import json
import re
from pathlib import Path

import pytest

from services.ai.context_builder import context_from_resources
from services.rules.compatibility import CHECKS, REQUIRES, evaluate_compatibility, load_catalog
from services.tests.dataset import load_patient, load_studies

PATIENTS = ["P01", "P02", "P03", "P04", "P05", "P06"]
LIGHTS = {"green", "orange", "red", "grey", "skipped"}
ROLES = {"surgeon", "oncologist", "radiation_oncologist", "radiologist", "pathologist", "pulmonologist",
         "cardiologist", "patient"}
MODALITIES = {"chirurgie", "chemoterapie", "rt", "hormonalni", "cilena", "imunoterapie", "jina-systemova",
              "diagnostika", "sledovani"}
GUIDELINE_ID = re.compile(r"^(KRC|PRS|PLI|OBC)-\d+\.\d+$|^RKT-\d{2}(/[ZV]\d+)?$")
EXTERNAL_FILE = Path(__file__).resolve().parents[1] / "iris" / "data" / "external_sources.json"   # T-504
EXTERNAL = {s["evidence_id"] for s in json.loads(EXTERNAL_FILE.read_text(encoding="utf-8"))["sources"]}


@pytest.fixture(scope="module")
def results():
    return {pid: {p["id"]: p for p in evaluate_compatibility(load_patient(pid))} for pid in PATIENTS}


def lights(procedure):
    return {r["rule_id"]: r["status"] for r in procedure["compatibility"]["rules"]}


# ── Očekávané barvy (§5.4) ────────────────────────────────────────────────────
EXPECTED = {
    "P03": {
        "krc-resekce-jater": ("orange", {"VS-KRC-01": "orange", "VS-KRC-02": "orange", "VS-KRC-03": "orange",
                                         "VS-CHIR-03": "green", "VS-CHIR-01": "green", "VS-OBC-04": "orange",
                                         "VS-OBC-02": "orange"}),
        "krc-konverzni-chemoterapie": ("orange", {"VS-KRC-05": "orange", "VS-KRC-08": "orange", "VS-KRC-09": "grey",
                                                  "VS-KRC-10": "orange"}),
        "krc-anti-egfr": ("red", {"VS-KRC-06": "red"}),
        "krc-imunoterapie": ("grey", {"VS-KRC-07": "grey"}),
    },
    "P04": {
        "pli-neoadjuvance-lobektomie": ("orange", {
            "VS-PLI-01": "orange", "VS-PLI-02": "grey", "VS-PLI-03": "orange", "VS-PLI-06": "orange",
            "VS-PLI-04": "orange", "VS-PLI-09": "orange", "VS-CHIR-02": "orange", "VS-OBC-03": "grey",
            "VS-OBC-04": "orange", "VS-PLI-11": "green"}),
        "pli-chrt-durvalumab": ("orange", {"VS-PLI-07": "green", "VS-PLI-06": "orange", "VS-PLI-10": "grey",
                                           "VS-PLI-04": "orange", "VS-OBC-04": "orange", "VS-PLI-11": "green"}),
    },
}


@pytest.mark.parametrize("patient_id, procedure_id", [(p, proc) for p, procs in EXPECTED.items() for proc in procs])
def test_expected_colors(results, patient_id, procedure_id):
    overall, rules = EXPECTED[patient_id][procedure_id]
    procedure = results[patient_id][procedure_id]
    assert lights(procedure) == rules
    assert procedure["compatibility"]["overall"] == overall


def test_all_options_shown_including_red(results):
    assert set(results["P03"]) == set(EXPECTED["P03"])        # anti-EGFR se neskryje
    assert set(results["P04"]) == set(EXPECTED["P04"])


@pytest.mark.parametrize("patient_id, procedure_id, rule_id, status, fragment", [
    ("P03", "krc-resekce-jater", "VS-KRC-01", "orange", "FLR 38 % < 40 %"),
    ("P03", "krc-resekce-jater", "VS-CHIR-03", "green", "operace nejdříve 2026-10-19"),
    ("P03", "krc-anti-egfr", "VS-KRC-06", "red", "G12D"),
    ("P04", "pli-neoadjuvance-lobektomie", "VS-PLI-01", "orange", "ppoFEV1 49 %, ppoDLCO 38 % < 60 % → zátěžový test"),
    ("P04", "pli-neoadjuvance-lobektomie", "VS-PLI-11", "green", "CrCl ≈ 76 ml/min"),
    ("P01", "prs-tdxd", "VS-PRS-03", "orange", "Diskordance HER2"),
    ("P02", "prs-anti-her2", "VS-PRS-01", "orange", "LVEF 63 → 52 %"),
    ("P02", "prs-srs", "VS-PRS-11", "green", "2 mozkové metastázy"),
    ("P05", "prs-parp-inhibitor", "VS-PRS-09", "orange", "třezalka"),
    ("P05", "prs-parp-inhibitor", "VS-PRS-07", "orange", "nejnižší dávka 200 mg"),
    ("P05", "prs-tdxd", "VS-PRS-03", "green", "HER2-low"),
    ("P06", "prs-anti-her2", "VS-PRS-10", "orange", "Neuropatie G2"),
])
def test_rule_texts(results, patient_id, procedure_id, rule_id, status, fragment):
    rule = next(r for r in results[patient_id][procedure_id]["compatibility"]["rules"] if r["rule_id"] == rule_id)
    assert rule["status"] == status
    assert fragment in rule["text"]


def test_derived_values_show_formula(results):
    bev = next(r for r in results["P03"]["krc-resekce-jater"]["compatibility"]["rules"] if r["rule_id"] == "VS-CHIR-03")
    assert bev["derived"]["inputs"] == ["P03-tx-bev-08", "P03-zad01-task"]
    rules = results["P04"]["pli-chrt-durvalumab"]["compatibility"]["rules"]
    crcl = next(r for r in rules if r["rule_id"] == "VS-PLI-11")
    assert "Cockcroft-Gault" in crcl["derived"]["formula"] and "1,23" in crcl["derived"]["formula"]
    assert crcl["derived"]["inputs"] == ["P04", "P04-vaha03", "P04-lab05-krea"]


def test_preferences_are_labels(results):
    resection = results["P03"]["krc-resekce-jater"]["compatibility"]
    texts = [p["text"] for p in resection["patient_preferences"]]
    assert any("Operaci bych chtěl" in t for t in texts)
    assert resection["overall"] == "orange"                       # preference barvu nemění
    srs = results["P02"]["prs-srs"]["compatibility"]["patient_preferences"]
    assert any("ozařování hlavy" in p["text"] for p in srs)


# ── Přeskočení a potvrzené komorbidity ────────────────────────────────────────
def test_skipped_field_is_not_evaluated():
    result = {p["id"]: p for p in evaluate_compatibility(load_patient("P03"), skipped_fields=["bm.mmr"])}
    rule = result["krc-imunoterapie"]["compatibility"]["rules"][0]
    assert rule["status"] == "skipped" and "neposuzováno" in rule["text"]
    assert result["krc-imunoterapie"]["compatibility"]["overall"] == "skipped"


def test_confirmed_comorbidities_turn_absence_green():
    plain = {p["id"]: p for p in evaluate_compatibility(load_patient("P02"))}
    confirmed = {p["id"]: p for p in evaluate_compatibility(load_patient("P02"), comorbidities_confirmed=True)}
    assert lights(plain["prs-tdxd"])["VS-PRS-02"] == "grey"
    assert lights(confirmed["prs-tdxd"])["VS-PRS-02"] == "green"


# ── Červená jen se zdrojem, integrita katalogu ────────────────────────────────
def test_red_only_with_source():
    catalog = copy.deepcopy(load_catalog())
    del catalog["rules"]["VS-KRC-06"]["source"]
    procedures = evaluate_compatibility(load_patient("P03"), catalog=catalog)
    procedure = next(p for p in procedures if p["id"] == "krc-anti-egfr")
    assert procedure["compatibility"]["rules"][0]["status"] == "orange"


def test_catalog_integrity():
    catalog = load_catalog()
    for rule_id, rule in catalog["rules"].items():
        assert rule["check"] in CHECKS, rule_id
        for source in filter(None, (rule["source"], rule.get("threshold_source"))):
            assert GUIDELINE_ID.match(source) or source in EXTERNAL, (rule_id, source)   # EXT jen z katalogu T-504
    for procedure in catalog["procedures"]:
        assert set(procedure["rules"]) <= set(catalog["rules"]), procedure["id"]
        assert procedure["owner_role"] in ROLES and procedure["modality"] in MODALITIES
        assert all(GUIDELINE_ID.match(g) for g in procedure["guidelines"])
        assert procedure.get("requires") is None or procedure["requires"] in REQUIRES
    ids = [p["id"] for p in catalog["procedures"]]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("patient_id", PATIENTS)
def test_contract_and_citations(results, patient_id):
    catalog = load_catalog()
    ctx = context_from_resources(patient_id, load_patient(patient_id), studies=load_studies())
    allowed_rule_sources = {s for r in catalog["rules"].values() for s in (r["source"], r.get("threshold_source")) if s}
    assert results[patient_id], f"{patient_id}: žádný postup"
    for procedure in results[patient_id].values():
        compatibility = procedure["compatibility"]
        statuses = [r["status"] for r in compatibility["rules"]]
        assert compatibility["overall"] in LIGHTS and set(statuses) <= LIGHTS
        order = ["red", "orange", "grey", "skipped", "green"]
        assert compatibility["overall"] == min(statuses, key=order.index)
        for rule in compatibility["rules"]:
            assert set(rule["patient_citations"]) <= ctx.allowed_ids, (rule["rule_id"], rule["patient_citations"])
            assert rule["rule_citation"] in allowed_rule_sources
            assert "doporučujeme" not in rule["text"].lower()
            if rule["status"] == "red":
                assert GUIDELINE_ID.match(rule["rule_citation"]) or rule["rule_citation"] in EXTERNAL
            if rule.get("derived"):
                assert set(rule["derived"]["inputs"]) <= ctx.allowed_ids
        for preference in compatibility["patient_preferences"]:
            assert preference["kind"] == "claim" and set(preference["citations"]) <= ctx.allowed_ids
