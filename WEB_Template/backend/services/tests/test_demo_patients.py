"""Demo pacienti P13–P32 (`data/demo_pacienti`): projdou ingestem, kontrolou úplnosti i podkladem a nominace
založí komise v listopadu 2026 (T-347)."""
from datetime import datetime

import pytest

from services.ai.brief import build_brief
from services.ai_service import MockAIProvider, is_synthetic_patient
from services.fhir import ingest
from services.mdt_seed import board_title, nominations
from services.rules.intake import intake_prefill

DEMO = ingest.demo_dataset_dir()
pytestmark = pytest.mark.skipif(DEMO is None, reason="data/demo_pacienti není k dispozici")
PATIENTS = ingest.patient_ids(DEMO) if DEMO else []


def resources(pid: str) -> list[dict]:
    return ingest.load_patient(DEMO, pid)


def test_cohort_ids_follow_dataset_conventions():
    assert PATIENTS == [f"P{n}" for n in range(13, 33)]
    report = ingest.collect(DEMO, include_shared=False)
    assert not report.warnings                              # ID podle services/fhir/ids.py, nic se neztratí
    assert all(is_synthetic_patient(part.resources) for part in report.parts)     # D-021: tag fiktivni-data


def test_nominations_make_committees_in_november():
    requests = [r for pid in PATIENTS for r in resources(pid) if r["resourceType"] == "ServiceRequest"]
    tasks = [r for pid in PATIENTS for r in resources(pid) if r["resourceType"] == "Task"]
    found = nominations(requests, tasks)
    assert len(found) == len(PATIENTS)
    boards = {(n["date"], n["title"]) for n in found}
    assert len(boards) == 9 and len({title for _, title in boards}) == 6
    assert all(n["date"].month == 11 and n["date"].utcoffset().total_seconds() == 3600 for n in found)   # zimní čas
    # stejná komise jako u datasetu (P03, P04) = stejný název boardu
    assert "GIT – kolorektální karcinom / hepatobiliární" in {board_title(r) for r in requests}
    assert min(n["date"] for n in found) == datetime.fromisoformat("2026-11-03T14:00:00+01:00")


@pytest.mark.parametrize("pid", PATIENTS)
def test_patient_prefill_and_brief(pid):
    data = resources(pid)
    prefill = intake_prefill(data)
    status = {f["id"]: f["status"] for f in prefill["fields"]}
    assert status["mdt.question"] == "present" and status["dx.histology"] == "present"
    assert status["treatment.history"] == "present"         # i „žádná“ je údaj z nominace
    brief = build_brief(pid, data, provider=MockAIProvider(), case_id="1")
    assert brief["header"]["display_name"].startswith(f"{pid} · ")
    assert brief["header"]["mdt_question"]["text"]


def test_some_patients_have_gaps_and_new_results():
    """Část kohorty má záměrně mezery (doplnit / přeskočit / do úkolů) a výsledky po nominaci (kontrola)."""
    missing_patient_ecog = [pid for pid in PATIENTS
                            if {f["id"]: f["status"] for f in intake_prefill(resources(pid))["fields"]}
                            ["ecog.patient"] == "missing"]
    assert set(missing_patient_ecog) == {"P15", "P27", "P32"}
    nominated = "2026-10-15"
    late = {pid for pid in PATIENTS for r in resources(pid)
            if (r.get("effectiveDateTime") or "")[:10] > nominated and r["resourceType"] in ("Observation", "DiagnosticReport")}
    assert late == {"P14", "P17", "P19", "P23", "P27", "P30"}
