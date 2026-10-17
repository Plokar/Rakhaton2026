"""Hrany diagnózy nalezené testovacími pacienty P07–P12 (T-320, data/dataset_test)."""
import base64

import pytest

from services.ai.context_builder import context_from_resources
from services.ai.guidelines import parse_guidelines
from services.rules import onko_kb
from services.rules import red_flags as rules
from services.rules.compatibility import evaluate_compatibility, lung_histology
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
    assert lung_histology(rules.PatientData(nsclc)) == "NSCLC" and lung_histology(rules.PatientData(sclc)) == "SCLC"
    assert "pli-neoadjuvance-lobektomie" in {p["id"] for p in evaluate_compatibility(nsclc)}
    assert not [p for p in evaluate_compatibility(sclc) if p["id"].startswith("pli-")]


def test_unknown_lung_histology_is_not_guessed():
    """Bez morfologie a bez zmínky v textu histologie neznámá: nic se nevyřadí (zadání, pravidlo 3)."""
    dg = condition("C34.1", "onkologická diagnóza")
    assert lung_histology(rules.PatientData([dg])) is None


@pytest.mark.skipif(onko_kb.q() is None, reason="data/onko není k dispozici")
def test_sclc_gets_sclc_procedures_from_kb():
    kb = {p["id"] for p in onko_kb.kb_for_patient(with_dg1("P04", morphology="8041/3"))}
    assert any(p.startswith("sclc-") for p in kb) and not any(p.startswith("pli-") for p in kb)


def test_metastatic_prostate_contexts():
    assert onko_kb.M1_CONTEXT.search("mHSPC vysoký objem") and onko_kb.M1_CONTEXT.search("mCRPC")
    assert not onko_kb.M1_CONTEXT.search("nmCRPC, PSADT ≤10 měsíců")


@pytest.mark.skipif(onko_kb.q() is None, reason="data/onko není k dispozici")
def test_metastatic_prostate_hspc_vs_crpc():
    """P08: M1 prostata dostane postupy mHSPC i mCRPC; podle kastračního statusu se dělí jen, když je v datech."""
    prostate = with_dg1("P03", code="C61")
    unknown = {p["id"] for p in onko_kb.kb_for_patient(prostate)}
    assert {"pro-mhspc-arpi", "pro-mhspc-triplet", "pro-mcrpc-taxan", "pro-ra223"} <= unknown
    assert "pro-nmcrpc" not in unknown                                    # nmCRPC je M0

    hspc = prostate + [document("P03", "Nově zjištěné, hormonálně senzitivní onemocnění, dosud bez ADT.")]
    kb = {p["id"] for p in onko_kb.kb_for_patient(hspc)}
    assert {"pro-mhspc-arpi", "pro-mhspc-triplet"} <= kb
    assert not kb & {"pro-ra223", "pro-mcrpc-taxan", "pro-lu-psma"}

    crpc = prostate + [document("P03", "Progrese PSA na ADT, onemocnění je kastračně rezistentní.")]
    kb = {p["id"] for p in onko_kb.kb_for_patient(crpc)}
    assert {"pro-mcrpc-taxan", "pro-ra223"} <= kb and not any(p.startswith("pro-mhspc") for p in kb)


# ── T-325: guidelines, které chybí nebo na diagnózu nesedí ───────────────────
def test_nsclc_trial_not_offered_for_sclc():
    from services.rules.guideline_sets import trial_is_relevant
    rkt04 = ["Nemalobuněčný karcinom plic, stadium II–IIIB, resekabilní"]
    assert trial_is_relevant(rkt04, ["PLI", "OBC"])                          # histologie neuvedená: nehádá se
    assert trial_is_relevant(rkt04, ["PLI", "OBC"], "NSCLC")
    assert not trial_is_relevant(rkt04, ["PLI", "OBC"], "SCLC")
    assert trial_is_relevant(["Solidní nádory"], ["PLI", "OBC"], "SCLC")


def test_sclc_context_without_rkt04_and_with_notice():
    from services.ai.brief import guideline_notices
    from services.tests.dataset import load_studies
    p04 = with_dg1("P04", morphology="8041/3")                              # P04 jako malobuněčný karcinom
    assert lung_histology(rules.PatientData(p04)) == "SCLC"
    ctx = context_from_resources("P04", p04, studies=load_studies())
    assert "RKT-04" not in {t.study_id for t in ctx.trials}
    passages = [p for md in load_guideline_markdowns().values() for p in parse_guidelines(md)]
    notices = guideline_notices(["PLI", "OBC"], passages, p04)
    assert [n["id"] for n in notices] == ["miss-guidelines-sclc"] and "nemalobuněčný" in notices[0]["text"]
    assert guideline_notices(["PLI", "OBC"], passages, load_patient("P04")) == []      # NSCLC: guidelines sedí


def test_missing_guidelines_are_visible_in_brief():
    from services.ai.brief import build_brief, guideline_notices
    from services.ai_service import MockAIProvider
    p03 = load_patient("P03")
    notices = guideline_notices(["KRC", "OBC"], [], p03)
    assert notices[0]["text"].startswith("Guidelines nejsou v IRIS (sady KRC, OBC)")
    brief = build_brief("P03", p03, provider=MockAIProvider(), notices=notices)
    summary = next(s for s in brief["sections"] if s["id"] == "summary")
    assert any(i["id"] == "miss-guidelines" and i["kind"] == "missing" for i in summary["items"])
