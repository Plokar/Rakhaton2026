"""
Generátor podkladu: blok A (souhrn, časová osa, hlavička D-018) + red flags (ARCHITEKTURA §5.1–5.4, T-106).

- Hlavička (D-018), časová osa, chybějící údaje a red flags jsou deterministické z FHIR.
- Souhrn píše LLM (Gemini, `response_schema`) jen nad kontextem pacienta; když volání selže nebo
  běží mock, použije se deterministický souhrn z dat (demo bez sítě, NFR-5).
- Každé tvrzení projde grounding validátorem v1 (`services/ai/grounding.py`).

Rozhraní pro joby (T-107): `generate_brief(case, config, progress) -> dict` vrací `Brief` (§8.2).
Jádro `build_brief()` je čistá funkce nad FHIR resources (testy bez IRIS a bez Djanga).
"""
from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from pydantic import BaseModel, Field

from services.ai.abbreviations import prompt_rules
from services.ai.context_builder import PatientContext, context_from_resources, load_resources
from services.ai.anamnesis import anamnesis_items, anamnesis_verbatim
from services.ai.decision_support import build_decision_support
from services.ai.diagnosis_data import modality_items
from services.ai.grounding import verify_claims
from services.ai.guidelines import GuidelinesUnavailable, load_guidelines
from services.ai.red_flags_llm import detect_llm_red_flags
from services.ai.prompt_config import output_limit, prompt_settings
from services.ai.roles import load_roles, role_section
from services.ai_service import BaseAIProvider, get_ai_provider
from services.fhir.values import cc_text, fhir_code, ref_id
from services.rules import red_flags as rules
from services.rules.alerts import header_alerts
from services.rules.compatibility import evaluate_compatibility
from services.rules.onko_kb import kb_for_patient
from services.rules.guideline_sets import guideline_sets_for
from services.rules.intake import intake_prefill
from services.rules.red_flags import PatientData

log = logging.getLogger(__name__)

SUMMARY_PROMPT = (Path(__file__).parent / "prompts" / "summary.md").read_text(encoding="utf-8")
SEX_CS = {"male": "muž", "female": "žena", "other": "jiné", "unknown": "neuvedeno"}
INTENT = {"kurativni": "C", "paliativni": "P"}
INTENT_CODE = {"C": "kurativni", "P": "paliativni"}

DEFAULT_SECTIONS = ["summary", "timeline", "red_flags", "anamnesis", "role_views", "modalities",
                    "decision_support", "trials", "questions", "mdt_question"]
DEFAULT_CONFIG = {
    "name": "Výchozí podklad",
    "sections": [{"id": s, "enabled": True, "order": i + 1} for i, s in enumerate(DEFAULT_SECTIONS)],
    "roles_present": ["surgeon", "oncologist", "radiologist", "pathologist", "patient"],
    "detail_level": "standard",
    "language": "cs",
    "hide_unverified": False,
}
TITLES = {"summary": "Souhrn případu", "timeline": "Časová osa", "anamnesis": "Anamnéza",
          "modalities": "Léčebné metody a odborníci"}


# ── Výstup LLM (response_schema) ──────────────────────────────────────────────
class SummaryItem(BaseModel):
    text: str = Field(description="Jeden bod souhrnu, česky, čísla a data přesně podle zdrojů")
    citations: list[str] = Field(description="ID zdrojů z podkladů, např. P03-img03#4")


class SummaryOutput(BaseModel):
    items: list[SummaryItem] = Field(description="3 až 5 bodů souhrnu")


# ── Veřejné API ───────────────────────────────────────────────────────────────
def generate_brief(case, config: dict, progress: Callable[[int], None], *,
                   provider: BaseAIProvider | None = None, log_call: Callable[[str, dict], Any] | None = None) -> dict:
    """Job generátoru (T-107): načte pacienta z IRIS a vrátí `Brief` (§8.2)."""
    progress(5)
    resources, studies = load_resources(case.patient_fhir_id)
    progress(25)
    sets = guideline_sets_for(rules.PatientData(resources).icd10)
    try:
        passages = load_guidelines(sets)
    except GuidelinesUnavailable as exc:          # blok A guidelines nutně nepotřebuje
        log.warning("Guidelines nejsou k dispozici: %s", exc)
        passages = []
    if log_call is None:
        log_call = _llm_call_log
    return build_brief(
        case.patient_fhir_id, resources, studies=studies, guidelines=passages, config=config,
        provider=provider, case_id=str(case.pk), skipped_fields=getattr(case, "skipped_fields", None) or [],
        intent_letter=getattr(case, "intent", None), progress=progress, log_call=log_call,
    )


