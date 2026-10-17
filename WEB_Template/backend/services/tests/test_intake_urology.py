"""Pole kontroly úplnosti pro prostatu (C61) a ledvinu (C64, D41.0) podle POZADAVKY §4.5–4.6 (T-513)."""
import base64

from services.rules.intake import intake_prefill
from services.rules.readiness import evaluate_readiness
from services.tests.dataset import load_patient

ICD10 = "http://hl7.org/fhir/sid/icd-10"


def _prostate(*, metastatic: bool, crpc: bool = False) -> list[dict]:
    """Syntetický pacient s karcinomem prostaty (dataset prostatu nemá)."""
    text = "Histopatologie: acinární adenokarcinom prostaty, Gleason 4+3=7, ISUP GG 3."
    if crpc:
        text += " Progrese PSA při kastrační hladině testosteronu: mCRPC."
    resources = [
        {"resourceType": "Patient", "id": "P90", "gender": "male",
         "extension": [{"url": "https://rakathon.example.org/fhir/StructureDefinition/vek-k-datu-mdt", "valueInteger": 71}]},
        {"resourceType": "Condition", "id": "P90-dg1", "category": [{"text": "onkologická diagnóza"}],
         "code": {"coding": [{"system": ICD10, "code": "C61"}], "text": "Zhoubný novotvar prostaty"},
         "subject": {"reference": "Patient/P90"}},
        {"resourceType": "ServiceRequest", "id": "P90-zad01", "subject": {"reference": "Patient/P90"},
         "reasonCode": [{"text": "Další léčba?"}]},
        {"resourceType": "Observation", "id": "P90-lab01-psa", "status": "final", "subject": {"reference": "Patient/P90"},
         "effectiveDateTime": "2026-10-01", "code": {"text": "PSA"}, "valueQuantity": {"value": 14.2, "unit": "ng/ml"}},
        {"resourceType": "DiagnosticReport", "id": "P90-pat01", "status": "final", "subject": {"reference": "Patient/P90"},
         "code": {"text": "Histopatologie – biopsie prostaty"},
         "presentedForm": [{"contentType": "text/plain", "data": base64.b64encode(text.encode()).decode()}]},
    ]
    if metastatic:
        resources.append({"resourceType": "Condition", "id": "P90-dg2", "category": [{"text": "onkologická diagnóza"}],
                          "code": {"coding": [{"system": ICD10, "code": "C79.5"}], "text": "Kostní metastázy"},
                          "subject": {"reference": "Patient/P90"}})
    return resources


def _fields(resources) -> dict:
    return {f["id"]: f for f in intake_prefill(resources)["fields"]}


def test_localized_prostate_fields():
    f = _fields(_prostate(metastatic=False))
    assert f["lab.psa"]["status"] == "present" and f["lab.psa"]["citation"] == "P90-lab01-psa"
    assert f["dx.isup"]["status"] == "present" and f["dx.isup"]["citation"] == "P90-pat01#1"
    assert f["staging.prostate_mr"]["status"] == "missing"
    assert {f[k]["required_by"] for k in ("lab.psa", "dx.isup", "staging.prostate_mr")} == {"EXT-EAU-PROSTATE-2025"}
    assert "lab.testosterone" not in f and "bm.hrr" not in f


def test_metastatic_crpc_prostate_fields():
    f = _fields(_prostate(metastatic=True, crpc=True))
    assert "staging.prostate_mr" not in f
    assert f["lab.testosterone"]["status"] == "missing"
    assert f["bm.hrr"]["status"] == "missing" and f["bm.mmr"]["status"] == "missing"
    assert "bm.hrr" not in _fields(_prostate(metastatic=True))          # hormonálně senzitivní: bez HRR / MMR


def test_prostate_items_not_duplicated_by_knowledge_base():
    warnings = {w["id"] for w in intake_prefill(_prostate(metastatic=False))["warnings"]}
    assert "missing:staging.prostate_mr" in warnings
    assert not warnings & {"CHYBI:pro.mri", "CHYBI:pro.psa", "CHYBI:pro.isup"}


def test_p06_gets_kidney_fields():
    """D41.0 = nádor ledviny nejistého chování: histologie chybí a cituje neověřenou diagnózu."""
    resources = load_patient("P06")
    f = _fields(resources)
    assert f["dx.renal_histology"]["status"] == "missing" and f["dx.renal_histology"]["citation"] == "P06-dg3"
    assert f["lab.egfr"]["status"] == "present" and f["staging.renal_ct"]["citation"] == "P06-img05"
    assert f["dx.renal_histology"]["required_by"] == "EXT-EAU-RCC-2025"
    assert "dx.renal_histology" not in {x["id"] for x in evaluate_readiness(resources)["unresolved"]}   # readiness beze změny


def test_dataset_patients_without_urology_keep_their_fields():
    for pid in ("P01", "P03", "P04"):
        ids = set(_fields(load_patient(pid)))
        assert not ids & {"lab.psa", "dx.isup", "dx.renal_histology", "lab.egfr"}, pid
