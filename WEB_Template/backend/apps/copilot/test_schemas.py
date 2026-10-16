"""
Testy kontraktů (T-009, ARCHITEKTURA §8): pydantic schémata, fixtures P03 a Evidence ID.

Fixtures (``data/fixtures``) a dataset leží mimo backend. V CI jsou v checkoutu repa,
v backend kontejneru je jen dataset (``DATASET_DIR``); co chybí, test přeskočí.
Dataset se tu čte jen kvůli kontrole citací, za běhu se čte z IRIS.
"""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

import pytest

from apps.copilot import schemas
from apps.copilot.evidence import GUIDELINE_ID_RE, is_evidence_id, parse_evidence_id
from services.ai.text import resource_paragraphs
from services.ai_service import MockAIProvider, gemini_json_schema

# Kořen repa (v CI a lokálně); v backend kontejneru je jen /code, tam je None.
REPO_ROOT = next((p for p in Path(__file__).resolve().parents if (p / "WEB_Template").is_dir()), None)


def _dir(env: str, *relative: str) -> Path | None:
    if os.environ.get(env):
        return Path(os.environ[env])
    return REPO_ROOT.joinpath(*relative) if REPO_ROOT else None


FIXTURES_DIR = _dir("FIXTURES_DIR", "data", "fixtures")
FRONTEND_FIXTURES_DIR = _dir("FRONTEND_FIXTURES_DIR", "WEB_Template", "frontend", "src", "fixtures")
DATASET_DIR = _dir("DATASET_DIR", "Dataset_MDT_Copilot_v1.1_pre_timy", "Dataset_MDT_Copilot_v1.1")

FIXTURES = {
    "brief_P03.json": schemas.Brief,
    "decision_P03.json": schemas.Decision,
    "intake_P03.json": schemas.IntakePrefill,
}

# Klíče, jejichž hodnota je Evidence ID nebo seznam Evidence ID (ARCHITEKTURA §8).
EVIDENCE_KEYS = {
    "citation", "citations", "guideline", "guideline_citations", "rule_citation",
    "patient_citations", "inputs", "criterion_id", "required_by", "transcript_ref",
}
# Resources, které vzniknou až v aplikaci (zápis komise, BON-3), v datasetu nejsou.
APP_CREATED_RE = re.compile(r"^P\d{2}-mdt\d{2}-prepis$")

LIGHT_RANK = {"green": 0, "grey": 1, "orange": 2, "red": 3}   # 🔴 > 🟠 > ⚪ > 🟢 (§5.9)

needs_fixtures = pytest.mark.skipif(
    not (FIXTURES_DIR and FIXTURES_DIR.is_dir()), reason="chybí data/fixtures (backend kontejner je nevidí)",
)
needs_dataset = pytest.mark.skipif(not (DATASET_DIR and DATASET_DIR.is_dir()), reason="chybí DATASET_DIR")


