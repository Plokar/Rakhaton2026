"""Kontrola před zasedáním (T-349, services/rules/review.py) nad demo pacienty s výsledky po zařazení."""
from datetime import datetime, timedelta, timezone

import pytest

from services.fhir import ingest
from services.rules.review import new_results, review_state

DEMO = ingest.demo_dataset_dir()
pytestmark = pytest.mark.skipif(DEMO is None, reason="data/demo_pacienti není k dispozici")
CET = timezone(timedelta(hours=1))
MEETING = datetime(2026, 11, 4, 14, 0, tzinfo=CET)
CREATED = datetime(2026, 10, 20, 9, 0, tzinfo=CET)


def state(pid: str, now: datetime, checked_at=None, **kw):
    return review_state(ingest.load_patient(DEMO, pid), service_request_id=f"{pid}-zad01", meeting=MEETING,
                        now=now, created=CREATED, checked_at=checked_at, **kw)


def test_new_results_since_nomination():
    found = state("P19", MEETING - timedelta(hours=30))["new_results"]
    assert [(n["citation"], n["date"], n["value"]) for n in found] == [("P19-lvef01", "2026-10-28", "48 %")]
    assert found[0]["label"] == "LVEF (echokardiografie)" and found[0]["unseen"] is True
    p17 = state("P17", MEETING - timedelta(hours=30))["new_results"]
    assert p17[0]["label"].startswith("BRCA1") and "c.5266dupC" in p17[0]["value"]


def test_status_window_check_and_missed():
    assert state("P19", MEETING - timedelta(hours=72))["status"] == "upcoming"
    due = state("P19", MEETING - timedelta(hours=30))
    assert (due["status"], due["unseen_count"], due["since"]) == ("due", 1, "2026-10-15")
    checked = state("P19", MEETING - timedelta(hours=20), checked_at=MEETING - timedelta(hours=24))
    assert (checked["status"], checked["unseen_count"]) == ("checked", 0)
    assert state("P19", MEETING + timedelta(minutes=5))["status"] == "missed"
    assert state("P18", MEETING - timedelta(hours=1), session_status="in_progress")["status"] == "missed"
    # bez nových výsledků se kontrola potvrzuje taky (lékař může chtít něco doplnit)
    assert state("P18", MEETING - timedelta(hours=10))["status"] == "due"


def test_result_after_check_reopens_review():
    checked_before = datetime(2026, 10, 25, 12, 0, tzinfo=CET)          # LVEF přišla 28. 10.
    s = state("P19", MEETING - timedelta(hours=10), checked_at=checked_before)
    assert (s["status"], s["unseen_count"]) == ("due", 1)


def test_app_written_resources_are_not_new_results():
    resources = ingest.load_patient(DEMO, "P18") + [
        {"resourceType": "Observation", "id": "P18-ecog-case07", "effectiveDateTime": "2026-10-30", "code": {"text": "ECOG"}},
        {"resourceType": "DocumentReference", "id": "P18-imp01", "date": "2026-10-30", "type": {"text": "Vložená zpráva"}},
        {"resourceType": "Composition", "id": "P18-mdt01", "date": "2026-10-30"},
    ]
    assert new_results(resources, datetime(2026, 10, 15).date()) == []