def build_brief(patient_id: str, resources: list[dict], *, studies: Iterable[dict] = (), guidelines: Iterable = (),
                config: dict | None = None, provider: BaseAIProvider | None = None, case_id: str = "",
                skipped_fields: Iterable[str] = (), intent_letter: str | None = None,
                progress: Callable[[int], None] = lambda _: None,
                log_call: Callable[[str, dict], Any] = lambda purpose, result: None) -> dict:
    """Čisté jádro: FHIR resources → `Brief` (§8.2)."""
    config = _merge_config(config)
    provider = provider or get_ai_provider()
    flags = rules.evaluate(resources, config.get("roles_present"))
    context = context_from_resources(patient_id, resources, studies=studies, guidelines=guidelines, red_flags=flags)
    data = PatientData(resources)
    progress(35)

    enabled = {s["id"] for s in config["sections"] if s.get("enabled", True)}
    roles = list(dict.fromkeys(config.get("roles_present") or [])) if "role_views" in enabled else []
    needs_decision_support = bool(enabled & {"decision_support", "trials", "questions"})
    compatibility = (evaluate_compatibility(resources, skipped_fields=skipped_fields)
                     if roles or needs_decision_support or "modalities" in enabled else [])
    # T-316: další postupy z báze data/onko jen do B2 a bloku metod; pohledy rolí stojí na katalogu
    kb = kb_for_patient(resources, context.allowed_ids) if needs_decision_support or "modalities" in enabled else []
    with ThreadPoolExecutor(max_workers=4 + len(roles)) as pool:          # všechna LLM volání paralelně (NFR-1)
        summary_future = pool.submit(_summary_items, context, provider, log_call, config) if "summary" in enabled else None
        llm_flags_future = pool.submit(_llm_flags, context, provider, log_call, config) if "red_flags" in enabled else None
        role_futures = [pool.submit(role_section, role, context, data, compatibility, provider, log_call, config)
                        for role in roles]
        anamnesis_future = (pool.submit(anamnesis_items, context, provider, log_call, config)
                            if "anamnesis" in enabled else None)
        ds_future = (pool.submit(build_decision_support, context, resources, compatibility + kb, provider, log_call, config)
                     if needs_decision_support else None)
        summary_items = summary_future.result() if summary_future else []
        llm_flags = llm_flags_future.result() if llm_flags_future else []
        role_sections = [future.result() for future in role_futures]
        decision_support = ds_future.result() if ds_future else None
        anamnesis = anamnesis_future.result() if anamnesis_future else []
    progress(75)

    sections = []
    for section in sorted(config["sections"], key=lambda s: s.get("order", 0)):
        if not section.get("enabled", True):
            continue
        if section["id"] == "role_views":
            sections += [{**rs, "items": [_public(c) for c in verify_claims(rs["items"], context)]}
                         for rs in role_sections]
            continue
        if section["id"] not in TITLES:
            continue
        verbatim = []
        if section["id"] == "summary":
            items = summary_items + _missing_items(resources, skipped_fields)
        elif section["id"] == "anamnesis":            # FR-A5 (T-507): shrnutí AI + doslovné znění k přepnutí
            items = anamnesis
            verbatim = anamnesis_verbatim(context)
        elif section["id"] == "modalities":           # FR-D5 (T-506)
            items = modality_items(context, compatibility + kb, {r: c["title"] for r, c in load_roles().items()})
        else:
            items = _timeline_items(data, context)
        sections.append({"id": section["id"], "title": TITLES[section["id"]], "ai_generated": True,
                         "items": [_public(c) for c in verify_claims(items, context)],
                         **({"verbatim": [_public(c) for c in verify_claims(verbatim, context)]} if verbatim else {})})
    progress(90)

    header = _header(data, context, intent_letter)
    header["alerts"] = [_public(c) for c in verify_claims(header["alerts"], context)]
    claims = [c for s in sections for c in s["items"]] + header["alerts"]
    if decision_support:
        claims += [c for option in decision_support["treatment_options"] for c in option["rationale"]]
        claims += [c for option in decision_support["treatment_options"] for c in option["prerequisites_missing"]]
    red_flags = [f.as_dict() for f in flags + llm_flags] if "red_flags" in enabled else []
    brief = {
        "case_id": case_id,
        "patient_id": patient_id,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": getattr(provider, "model_name", None) or _model_name(provider),
        "config": config,
        "status": "draft",
        "header": header,
        "sections": sections,
        "red_flags": red_flags,
        "decision_support": decision_support,
        "stats": {
            "claims_total": sum(1 for c in claims if c["kind"] == "claim"),
            "claims_unverified": sum(1 for c in claims if c["kind"] == "claim" and c["verification"] == "unverified"),
            "missing_total": sum(1 for c in claims if c["kind"] == "missing"),
        },
    }
    progress(100)
    return brief


