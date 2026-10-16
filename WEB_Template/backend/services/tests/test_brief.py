"""Testy generátoru bloku A a grounding validátoru v2 (T-106, T-213, ARCHITEKTURA §5.3)."""
import types

import pytest

from apps.copilot import schemas
from services.ai import brief as brief_module
from services.ai.brief import build_brief, generate_brief
from services.ai.context_builder import context_from_resources
from services.ai.grounding import check_claim, verify_claims
from services.ai_service import MockAIProvider
from services.tests.dataset import load_patient, load_studies

PATIENTS = ["P01", "P02", "P03", "P04", "P05", "P06"]


@pytest.fixture(autouse=True)
def indexed_grounding_vectors(grounding_vectors):
    """Podklady ověřují grounding proti stejným in-memory vektorům jako IRIS."""

# Souhrn, jak by ho napsal LLM: čísla a data přesně podle zdrojů, citace odstavců
P03_SUMMARY = {"items": [
    {"text": "Adenokarcinom sigmatu G2, cT3 cN1 cM1a, stadium IVA, s jaterními metastázami; KRAS G12D.",
     "citations": ["P03-pat01#3", "P03-tnm01", "P03-dg2", "P03-bm01"]},
    {"text": "Po 8 cyklech FOLFOX + bevacizumab parciální odpověď: součet cílových lézí 83 mm → 50 mm (pokles o 40 %).",
     "citations": ["P03-img01#5", "P03-img03#4", "P03-doc07#6"]},
    {"text": "ECOG 0 podle lékaře, pacient uvádí stupeň 1: těžší fyzickou práci nezvládá.",
     "citations": ["P03-ecog03", "P03-prom02"]},
]}


def brief_for(patient_id, provider=None, **kwargs):
    return build_brief(patient_id, load_patient(patient_id), studies=load_studies(),
                       provider=provider or MockAIProvider(), case_id="7", **kwargs)


