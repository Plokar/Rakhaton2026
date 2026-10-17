"""Hrany diagnózy nalezené testovacími pacienty P07–P12 (T-320, data/dataset_test)."""
import base64

import pytest

from services.ai.context_builder import context_from_resources
from services.ai.guidelines import parse_guidelines
from services.rules import onko_kb
from services.rules import red_flags as rules
from services.rules.compatibility import evaluate_compatibility, is_sclc
from services.rules.guideline_sets import is_oncologic
from services.tests.dataset import load_guideline_markdowns, load_patient

ICD10 = "http://hl7.org/fhir/sid/icd-10"


def condition(code: str, category: str | None) -> dict:
    out = {"resourceType": "Condition", "id": "X-dg1", "code": {"coding": [{"system": ICD10, "code": code}]}}
    if category is not None:
        out["category"] = [{"text": category}]
    return out


def with_dg1(pid: str, **changes) -> list[dict]:
    resources = load_patient(pid)
    dg1 = next(r for r in resources if r["id"] == f"{pid}-dg1")
    for key, value in changes.items():
        if key == "code":
            dg1["code"] = {"coding": [{"system": ICD10, "code": value}], "text": value}
        elif key == "category":
            for c in (r for r in resources if r["resourceType"] == "Condition" and "onkolog" in str(r.get("category"))):
                c["category"] = [{"text": value}]
        elif key == "morphology":
            ext = next(e for e in dg1["extension"] if e["url"].endswith("/icd-o-3-morfologie"))
            ext["valueCodeableConcept"]["coding"][0]["code"] = value
    return resources


def document(pid: str, text: str) -> dict:
    return {"resourceType": "DocumentReference", "id": f"{pid}-doc99", "status": "current",
            "subject": {"reference": f"Patient/{pid}"},
            "content": [{"attachment": {"contentType": "text/plain; charset=utf-8",
                                        "data": base64.b64encode(text.encode()).decode()}}]}


@pytest.mark.parametrize("code, category, expected", [
    ("C18.7", "onkologická diagnóza", True),
    ("C18.7", "hlavní diagnóza", True),            # jiný zdrojový systém (P12)
    ("C18.7", None, True),
    ("D41.0", None, True),                          # nejisté chování (P06)
    ("D05.1", None, True),                          # in situ
    ("D12.5", None, False),                         # nezhoubný novotvar
    ("C50.9", "komorbidita", False),                # stav po nádoru vedený jako komorbidita
    ("D64.8", "nežádoucí účinek léčby", False),     # P05-ae1
    ("I10", "hlavní diagnóza", False),
])
def test_is_oncologic(code, category, expected):
    assert is_oncologic(condition(code, category)) is expected


def test_cancer_without_oncologic_category_gets_its_guidelines():
    """P12: výběr sad, kontext AI i semafor se shodnou, i když diagnóza nemá kategorii „onkologická diagnóza“."""
    resources = with_dg1("P03", category="hlavní diagnóza")
    passages = [p for md in load_guideline_markdowns().values() for p in parse_guidelines(md)]
    data = rules.PatientData(resources)
    context = context_from_resources("P03", resources, guidelines=[p for p in passages if p.guideline_set in data.sets])
    assert data.sets == context.guideline_sets == ["KRC", "OBC"]
    assert {p.guideline_set for p in context.guidelines} == {"KRC", "OBC"}
    assert [d["icd10"] for d in context.facts["diagnoses"]] == ["C18.7", "C78.7"]
    assert {p["id"] for p in evaluate_compatibility(resources)} == {p["id"] for p in evaluate_compatibility(load_patient("P03"))}


def test_sclc_has_no_nsclc_catalog_procedures():
    """P09: postupy PLI jsou pro nemalobuněčný karcinom; SCLC je dostane z báze data/onko."""
    nsclc = load_patient("P04")
    sclc = with_dg1("P04", morphology="8041/3")
    assert not is_sclc(rules.PatientData(nsclc)) and is_sclc(rules.PatientData(sclc))
    assert "pli-neoadjuvance-lobektomie" in {p["id"] for p in evaluate_compatibility(nsclc)}
    assert not [p for p in evaluate_compatibility(sclc) if p["id"].startswith("pli-")]


@pytest.mark.skipif(onko_kb.q() is None, reason="data/onko není k dispozici")
def test_sclc_gets_sclc_procedures_from_kb():
    kb = {p["id"] for p in onko_kb.kb_for_patient(with_dg1("P04", morphology="8041/3"))}
    assert any(p.startswith("sclc-") for p in kb) and not any(p.startswith("pli-") for p in kb)


def test_metastatic_prostate_contexts():
    assert onko_kb.M1_CONTEXT.search("mHSPC vysoký objem") and onko_kb.M1_CONTEXT.search("mCRPC")
    assert not onko_kb.M1_CONTEXT.search("nmCRPC, PSADT ≤10 měsíců")


@pytest.mark.skipif(onko_kb.q() is None, reason="data/onko není k dispozici")
def test_metastatic_prostate_hspc_vs_crpc():
    """P08: u M1 prostaty postupy mHSPC; mCRPC (vč. Radium-223) až při kastrační rezistenci."""
    hspc = with_dg1("P03", code="C61")
    kb = {p["id"] for p in onko_kb.kb_for_patient(hspc)}
    assert {"pro-mhspc-arpi", "pro-mhspc-triplet"} <= kb
    assert not kb & {"pro-ra223", "pro-mcrpc-taxan", "pro-lu-psma", "pro-nmcrpc"}

    crpc = hspc + [document("P03", "Progrese PSA na ADT, onemocnění je kastračně rezistentní.")]
    kb = {p["id"] for p in onko_kb.kb_for_patient(crpc)}
    assert {"pro-mcrpc-taxan", "pro-ra223"} <= kb and not any(p.startswith("pro-mhspc") for p in kb)
