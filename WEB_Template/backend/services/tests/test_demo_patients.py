"""Demo pacienti P13–P172 (`data/demo_pacienti`): projdou ingestem, kontrolou úplnosti i podkladem a nominace
založí 10 komisí s 36 zasedáními od 3. 11. do 18. 12. 2026 (T-347, T-351, T-355)."""
from collections import Counter
from datetime import datetime

import pytest

from services.ai.brief import build_brief
from services.ai_service import MockAIProvider, is_synthetic_patient
from services.fhir import ingest
from services.mdt_seed import board_title, nominations
from services.rules.intake import intake_prefill
from services.rules.review import new_results, nomination_day

DEMO = ingest.demo_dataset_dir()
pytestmark = pytest.mark.skipif(DEMO is None, reason="data/demo_pacienti není k dispozici")
PATIENTS = ingest.patient_ids(DEMO) if DEMO else []


def resources(pid: str) -> list[dict]:
    return ingest.load_patient(DEMO, pid)


def test_cohort_ids_follow_dataset_conventions():
    assert PATIENTS == [f"P{n}" for n in range(13, 173)]
    report = ingest.collect(DEMO, include_shared=False)
    assert not report.warnings                              # ID podle services/fhir/ids.py, nic se neztratí
    assert all(is_synthetic_patient(part.resources) for part in report.parts)     # D-021: tag fiktivni-data


def test_nominations_make_committees_for_five_weeks():
    requests = [r for pid in PATIENTS for r in resources(pid) if r["resourceType"] == "ServiceRequest"]
    tasks = [r for pid in PATIENTS for r in resources(pid) if r["resourceType"] == "Task"]
    found = nominations(requests, tasks)
    assert len(found) == len(PATIENTS)
    boards = {(n["date"], n["title"]) for n in found}
    titles = {title for _, title in boards}
    assert len(boards) == 36 and len(titles) == 10
    assert {"Neuroonkologická komise", "Hematoonkologická komise", "Komise pro melanom a kožní nádory",
            "Komise pro sarkomy a GIST"} <= titles
    assert all(n["date"].month in (11, 12) and n["date"].utcoffset().total_seconds() == 3600 for n in found)   # zimní čas
    assert max(n["date"] for n in found) == datetime.fromisoformat("2026-12-18T14:00:00+01:00")
    # stejná komise jako u datasetu (P03, P04) = stejný název boardu
    assert "GIT – kolorektální karcinom / hepatobiliární" in {board_title(r) for r in requests}
    assert min(n["date"] for n in found) == datetime.fromisoformat("2026-11-03T14:00:00+01:00")
    # T-355: každé zasedání od 10. 11. má 4–8 případů
    per_board = Counter((n["date"], n["title"]) for n in found)
    assert all(4 <= k <= 8 for (day, _), k in per_board.items() if day >= datetime.fromisoformat("2026-11-10T00:00:00+01:00"))


@pytest.mark.parametrize("pid", PATIENTS)
def test_patient_prefill_and_brief(pid):
    data = resources(pid)
    prefill = intake_prefill(data)
    status = {f["id"]: f["status"] for f in prefill["fields"]}
    assert status["mdt.question"] == "present" and status["dx.histology"] == "present"
    assert status["treatment.history"] == "present"         # i „žádná“ je údaj z nominace
    assert status["staging.imaging"] == "present"           # posun dat druhé vlny drží zobrazení ≤ 6 týdnů
    brief = build_brief(pid, data, provider=MockAIProvider(), case_id="1")
    assert brief["header"]["display_name"].startswith(f"{pid} · ")
    assert brief["header"]["mdt_question"]["text"]


def test_some_patients_have_gaps_and_new_results():
    """Část kohorty má záměrně mezery (doplnit / přeskočit / do úkolů) a výsledky po nominaci (kontrola)."""
    missing_patient_ecog = [pid for pid in PATIENTS
                            if {f["id"]: f["status"] for f in intake_prefill(resources(pid))["fields"]}
                            ["ecog.patient"] == "missing"]
    assert set(missing_patient_ecog) == {"P15", "P27", "P32", "P40", "P41", "P46", "P57", "P60", "P61", "P67", "P70",
                                         "P75", "P84", "P93", "P100", "P110", "P117", "P127", "P140", "P150", "P161"}
    late = {}
    for pid in PATIENTS:
        data = resources(pid)
        meeting = next(r for r in data if r["resourceType"] == "Task")["restriction"]["period"]["start"][:10]
        found = new_results(data, nomination_day(data, f"{pid}-zad01"))
        assert all(n["date"] < meeting for n in found), pid           # nic „nového“ až po zasedání
        if found:
            late[pid] = len(found)
    assert set(late) == {"P14", "P17", "P19", "P23", "P27", "P30", "P36", "P41", "P45", "P48", "P54", "P63", "P69",
                         "P74", "P86", "P95", "P107", "P119", "P131", "P137", "P143", "P149", "P170"}


def test_third_wave_gaps_and_fictional_identity():
    """T-355: bez preference a bez laboratoře u části třetí vlny; každý demo pacient má fiktivní jméno a RČ."""
    from services import rc

    def status(pid):
        return {f["id"]: f["status"] for f in intake_prefill(resources(pid))["fields"]}
    assert {pid for pid in PATIENTS[60:] if status(pid)["preferences"] == "missing"} == {"P77", "P99", "P115", "P124", "P146"}
    no_labs = {pid for pid in PATIENTS if not any(r["id"].startswith(f"{pid}-lab01-") and r["id"] != f"{pid}-lab01-na"
                                                  for r in resources(pid))}
    assert no_labs == {"P91", "P109", "P135", "P154", "P166"}
    seen = set()
    for pid in PATIENTS:
        patient = next(r for r in resources(pid) if r["resourceType"] == "Patient")
        assert patient["name"][0]["text"].endswith(" (fiktivní)")
        value = next(i["value"] for i in patient["identifier"] if i["system"].endswith("/rc-fiktivni"))
        parsed = rc.parse(value)                                   # formálně platné RČ
        assert parsed.gender == patient["gender"] and parsed.birth_date.isoformat() == patient["birthDate"]
        assert value.split("/")[1].startswith("99") and value not in seen     # vymyšlený rozsah, unikátní
        seen.add(value)