class PromptCaptureProvider(MockAIProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompts = []

    def generate(self, prompt, **kwargs):
        self.system_prompts.append(kwargs.get("system_prompt", ""))
        return super().generate(prompt, **kwargs)


def section(brief, section_id):
    return next(s for s in brief["sections"] if s["id"] == section_id)


# ── DoD: P03 ──────────────────────────────────────────────────────────────────
def test_p03_brief_valid_and_grounded():
    brief = brief_for("P03", MockAIProvider(responses={"SummaryOutput": P03_SUMMARY}))
    schemas.Brief.model_validate(brief)
    assert brief["stats"]["claims_unverified"] == 0
    header = brief["header"]
    assert header["display_name"] == "P03 · muž · 67 let"
    assert (header["ecog"]["physician"]["value"], header["ecog"]["patient"]["value"]) == (0, 1)   # ECOG 0 vs. 1
    assert header["ecog"]["patient"]["answer_text"].startswith("Těžší fyzickou práci")
    assert header["intent"] == {"letter": "C", "code": "kurativni", "source": "previous_mdt"}
    assert header["tnm"] == {"text": "cT3 cN1 cM1a", "stage": "IVA", "citation": "P03-tnm01"}
    assert header["mdt_question"]["citation"] == "P03-zad01#1"
    assert header["mdt_date"].startswith("2026-10-21")
    assert [c["citation"] for c in header["comorbidities"]] == ["P03-kom1", "P03-kom2", "P03-kom3"]
    assert any("stentu" in a["text"] for a in header["alerts"]) and any("portu" in a["text"] for a in header["alerts"])
    summary = section(brief, "summary")["items"]
    assert [i["text"] for i in summary[:3]] == [i["text"] for i in P03_SUMMARY["items"]]
    missing = [i["text"] for i in summary if i["kind"] == "missing"]
    assert any(t.startswith("MMR / MSI") for t in missing) and any(t.startswith("CT hrudníku") for t in missing)
    assert {"RF-TOX", "RF-ECOG", "RF-STALE", "RF-MISSING"} <= {f["rule"] for f in brief["red_flags"]}


def test_p03_decision_support_screens_trials_and_has_discussion_questions():
    decision = brief_for("P03")["decision_support"]
    schemas.DecisionSupport.model_validate(decision)
    rkt03 = next(trial for trial in decision["trials"] if trial["study_id"] == "RKT-03")
    criteria = {criterion["criterion_id"]: criterion for criterion in rkt03["criteria"]}
    assert criteria["RKT-03/Z1"]["status"] == "unknown"
    assert criteria["RKT-03/V2"]["status"] == "unknown"
    assert 2 <= len(decision["discussion_questions"]) <= 3
    assert all("doporučujeme" not in option["title"].lower() for option in decision["treatment_options"])
    assert all(c["status"] != "unknown" or c.get("missing") for trial in decision["trials"]
               for c in trial["criteria"])


class LiveLikeProvider(MockAIProvider):
    is_mock = False                                               # B2 volá LLM jen mimo mock


def test_decision_support_keeps_every_option_even_when_llm_picks_two():
    """D-015: LLM vybere 2 možnosti, podklad i tak ukáže všechny postupy ze sady guidelines (i červené)."""
    all_ids = [o["id"] for o in brief_for("P03")["decision_support"]["treatment_options"]]
    picked = {"options": [{"procedure_id": pid, "title": pid, "rationale": [], "guideline_citations": [],
                           "considerations": []} for pid in all_ids[:2]]}
    decision = brief_for("P03", LiveLikeProvider(responses={"OptionsDraft": picked}))["decision_support"]
    assert sorted(o["id"] for o in decision["treatment_options"]) == sorted(all_ids)
    assert any(o["compatibility"]["overall"] == "red" for o in decision["treatment_options"])


def test_p05_decision_support_includes_basket_trial():
    decision = brief_for("P05")["decision_support"]
    rkt06 = next(trial for trial in decision["trials"] if trial["study_id"] == "RKT-06")
    assert rkt06["criteria"]
    assert all(c["criterion_id"].startswith("RKT-06/") for c in rkt06["criteria"])
    assert any("dávkovací protokol" in question["text"] and "RKT-06" in question["citations"]
               for question in decision["discussion_questions"])


def test_hallucinated_number_is_unverified():
    wrong = {"items": [{"text": "Součet cílových lézí klesl na 45 mm.", "citations": ["P03-img03#4"]},
                       {"text": "ECOG 0 podle lékaře.", "citations": ["P03-ecog03", "P03-neexistuje"]}]}
    brief = brief_for("P03", MockAIProvider(responses={"SummaryOutput": wrong}))
    items = section(brief, "summary")["items"]
    assert [i["verification"] for i in items[:2]] == ["unverified", "unverified"]
    assert brief["stats"]["claims_unverified"] == 2
    assert all("_grounding" not in i for i in items)          # důvody nejsou v kontraktu


def test_llm_failure_falls_back_to_data_summary():
    brief = brief_for("P03", MockAIProvider(responses={"SummaryOutput": {"items": [{"text": "bez citací"}]}}))
    summary = [i for i in section(brief, "summary")["items"] if i["kind"] == "claim"]
    assert summary and all(i["verification"] == "verified" for i in summary)
    assert any("ECOG podle lékaře 0" in i["text"] and "podle pacienta 1" in i["text"] for i in summary)


@pytest.mark.parametrize("patient_id", PATIENTS)
def test_every_patient_valid_and_grounded(patient_id):
    brief = brief_for(patient_id)
    schemas.Brief.model_validate(brief)
    assert brief["stats"]["claims_unverified"] == 0
    timeline = [i["text"][:10] for i in section(brief, "timeline")["items"]]
    assert timeline == sorted(timeline)


# ── Nastavení a vstupy od lékaře ──────────────────────────────────────────────
def test_skipped_field_shown_as_skipped():
    brief = brief_for("P03", skipped_fields=["bm.mmr"])
    texts = [i["text"] for i in section(brief, "summary")["items"]]
    assert "MMR / MSI: Chybí (přeskočeno lékařem)" in texts


def test_intent_from_physician():
    brief = brief_for("P04", intent_letter="P")
    assert brief["header"]["intent"] == {"letter": "P", "code": "paliativni", "source": "physician"}
    assert brief_for("P04")["header"]["intent"] is None            # minulá MDT: odloženo


def test_config_controls_sections():
    config = {"sections": [{"id": "timeline", "enabled": True, "order": 1},
                           {"id": "summary", "enabled": False, "order": 2},
                           {"id": "red_flags", "enabled": False, "order": 3}]}
    brief = brief_for("P03", config=config)
    assert [s["id"] for s in brief["sections"]] == ["timeline"]
    assert brief["red_flags"] == []
    assert brief["config"]["roles_present"]                        # doplněno z výchozí konfigurace


def test_config_detail_override_changes_summary_output_and_language_prompt():
    response = {"items": [{"text": f"Fakt {letter}", "citations": ["P03-img03#4"]}
                          for letter in "ABCDE"]}
    brief_config = {"detail_level": "standard", "language": "en",
                    "sections": [{"id": "summary", "enabled": True, "order": 1, "detail": "brief"}]}
    detailed_config = {"detail_level": "brief", "language": "sk",
                       "sections": [{"id": "summary", "enabled": True, "order": 1, "detail": "detailed"}]}
    brief_provider = PromptCaptureProvider(responses={"SummaryOutput": response})
    detailed_provider = PromptCaptureProvider(responses={"SummaryOutput": response})

    brief = brief_for("P03", brief_provider, config=brief_config)
    detailed = brief_for("P03", detailed_provider, config=detailed_config)

    brief_claims = [c for c in section(brief, "summary")["items"] if c["kind"] == "claim"]
    detailed_claims = [c for c in section(detailed, "summary")["items"] if c["kind"] == "claim"]
    assert len(brief_claims) == 3
    assert len(detailed_claims) == 5
    assert "Piš anglicky" in brief_provider.system_prompts[0]
    assert "Úroveň detailu brief" in brief_provider.system_prompts[0]
    assert brief_provider.system_prompts[0].endswith("Write all newly generated text exclusively in English.")
    assert "Piš slovensky" in detailed_provider.system_prompts[0]
    assert "Úroveň detailu detailed" in detailed_provider.system_prompts[0]
    assert detailed_provider.system_prompts[0].endswith("Všetok novo vytvorený text napíš výhradne po slovensky.")


def test_config_applies_language_and_detail_to_role_prompt():
    response = {"items": [{"text": f"Role fact {letter}", "citations": ["P03-img03#4"]}
                          for letter in "ABCDEF"]}
    provider = PromptCaptureProvider(responses={"RoleViewOutput": response})
    config = {"language": "en", "detail_level": "standard", "roles_present": ["surgeon"],
              "sections": [{"id": "role_views", "enabled": True, "order": 1, "detail": "brief"}]}

    brief = brief_for("P03", provider, config=config)

    role = next(s for s in brief["sections"] if s.get("role") == "surgeon")
    assert len([i for i in role["items"] if "-dx-" not in i["id"]]) == 3       # údaje podle diagnózy se nekrátí
    assert "Piš anglicky" in provider.system_prompts[0]
    assert "Úroveň detailu brief" in provider.system_prompts[0]
    assert provider.system_prompts[0].endswith("Write all newly generated text exclusively in English.")


def test_config_applies_language_to_red_flag_prompt():
    provider = PromptCaptureProvider(responses={"LlmRedFlags": {"flags": []}})
    config = {"language": "sk", "sections": [
        {"id": "red_flags", "enabled": True, "order": 1, "detail": "detailed"}]}

    brief_for("P03", provider, config=config)

    assert len(provider.system_prompts) == 1
    assert provider.system_prompts[0].endswith("Všetok novo vytvorený text napíš výhradne po slovensky.")


def test_generate_brief_job_interface(monkeypatch):
    resources, studies = load_patient("P03"), load_studies()
    monkeypatch.setattr(brief_module, "load_resources", lambda pid: (resources, studies))
    monkeypatch.setattr(brief_module, "load_guidelines", lambda sets: [])
    progress, calls = [], []
    case = types.SimpleNamespace(pk=12, patient_fhir_id="P03", skipped_fields=[], intent=None)
    result = generate_brief(case, {}, progress.append, provider=MockAIProvider(),
                            log_call=lambda purpose, r: calls.append((purpose, r["status"])))
    schemas.Brief.model_validate(result)
    assert result["case_id"] == "12" and result["model"] == "mock"
    roles = brief_module.DEFAULT_CONFIG["roles_present"]
    assert sorted(calls) == sorted([("brief.rf_llm", "success"), ("brief.summary", "success"),
                                    ("brief.recist.extract", "success")]
                                   + [(f"brief.role.{r}", "success") for r in roles])
    assert progress[0] == 5 and progress[-1] == 100 and progress == sorted(progress)


# ── Grounding validátor v1 ────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def p03_context():
    return context_from_resources("P03", load_patient("P03"), studies=load_studies())


@pytest.mark.parametrize("text, citations, verified", [
    ("CEA 13,9 µg/l", ["P03-lab06-cea"], True),
    ("CEA 13.9 µg/l", ["P03-lab06-cea"], True),                    # desetinná tečka = čárka
    ("CEA 14,9 µg/l", ["P03-lab06-cea"], False),
    ("ECOG 0 dne 2026-10-05", ["P03-ecog03"], True),
    ("ECOG 0 dne 6. 10.", ["P03-ecog03"], False),                   # datum není ve zdroji
    ("CT z 21. 9. 2026 bez hrudníku", ["P03-img03"], True),
    ("Ložisko S3 4 mm", ["P03-img04#2"], True),                     # S3 není číslo k ověření
    ("Bez citace", [], False),
    ("Neexistující zdroj", ["P03-img99"], False),
])
def test_grounding_checks(p03_context, text, citations, verified):
    result = check_claim({"kind": "claim", "text": text, "citations": citations}, p03_context)
    assert result.verified is verified, result.reasons


def test_missing_items_only_need_existing_citations(p03_context):
    assert check_claim({"kind": "missing", "text": "MMR chybí 12", "citations": ["P03-bm04"]}, p03_context).verified
    assert check_claim({"kind": "missing", "text": "MMR chybí", "citations": []}, p03_context).verified
    assert not check_claim({"kind": "missing", "text": "x", "citations": ["P03-xx"]}, p03_context).verified


def test_grounding_v2_rejects_semantically_wrong_citation(p03_context, monkeypatch):
    from services.iris import vector_store

    monkeypatch.setattr(vector_store, "similarity", lambda text, citations: {citations[0]: 0.21})
    result = verify_claims([
        {"kind": "claim", "text": "CT z 21. 9. 2026 bez hrudníku", "citations": ["P03-img03"]},
    ], p03_context)[0]
    assert result["verification"] == "unverified"
    assert "sémantická podobnost" in result["_grounding"][0]


def test_grounding_v2_rejects_wrong_citation_against_indexed_vectors(p03_context):
    result = verify_claims([
        {"kind": "claim", "text": "Pacient užívá tamoxifen.", "citations": ["P03-img03#1"]},
    ], p03_context)[0]
    assert result["verification"] == "unverified"


def test_grounding_v2_accepts_matching_citation_and_keeps_missing_exempt(p03_context, monkeypatch):
    from services.iris import vector_store

    def matching_similarity(text, citations):
        return {citations[0]: 0.81} if citations else {}

    monkeypatch.setattr(vector_store, "similarity", matching_similarity)
    result = verify_claims([
        {"kind": "claim", "text": "CEA 13,9 µg/l", "citations": ["P03-lab06-cea"]},
        {"kind": "missing", "text": "MMR chybí", "citations": []},
    ], p03_context)
    assert [item["verification"] for item in result] == ["verified", "verified"]


def test_grounding_v2_skips_structured_citations_without_vectors(p03_context, monkeypatch):
    """Q23: strukturovaná data (lab, TNM, biomarkery) vektor nemají, stačí jim body 1–3."""
    from services.iris import vector_store

    monkeypatch.setattr(vector_store, "similarity", lambda text, citations: {})
    result = verify_claims([
        {"kind": "claim", "text": "CEA 13,9 µg/l", "citations": ["P03-lab06-cea"]},
        {"kind": "claim", "text": "CT z 21. 9. 2026 bez hrudníku", "citations": ["P03-img03"]},
    ], p03_context)
    assert [item["verification"] for item in result] == ["verified", "unverified"]


# ── T-507: anamnéza (FR-A5) ───────────────────────────────────────────────────
def test_short_anamnesis_is_verbatim_with_citations():
    items = section(brief_for("P03"), "anamnesis")["items"]
    texts = [i["text"] for i in items]
    assert texts[0].startswith("Osobní anamnéza: IM 2019, st. p. PCI RIA")
    assert "Rodinná anamnéza: otec karcinom tlustého střeva v 72 letech." in texts
    assert "Alergie: neudává." in texts
    assert all(i["verification"] == "verified" and i["citations"][0].startswith("P03-doc02#") for i in items)


def test_long_anamnesis_is_ai_summary_with_citations(monkeypatch):
    monkeypatch.setenv("INTAKE_ANAMNESIS_MAX_CHARS", "300")          # P06 má ~570 znaků → shrnutí
    llm = {"items": [{"text": "Žije sama, chodí s holí, dříve dlouhodobě kouřila.", "citations": ["P06-doc05#3"]},
                     {"text": "Vymyšlený bod bez platné citace.", "citations": ["P06-doc99#1"]}]}
    items = section(brief_for("P06", MockAIProvider(responses={"AnamnesisOutput": llm})), "anamnesis")["items"]
    assert [i["text"] for i in items] == ["Žije sama, chodí s holí, dříve dlouhodobě kouřila."]
    fallback = section(brief_for("P06"), "anamnesis")["items"]               # mock bez odpovědi: první věty
    assert fallback[0]["text"].startswith("Nynější onemocnění: Pravidelně chodila") and fallback[0]["text"].endswith("…")
    assert all(i["verification"] == "verified" for i in fallback)