# ── Pomocné funkce ────────────────────────────────────────────────────────────
def _merge_config(config: dict | None) -> dict:
    """Konfigurace z presetu (§8.5) doplněná o výchozí hodnoty; prázdný seznam = nenastaveno."""
    return {**DEFAULT_CONFIG, **{k: v for k, v in (config or {}).items() if v is not None and v != []}}


def _model_name(provider: BaseAIProvider) -> str:
    from services.ai_service import ai_model
    return "mock" if provider.is_mock else ai_model()


def _public(claim: dict) -> dict:
    return {k: v for k, v in claim.items() if not k.startswith("_")}


def _llm_call_log(purpose: str, result: dict) -> None:
    try:
        from apps.copilot.models import LlmCallLog
        LlmCallLog.record(purpose, result)
    except Exception:                                  # audit nesmí shodit generování
        log.exception("Nepodařilo se zapsat LlmCallLog (%s)", purpose)


def _summary_items(context: PatientContext, provider: BaseAIProvider, log_call, config: dict | None = None) -> list[dict]:
    prompt = context.render()
    system = f"{SUMMARY_PROMPT}\n\n{prompt_rules()}\n\n{prompt_settings(config, 'summary')}"
    result = provider.generate(prompt, system_prompt=system,
                               response_schema=SummaryOutput, temperature=0.1)
    log_call("brief.summary", result)
    items = (result.get("data") or {}).get("items") or [] if result.get("status") == "success" else []
    claims = [{"id": f"sum-{i:02d}", "kind": "claim", "text": item["text"].strip(),
               "citations": list(dict.fromkeys(item["citations"]))} for i, item in enumerate(items, 1)
              if item.get("text", "").strip()]
    if claims:
        return claims[:output_limit(config, "summary")]
    if result.get("status") != "success":
        log.warning("Souhrn z LLM selhal (%s), použije se souhrn z dat", result.get("error"))
    return _fallback_summary(context)[:output_limit(config, "summary")]


def _llm_flags(context: PatientContext, provider: BaseAIProvider, log_call,
               config: dict | None = None) -> list[rules.RedFlag]:
    flags, result = detect_llm_red_flags(context, provider, config=config)
    log_call("brief.rf_llm", result)
    return flags


def _fallback_summary(context: PatientContext) -> list[dict]:
    """Souhrn z dat bez LLM: diagnóza + TNM, poslední zobrazení, ECOG lékař vs. pacient, otázka."""
    facts, items = context.facts, []
    by_id = {line.id: line for line in context.evidence}
    diagnoses = facts.get("diagnoses") or []
    if diagnoses:
        tnm = next((line for line in context.evidence if line.resource_type == "Observation"
                    and line.text.startswith("Staging – TNM")), None)
        text = "; ".join(f"{d['icd10']} {d['text']}" for d in diagnoses)
        if tnm:
            text += f"; {tnm.text.split(': ', 1)[-1].split(' · ')[0]}"
        items.append(("Diagnóza: " + text, [d["id"] for d in diagnoses] + ([tnm.id] if tnm else [])))
    imaging = [line for line in context.evidence if line.group == "imaging" and line.paragraph
               and line.text.startswith("Závěr")]
    if imaging:
        last = max(imaging, key=lambda line: (line.date, line.id))
        items.append((f"Poslední zobrazení ({last.date}): {last.text.split(':', 1)[1].strip()}", [last.id]))
    ecog = [line for line in context.evidence if line.text.startswith("ECOG – hodnoceno lékařem")]
    proms = [line for line in context.evidence if line.resource_type == "QuestionnaireResponse"]
    if ecog:
        physician = max(ecog, key=lambda line: (line.date, line.id))
        value = physician.text.split(":", 1)[1].split("·")[0].strip()
        text, citations = f"ECOG podle lékaře {value} ({physician.date})", [physician.id]
        if proms:
            last = max(proms, key=lambda line: (line.date, line.id))
            match = re.search(r"samostatnost \(ECOG podle pacienta\): (\d)", last.text)
            if match:
                text += f", podle pacienta {match.group(1)} ({last.date})"
                citations.append(last.id)
        items.append((text, citations))
    question = by_id.get(f"{facts.get('service_request_id')}#1")
    if question:
        items.append((question.text, [question.id]))
    return [{"id": f"sum-{i:02d}", "kind": "claim", "text": text, "citations": citations}
            for i, (text, citations) in enumerate(items, 1)]


