"""
Pohledy odborníků a posouzení role (blok B, FR-B1 až FR-B7, ARCHITEKTURA §5.5, T-201).

Pro každou přítomnou roli jedno volání LLM (souběžně se souhrnem, NFR-1). Výstup:
`BriefSection` (§8.2) s `role`, tvrzeními a `RoleAssessment` (verdikt po kritériích s citacemi).

- Kritérium s citací mimo kontext se nezapočítá jako splněné / nesplněné: stav `unknown`.
- Když LLM selže nebo běží mock: tvrzení z dat podle zaměření role a posouzení deterministicky ze
  semaforu postupů, za které role odpovídá (red → not_candidate, orange → conditional, …).
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Literal, Optional

import yaml
from pydantic import BaseModel, Field

from services.ai.abbreviations import prompt_rules
from services.ai.context_builder import PatientContext
from services.ai.recist import recist_claim
from services.ai_service import BaseAIProvider
from services.rules.compatibility import CHECKS, load_catalog
from services.rules.red_flags import PatientData

log = logging.getLogger(__name__)

ROLES_FILE = Path(__file__).parent / "data" / "roles.yaml"
ROLE_PROMPT = (Path(__file__).parent / "prompts" / "role_view.md").read_text(encoding="utf-8")
NOTE = "Podklad pro diskusi, rozhoduje lékař."
FALLBACK_NOTE = "Podklad pro diskusi, rozhoduje lékař. Posouzení vychází z pravidel semaforu se zdroji (bez AI)."
STATUS_FROM_LIGHT = {"green": "met", "red": "not_met", "orange": "unknown", "grey": "unknown", "skipped": "unknown"}
VERDICT_ORDER = ["candidate", "conditional", "insufficient_data", "not_candidate"]
VERDICT_FROM_LIGHT = {"green": "candidate", "orange": "conditional", "grey": "insufficient_data",
                      "skipped": "insufficient_data", "red": "not_candidate"}
RADIOLOGY_RULES = {"OBC": ["VS-OBC-09", "VS-OBC-10"], "KRC": ["VS-KRC-02"], "PLI": ["VS-PLI-05"]}


# ── Výstup LLM (response_schema) ──────────────────────────────────────────────
class RoleItem(BaseModel):
    text: str
    citations: list[str] = Field(description="ID zdrojů z podkladů")


class RoleCriterion(BaseModel):
    text: str
    status: Literal["met", "not_met", "unknown"]
    citations: list[str] = Field(description="Fakta pacienta")
    guideline: Optional[str] = Field(default=None, description="ID pasáže guidelines, např. KRC-2.1")
    missing: Optional[str] = Field(default=None, description="U unknown: co je třeba doplnit")


class RoleAssessmentOutput(BaseModel):
    question: str
    verdict: Literal["candidate", "conditional", "not_candidate", "insufficient_data"]
    criteria: list[RoleCriterion]


class RoleViewOutput(BaseModel):
    items: list[RoleItem] = Field(description="3 až 6 bodů pro odbornost")
    assessment: Optional[RoleAssessmentOutput] = None


@lru_cache(maxsize=1)
def load_roles() -> dict:
    return yaml.safe_load(ROLES_FILE.read_text(encoding="utf-8"))


def role_question(role: str, guideline_sets: list[str]) -> str | None:
    questions = load_roles()[role].get("question") or {}
    return next((questions[s] for s in guideline_sets if s in questions), None)


# ── Sekce role ────────────────────────────────────────────────────────────────
def role_section(role: str, context: PatientContext, data: PatientData, compatibility: list[dict],
                 provider: BaseAIProvider, log_call: Callable[[str, dict], Any]) -> dict:
    cfg = load_roles()[role]
    question = role_question(role, context.guideline_sets)
    system = (f"{ROLE_PROMPT}\n\nTvoje role: {cfg['title']}. Zaměř se na: {cfg['focus']}.\n"
              + (f"Otázka posouzení: {question}\n" if question else "Posouzení role (assessment) nevyplňuj.\n")
              + "\n" + prompt_rules())
    result = provider.generate(context.render(), system_prompt=system, response_schema=RoleViewOutput,
                               temperature=0.1)
    log_call(f"brief.role.{role}", result)
    output = result.get("data") if result.get("status") == "success" else None

    items = [{"id": f"{role}-{i:02d}", "kind": "claim", "text": item["text"].strip(),
              "citations": list(dict.fromkeys(item["citations"]))}
             for i, item in enumerate((output or {}).get("items") or [], 1) if item.get("text", "").strip()]
    if not items:
        items = _fallback_items(role, cfg, context, data)
    if role == "radiologist":
        recist = recist_claim(context, provider, log_call)
        if recist:
            items.append(recist)

    assessment = None
    if question:
        llm_assessment = (output or {}).get("assessment")
        assessment = (_sanitize_assessment(role, question, llm_assessment, context) if llm_assessment
                      else _fallback_assessment(role, question, cfg, context, data, compatibility))
    return {"id": "role_views", "role": role, "title": cfg["title"], "ai_generated": True, "items": items,
            **({"assessment": assessment} if assessment else {})}


def _sanitize_assessment(role: str, question: str, raw: dict, context: PatientContext) -> dict:
    allowed = context.allowed_ids
    criteria = []
    for c in raw.get("criteria") or []:
        citations = [x for x in dict.fromkeys(c.get("citations") or []) if x in allowed]
        status, missing = c["status"], c.get("missing")
        if status != "unknown" and not citations:            # tvrzení bez ověřitelné citace nesmí rozhodovat
            status, missing = "unknown", missing or "Citace kritéria se nepodařilo ověřit."
        guideline = c.get("guideline") if c.get("guideline") in allowed else None
        criteria.append({k: v for k, v in {"text": c["text"], "status": status, "citations": citations,
                                           "guideline": guideline, "missing": missing}.items() if v is not None})
    verdict = raw["verdict"] if criteria else "insufficient_data"
    return {"role": role, "question": question, "verdict": verdict, "criteria": criteria, "note": NOTE}


def _fallback_assessment(role: str, question: str, cfg: dict, context: PatientContext, data: PatientData,
                         compatibility: list[dict]) -> dict | None:
    allowed = context.allowed_ids
    criteria, lights = [], []
    if role == "radiologist":
        catalog = load_catalog()
        sets = list(dict.fromkeys(["OBC", *context.guideline_sets]))
        rule_ids = [r for s in sets for r in RADIOLOGY_RULES.get(s, [])]
        facts = _facts(data)
        for rule_id in rule_ids:
            rule = catalog["rules"][rule_id]
            result = CHECKS[rule["check"]](facts, rule)
            if result is None:
                continue
            lights.append(result.status)
            criteria.append(_criterion(f"{rule['title']}: {result.text}", result.status, result.patient_citations,
                                       rule["source"], allowed))
    else:
        procedures = [p for p in compatibility if p["compatibility"]["modality"] in cfg.get("modalities", [])]
        for procedure in procedures:
            lights.append(procedure["compatibility"]["overall"])
            prefix = f"{procedure['title'].split(' (')[0]}: " if len(procedures) > 1 else ""
            for rule in procedure["compatibility"]["rules"]:
                criteria.append(_criterion(prefix + rule["text"], rule["status"], rule["patient_citations"],
                                           rule["rule_citation"], allowed))
    if not criteria:
        return None
    if role == "radiologist":
        verdict = VERDICT_FROM_LIGHT[min(lights, key=["red", "orange", "grey", "skipped", "green"].index)]
    else:   # kandidát aspoň jednoho postupu z jeho oboru
        verdict = min((VERDICT_FROM_LIGHT[light] for light in lights), key=VERDICT_ORDER.index)
    return {"role": role, "question": question, "verdict": verdict, "criteria": criteria, "note": FALLBACK_NOTE}


def _criterion(text: str, light: str, citations: list[str], source: str | None, allowed: set[str]) -> dict:
    status = STATUS_FROM_LIGHT[light]
    item = {"text": text, "status": status, "citations": [c for c in citations if c in allowed]}
    if source in allowed:
        item["guideline"] = source
    if status == "unknown":
        item["missing"] = "Údaj chybí nebo je hraniční, viz text kritéria." if light != "skipped" \
            else "Údaj lékař přeskočil."
    return item


def _facts(data: PatientData):
    from services.rules.compatibility import Facts
    return Facts(data.resources)


# ── Tvrzení z dat (bez LLM) ───────────────────────────────────────────────────
_NOISE = re.compile(r"\s*·\s*(zdroj|hodnotil|vzorek|týká se): [^·]*")


def _fallback_items(role: str, cfg: dict, context: PatientContext, data: PatientData) -> list[dict]:
    if role == "patient":
        return _patient_items(data)
    items = []
    for selector in cfg.get("evidence", []):
        pattern = re.compile(selector["pattern"], re.IGNORECASE)
        lines = [line for line in context.evidence if line.group == selector["group"] and pattern.search(line.text)]
        if selector.get("last"):
            lines = sorted(lines, key=lambda line: (line.date, line.id))[-selector["last"]:]
        for line in lines:
            text = _NOISE.sub("", line.text).strip()
            items.append({"kind": "claim", "text": f"{line.date} · {text}" if line.date else text,
                          "citations": [line.id]})
    unique = list({item["text"]: item for item in items}.values())[:8]
    if not unique:      # role je přítomná, ale podklady pro ni nemají nic specifického
        text = f"Pro odbornost {cfg['title'].lower()} nejsou v podkladech specifické údaje."
        unique = [{"kind": "missing", "text": text, "citations": []}]
    return [{"id": f"{role}-{i:02d}", **item} for i, item in enumerate(unique, 1)]


SYMPTOMS = {"bolest": "bolest", "unava": "únava", "nevolnost": "nevolnost", "dusnost": "dušnost",
            "chut": "chuť k jídlu", "brneni": "brnění", "prujem": "průjem", "psychika": "psychika", "spanek": "spánek"}


def _patient_items(data: PatientData) -> list[dict]:
    if not data.proms:
        return []
    last = data.proms[-1]
    answers = data.answers(last)
    before = data.answers(data.proms[-2]) if len(data.proms) > 1 else {}
    cites = [last["id"]] + ([data.proms[-2]["id"]] if before else [])
    items = []
    burden = []
    for link, label in SYMPTOMS.items():
        value = answers.get(link)
        if isinstance(value, (int, float)) and value >= 5:
            previous = before.get(link)
            trend = f" (dříve {previous}/10)" if isinstance(previous, (int, float)) else ""
            burden.append(f"{label} {value}/10{trend}")
    if burden:
        items.append(("Výrazné symptomy: " + ", ".join(burden), cites))
    displays = {i["linkId"]: i["answer"][0].get("valueCoding", {}).get("display")
                for i in last.get("item", []) if i.get("answer")}
    if displays.get("samostatnost"):
        items.append((f"Samostatnost (ECOG podle pacienta {answers.get('samostatnost')}): {displays['samostatnost']}",
                      [last["id"]]))
    for link, label in (("nove-obtize", "Nové obtíže"), ("postoj", "Co mají lékaři vědět"),
                        ("leky-mimo", "Léky a doplňky navíc")):
        value = str(answers.get(link) or "").strip()
        if value and value.lower() not in ("nic", "nic nového", "ne"):
            items.append((f"{label}: „{value}“", [last["id"]]))
    for link, label in (("priorita", "Priorita"), ("podpora", "Podpora doma")):
        if displays.get(link):
            items.append((f"{label}: {displays[link]}", [last["id"]]))
    return [{"id": f"patient-{i:02d}", "kind": "claim", "text": text, "citations": citations}
            for i, (text, citations) in enumerate(items, 1)]
