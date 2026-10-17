"""Znalostní báze data/onko v semaforu (T-316): katalog beze změny, další postupy filtrované podle pacienta."""
import pytest

from services.rules import onko_kb
from services.rules.compatibility import evaluate_compatibility
from services.tests.dataset import load_patient

pytestmark = pytest.mark.skipif(onko_kb.q() is None, reason="data/onko není k dispozici")


def ids(pid):
    return {p["id"]: p for p in onko_kb.kb_for_patient(load_patient(pid))}


def test_catalog_procedures_untouched_and_not_duplicated():
    """DoD: P03/P04 mají v katalogu stejné barvy jako dřív; báze žádný katalogový postup nezdvojí."""
    for pid in ("P03", "P04"):
        catalog = {p["id"] for p in evaluate_compatibility(load_patient(pid))}
        assert catalog and not catalog & set(ids(pid))


def test_p03_kb_procedures_fit_the_patient():
    kb = ids("P03")
    assert {"krc-ablace", "krc-m-chemo-bev"} <= set(kb)                  # M1 kolorektum
    assert "krc-m-kras" not in kb and "krc-m-braf" not in kb             # KRAS G12D (ne G12C), BRAF wt
    assert "krc-kolektomie" not in kb and "krc-adj-capox" not in kb      # stadium I–III, ne M1
    assert "krc-m-her2" not in kb                                         # HER2 cesta jen u RAS wt
    assert "sup-genetika" in kb and "sup-fertilita" not in kb            # Lynch v rodině; věk 67


def test_p04_stage_and_histology_filters():
    kb = ids("P04")
    assert "pli-biopsie-tt" in kb                                         # ložisko nadledviny (PLI-1.2)
    assert not [p for p in kb if p.startswith("sclc-")]                   # adenokarcinom, ne SCLC
    assert "pli-segmentektomie" not in kb and "pli-sbrt" not in kb        # stadium I
    assert not [p for p in kb if p.startswith("pli-m-")]                  # cN2 M0, ne M1


def test_p06_her2_positive_has_no_tnbc():
    assert not [p for p in ids("P06") if "tnbc" in p]


def test_rules_have_sources_and_no_unverified_red():
    for pid in ("P01", "P02", "P03", "P04", "P05", "P06"):
        for p in onko_kb.kb_for_patient(load_patient(pid)):
            for r in p["compatibility"]["rules"]:
                assert r["rule_citation"], (pid, p["id"], r["rule_id"])
                if r["status"] == "red":
                    assert r["patient_citations"] and "práh k ověření" not in r["text"]


def test_facts_carry_citations():
    facts, cites = onko_kb.patient_facts(load_patient("P03"))
    assert facts["bm.kras"] == "mut" and facts["bm.ras"] == "mut" and facts["bm.mmr"] == "nezn"
    assert facts["ecog.diff"] == 1 and cites["ecog.diff"] == ["P03-ecog03", "P03-prom02"]
    assert all(cites[k] for k in ("dg", "age", "ecog.physician", "bm.kras", "lab.hb"))
