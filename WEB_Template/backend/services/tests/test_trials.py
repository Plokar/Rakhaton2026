"""Screening studií: kritéria nad historií léčby z nominace (T-302, 2. kolo). Každý výsledek má citaci."""
import pytest

from services.rules.compatibility import Facts
from services.rules.trials import evaluate_criterion
from services.tests.dataset import load_patient


@pytest.fixture(scope="module")
def facts():
    return {pid: Facts(load_patient(pid)) for pid in ("P01", "P02", "P04", "P05", "P06")}


@pytest.mark.parametrize("pid, criterion, status, citation", [
    # předchozí fulvestrant / SERD: P05 ho měla ve 2. linii, P01 ne (seznam linií v nominaci)
    ("P05", "RKT-01/V4", "met", "P05-zad01#3"),
    ("P01", "RKT-01/V4", "not_met", "P01-zad01#3"),
    # progrese po AI + CDK4/6: P05 má po letrozolu + palbociklibu další linie, P01 progresi na CT po zahájení
    ("P05", "RKT-01/Z3", "met", "P05-zad01#3"),
    ("P01", "RKT-01/Z3", "met", "P01-zad01#3"),
    # nejvýše 1 linie chemoterapie v M1: P01 jen adjuvance, P05 paklitaxel ve 3. linii
    ("P01", "RKT-01/Z4", "met", "P01-zad01#3"),
    ("P05", "RKT-01/Z4", "met", "P05-zad01#3"),
    # progrese po trastuzumabu a taxanu: nové mozkové metastázy (diagnóza) po zahájení léčby
    ("P02", "RKT-02/Z2", "met", "P02-dg3"),
    # předchozí T-DXd: v historii není (v otázce nominace je jen jako možnost)
    ("P02", "RKT-02/V2", "not_met", "P02-zad01#3"),
    ("P06", "RKT-02/V2", "not_met", "P06-zad01#3"),
    # ILD: CT výslovně „bez známek pneumonitidy“
    ("P02", "RKT-02/V1", "not_met", "P02-img06#4"),
    # neléčené mozkové metastázy: v historii ani výkonech není RT / SRS / operace mozku
    ("P02", "RKT-06/V3", "met", "P02-zad01#3"),
    # předchozí PARP inhibitor: P01 ne (historie), P05 je ve studii (není to předchozí léčba)
    ("P01", "RKT-06/V1", "not_met", "P01-zad01#3"),
    ("P05", "RKT-06/V1", "not_met", None),
])
def test_history_based_criteria(facts, pid, criterion, status, citation):
    result = evaluate_criterion(criterion, facts[pid])
    assert result.status == status, result
    assert result.citations, result                     # žádný výsledek bez citace (AGENTS.md)
    assert citation is None or citation in result.citations, result


def test_without_history_stays_unknown(facts):
    """P04 nemá v nominaci předchozí léčbu: o předchozích lécích se nic neusuzuje."""
    for criterion in ("RKT-01/V4", "RKT-01/Z4"):
        assert evaluate_criterion(criterion, facts["P04"]).status == "unknown"


def test_negated_progression_is_not_progression(facts):
    """„Bez nových ložisek“ ani „nezvětšené uzliny“ nejsou progrese."""
    from services.rules.trials import PROGRESSION, _affirmed
    assert not _affirmed("Břicho a skelet: bez nových ložisek.", PROGRESSION)
    assert not _affirmed("Ostatní uzliny nezvětšené.", PROGRESSION)
    assert _affirmed("Nově 2 ložiska v játrech.", PROGRESSION)