def _missing_items(resources: list[dict], skipped_fields: Iterable[str]) -> list[dict]:
    """Chybějící povinné údaje (T-502) jako `kind: "missing"`; přeskočené „Chybí (přeskočeno lékařem)“ (D-019)."""
    prefill = intake_prefill(resources, skipped_fields)
    items = []
    for field in prefill["fields"]:
        if field["status"] == "present":
            continue
        if field["status"] == "skipped":
            text = f"{field['label']}: Chybí (přeskočeno lékařem)"
        elif field["status"] == "pending":
            text = f"{field['label']}: čeká se na výsledek ({field.get('value', '')})".replace(" ()", "")
        else:
            text = f"{field['label']}: údaj chybí v podkladech" + (f" ({field['value']})" if field.get("value") else "")
        items.append({"id": f"miss-{field['id']}", "kind": "missing", "text": text,
                      "citations": [field["citation"]] if field.get("citation") else [],
                      "expected_source": f"povinné podle {field['required_by']}" if field.get("required_by") else None})
    # T-318: povinné údaje znalostní báze, které formulář nehlídá (`CHYBI:*`), např. P04 osmolalita při Na 129
    resource_ids = {r["id"] for r in resources}
    for w in prefill["warnings"]:
        if not w["id"].startswith("CHYBI:"):
            continue
        patient = [c for c in w["citations"] if c in resource_ids]
        sources = [c for c in w["citations"] if c not in resource_ids]
        items.append({"id": f"miss-{w['id']}", "kind": "missing",
                      "text": f"{w['title'].removeprefix('Chybí: ')}: údaj chybí v podkladech ({w['detail'].rstrip('.')})",
                      "citations": patient,
                      "expected_source": f"povinné podle {', '.join(sources)}" if sources else None})
    return [{k: v for k, v in item.items() if v is not None} for item in items]


def _paragraph_starting(context: PatientContext, resource_id: str, prefix: str):
    return next((line for line in context.evidence if line.resource_id == resource_id and line.paragraph
                 and line.text.startswith(prefix)), None)


def _short(text: str, limit: int = 180) -> str:
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


def _timeline_items(data: PatientData, context: PatientContext) -> list[dict]:
    """Časová osa z FHIR (FR-A3): diagnózy, výkony, patologie, zobrazení, léčba, předchozí MDT, PROMs."""
    events: list[tuple[str, str, list[str]]] = []
    for c in data.oncologic:
        onset = c.get("onsetDateTime", "")
        if onset:
            events.append((onset[:10], f"Diagnóza: {fhir_code(c.get('code'), 'icd-10')} {cc_text(c.get('code'))}",
                           [c["id"]]))
    for p in data.by_type.get("Procedure", []):
        when = p.get("performedDateTime") or p.get("performedPeriod", {}).get("start", "")
        if when:
            events.append((when[:10], f"{cc_text(p.get('category')).capitalize()}: {cc_text(p.get('code'))}",
                           [p["id"]]))
    for r in data.by_type.get("DiagnosticReport", []):
        section = fhir_code((r.get("category") or [{}])[0], "v2-0074")
        if section not in ("RAD", "SP"):
            continue
        conclusion = _paragraph_starting(context, r["id"], "Závěr")
        label = cc_text(r.get("code"))
        text = f"{label}: {conclusion.text.split(':', 1)[1].strip()}" if conclusion else label
        citations = [r["id"]] + ([conclusion.id] if conclusion else [])     # název zprávy je v řádku resource
        events.append((r.get("effectiveDateTime", "")[:10], _short(text), citations))
    regimens: dict[str, list[dict]] = {}
    for m in data.by_type.get("MedicationAdministration", []):
        regimens.setdefault(cc_text(m.get("category")) or cc_text(m.get("medicationCodeableConcept")), []).append(m)
    for regimen, doses in regimens.items():
        doses.sort(key=lambda m: m.get("effectiveDateTime", ""))
        first, last = doses[0], doses[-1]
        dates = sorted({d.get("effectiveDateTime", "")[:10] for d in doses})
        span = f"{dates[0]} až {dates[-1]}" if len(dates) > 1 else dates[0]     # počet podání ve zdroji není
        events.append((dates[0], f"{regimen}: podání {span}", [first["id"], last["id"]]))
    for comp in data.by_type.get("Composition", []):
        if fhir_code(comp.get("type"), "mdt-typ-zaznamu") != "mdt-zaznam":
            continue
        conclusion = _paragraph_starting(context, comp["id"], "Závěr MDT")
        text = conclusion.text.split(":", 1)[1].strip() if conclusion else cc_text(comp.get("type"))
        citation = conclusion.id if conclusion else comp["id"]
        events.append((comp.get("date", "")[:10], _short(f"MDT: {text}"), [citation]))
    for qr in data.proms:
        events.append((qr.get("authored", "")[:10], "Dotazník pacienta (PROMs)", [qr["id"]]))
    events = sorted((e for e in events if e[0]), key=lambda e: (e[0], e[1]))
    return [{"id": f"tl-{i:02d}", "kind": "claim", "text": f"{date} · {text}", "citations": citations}
            for i, (date, text, citations) in enumerate(events, 1)]


