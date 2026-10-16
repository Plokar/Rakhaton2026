"""Testy red flags (T-202): deterministická pravidla nad datasetem + RF-LLM přes mock provider."""
import pytest

from services.ai.context_builder import context_from_resources
from services.ai.guidelines import parse_guidelines
from services.ai.red_flags_llm import detect_llm_red_flags
from services.ai_service import MockAIProvider
from services.rules.red_flags import evaluate
from services.tests.dataset import load_guideline_markdowns, load_patient, load_studies

PATIENTS = ["P01", "P02", "P03", "P04", "P05", "P06"]


@pytest.fixture(scope="module")
def flags():
    return {pid: evaluate(load_patient(pid)) for pid in PATIENTS}


@pytest.fixture(scope="module")
def guidelines():
    return [p for md in load_guideline_markdowns().values() for p in parse_guidelines(md)]


def find(flags, rule, citation=None):
    return [f for f in flags if f.rule == rule and (citation is None or citation in f.citations)]


# ── Hypotézy z DATASET §9 ─────────────────────────────────────────────────────
@pytest.mark.parametrize("patient_id, rule, citation, severity, guideline", [
    # P03: KRC s jaterními metastázami (demo pacient)
    ("P03", "RF-ECOG", "P03-ecog03", "moderate", "OBC-1.3"),
    ("P03", "RF-TOX", "P03-neuro01", "high", "KRC-3.2"),
    ("P03", "RF-STALE", "P03-img03#1", "high", "KRC-2.4"),            # „hrudník nebyl požadován“
    ("P03", "RF-MISSING", "P03-bm04", "moderate", "KRC-1.1"),          # MMR/MSI nevyšetřeno
    ("P03", "RF-WEIGHT", "P03-vaha01", "moderate", "OBC-2.3"),         # 84 → 78 kg
    ("P03", "RF-LAB", "P03-lab06-cea", "moderate", None),              # CEA 9,1 → 13,9
    ("P03", "RF-MED", "P03-prom02", "moderate", None),                 # hořčík, vitamin B
    # P05: PARPi ve studii RKT-06
    ("P05", "RF-MED", "P05-doc03#4", "high", None),                    # třezalka × PARPi, varování farmaceuta
    ("P05", "RF-LAB", "P05-lab04-hb-f", "high", None),                 # Hb 76 a 77 g/l
    ("P05", "RF-GENETIC", "P05-bm14", "moderate", "PRS-1.4"),          # gBRCA nevyšetřeno
    ("P05", "RF-MISSING", "P05-bm12", "moderate", "PRS-1.3"),          # ESR1 ctDNA
    ("P05", "RF-STALE", "P05-img04", "moderate", "OBC-1.2"),           # 83 dní
    ("P05", "RF-PROMS", "P05-prom02", "moderate", "OBC-1.3"),          # únava 8, psychika 7
    # ostatní pacienti
    ("P01", "RF-STALE", "P01-img06", "moderate", "OBC-1.2"),
    ("P01", "RF-NEWSYMPTOM", "P01-prom02", "high", "PRS-4.2"),         # bolest kyčle
    ("P01", "RF-GENETIC", "P01-bm11", "moderate", "PRS-1.4"),
    ("P02", "RF-LAB", "P02-lab06-glu", "moderate", "OBC-3.1"),         # glykémie při dexametazonu
    ("P02", "RF-LAB", "P02-lvef07", "moderate", "PRS-3.4"),
    ("P02", "RF-STEROID", "P02-med03", "low", "PRS-3.3"),
    ("P02", "RF-NEWSYMPTOM", "P02-prom02", "high", "PRS-4.2"),         # hlava, rozmazané vidění
    ("P04", "RF-TNM", "P04-tnm02", "moderate", "OBC-1.1"),             # IIIB vs. IIIA
    ("P04", "RF-LESION", "P04-img03#2", "high", "PLI-1.2"),            # nadledvina
    ("P04", "RF-LAB", "P04-lab05-na", "moderate", "PLI-3.2"),          # Na 136 → 129
    ("P04", "RF-MISSING", "P04-bm05", "moderate", "PLI-1.3"),          # EGFR probíhá
    ("P04", "RF-GERI", "P04", "low", "OBC-2.2"),
    ("P06", "RF-NOMINATION", "P06-lvef04", "moderate", "OBC-1.1"),     # LVEF 61 % v nominaci vs. 55 %
    ("P06", "RF-LESION", "P06-dg2", "high", "OBC-1.4"),
    ("P06", "RF-LAB", "P06-lvef04", "moderate", "PRS-3.4"),
    ("P06", "RF-GERI", "P06", "low", "OBC-2.2"),
])
def test_dataset_hypotheses(flags, patient_id, rule, citation, severity, guideline):
    matches = find(flags[patient_id], rule, citation)
    assert matches, f"{patient_id}: {rule} s citací {citation} nenalezen"
    assert matches[0].severity == severity
    assert matches[0].guideline == guideline


