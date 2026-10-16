"""mCODE v exportu (BON-5, T-307): profily a kódy LOINC jen v kopii, data se nemění."""
from services.fhir.mcode import LOINC, MCODE, apply_profiles
from services.tests.dataset import load_patient


def _by_id(pid):
    return {r["id"]: r for r in load_patient(pid)}


def test_p03_profiles_and_codes():
    r = _by_id("P03")
    assert apply_profiles(r["P03"])["meta"]["profile"] == [f"{MCODE}/mcode-cancer-patient"]
    assert apply_profiles(r["P03-dg1"])["meta"]["profile"] == [f"{MCODE}/mcode-primary-cancer-condition"]
    assert apply_profiles(r["P03-dg2"])["meta"]["profile"] == [f"{MCODE}/mcode-secondary-cancer-condition"]   # C78.7
    tnm = apply_profiles(r["P03-tnm01"])
    assert f"{MCODE}/mcode-tnm-stage-group" in tnm["meta"]["profile"]
    assert {"system": LOINC, "code": "21908-9", "display": "Stage group.clinical Cancer"} in tnm["code"]["coding"]
    assert tnm["valueString"] == r["P03-tnm01"]["valueString"]                          # text zůstává
    assert "meta" not in r["P03-tnm01"] or "profile" not in r["P03-tnm01"]["meta"]       # originál beze změny
    assert apply_profiles(r["P03-ecog03"])["meta"]["profile"] == [f"{MCODE}/mcode-ecog-performance-status"]
    assert apply_profiles(r["P03-bm01"])["meta"]["profile"] == [f"{MCODE}/mcode-tumor-marker-test"]          # KRAS bez kódu


def test_breast_markers_and_pathological_stage():
    r = _by_id("P01")
    codes = {rid: [c["code"] for c in apply_profiles(r[rid])["code"].get("coding", [])] for rid in ("P01-bm01", "P01-bm02", "P01-bm03")}
    assert codes == {"P01-bm01": ["16112-5"], "P01-bm02": ["16113-3"], "P01-bm03": ["48676-1"]}
    assert "21902-2" in [c["code"] for c in apply_profiles(r["P01-tnm01"])["code"]["coding"]]       # pT2 pN1a
    assert apply_profiles(r["P01-pat01"]) == r["P01-pat01"]                                           # mimo mCODE beze změny
