"""Testy bloku B: pohledy odborníků a posouzení role (T-201, FR-B1 až FR-B7)."""
import time

import pytest

from apps.copilot import schemas
from services.ai.brief import build_brief
from services.ai.guidelines import parse_guidelines
from services.ai_service import MockAIProvider
from services.tests.dataset import load_guideline_markdowns, load_patient, load_studies

ROLES = ["surgeon", "oncologist", "radiologist", "pathologist", "radiation_oncologist", "patient"]


@pytest.fixture(scope="module")
def guidelines():
    return [p for md in load_guideline_markdowns().values() for p in parse_guidelines(md)]


def brief_for(patient_id, guidelines, provider=None, roles=ROLES):
    return build_brief(patient_id, load_patient(patient_id), studies=load_studies(), guidelines=guidelines,
                       provider=provider or MockAIProvider(), case_id="1", config={"roles_present": roles})


def role_sections(brief):
    return {s["role"]: s for s in brief["sections"] if s["id"] == "role_views"}


def test_p03_three_roles_with_verdict(guidelines):
    brief = brief_for("P03", guidelines, roles=["surgeon", "oncologist", "radiologist"])
    schemas.Brief.model_validate(brief)
    sections = role_sections(brief)
    assert list(sections) == ["surgeon", "oncologist", "radiologist"]
    for section in sections.values():
        assert section["assessment"]["verdict"] in {"candidate", "conditional", "not_candidate", "insufficient_data"}
        assert section["assessment"]["note"].startswith("Podklad pro diskusi, rozhoduje lékař")
        assert section["items"] and all(i["verification"] == "verified" for i in section["items"])
    surgeon = sections["surgeon"]["assessment"]
    assert surgeon["question"] == "Je pacient kandidátem resekce jaterních metastáz?"
    assert surgeon["verdict"] == "conditional"                       # semafor resekce 🟠
    assert {c.get("guideline") for c in surgeon["criteria"]} >= {"KRC-2.1", "KRC-2.4", "KRC-2.3"}
    assert brief["stats"]["claims_unverified"] == 0


def test_role_specific_content(guidelines):
    sections = role_sections(brief_for("P03", guidelines))
    patient = [i["text"] for i in sections["patient"]["items"]]
    assert any("brnění 6/10 (dříve 0/10)" in t for t in patient)
    assert any(t.startswith("Samostatnost (ECOG podle pacienta 1)") for t in patient)
    radiologist = sections["radiologist"]["assessment"]["criteria"]
    assert any(c["status"] == "unknown" and c.get("guideline") == "KRC-2.4" for c in radiologist)
    assert sections["radiation_oncologist"]["items"][0]["kind"] == "missing"
    assert "assessment" not in sections["pathologist"]                # bez otázky posouzení
    oncologist = [i["text"] for i in sections["oncologist"]["items"]]
    assert any("MMR / MSI: nevyšetřeno" in t for t in oncologist)
    assert all("zdroj:" not in t for t in oncologist)


def test_radiologist_section_includes_cited_recist_for_p03(guidelines):
    radiologist = role_sections(brief_for("P03", guidelines, roles=["radiologist"]))["radiologist"]
    recist = next(item for item in radiologist["items"] if item["id"] == "radiologist-recist")
    assert "83 → 50 mm" in recist["text"] and "PR" in recist["text"]
    assert recist["citations"] == ["P03-img01", "P03-img03"]
    assert recist["verification"] == "verified"


@pytest.mark.parametrize("patient_id", ["P01", "P05"])
def test_supportive_care_does_not_make_oncology_candidate(guidelines, patient_id):
    oncologist = role_sections(brief_for(patient_id, guidelines))["oncologist"]["assessment"]
    assert oncologist["verdict"] == "conditional"
    assert not any("zoledronov" in c["text"] for c in oncologist["criteria"])


LLM_ROLE = {
    "items": [{"text": "FLR levého laloku odhadem 38 % celkového objemu jater.", "citations": ["P03-img04#3"]},
              {"text": "FLR 45 %.", "citations": ["P03-img04#3"]}],
    "assessment": {
        "question": "x", "verdict": "conditional",
        "criteria": [
            {"text": "FLR ≥ 40 % po intenzivní chemoterapii", "status": "not_met", "citations": ["P03-img04#3"],
             "guideline": "KRC-2.1"},
            {"text": "R0 resekce dosažitelná", "status": "met", "citations": ["P03-img99"], "guideline": "PRS-1.1"},
        ],
    },
}


def test_llm_role_output_is_sanitized(guidelines):
    provider = MockAIProvider(responses={"RoleViewOutput": LLM_ROLE})
    surgeon = role_sections(brief_for("P03", guidelines, provider, roles=["surgeon"]))["surgeon"]
    assert [i["verification"] for i in surgeon["items"]] == ["verified", "unverified"]   # 45 % ve zdroji není
    assessment = surgeon["assessment"]
    assert assessment["question"] == "Je pacient kandidátem resekce jaterních metastáz?"   # otázka ze systému
    first, second = assessment["criteria"]
    assert (first["status"], first["guideline"]) == ("not_met", "KRC-2.1")
    assert second["status"] == "unknown" and second["citations"] == [] and "guideline" not in second
    assert "ověřit" in second["missing"]


class SlowProvider(MockAIProvider):
    def generate(self, *args, **kwargs):
        time.sleep(0.3)
        return super().generate(*args, **kwargs)


def test_sections_generated_in_parallel(guidelines):
    started = time.monotonic()
    brief_for("P03", guidelines, SlowProvider())                   # 8 volání LLM po 0,3 s
    assert time.monotonic() - started < 1.5


def test_radiologist_recist_new_lesion_from_llm_is_pd(guidelines):
    """P02: extrakraniálně nadir, ale nové mozkové metastázy (P02-img05) = PD (dev GT)."""
    provider = MockAIProvider(responses={"SldExtraction": {
        "measurements": [], "new_lesions": [{"citation": "P02-img05", "description": "2 metastázy mozku"}]}})
    radiologist = role_sections(brief_for("P02", guidelines, provider, roles=["radiologist"]))["radiologist"]
    recist = next(item for item in radiologist["items"] if item["id"] == "radiologist-recist")
    assert "odpověď PD (nová léze: P02-img05)" in recist["text"]
    assert "P02-img05" in recist["citations"] and recist["verification"] == "verified"
