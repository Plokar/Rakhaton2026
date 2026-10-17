"""T-332: Q&A nad případem, míra jistoty citací, vypnutá pravidla red flags (bez IRIS, dataset P03)."""
import pytest

from services.ai.brief import build_brief
from services.ai.case_qa import NOT_FOUND, answer_question
from services.ai.grounding import verify_claims
from services.ai_service import MockAIProvider
from services.rules import red_flags
from services.tests.dataset import load_patient, load_studies


@pytest.fixture(autouse=True)
def indexed_grounding_vectors(grounding_vectors):
    """Grounding proti stejným in-memory vektorům jako IRIS."""


def _log(calls):
    return lambda purpose, result: calls.append(purpose)


def test_qa_search_without_llm_cites_documentation():
    """Bez LLM (mock) odpoví vyhledáním: řádky dokumentace doslova, s citací a datem."""
    out = answer_question("P03", "Jaký je výsledek CEA?", load_patient("P03"), MockAIProvider(), _log([]))
    assert out["mode"] == "search" and out["items"]
    assert all(i["kind"] == "claim" and i["citations"] for i in out["items"])
    assert any("CEA" in i["text"] for i in out["items"])


def test_qa_llm_answer_is_grounded_and_logged():
    calls = []
    provider = MockAIProvider({"QaOutput": {"found": True, "items": [
        {"text": "CEA 13,9 µg/l.", "citations": ["P03-lab06-cea"]},
        {"text": "Věta s vymyšlenou citací.", "citations": ["P99-neexistuje"]},
    ]}})
    out = answer_question("P03", "Kolik je CEA?", load_patient("P03"), provider, _log(calls))
    assert out["mode"] == "ai" and calls == ["case.qa"]
    assert out["items"][0]["verification"] == "verified"
    assert out["items"][1]["verification"] == "unverified"           # neznámé ID neprojde groundingem


def test_qa_not_found_is_explicit():
    provider = MockAIProvider({"QaOutput": {"found": False, "items": []}})
    out = answer_question("P03", "Jaká je krevní skupina?", load_patient("P03"), provider, _log([]))
    assert out["items"][0]["kind"] == "missing" and out["items"][0]["text"] == NOT_FOUND


def test_confidence_from_semantic_grounding(monkeypatch):
    from services.ai.context_builder import context_from_resources
    from services.iris import vector_store

    context = context_from_resources("P03", load_patient("P03"), studies=load_studies())
    monkeypatch.setattr(vector_store, "similarity", lambda text, citations: {citations[0]: 0.8134})
    claim = {"kind": "claim", "text": "CT hrudníku nebylo požadováno.", "citations": ["P03-img03"]}
    [result] = verify_claims([claim], context)
    assert result["verification"] == "verified" and result["confidence"] == 0.81
    [structured] = verify_claims([{"kind": "claim", "text": "CEA 13,9 µg/l", "citations": ["P03-lab06-cea"]}], context)
    assert "confidence" not in structured                       # strukturovaná data: jen čísla a data, bez jistoty


def test_disabled_rules_are_not_evaluated():
    resources = load_patient("P03")
    rules_all = {f.rule for f in red_flags.evaluate(resources)}
    assert "RF-TOX" in rules_all
    assert "RF-TOX" not in {f.rule for f in red_flags.evaluate(resources, disabled=["RF-TOX"])}
    brief = build_brief("P03", resources, studies=load_studies(), provider=MockAIProvider(), case_id="1",
                        config={"disabled_rules": ["RF-TOX", "RF-LLM"]})
    assert "RF-TOX" not in {f["rule"] for f in brief["red_flags"]}
    assert brief["config"]["disabled_rules"] == ["RF-TOX", "RF-LLM"]


def test_extra_roles_get_sections():
    """BONUS B: nukleární medicína, paliativní péče, geriatrie, genetika a koordinátor jako pohledy rolí."""
    extra = ["nuclear_medicine", "palliative_care", "geriatrician", "geneticist", "coordinator"]
    brief = build_brief("P05", load_patient("P05"), studies=load_studies(), provider=MockAIProvider(), case_id="1",
                        config={"roles_present": ["oncologist", *extra]})
    roles = {s["role"]: s for s in brief["sections"] if s["id"] == "role_views"}
    assert set(extra) <= set(roles)
    for role in extra:
        assert roles[role]["title"] and roles[role]["items"]            # tvrzení s citací, nebo „chybí“
        assert all(i["citations"] or i["kind"] == "missing" for i in roles[role]["items"])
    assert any(i["kind"] == "claim" for i in roles["palliative_care"]["items"])


def test_rule_catalog_covers_every_rule():
    resources = [load_patient(p) for p in ("P01", "P02", "P03", "P04", "P05", "P06")]
    seen = {f.rule for r in resources for f in red_flags.evaluate(r)}
    assert seen <= set(red_flags.RULE_CATALOG)
