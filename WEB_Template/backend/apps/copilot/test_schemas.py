"""
Testy kontraktů (T-009, ARCHITEKTURA §8): pydantic schémata, fixtures P03 a shoda výstupů
ostatních lanes s kontraktem (red flags T-202, zařazení T-502, semafor T-503, API pacientů T-103,
resolver citací T-104).

Fixtures (``data/fixtures``) leží mimo backend. V CI jsou v checkoutu repa, v backend kontejneru
chybí a testy s nimi se přeskočí. Dataset se čte jen v testech (``services/tests/dataset.py``),
za běhu se čte z IRIS.
"""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

import pytest

from apps.copilot import schemas
from services import evidence as evidence_resolver
from services import patients as patient_service
from services.ai.text import resource_paragraphs
from services.ai_service import MockAIProvider, gemini_json_schema
from services.conftest import dataset_root, fake_fhir, fake_fhir_dataset, fake_iris  # noqa: F401  (FHIR + IRIS v paměti)
from services.fhir import ingest
from services.fhir.ids import parse_evidence_id
from services.iris import indexing
from services.iris import vector_store as vs
from services.rules.compatibility import evaluate_compatibility
from services.rules.intake import intake_prefill
from services.rules.red_flags import evaluate
from services.tests.dataset import dataset_dir, load_patient

PATIENTS = ["P01", "P02", "P03", "P04", "P05", "P06"]

# Kořen repa (v CI a lokálně); v backend kontejneru je jen /code, tam je None.
REPO_ROOT = next((p for p in Path(__file__).resolve().parents if (p / "WEB_Template").is_dir()), None)


def _dir(env: str, *relative: str) -> Path | None:
    if os.environ.get(env):
        return Path(os.environ[env])
    return REPO_ROOT.joinpath(*relative) if REPO_ROOT else None


FIXTURES_DIR = _dir("FIXTURES_DIR", "data", "fixtures")
FRONTEND_FIXTURES_DIR = _dir("FRONTEND_FIXTURES_DIR", "WEB_Template", "frontend", "src", "fixtures")

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

LIGHT_RANK = {"green": 0, "skipped": 1, "grey": 2, "orange": 3, "red": 4}   # 🔴 > 🟠 > ⚪ > neposuzováno > 🟢 (§5.9)

needs_fixtures = pytest.mark.skipif(
    not (FIXTURES_DIR and FIXTURES_DIR.is_dir()), reason="chybí data/fixtures (backend kontejner je nevidí)",
)


def load_fixture(name: str):
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def assert_contract(schema, data):
    """Data projdou schématem a nic se neztratí: žádný klíč navíc ani s překlepem."""
    model = schema.model_validate(data)
    assert model.model_dump(mode="json", exclude_unset=True) == data


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


def fixture_citations() -> list[str]:
    """Citace ze všech fixtures (bez resources, které vzniknou až v aplikaci)."""
    ids = {e for name in FIXTURES for e in evidence_ids(load_fixture(name))}
    return sorted(e for e in ids if not APP_CREATED_RE.match(e))


