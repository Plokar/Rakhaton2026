"""Testy kontroly úplnosti při zařazení pacienta (T-502, ARCHITEKTURA §5.10, kontrakt §8.6)."""
import pytest

from services.ai.context_builder import context_from_resources
from services.rules.intake import intake_prefill
from services.rules.onko_kb import ext_ids
from services.tests.dataset import load_patient, load_studies

PATIENTS = ["P01", "P02", "P03", "P04", "P05", "P06"]
FIELD_STATUS = {"present", "missing", "pending", "skipped"}
WARNING_KIND = {"missing", "out_of_range", "conflict", "ai_uncertain"}


@pytest.fixture(scope="module")
def prefills():
    return {pid: intake_prefill(load_patient(pid)) for pid in PATIENTS}


def fields(prefill):
    return {f["id"]: f for f in prefill["fields"]}


def warning_ids(prefill, kind=None):
    return [w["id"] for w in prefill["warnings"] if kind is None or w["kind"] == kind]


# ── DoD: P03 a P04 ────────────────────────────────────────────────────────────
def test_p03(prefills):
    p03 = prefills["P03"]
    f = fields(p03)
    assert f["bm.mmr"]["status"] == "missing" and f["bm.mmr"]["citation"] == "P03-bm04"
    assert f["staging.chest_ct"]["status"] == "missing" and f["staging.chest_ct"]["citation"] == "P03-img01"
    assert "RF-MISSING:P03-bm04" in warning_ids(p03, "missing")                 # chybí MMR
    assert "RF-STALE:hrudnik" in warning_ids(p03, "missing")                    # chybí CT hrudníku
    assert "RF-TOX:P03-neuro01" in warning_ids(p03, "conflict")                 # rozpor neuropatie
    uncertain = [w for w in p03["warnings"] if w["kind"] == "ai_uncertain"]
    assert uncertain and "ECOG 0–1" in uncertain[0]["title"]                    # nejistota „ECOG 0–1“
    assert uncertain[0]["citations"] == ["P03-doc06#2", "P03-ecog02"]
    assert f["liver.flr"]["value"].endswith("38 % celkového objemu jater.")
    assert f["treatment.bevacizumab"]["value"] == "2026-09-07"
    assert p03["ecog_physician"] == {"value": 0, "citation": "P03-ecog03"}
    assert p03["intent_prefill"] == "C"
    assert p03["service_request_id"] == "P03-zad01"


def test_p04(prefills):
    p04 = prefills["P04"]
    f = fields(p04)
    assert f["geri.g8"]["status"] == "missing"                                  # chybí G8
    assert f["spiro.vo2max"]["status"] == "missing"                             # chybí VO2max
    assert f["spiro.vo2max"]["citation"] == "P04-doc06#5"                       # „doporučena spiroergometrie“
    assert f["bm.egfr"]["status"] == "pending"
    assert "RF-GERI:P04" in warning_ids(p04, "missing")
    assert "missing:spiro.vo2max" in warning_ids(p04, "missing")
    assert "missing:geri.g8" not in warning_ids(p04)                            # bez duplicity s RF-GERI
    assert "intent_prefill" not in p04                                          # minulá MDT: odloženo


def test_other_patients(prefills):
    assert fields(prefills["P06"])["lvef"]["status"] == "present"              # HER2+ (3+ v primárním nádoru)
    assert "bm.esr1" not in fields(prefills["P06"])
    assert fields(prefills["P05"])["comorbidities"]["citation"] == "P05-zad01#4"    # „bez chronických onemocnění“
    assert fields(prefills["P01"])["bm.gbrca"]["status"] == "missing"
    assert [prefills[p]["intent_prefill"] for p in ("P01", "P02", "P05", "P06")] == ["P", "P", "P", "P"]


# ── Přeskočení (FR-P4, D-019) ─────────────────────────────────────────────────
def test_skipped_fields_silence_their_warnings():
    prefill = intake_prefill(load_patient("P03"), skipped_fields=["bm.mmr", "staging.chest_ct"])
    f = fields(prefill)
    assert f["bm.mmr"]["status"] == "skipped" and f["staging.chest_ct"]["status"] == "skipped"
    ids = warning_ids(prefill)
    assert "RF-MISSING:P03-bm04" not in ids and "RF-STALE:hrudnik" not in ids
    assert "RF-TOX:P03-neuro01" in ids                                          # ostatní varování zůstávají


def test_question_cannot_be_skipped():
    prefill = intake_prefill(load_patient("P03"), skipped_fields=["mdt.question"])
    assert fields(prefill)["mdt.question"]["status"] == "present"


def test_skip_g8_silences_rf_geri():
    prefill = intake_prefill(load_patient("P04"), skipped_fields=["geri.g8"])
    assert fields(prefill)["geri.g8"]["status"] == "skipped"
    assert "RF-GERI:P04" not in warning_ids(prefill)


def test_warning_ids_match_red_flags(prefills):
    """Varování z red flags má id flagu: odkliknutí jde spárovat a flag v podkladu zůstane (D-019)."""
    from services.rules.red_flags import evaluate
    flag_ids = {f.id for f in evaluate(load_patient("P03")) if f.rule != "RF-PRIOR-PROC"}   # info do hlavičky
    assert flag_ids <= set(warning_ids(prefills["P03"]))


# ── Kontrakt §8.6 a citace ────────────────────────────────────────────────────
@pytest.mark.parametrize("patient_id", PATIENTS)
def test_contract_and_citations(patient_id, prefills):
    prefill = prefills[patient_id]
    ctx = context_from_resources(patient_id, load_patient(patient_id), studies=load_studies())
    allowed = ctx.allowed_ids | {f"{s}-{n}" for s in ("KRC", "PRS", "PLI", "OBC") for n in
                                 ("1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4", "2.5",
                                  "3.1", "3.2", "3.3", "3.4", "4.1", "4.2")} | ext_ids()   # EXT jen z katalogu (T-504)
    assert prefill["patient_id"] == patient_id
    ids = [f["id"] for f in prefill["fields"]]
    assert len(ids) == len(set(ids))
    for f in prefill["fields"]:
        assert f["status"] in FIELD_STATUS and f["label"]
        assert "citation" not in f or f["citation"] in ctx.allowed_ids, f
        assert f["status"] != "present" or "citation" in f, f
    warning_list = [w["id"] for w in prefill["warnings"]]
    assert len(warning_list) == len(set(warning_list))
    for w in prefill["warnings"]:
        assert w["kind"] in WARNING_KIND and w["severity"] in {"high", "moderate", "low"}
        assert w["citations"] and set(w["citations"]) <= allowed, w