def _header(data: PatientData, context: PatientContext, intent_letter: str | None) -> dict:
    """Hlavička D-018: `Pxx · pohlaví · věk`, diagnóza + TNM, ECOG lékař i pacient, záměr C/P, otázka."""
    facts = context.facts
    nominated = [ref_id(r) for r in data.request.get("reasonReference", [])]
    primary = next((c for c in data.oncologic if c["id"] in nominated and not re.match(
        r"C7[789]", fhir_code(c.get("code"), "icd-10"))), None) or (data.oncologic or [{}])[0]
    tnm_obs = [o for o in data.by_category("Staging") if any(ref_id(f) == primary.get("id")
                                                             for f in o.resource.get("focus", []))]
    tnm_obs = tnm_obs or data.by_category("Staging")
    tnm = None
    if tnm_obs:
        last = tnm_obs[-1]
        value = str(last.value or "")
        stage = re.search(r"stadium\s+([IV]+[ABC]?\d?)", value)
        tnm = {"text": value.split(",")[0].strip(), "stage": stage.group(1) if stage else None, "citation": last.id}

    ecog = {}
    physician = data.by_loinc("ecog")
    if physician:
        last = physician[-1]
        performer = [ref_id(p) for p in last.resource.get("performer", [])]
        ecog["physician"] = {"value": int(last.value), "date": str(last.date), "citation": last.id,
                             **({"entered_by": performer[0]} if performer else {})}
    qr = next((q for q in reversed(data.proms) if str(data.answers(q).get("samostatnost", "")).isdigit()), None)
    if qr:
        answer = next((i["answer"][0]["valueCoding"] for i in qr.get("item", []) if i.get("linkId") == "samostatnost"
                       and i.get("answer")), {})
        ecog["patient"] = {"value": int(answer.get("code")), "date": qr.get("authored", "")[:10], "citation": qr["id"],
                           "answer_text": answer.get("display", "")}

    intent = None
    if intent_letter in INTENT_CODE:
        intent = {"letter": intent_letter, "code": INTENT_CODE[intent_letter], "source": "physician"}
    else:
        plans = sorted(data.by_type.get("CarePlan", []), key=lambda c: c.get("created", ""))
        code = fhir_code((plans[-1].get("category") or [{}])[0], "mdt-lecebny-zamer") if plans else ""
        if code in INTENT:
            intent = {"letter": INTENT[code], "code": code, "source": "previous_mdt"}

    question_id = f"{data.request.get('id')}#1"
    comorbidities = [{"text": cc_text(c.get("code")), "icd10": fhir_code(c.get("code"), "icd-10") or None,
                      "citation": c["id"]}
                     for c in data.conditions if "komorbid" in cc_text((c.get("category") or [{}])[0]).lower()]
    return {
        "display_name": f"{data.patient_id} · {SEX_CS.get(facts.get('sex'), 'neuvedeno')} · {facts.get('age')} let",
        "age": facts.get("age") or 0,
        "sex": facts.get("sex") or "unknown",
        "diagnosis": {"text": cc_text(primary.get("code")), "icd10": fhir_code(primary.get("code"), "icd-10"),
                      "citation": primary.get("id", data.patient_id)},
        "tnm": tnm,
        "ecog": ecog,
        "intent": intent,
        "mdt_question": {"text": facts.get("mdt_question") or "", "citation": question_id},
        "mdt_date": data.task.get("restriction", {}).get("period", {}).get("start", ""),
        "comorbidities": [{k: v for k, v in c.items() if v is not None} for c in comorbidities],
        "alerts": header_alerts(data.resources),
    }
