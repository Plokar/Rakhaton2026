"""Deterministic parts of B2 decision support (ARCHITEKTURA §5.5, T-204)."""
from __future__ import annotations

import re
from typing import Callable, Any

from pydantic import BaseModel, Field

from services.ai.context_builder import PatientContext
from services.ai.grounding import verify_claims
from services.ai.abbreviations import prompt_rules
from services.ai.prompt_config import prompt_settings
from services.ai_service import BaseAIProvider
from services.rules.compatibility import Facts
from services.rules.trials import evaluate_criterion, overall

class OptionClaim(BaseModel):
    text: str
    citations: list[str]


class OptionDraft(BaseModel):
    procedure_id: str = Field(description="ID dostupného postupu z nabídky v promptu")
    title: str
    rationale: list[OptionClaim]
    guideline_citations: list[str]
    considerations: list[str]


class OptionsDraft(BaseModel):
    options: list[OptionDraft] = Field(description="2 až 4 alternativy, bez řazení a doporučení")


OPTIONS_PROMPT = """Připrav 2 až 4 možnosti postupu k diskusi MDT podle dodaných guidelines.
Nevybírej ani neřaď preferovanou možnost, nepoužívej slovo doporučujeme. Každý bod rationale
musí popisovat doložené fakta pacienta a mít jejich ID citace. guideline_citations smí obsahovat
jen ID dodaných pasáží. Vyber procedure_id pouze z uvedeného katalogu. Co není v podkladech,
neodhaduj. Jazyk čeština. """


LIGHT_TEXT = {"green": "zelená (stav postup nevylučuje)", "orange": "oranžová (dávat pozor)",
              "red": "červená (stav postup vylučuje)", "grey": "šedá (nelze posoudit)", "skipped": "neposuzováno"}


def build_decision_support(context: PatientContext, resources: list[dict], compatibility: list[dict],
                           provider: BaseAIProvider, log_call: Callable[[str, dict], Any],
                           config: dict | None = None) -> dict:
    trials = screen_trials(context, resources)
    options = _treatment_options(context, compatibility, provider, log_call, config)
    questions = _discussion_questions(context, trials)
    return {
        "treatment_options": options,
        "trials": trials,
        "discussion_questions": questions,
        "disclaimer": "AI předkládá možnosti, nerozhoduje.",
    }


def _treatment_options(context: PatientContext, compatibility: list[dict], provider: BaseAIProvider,
                       log_call: Callable[[str, dict], Any], config: dict | None = None) -> list[dict]:
    available = {p["id"]: p for p in compatibility}
    if not available:
        return []
    draft = None
    if not provider.is_mock:
        # Menu z výsledků semaforu (katalog i báze data/onko, T-316), ne jen z katalogu
        menu = [{"procedure_id": p["id"], "title": p["title"], "guidelines": p.get("guideline_citations", [])}
                for p in compatibility]
        prompt = context.render() + "\n## Možnosti v katalogu\n" + repr(menu)
        system = f"{OPTIONS_PROMPT}\n\n{prompt_rules()}\n\n{prompt_settings(config, 'decision_support')}"
        result = provider.generate(prompt, system_prompt=system, response_schema=OptionsDraft, temperature=0.1)
        log_call("brief.decision_support", result)
        if result.get("status") == "success":
            draft = result.get("data")
    options = _sanitize_options(draft.get("options") or [], available, context) if draft else []
    # D-015: vždy všechny postupy ze sady guidelines, i červené; co LLM nezmínil, doplní katalog.
    covered = {o["id"] for o in options}
    return options + _fallback_options([p for p in compatibility if p["id"] not in covered], context)


def _sanitize_options(raw_options: list[dict], available: dict[str, dict], context: PatientContext) -> list[dict]:
    options, seen = [], set()
    for raw in raw_options:
        pid = raw.get("procedure_id")
        procedure = available.get(pid)
        if not procedure or pid in seen:
            continue
        seen.add(pid)
        rationale = []
        for index, claim in enumerate(raw.get("rationale") or [], 1):
            citations = list(dict.fromkeys(c for c in claim.get("citations", []) if c in context.allowed_ids))
            if not citations or not claim.get("text", "").strip():
                continue
            rationale.append({"id": f"{pid}-why-{index}", "kind": "claim", "text": claim["text"].strip(),
                              "citations": citations})
        rationale = verify_claims(rationale, context)
        p = procedure["compatibility"]
        guidelines = list(dict.fromkeys(c for c in raw.get("guideline_citations", [])
                                         if c in context.allowed_ids and c.startswith(("KRC-", "PRS-", "PLI-", "OBC-"))))
        if not guidelines:
            guidelines = [c for c in procedure.get("guideline_citations", []) if c in context.allowed_ids]
        options.append({
            "id": pid,
            "title": raw.get("title", "").strip() or procedure["title"],
            "rationale": rationale,
            "guideline_citations": guidelines,
            "prerequisites_missing": _missing_prerequisites(procedure, pid, context),
            "considerations": ([s.strip() for s in raw.get("considerations", []) if s.strip()]
                               if rationale else []),
            "compatibility": p,
        })
    return options


