"""Anamnéza ze zpráv (FR-A5, T-507): sekce OA, FA, RA, SA, GA, NO, alergie.

Z odstavců `DocumentReference` vezme pro každou sekci nejnovější znění s citací odstavce. Krátkou anamnézu
(do `INTAKE_ANAMNESIS_MAX_CHARS`, výchozí 600 znaků) dá doslovně, dlouhou zkrátí LLM na shrnutí s citacemi.
Když LLM selže nebo běží mock, zůstane doslovné znění zkrácené na první větu (nic se nedomýšlí).
"""
from __future__ import annotations

import os
import re
from typing import Any, Callable

from pydantic import BaseModel, Field

from services.ai.abbreviations import prompt_rules
from services.ai.context_builder import PatientContext
from services.ai.prompt_config import prompt_settings
from services.ai_service import BaseAIProvider

LABELS = {
    "NO": "Nynější onemocnění", "OA": "Osobní anamnéza", "FA": "Farmakologická anamnéza", "Alergie": "Alergie",
    "RA": "Rodinná anamnéza", "GA": "Gynekologická anamnéza", "SA": "Sociální anamnéza", "Anamnéza": "Anamnéza",
}
MARKER = re.compile(r"(?:^|(?<=[\s.]))(Léková anamnéza|OA|FA|RA|SA|GA|NO|Alergie|Anamnéza)\s*:\s*")
ALIASES = {"Léková anamnéza": "FA"}
FIRST_SENTENCE = re.compile(r"^(.+?[.!?])(\s|$)")

PROMPT = """Shrň anamnézu pacienta pro onkologickou komisi do krátkých bodů, jeden bod na sekci (OA, FA, RA,
SA, GA, NO, alergie). Zachovej klinicky důležité údaje (dědičná zátěž, léky s interakcemi, komorbidity),
čísla a data přesně podle zdroje. Ke každému bodu uveď Evidence ID odstavců z hranatých závorek.
Nic nedomýšlej; co ve zdroji není, neuváděj."""


class AnamnesisItem(BaseModel):
    text: str
    citations: list[str] = Field(description="Evidence ID odstavců, např. P06-doc05#3")


class AnamnesisOutput(BaseModel):
    items: list[AnamnesisItem]


def max_chars() -> int:
    try:
        return int(os.environ.get("INTAKE_ANAMNESIS_MAX_CHARS", "600"))
    except ValueError:
        return 600


def sections(context: PatientContext) -> list[dict]:
    """Nejnovější znění každé sekce: `{key, label, text, citation, date}` v pořadí `LABELS`."""
    latest: dict[str, dict] = {}
    lines = [line for line in context.evidence if line.resource_type == "DocumentReference" and "#" in line.id]
    for line in sorted(lines, key=lambda line: (line.date, line.id)):
        parts = MARKER.split(line.text)
        for raw_key, text in zip(parts[1::2], parts[2::2]):
            key = ALIASES.get(raw_key, raw_key)
            if text.strip():
                latest[key] = {"key": key, "label": LABELS[key], "text": text.strip(), "citation": line.id,
                               "date": line.date}
    return [latest[key] for key in LABELS if key in latest]


def anamnesis_items(context: PatientContext, provider: BaseAIProvider, log_call: Callable[[str, dict], Any],
                    config: dict | None = None) -> list[dict]:
    found = sections(context)
    if not found:
        return [{"id": "anamnesis-01", "kind": "missing", "text": "Anamnéza (OA, FA, RA…) ve zprávách chybí",
                 "citations": []}]
    verbatim = [{"kind": "claim", "text": f"{s['label']}: {s['text']}", "citations": [s["citation"]],
                 "_computed": True} for s in found]
    if sum(len(s["text"]) for s in found) > max_chars():
        summary = _llm_summary(found, context, provider, log_call, config)
        items = summary or [{**item, "text": _first_sentence(item["text"])} for item in verbatim]
    else:
        items = verbatim
    return [{"id": f"anamnesis-{i:02d}", **item} for i, item in enumerate(items, 1)]


def anamnesis_verbatim(context: PatientContext) -> list[dict]:
    """Doslovné znění k dlouhé anamnéze (FR-A5: lékař přepne shrnutí AI ↔ doslovně). U krátké je `items` už doslovně,
    proto prázdné."""
    found = sections(context)
    if sum(len(s["text"]) for s in found) <= max_chars():
        return []
    return [{"id": f"anamnesis-verbatim-{i:02d}", "kind": "claim", "text": f"{s['label']}: {s['text']}",
             "citations": [s["citation"]], "_computed": True} for i, s in enumerate(found, 1)]


def _first_sentence(text: str) -> str:
    match = FIRST_SENTENCE.match(text)
    return f"{match.group(1)} …" if match and len(match.group(1)) < len(text) else text


def _llm_summary(found: list[dict], context: PatientContext, provider: BaseAIProvider,
                 log_call: Callable[[str, dict], Any], config: dict | None) -> list[dict]:
    prompt = "\n".join(f"[{s['citation']}] {s['date']} {s['key']}: {s['text']}" for s in found)
    system = f"{PROMPT}\n\n{prompt_rules()}\n\n{prompt_settings(config, 'anamnesis')}"
    result = provider.generate(prompt, system_prompt=system, response_schema=AnamnesisOutput, temperature=0.1)
    log_call("brief.anamnesis", result)
    if result.get("status") != "success":
        return []
    allowed = {s["citation"] for s in found}
    items = []
    for item in (result.get("data") or {}).get("items") or []:
        citations = [c for c in dict.fromkeys(item.get("citations") or []) if c in allowed]
        if item.get("text", "").strip() and citations:
            items.append({"kind": "claim", "text": item["text"].strip(), "citations": citations})
    return items