@pytest.mark.parametrize("patient_id, ecog_flag", [
    ("P01", True), ("P02", True), ("P03", True), ("P04", True), ("P05", False), ("P06", True)])
def test_ecog_difference(flags, patient_id, ecog_flag):
    assert bool(find(flags[patient_id], "RF-ECOG")) == ecog_flag


@pytest.mark.parametrize("patient_id, rule", [
    ("P05", "RF-TNM"),          # IIIA před 12 lety vs. IV = progrese, ne rozpor
    ("P04", "RF-STEROID"),      # inhalační budesonid není systémový kortikoid
    ("P03", "RF-PALIATIVE"),    # bez symptomu ≥ 7 a bez zhoršení
    ("P02", "RF-STALE"),        # MDT 14. 10., CT 24. 9.
    ("P06", "RF-NOMINATION:nadory"),
])
def test_no_false_positive(flags, patient_id, rule):
    assert not [f for f in flags[patient_id] if f.rule == rule or f.id.startswith(rule)]


def test_p05_interaction_details(flags):
    flag = next(f for f in flags["P05"] if f.id == "RF-MED:interakce-trezalk")
    assert "RKT-PARPi" in flag.title and "výslovně varovala" in flag.description
    assert flag.citations[:2] == ("P05-prom02", "P05-tx-parpred-01")


def test_p04_adrenal_lesion_merged(flags):
    lesions = find(flags["P04"], "RF-LESION")
    assert len(lesions) == 1
    assert lesions[0].citations == ("P04-img03#2", "P04-img02#4", "P04-zad01")


def test_sorted_by_severity(flags):
    order = {"high": 0, "moderate": 1, "low": 2}
    for patient_flags in flags.values():
        severities = [order[f.severity] for f in patient_flags]
        assert severities == sorted(severities)


@pytest.mark.parametrize("patient_id", PATIENTS)
def test_citations_exist_in_context(patient_id, flags, guidelines):
    """Každá citace a pasáž guidelines jde dohledat v kontextu (stejná ID jako v IRIS)."""
    ctx = context_from_resources(patient_id, load_patient(patient_id), studies=load_studies(), guidelines=guidelines)
    ids = [f.id for f in flags[patient_id]]
    assert len(ids) == len(set(ids))
    for flag in flags[patient_id]:
        assert len(flag.citations) >= 2, flag.id
        assert set(flag.citations) <= ctx.allowed_ids, (flag.id, set(flag.citations) - ctx.allowed_ids)
        assert flag.guideline is None or flag.guideline in ctx.allowed_ids, (flag.id, flag.guideline)
        assert flag.verification == "verified"
        assert flag.as_dict()["citations"] == list(flag.citations)


def _move_derived_from_to_extension(resources):
    """Navržená sanitizace z Q15: `derivedFrom` → DiagnosticReport do extension `derived-from`."""
    from services.rules.red_flags import DERIVED_FROM_EXTENSION
    out = []
    for r in resources:
        r = dict(r)
        refs = r.get("derivedFrom") or []
        moved = [ref for ref in refs if ref.get("reference", "").startswith("DiagnosticReport/")]
        if moved:
            r["derivedFrom"] = [ref for ref in refs if ref not in moved]
            if not r["derivedFrom"]:
                del r["derivedFrom"]
            r["extension"] = list(r.get("extension", [])) + [
                {"url": DERIVED_FROM_EXTENSION, "valueReference": ref} for ref in moved]
        out.append(r)
    return out


@pytest.mark.parametrize("patient_id", ["P03", "P04", "P05"])
def test_derived_from_extension_keeps_citations(patient_id, guidelines):
    """Q15: když ingest přesune derivedFrom do extension, citace zdrojů zůstanou stejné."""
    original = load_patient(patient_id)
    moved = _move_derived_from_to_extension(original)
    assert moved != original
    assert [f.as_dict() for f in evaluate(moved)] == [f.as_dict() for f in evaluate(original)]
    ctx_a = context_from_resources(patient_id, original, studies=load_studies(), guidelines=guidelines)
    ctx_b = context_from_resources(patient_id, moved, studies=load_studies(), guidelines=guidelines)
    assert ctx_a.render() == ctx_b.render()