def _fallback_options(compatibility: list[dict], context: PatientContext) -> list[dict]:
    """Mock/offline output stays deterministic and keeps every catalogued alternative visible."""
    options = []
    for procedure in compatibility:
        pid = procedure["id"]
        comp = procedure["compatibility"]
        cited = list(dict.fromkeys(c for rule in comp["rules"] for c in rule["patient_citations"]
                                   if c in context.allowed_ids))
        rationale = []
        if cited:
            rationale = verify_claims([{"id": f"{pid}-why-1", "kind": "claim",
                                        "text": f"Soulad postupu se stavem pacienta: {LIGHT_TEXT.get(comp['overall'], comp['overall'])}.",
                                        "citations": cited, "_computed": True}], context)
        options.append({
            "id": pid,
            "title": procedure["title"],
            "rationale": rationale,
            "guideline_citations": [c for c in procedure.get("guideline_citations", [])
                                    if c in context.allowed_ids],
            "prerequisites_missing": _missing_prerequisites(procedure, pid, context),
            "considerations": [],
            "compatibility": comp,
        })
    return options


def _missing_prerequisites(procedure: dict, procedure_id: str, context: PatientContext) -> list[dict]:
    missing = []
    for index, rule in enumerate(procedure["compatibility"]["rules"], 1):
        if rule["status"] not in ("grey", "skipped"):
            continue
        source = rule.get("rule_citation")
        missing.append({
            "id": f"{procedure_id}-missing-{index}", "kind": "missing", "text": rule["text"],
            "citations": [c for c in rule["patient_citations"] if c in context.allowed_ids],
            "expected_source": source if source in context.allowed_ids else None,
            "verification": "verified",
        })
    return missing


def _discussion_questions(context: PatientContext, trials: list[dict]) -> list[dict]:
    questions, seen = [], set()
    rkt06 = next((trial for trial in context.trials if trial.study_id == "RKT-06" and trial.protocol), None)
    if rkt06:
        anemia = [line.id for line in context.evidence if re.search(r"anemi|hemoglobin|\bHb\b", line.text, re.I)]
        anemia = list(dict.fromkeys(anemia))[-5:]
        if anemia:
            questions.append({
                "text": f"Jak na pacientku použít dávkovací protokol studie: {rkt06.protocol}?",
                "citations": ["RKT-06", *anemia],
            })
            seen.update(anemia)
    for flag in context.red_flags:
        citations = [c for c in flag.citations if c in context.allowed_ids]
        if citations and not set(citations) <= seen:
            questions.append({"text": f"Jak ověřit a zohlednit upozornění: {flag.title}?", "citations": citations})
            seen.update(citations)
        if len(questions) == 2:
            break
    if len(questions) < 2:
        for trial in trials:
            for criterion in trial["criteria"]:
                if criterion["status"] == "unknown":
                    citations = [criterion["criterion_id"]] + criterion["citations"]
                    questions.append({"text": f"Jak doplnit nebo posoudit: {criterion['missing'] or criterion['text']}?",
                                      "citations": [c for c in citations if c in context.allowed_ids]})
                    if len(questions) == 2:
                        break
            if len(questions) == 2:
                break
    if len(questions) < 3:
        request_id = context.facts.get("service_request_id")
        question_id = f"{request_id}#1" if request_id else None
        if question_id not in context.allowed_ids and request_id in context.allowed_ids:
            question_id = request_id
        question_text = context.facts.get("mdt_question")
        if question_id and question_text and question_id in context.allowed_ids and question_id not in seen:
            questions.append({"text": f"Jak zodpovědět otázku nominace: {question_text}", "citations": [question_id]})
    return questions[:3]


def screen_trials(context: PatientContext, resources: list[dict]) -> list[dict]:
    """Evaluate every criterion of every diagnosis-relevant trial, preserving unknowns."""
    facts = Facts(resources)
    result = []
    for trial in context.trials:
        criteria = []
        for criterion in trial.criteria:
            evaluated = evaluate_criterion(criterion.evidence_id, facts)
            if evaluated is None:
                status, citations = "unknown", []
                missing = "Kritérium vyžaduje individuální posouzení týmem MDT"
            else:
                status = evaluated.status
                citations = [citation for citation in evaluated.citations if citation in context.allowed_ids]
                missing = evaluated.missing
                if status != "unknown" and not citations:
                    status, missing = "unknown", "Citaci podkladu se nepodařilo ověřit"
            item = {
                "criterion_id": criterion.evidence_id,
                "text": criterion.text,
                "kind": criterion.kind,
                "status": status,
                "citations": citations,
            }
            if missing:
                item["missing"] = missing
            criteria.append(item)
        result.append({
            "study_id": trial.study_id,
            "title": trial.title,
            "overall": overall(criteria),
            "criteria": criteria,
        })
    return result
