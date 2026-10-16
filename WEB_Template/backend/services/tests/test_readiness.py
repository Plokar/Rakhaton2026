"""Readiness podle checklistu OBC-1.1/OBC-1.2 a biomarkerů (T-303)."""
from services.rules.readiness import evaluate_readiness
from services.tests.dataset import load_patient


def test_p03_readiness_reports_missing_mmr_and_chest_ct():
    result = evaluate_readiness(load_patient("P03"))
    unresolved = {field["id"]: field for field in result["unresolved"]}
    assert result["status"] == "incomplete"
    assert unresolved["bm.mmr"]["status"] == "missing"
    assert unresolved["staging.chest_ct"]["status"] == "missing"
    assert result["score"]["total"] > result["score"]["present"]


def test_p01_and_p05_report_stale_staging():
    for patient_id, age in (("P01", 50), ("P05", 83)):
        result = evaluate_readiness(load_patient(patient_id))
        stale = {item["id"]: item for item in result["stale_staging"]}
        assert stale["staging.imaging"]["age_days"] == age
        assert stale["staging.imaging"]["citation"]


def test_skipped_fields_stay_unresolved():
    result = evaluate_readiness(load_patient("P03"), skipped_fields=["bm.mmr"])
    unresolved = {field["id"]: field for field in result["unresolved"]}
    assert unresolved["bm.mmr"]["status"] == "skipped"
