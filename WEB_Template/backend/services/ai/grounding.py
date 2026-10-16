"""
Grounding validátor v1 (ARCHITEKTURA §5.3, T-106).

Každé tvrzení (`Claim`) projde kontrolami; výsledek nastavuje `verification` (LLM ho nikdy nenastavuje):

1. citace existují v povolených ID kontextu (`PatientContext.allowed_ids`);
2. čísla z tvrzení (desetinná čárka i tečka) jsou v citovaných zdrojích;
3. data z tvrzení (ISO i „21. 9.“ / „21. 9. 2026“) jsou v citovaných zdrojích.

Vektorová podobnost tvrzení a zdroje přijde v2 (T-213). Chybějící údaje (`kind = "missing"`) se jen
kontrolují na existenci citací.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from services.ai.context_builder import PatientContext

NUMBER = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?![\w])")
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
CZ_DATE = re.compile(r"\b(\d{1,2})\.\s?(\d{1,2})\.(?:\s?(\d{4}))?")
ID_LIKE = re.compile(r"\b[A-Z]{1,6}[-‐]?\d+(?:[.,/]\d+)*[a-zA-Z]?\b")     # S3, G2, RKT-03, KRC-2.4, T4b …


@dataclass
class GroundingResult:
    verified: bool
    reasons: list[str] = field(default_factory=list)


def _numbers(text: str) -> set[str]:
    text = ID_LIKE.sub(" ", ISO_DATE.sub(" ", CZ_DATE.sub(" ", text)))
    out = set()
    for raw in NUMBER.findall(text):
        value = raw.replace(",", ".")
        if "." in value:
            value = value.rstrip("0").rstrip(".")
        out.add(str(int(value)) if value.isdigit() else value)
    return out


def _dates(text: str) -> set[tuple[int, int]]:
    """(den, měsíc) ze všech dat v textu (ISO i český zápis)."""
    found = {(int(d), int(m)) for _, m, d in ISO_DATE.findall(text)}
    found |= {(int(d), int(m)) for d, m, _ in CZ_DATE.findall(text) if 1 <= int(m) <= 12 and 1 <= int(d) <= 31}
    return found


def source_text(context: PatientContext, evidence_id: str) -> str:
    """Text zdroje včetně data řádku (data musí jít ověřit)."""
    lines = [line for line in context.evidence
             if line.id == evidence_id or ("#" not in evidence_id and line.resource_id == evidence_id)]
    if lines:
        return "\n".join(f"{line.date} {line.text}" for line in lines)
    return context.source_text(evidence_id) or ""


def check_claim(claim: dict, context: PatientContext) -> GroundingResult:
    citations = claim.get("citations") or []
    allowed = context.allowed_ids
    unknown = [c for c in citations if c not in allowed]
    reasons = [f"neznámá citace {c}" for c in unknown]
    if claim.get("kind") == "missing":
        return GroundingResult(not reasons, reasons)
    if not citations:
        return GroundingResult(False, ["tvrzení bez citace"])
    sources = "\n".join(source_text(context, c) for c in citations if c in allowed)
    missing_numbers = _numbers(claim.get("text", "")) - _numbers(sources)
    reasons += [f"číslo {n} není ve zdroji" for n in sorted(missing_numbers)]
    missing_dates = _dates(claim.get("text", "")) - _dates(sources)
    reasons += [f"datum {d}. {m}. není ve zdroji" for d, m in sorted(missing_dates)]
    return GroundingResult(not reasons, reasons)


def verify_claims(claims: list[dict], context: PatientContext) -> list[dict]:
    """Nastaví `verification` u každého tvrzení; důvody neověření vrátí v `_grounding` (mimo kontrakt)."""
    out = []
    for claim in claims:
        result = check_claim(claim, context)
        item = {**claim, "verification": "verified" if result.verified else "unverified"}
        if result.reasons:
            item["_grounding"] = result.reasons
        out.append(item)
    return out
