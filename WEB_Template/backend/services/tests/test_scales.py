"""Karta Lung-RADS / Fleischner s kontrolou použitelnosti (BON-6, T-508)."""
import pytest

from services.rules.scales import evaluate_scales, scale_claims
from services.tests.dataset import load_patient


@pytest.mark.parametrize("patient_id", ["P01", "P02", "P03", "P04", "P05", "P06"])
def test_dataset_patients_cannot_use_scales(patient_id):
    """DoD: u všech 6 pacientů „nelze použít“ s důvodem a citací (známý nádor, žádné screeningové CT)."""
    lung_rads, fleischner = evaluate_scales(load_patient(patient_id))
    assert not lung_rads["applicable"] and "screeningové" in lung_rads["reason"] and lung_rads["patient_citations"]
    assert not fleischner["applicable"] and fleischner["reason"].startswith("známý nádor")
    assert fleischner["patient_citations"][0].startswith(f"{patient_id}-")
    assert all(c["text"].split(":")[1].strip().startswith("nelze použít") for c in scale_claims(load_patient(patient_id), "radiologist"))


def _screening_patient(report_text: str, age: int = 62, cancer: bool = False) -> list[dict]:
    resources = [
        {"resourceType": "Patient", "id": "X01", "gender": "male",
         "extension": [{"url": "https://rakathon.example.org/fhir/StructureDefinition/vek-k-datu-mdt", "valueInteger": age}]},
        {"resourceType": "DiagnosticReport", "id": "X01-img01", "status": "final", "effectiveDateTime": "2026-09-01",
         "subject": {"reference": "Patient/X01"}, "code": {"text": "Nízkodávkové CT plic – screening"},
         "conclusion": report_text},
    ]
    if cancer:
        resources.append({"resourceType": "Condition", "id": "X01-dg1", "subject": {"reference": "Patient/X01"},
                          "category": [{"text": "Onkologická diagnóza"}], "code": {"text": "Zhoubný novotvar plic"}})
    return resources


@pytest.mark.parametrize("size, category", [("5", "2"), ("7", "3"), ("12", "4A"), ("18", "4B")])
def test_fictional_screening_nodule_gets_lung_rads_category(size, category):
    lung_rads, fleischner = evaluate_scales(_screening_patient(f"Solidní uzel v pravém horním laloku {size} mm."))
    assert lung_rads["applicable"] and lung_rads["category"] == category
    assert lung_rads["patient_citations"] == ["X01-img01"]
    assert not fleischner["applicable"] and "Lung-RADS" in fleischner["reason"]       # screening ≠ Fleischner


def test_incidental_nodule_without_cancer_is_fleischner_but_not_yet_scored():
    resources = _screening_patient("Náhodně zjištěný uzel 6 mm.")
    resources[1]["code"]["text"] = "CT hrudníku s k. l. – bolest na hrudi"
    lung_rads, fleischner = evaluate_scales(resources)
    assert not lung_rads["applicable"]
    assert fleischner["applicable"] and fleischner["category"] is None and "nelze posoudit" in fleischner["reason"]
    young = evaluate_scales([{**resources[0], "extension": [{"url": "x/vek-k-datu-mdt", "valueInteger": 30}]}, resources[1]])
    assert not young[1]["applicable"] and "35" in young[1]["reason"]
