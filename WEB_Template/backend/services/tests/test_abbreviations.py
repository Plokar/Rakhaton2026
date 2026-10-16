"""Testy výkladu zkratek a NEJISTOTY AI (T-509, FR-R5, docs/POZADAVKY_LEKARE.md §7.2)."""
import pytest

from services.ai.abbreviations import (
    interpret, load_rules, prompt_rules, scan_resources, scan_text, uncertainty_warnings,
)
from services.tests.dataset import load_patient

PATIENTS = ["P01", "P02", "P03", "P04", "P05", "P06"]


@pytest.fixture(scope="module")
def dataset():
    return {item.evidence_id + ":" + item.abbreviation: item
            for pid in PATIENTS for item in scan_resources(load_patient(pid))}


def meaning_at(dataset, evidence_id, abbreviation):
    matches = [i for key, i in dataset.items() if key == f"{evidence_id}:{abbreviation}"]
    assert matches, f"{abbreviation} v {evidence_id} nenalezeno"
    return matches[0].meaning


# ── Tabulka §7.2 na skutečných textech datasetu ───────────────────────────────
@pytest.mark.parametrize("evidence_id, abbreviation, meaning", [
    ("P03-pat01#3", "G2", "grade nádoru"),                          # „středně diferencovaný (G2)“
    ("P02-pat01#2", "G3", "grade nádoru"),                          # Nottingham skóre 8 (G3)
    ("P01-doc03#4", "G3", "stupeň toxicity (CTCAE)"),               # neutropenie G3
    ("P01-doc01#8", "G2", "stupeň toxicity (CTCAE)"),               # artralgie G2
    ("P06-doc05#6", "G3a", "stadium chronického onemocnění ledvin (CKD)"),
    ("P01-pat01#5", "PR", "progesteronový receptor"),
    ("P06-img02#8", "LDL", "levý dolní plicní lalok"),
    ("P03-doc02#3", "OA", "osobní anamnéza"),
    ("P03-doc02#6", "RA", "rodinná anamnéza"),
    ("P02-doc01#2", "PAD", "perorální antidiabetika"),
    ("P06-doc05#3", "CMP", "cévní mozková příhoda"),
    ("P03-img02#2", "S3", "jaterní segment"),
    ("P02-img02#3", "S3", "plicní segment"),
    ("P03-img04#2", "S3", "jaterní segment"),                       # bez slova v odstavci → název „MR jater“
    ("P03-zad01#1", "S3", "jaterní segment"),                       # zaměření komise hepatobiliární
    ("P02-doc07#8", "PH", "pertuzumab + trastuzumab"),
])
def test_dataset_examples(dataset, evidence_id, abbreviation, meaning):
    assert meaning_at(dataset, evidence_id, abbreviation) == meaning


def test_no_uncertain_abbreviation_in_dataset(dataset):
    assert [k for k, i in dataset.items() if i.uncertain] == []


# ── Druhé významy a nejistota (syntetické texty) ──────────────────────────────
@pytest.mark.parametrize("text, abbreviation, meaning", [
    ("Restaging: parciální odpověď, PR dle RECIST 1.1.", "PR", "parciální odpověď (RECIST)"),
    ("Na CT nové ložisko v játrech, PD dle RECIST.", "PD", "progrese (RECIST)"),
    ("LDL cholesterol 3,2 mmol/l na atorvastatinu.", "LDL", "LDL cholesterol"),
    ("RTG hrudníku PA a bočný: bez ložisek.", "PA", "RTG projekce zezadu dopředu (posteroanteriorní)"),
    ("PA: úřednice, nyní v invalidním důchodu.", "PA", "pracovní anamnéza"),
    ("Echokardiografie: PH, PASP 45 mmHg.", "PH", "plicní hypertenze"),
    ("Dilatační CMP, LVEF 30 %.", "CMP", "kardiomyopatie"),
    ("Kloubní obtíže, OA kolen.", "OA", "osteoartróza"),
])
def test_other_meanings(text, abbreviation, meaning):
    assert interpret(abbreviation, text).meaning == meaning


@pytest.mark.parametrize("text, abbreviation", [
    ("Hodnoceno jako G2.", "G2"),                                   # bez kontextu
    ("PR.", "PR"),
    ("Receptory: PR, RECIST", "PR"),                                # dva výklady stejně blízko
])
def test_uncertain_without_context(text, abbreviation):
    result = interpret(abbreviation, text)
    assert result.uncertain and result.meaning is None and result.reason


def test_not_confused_with_longer_tokens():
    assert scan_text("CHOPN GOLD 2, PD-L1 TPS 60 %, PDL 12 mm") == []


def test_uncertainty_warning_shape():
    resource = {"resourceType": "DocumentReference", "id": "P99-doc01",
                "content": [{"attachment": {"data": "SG9kbm9jZW5vIGpha28gRzIu"}}]}   # „Hodnoceno jako G2.“
    warnings = uncertainty_warnings([resource])
    assert warnings == [{
        "id": "ai_uncertain:abbr-G2:P99-doc01#1", "kind": "ai_uncertain", "severity": "low",
        "title": "Nejednoznačná zkratka „G2“",
        "detail": "Kontext nestačí k jednoznačnému výkladu. AI zkratku nerozepisuje, výklad potvrdí lékař.",
        "citations": ["P99-doc01#1"],
    }]


def test_prompt_rules_cover_table():
    text = prompt_rules()
    for entry in load_rules()["ambiguous"].values():
        assert entry["pattern"] in text
    assert "nepřeváděj na jedno číslo" in text and "l. dx. = vpravo" in text
