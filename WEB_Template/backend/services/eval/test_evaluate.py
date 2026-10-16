"""Eval proti ground truth (T-301): skóre nad podkladem z mocku (bez LLM, bez IRIS)."""
import pytest

from services.ai.brief import build_brief
from services.ai_service import MockAIProvider
from services.eval import ground_truth
from services.eval.evaluate import METRICS, report, score
from services.rules.intake import intake_prefill
from services.tests.dataset import load_patient, load_studies


@pytest.fixture(autouse=True)
def vectors(grounding_vectors):
    """Grounding v2 nad in-memory vektory."""


@pytest.mark.parametrize("pid", ["P03", "P05"])
def test_score_counts_match_ground_truth(pid):
    gt = ground_truth.load()[pid]
    resources = load_patient(pid)
    brief = build_brief(pid, resources, studies=load_studies(), provider=MockAIProvider(), case_id="eval")
    result = score(gt, brief, intake_prefill(resources))
    assert result["red_flags_all"][1] == len(gt.red_flags) and result["key_facts"][1] == len(gt.key_facts)
    assert result["red_flags_key"][0] >= 1 and result["missing_data"][0] >= 1     # pravidla bez LLM něco najdou
    assert result["unverified"][0] == 0                                            # mock: 0 neověřených tvrzení
    md = report([{**result, "seconds": 1.0}], "test")
    assert md.startswith("## test") and "**Celkem**" in md and all(label in md for _, label in METRICS)


def test_p03_recist_and_trials_scored():
    gt = ground_truth.load()["P03"]
    resources = load_patient("P03")
    brief = build_brief("P03", resources, studies=load_studies(), provider=MockAIProvider(), case_id="eval")
    result = score(gt, brief, intake_prefill(resources))
    assert result["recist"] == (1, 1)                                              # PR 83 → 50 mm
    assert result["trial_criteria"][1] > 0 and result["compatibility"][1] > 0