def all_strings(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from all_strings(v)
    elif isinstance(node, list):
        for item in node:
            yield from all_strings(item)
    elif isinstance(node, str):
        yield node


@lru_cache(maxsize=None)
def patient_resources(patient_id: str) -> dict[str, dict]:
    """Resources pacienta se stejnou sanitizací jako ingest do IRIS (T-101)."""
    return {r["id"]: r for r in load_patient(patient_id)}


def paragraph_text(evidence_id: str) -> str | None:
    ref = parse_evidence_id(evidence_id)
    paragraphs = resource_paragraphs(patient_resources(ref.patient_id)[ref.resource_id])
    return paragraphs[ref.paragraph - 1].text if ref.paragraph <= len(paragraphs) else None


@lru_cache(maxsize=None)
def guideline_ids() -> frozenset[str]:
    ids = set()
    for path in (dataset_dir() / "guidelines").glob("*.md"):
        ids.update(re.findall(r"^\*\*([A-Z]{3}-\d+\.\d+) – ", path.read_text(encoding="utf-8"), re.MULTILINE))
    return frozenset(ids)


@lru_cache(maxsize=None)
def trial_ids() -> frozenset[str]:
    data = json.loads((dataset_dir() / "studie" / "studie.json").read_text(encoding="utf-8"))
    ids = set()
    for study in data["studie"]:
        for criterion in study.get("zarazeni", []) + study.get("vyrazeni", []):
            ids.add(f"{study['id']}/{criterion['id']}")
    return frozenset(ids)


@lru_cache(maxsize=None)
def external_ids() -> frozenset[str]:
    return frozenset(c.EvidenceId for c in indexing.external_chunks())


# ── Schémata ──────────────────────────────────────────────────────────────────
class TestSchemas:
    @pytest.mark.parametrize("schema", [
        schemas.Brief, schemas.DecisionSupport, schemas.Decision, schemas.IntakePrefill,
        schemas.MdtCase, schemas.BriefConfig, schemas.TimelineEvent, schemas.PatientDetail,
        schemas.ObservationSeries, schemas.ProcedureCompatibility,
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
        assert_contract(schema, load_fixture(name))

    @pytest.mark.parametrize("name", FIXTURES)
    def test_evidence_id_format(self, name):
        bad = [e for e in evidence_ids(load_fixture(name)) if parse_evidence_id(e) is None]
        assert not bad

    def test_evidence_fixture(self):
        """`evidence_P03.json` (zdroje pro UI bez backendu) pokrývá všechny citace a odpovídá EvidenceSource."""
        sources = load_fixture("evidence_P03.json")
        assert sorted(sources) == fixture_citations()
        for evidence_id, source in sources.items():
            assert source["evidence_id"] == evidence_id
            assert_contract(schemas.EvidenceSource, source)

    @pytest.mark.parametrize("name", [*FIXTURES, "evidence_P03.json"])
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
                assert ref and ref.kind in ("guideline", "trial_criterion", "external"), rule.rule_id

    def test_p03_expected_lights(self):
        """Barvy semaforu pro P03 podle docs/POZADAVKY_LEKARE.md §5.4."""
        brief = schemas.Brief.model_validate(load_fixture("brief_P03.json"))
        lights = {o.id: o.compatibility.overall for o in brief.decision_support.treatment_options}
        assert lights == {
            "krc-resekce-jater": "orange", "krc-konverzni-chemoterapie": "orange",
            "krc-anti-egfr": "red", "krc-imunoterapie": "grey",
        }

    @pytest.mark.parametrize("name", FIXTURES)
    def test_never_recommends(self, name):
        """AI předkládá, nevybírá: v textech není „doporučujeme“ (zadání, D-015)."""
        assert not [s for s in all_strings(load_fixture(name)) if "doporučuj" in s.lower()]

    def test_intake_question_cannot_be_skipped(self):
        intake = schemas.IntakePrefill.model_validate(load_fixture("intake_P03.json"))
        question = next(f for f in intake.fields if f.id == "mdt.question")
        assert question.status == "present"

    def test_citations_exist_in_dataset(self):
        """Každá citace ukazuje na existující resource, odstavec, pasáž, kritérium nebo externí zdroj."""
        problems = []
        for evidence_id in fixture_citations():
            ref = parse_evidence_id(evidence_id)
            if ref.kind in ("resource", "paragraph"):
                if ref.resource_id not in patient_resources(ref.patient_id):
                    problems.append(f"{evidence_id}: resource není v datasetu")
                elif ref.paragraph is not None and paragraph_text(evidence_id) is None:
                    problems.append(f"{evidence_id}: odstavec neexistuje")
            elif ref.kind == "guideline" and evidence_id not in guideline_ids():
                problems.append(f"{evidence_id}: pasáž není v guidelines")
            elif ref.kind == "trial_criterion" and evidence_id not in trial_ids():
                problems.append(f"{evidence_id}: kritérium studie neexistuje")
            elif ref.kind == "external" and evidence_id not in external_ids():
                problems.append(f"{evidence_id}: externí zdroj není v katalogu T-504")
        assert not problems

    def test_resolver_opens_every_citation(self, fake_fhir_dataset, fake_iris, dataset_root):
        """UI otevře zdroj u každé citace: resolver T-104 ji najde a odpověď odpovídá EvidenceSource."""
        vs.ensure_schema()
        indexing.index_guidelines(indexing.guideline_chunks(dataset_root) + indexing.external_chunks())
        indexing.index_trials(indexing.trial_criteria(ingest.load_studies(dataset_root)))
        for evidence_id in fixture_citations():
            source = evidence_resolver.resolve(evidence_id)
            assert_contract(schemas.EvidenceSource, source)
            if source["kind"] == "paragraph":
                h = source["highlight"]
                assert source["text"][h["start"]:h["end"]] == paragraph_text(evidence_id), evidence_id


# ── Dataset a výstupy ostatních lanes ─────────────────────────────────────────
class TestDataset:
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


class TestProducersMatchContract:
    """Co vracejí pravidla a API pacientů, odpovídá přesně kontraktu §8 (žádný klíč navíc ani chybějící)."""

    @pytest.mark.parametrize("patient_id", PATIENTS)
    def test_red_flags(self, patient_id):
        for flag in evaluate(load_patient(patient_id)):
            assert_contract(schemas.RedFlag, flag.as_dict())

    @pytest.mark.parametrize("patient_id", PATIENTS)
    def test_intake_prefill(self, patient_id):
        assert_contract(schemas.IntakePrefill, intake_prefill(load_patient(patient_id)))

    @pytest.mark.parametrize("patient_id", PATIENTS)
    def test_compatibility(self, patient_id):
        for procedure in evaluate_compatibility(load_patient(patient_id)):
            assert_contract(schemas.ProcedureCompatibility, procedure)

    @pytest.mark.parametrize("patient_id", PATIENTS)
    def test_patients_api(self, patient_id):
        resources = load_patient(patient_id)
        assert_contract(schemas.PatientListItem, patient_service.summary(patient_id, resources))
        assert_contract(schemas.PatientDetail, patient_service.detail(patient_id, resources))
        for event in patient_service.timeline(resources):
            assert_contract(schemas.TimelineEvent, event)
        for series in patient_service.observations(resources):
            assert_contract(schemas.ObservationSeries, series)