def load_fixture(name: str):
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def evidence_ids(node, key: str | None = None):
    """Všechna Evidence ID ve fixture (podle jmen klíčů)."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from evidence_ids(v, k)
    elif isinstance(node, list):
        for item in node:
            yield from evidence_ids(item, key)
    elif isinstance(node, str) and key in EVIDENCE_KEYS:
        yield node


def all_strings(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from all_strings(v)
    elif isinstance(node, list):
        for item in node:
            yield from all_strings(item)
    elif isinstance(node, str):
        yield node


def sanitize_id(resource_id: str) -> str:
    return resource_id.replace("_", "-")   # DATASET §6.2


@lru_cache(maxsize=None)
def patient_resources(patient_id: str) -> dict[str, dict]:
    bundle = json.loads((DATASET_DIR / "pacienti" / patient_id / f"{patient_id}_bundle.json").read_text(encoding="utf-8"))
    return {sanitize_id(e["resource"]["id"]): e["resource"] for e in bundle["entry"]}


def paragraph_text(evidence_id: str) -> str | None:
    ref = parse_evidence_id(evidence_id)
    paragraphs = resource_paragraphs(patient_resources(ref.patient_id)[ref.resource_id])
    return paragraphs[ref.paragraph - 1].text if ref.paragraph <= len(paragraphs) else None


@lru_cache(maxsize=None)
def guideline_ids() -> frozenset[str]:
    ids = set()
    for path in (DATASET_DIR / "guidelines").glob("*.md"):
        ids.update(re.findall(r"^\*\*([A-Z]{3}-\d+\.\d+) – ", path.read_text(encoding="utf-8"), re.MULTILINE))
    return frozenset(ids)


@lru_cache(maxsize=None)
def trial_ids() -> frozenset[str]:
    data = json.loads((DATASET_DIR / "studie" / "studie.json").read_text(encoding="utf-8"))
    ids = set()
    for study in data["studie"]:
        ids.add(study["id"])
        for criterion in study.get("zarazeni", []) + study.get("vyrazeni", []):
            ids.add(f"{study['id']}/{criterion['id']}")
    return frozenset(ids)


# ── Evidence ID ───────────────────────────────────────────────────────────────
class TestEvidenceId:
    @pytest.mark.parametrize("evidence_id, kind, resource_id, paragraph, criterion", [
        ("P03", "patient", "P03", None, None),
        ("P03-ecog03", "patient", "P03-ecog03", None, None),
        ("P03-img03#3", "patient", "P03-img03", 3, None),
        ("P01-lab01-hb-f", "patient", "P01-lab01-hb-f", None, None),
        ("KRC-2.4", "guideline", "KRC-2.4", None, None),
        ("RKT-03", "trial", "RKT-03", None, None),
        ("RKT-03/V3", "trial", "RKT-03", None, "V3"),
        ("EXT-EMA-DPD-2020", "external", "EXT-EMA-DPD-2020", None, None),
    ])
    def test_parse(self, evidence_id, kind, resource_id, paragraph, criterion):
        ref = parse_evidence_id(evidence_id)
        assert (ref.kind, ref.resource_id, ref.paragraph, ref.criterion) == (kind, resource_id, paragraph, criterion)

    @pytest.mark.parametrize("evidence_id", [
        "", "P3-img03", "P03-img03#0", "P03-img03#a", "KRC-2", "KRC-2.4#1", "RKT-3/V3",
        "RKT-03/X1", "EXT-", "ext-ema", "P01-lab01-hb_f", "[P03-img03]",
    ])
    def test_invalid(self, evidence_id):
        assert not is_evidence_id(evidence_id)

    def test_guideline_regex(self):
        assert GUIDELINE_ID_RE.match("OBC-1.3")
        assert not GUIDELINE_ID_RE.match("XYZ-1.3")


# ── Schémata ──────────────────────────────────────────────────────────────────
class TestSchemas:
    @pytest.mark.parametrize("schema", [
        schemas.Brief, schemas.DecisionSupport, schemas.Decision, schemas.IntakePrefill,
        schemas.MdtCase, schemas.BriefConfig, schemas.TimelineEvent,
    ])
    def test_usable_as_response_schema(self, schema):
        """Schéma projde čištěním pro Gemini a mock z něj vyrobí validní instanci (T-012)."""
        assert gemini_json_schema(schema)["type"] == "object"
        result = MockAIProvider().generate("test", response_schema=schema)
        assert result["status"] == "success", result.get("error")
        schema.model_validate(result["data"])

    def test_verification_defaults_to_unverified(self):
        claim = schemas.Claim(id="c1", kind="claim", text="x", citations=["P03-ecog03"])
        assert claim.verification == "unverified"

    def test_ecog_range(self):
        with pytest.raises(ValueError):
            schemas.EcogPrefill(value=5, citation="P03-ecog03")


# ── Fixtures ──────────────────────────────────────────────────────────────────
@needs_fixtures
class TestFixtures:
    @pytest.mark.parametrize("name, schema", FIXTURES.items())
    def test_valid_and_roundtrip(self, name, schema):
        """Fixture projde validací a nic se neztratí (odhalí překlepy v klíčích)."""
        data = load_fixture(name)
        model = schema.model_validate(data)
        assert model.model_dump(mode="json", exclude_unset=True) == data

    @pytest.mark.parametrize("name", FIXTURES)
    def test_evidence_id_format(self, name):
        bad = [e for e in evidence_ids(load_fixture(name)) if not is_evidence_id(e)]
        assert not bad

    @pytest.mark.parametrize("name", FIXTURES)
    def test_frontend_copy_is_identical(self, name):
        if not FRONTEND_FIXTURES_DIR:
            pytest.skip("chybí frontend")
        copy = FRONTEND_FIXTURES_DIR / name
        if not copy.exists():
            pytest.skip(f"chybí {copy}")
        assert json.loads(copy.read_text(encoding="utf-8")) == load_fixture(name)

    def test_brief_stats(self):
        brief = schemas.Brief.model_validate(load_fixture("brief_P03.json"))
        assert brief.stats == schemas.compute_stats(brief)

    def test_brief_semantics(self):
        brief = schemas.Brief.model_validate(load_fixture("brief_P03.json"))
        for claim in schemas.iter_claims(brief):
            if claim.kind == "claim":
                assert claim.citations, claim.id
        for flag in brief.red_flags:
            assert len(flag.citations) >= 2, flag.id
        roles = [s.role for s in brief.sections if s.id == "role_views"]
        assert len([r for r in roles if r != "patient"]) >= 3   # zadání: min. 3 role
        assert set(roles) <= set(brief.config.roles_present)

    def test_compatibility_overall_is_worst_rule(self):
        brief = schemas.Brief.model_validate(load_fixture("brief_P03.json"))
        for option in brief.decision_support.treatment_options:
            compat = option.compatibility
            worst = max((r.status for r in compat.rules), key=LIGHT_RANK.__getitem__)
            assert compat.overall == worst, option.id
            for rule in compat.rules:
                ref = parse_evidence_id(rule.rule_citation)
                assert ref and ref.kind != "patient", rule.rule_id   # pravidlo cituje zdroj, ne fakt pacienta

    def test_p03_expected_lights(self):
        """Barvy semaforu pro P03 podle docs/POZADAVKY_LEKARE.md §5.4."""
        brief = schemas.Brief.model_validate(load_fixture("brief_P03.json"))
        lights = {o.id: o.compatibility.overall for o in brief.decision_support.treatment_options}
        assert lights == {"opt-resekce": "orange", "opt-folfox": "orange", "opt-anti-egfr": "red", "opt-io": "grey"}

    @pytest.mark.parametrize("name", FIXTURES)
    def test_never_recommends(self, name):
        """AI předkládá, nevybírá: v textech není „doporučujeme“ (zadání, D-015)."""
        assert not [s for s in all_strings(load_fixture(name)) if "doporučuj" in s.lower()]

    def test_intake_question_cannot_be_skipped(self):
        intake = schemas.IntakePrefill.model_validate(load_fixture("intake_P03.json"))
        question = next(f for f in intake.fields if f.id == "mdt.question")
        assert question.status == "present"


@needs_fixtures
@needs_dataset
class TestFixtureCitations:
    @pytest.mark.parametrize("name", FIXTURES)
    def test_citations_exist_in_dataset(self, name):
        """Každá citace ukazuje na existující resource, odstavec, pasáž nebo kritérium."""
        problems = []
        for evidence_id in evidence_ids(load_fixture(name)):
            ref = parse_evidence_id(evidence_id)
            if ref.kind == "patient":
                if APP_CREATED_RE.match(ref.resource_id):
                    continue
                if ref.resource_id not in patient_resources(ref.patient_id):
                    problems.append(f"{evidence_id}: resource není v datasetu")
                elif ref.paragraph is not None and paragraph_text(evidence_id) is None:
                    problems.append(f"{evidence_id}: odstavec neexistuje")
            elif ref.kind == "guideline" and evidence_id not in guideline_ids():
                problems.append(f"{evidence_id}: pasáž není v guidelines")
            elif ref.kind == "trial" and evidence_id not in trial_ids():
                problems.append(f"{evidence_id}: studie nebo kritérium neexistuje")
        assert not problems

    @pytest.mark.parametrize("evidence_id, snippet", [
        ("P03-img01#5", "83 mm"),
        ("P03-img03#4", "50 mm (pokles o 40 %)"),
        ("P03-img03#1", "hrudník nebyl požadován"),
        ("P03-img04#3", "38 %"),
        ("P03-doc02#5", "Alergie: neudává"),
        ("P03-doc02#6", "otec karcinom tlustého střeva"),
        ("P03-doc06#2", "ECOG 0–1"),
        ("P03-pat02#8", "MMR/MSI nebylo požadováno"),
    ])
    def test_demo_citations_point_to_right_paragraph(self, evidence_id, snippet):
        """Klíčové citace dema P03 podle číslování ze services/ai/text.py (T-105)."""
        assert snippet in paragraph_text(evidence_id)

    def test_guidelines_count(self):
        assert len(guideline_ids()) == 42   # DATASET §7