# ── RF-ROLES (přítomné role z konfigurace) ────────────────────────────────────
def test_roles_resection_needs_surgeon_and_radiologist():
    resources = load_patient("P03")
    assert not find(evaluate(resources, ["oncologist", "surgeon", "radiologist"]), "RF-ROLES")
    flag = find(evaluate(resources, ["oncologist"]), "RF-ROLES")[0]
    assert flag.guideline == "KRC-2.1" and "surgeon" in flag.description and "radiologist" in flag.description
    assert not find(evaluate(resources), "RF-ROLES")            # bez konfigurace se nevyhodnocuje


def test_roles_stage_iii_lung():
    flag = find(evaluate(load_patient("P04"), ["oncologist", "surgeon", "radiologist"]), "RF-ROLES")[0]
    assert flag.guideline == "PLI-2.1"
    assert "pulmonologist" in flag.description and "radiation_oncologist" in flag.description


# ── Syntetické případy ────────────────────────────────────────────────────────
def _patient(*resources):
    return [{"resourceType": "Patient", "id": "P99"},
            {"resourceType": "ServiceRequest", "id": "P99-zad01",
             "reasonReference": [{"reference": "Condition/P99-dg1"}]},
            *resources]


def _condition(cid, icd):
    return {"resourceType": "Condition", "id": cid, "category": [{"text": "onkologická diagnóza"}],
            "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": icd}]}}


def test_ecog_difference_two_is_high():
    resources = _patient(
        {"resourceType": "Observation", "id": "P99-ecog01", "effectiveDateTime": "2026-10-01",
         "code": {"coding": [{"system": "http://loinc.org", "code": "89247-1"}]}, "valueInteger": 0},
        {"resourceType": "QuestionnaireResponse", "id": "P99-prom01", "authored": "2026-10-02",
         "item": [{"linkId": "samostatnost", "answer": [{"valueCoding": {"code": "2"}}]}]},
    )
    flag = find(evaluate(resources), "RF-ECOG")[0]
    assert flag.severity == "high" and flag.citations == ("P99-ecog01", "P99-prom01")


def test_nomination_missing_second_tumour():
    resources = _patient(_condition("P99-dg1", "C50.4"), _condition("P99-dg2", "C64"))
    flag = next(f for f in evaluate(resources) if f.id == "RF-NOMINATION:nadory")
    assert flag.guideline == "OBC-1.4" and "P99-dg2" in flag.citations


def test_empty_patient_has_no_flags():
    assert evaluate([{"resourceType": "Patient", "id": "P99"}]) == []


# ── RF-LLM ────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def p03_context(guidelines):
    resources = load_patient("P03")
    return context_from_resources("P03", resources, studies=load_studies(), guidelines=guidelines,
                                  red_flags=evaluate(resources))


def test_context_contains_rule_results(p03_context):
    text = p03_context.render()
    assert "## Výsledky deterministických pravidel" in text
    assert "- RF-TOX (high): Neuropatie: lékař G1, pacient popisuje víc." in text
    assert len(p03_context.red_flags) == len(p03_context.rule_results)


def test_llm_flags_are_validated(p03_context):
    provider = MockAIProvider(responses={"LlmRedFlags": {"flags": [
        {"title": "Zpráva vs. PROMs", "description": "Zpráva: neuropatie mírná; pacient: padají mi věci z ruky.",
         "severity": "moderate", "citations": ["P03-doc07#2", "P03-prom02"], "guideline": "KRC-3.2"},
        {"title": "Vymyšlená citace", "description": "x", "severity": "high",
         "citations": ["P03-doc07#2", "P03-doc99"], "guideline": "PRS-4.2"},
        {"title": "Jeden zdroj", "description": "x", "severity": "low", "citations": ["P03-prom02"]},
    ]}})
    flags, result = detect_llm_red_flags(p03_context, provider)
    assert result["status"] == "success"
    assert [f.rule for f in flags] == ["RF-LLM"] * 3
    by_title = {f.title: f for f in flags}
    assert by_title["Zpráva vs. PROMs"].verification == "verified"
    assert by_title["Zpráva vs. PROMs"].guideline == "KRC-3.2"
    assert by_title["Vymyšlená citace"].verification == "unverified"
    assert by_title["Vymyšlená citace"].guideline is None          # PRS-4.2 není v sadě pacienta
    assert by_title["Jeden zdroj"].verification == "unverified"
    assert flags[0].severity == "high"


def test_llm_mock_default_returns_no_flags(p03_context):
    flags, result = detect_llm_red_flags(p03_context, MockAIProvider())
    assert flags == [] and result["status"] == "success"


def test_llm_error_returns_empty(p03_context):
    provider = MockAIProvider(responses={"LlmRedFlags": {"flags": [{"title": "bez povinných polí"}]}})
    flags, result = detect_llm_red_flags(p03_context, provider)
    assert flags == [] and result["status"] == "error"
