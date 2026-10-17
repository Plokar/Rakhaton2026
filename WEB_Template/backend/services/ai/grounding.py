"""
Grounding validátor v1 (ARCHITEKTURA §5.3, T-106).

Každé tvrzení (`Claim`) projde kontrolami; výsledek nastavuje `verification` (LLM ho nikdy nenastavuje):

1. citace existují v povolených ID kontextu (`PatientContext.allowed_ids`);
2. čísla z tvrzení (desetinná čárka i tečka) jsou v citovaných zdrojích;
3. data z tvrzení (ISO i „21. 9.“ / „21. 9. 2026“) jsou v citovaných zdrojích.

4. (v2, T-213) vektorová podobnost tvrzení a citovaných textů, ale jen když **všechny** citace mají
   vektor (odstavce, textové zprávy, guidelines, kritéria studií). Strukturovaná data (`bm`, `tnm`, `dg`,
   `proc`, ECOG…) vektor nemají a stačí jim body 1–3 (Q23). Stejně tvrzení, která sestavil kód
   (`_computed`, např. RECIST), protože citace k nim nepřiřazuje LLM.

Chybějící údaje (`kind = "missing"`) se jen kontrolují na existenci citací.
"""
from __future__ import annotations

import logging
import math
import os
import re
from dataclasses import dataclass, field

from services.ai.abbreviations import TEXT_TYPES
from services.ai.context_builder import PatientContext

log = logging.getLogger(__name__)
DEFAULT_MIN_SIMILARITY = 0.55
# Práh závisí na embedding modelu. NVIDIA nemotron-3-embed (T-323, 135 + 135 párů z podkladů P01–P06): správná
# citace medián 0,67, cizí odstavec téhož pacienta 0,23; 0,40 propustí ~90 % správných a ~10 % cizích.
MIN_SIMILARITY_BY_EMBEDDING = {"nvidia": 0.40}


def default_min_similarity() -> float:
    from services.ai_service import embedding_provider_name

    return MIN_SIMILARITY_BY_EMBEDDING.get(embedding_provider_name(), DEFAULT_MIN_SIMILARITY)

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


def has_vector(context: PatientContext, evidence_id: str) -> bool:
    """Má citace text indexovaný v IRIS Vector Search (`MDT.EvidenceChunk` / `GuidelineChunk` / `TrialCriterion`)?"""
    if "#" in evidence_id:
        return True
    if any(p.evidence_id == evidence_id for p in context.guidelines):
        return True
    if any(c.evidence_id == evidence_id for t in context.trials for c in t.criteria):
        return True
    return any(line.resource_id == evidence_id and line.resource_type in TEXT_TYPES for line in context.evidence)


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
    # Číslo z tokenu zdroje („G2“, „S3“) smí tvrzení napsat i slovy („grade 2“); opačně se nekontroluje.
    source_numbers = _numbers(sources) | {str(int(d)) for tok in ID_LIKE.findall(sources) for d in re.findall(r"\d+", tok)}
    missing_numbers = _numbers(claim.get("text", "")) - source_numbers - set(claim.get("_derived") or [])
    reasons += [f"číslo {n} není ve zdroji" for n in sorted(missing_numbers)]
    missing_dates = _dates(claim.get("text", "")) - _dates(sources)
    reasons += [f"datum {d}. {m}. není ve zdroji" for d, m in sorted(missing_dates)]
    return GroundingResult(not reasons, reasons)


def _known_citations(citations: list[str], allowed: set[str]) -> list[str]:
    """Odstavec, který zdroj nemá (model cituje „P02-prom02#3“ u dotazníku bez odstavců), se cituje jako celý
    zdroj; úplně neznámé ID zůstane a tvrzení neprojde."""
    fixed = [c.split("#", 1)[0] if c not in allowed and c.split("#", 1)[0] in allowed else c for c in citations]
    return list(dict.fromkeys(fixed))


def verify_claims(claims: list[dict], context: PatientContext) -> list[dict]:
    """Nastaví `verification` včetně sémantické kontroly přes IRIS Vector Search.

    Důvody neověření vrátí v `_grounding` (mimo kontrakt). Chybějící údaje nepopisují
    klinický fakt a zůstávají kontrolované pouze podle citací.
    """
    default = default_min_similarity()
    try:
        min_similarity = float(os.environ.get("GROUNDING_MIN_SIMILARITY", default))
    except (TypeError, ValueError):
        min_similarity = default
    if not 0 <= min_similarity <= 1:
        min_similarity = default

    out = []
    for claim in claims:
        claim = {**claim, "citations": _known_citations(claim.get("citations") or [], context.allowed_ids)}
        result = check_claim(claim, context)
        citations = claim["citations"]
        semantic = (claim.get("kind") != "missing" and not claim.get("_computed")
                    and all(has_vector(context, c) for c in citations))
        if result.verified and semantic:
            try:
                from services.iris.vector_store import similarity

                scores = similarity(claim.get("text", ""), citations)
                valid_scores = [score for score in scores.values()
                                if isinstance(score, (int, float)) and math.isfinite(score)]
                if not valid_scores:
                    result = GroundingResult(False, ["citované zdroje nemají dostupné vektory"])
                elif max(valid_scores) < min_similarity:
                    best = max(valid_scores)
                    result = GroundingResult(False, [
                        f"sémantická podobnost {best:.3f} je pod prahem {min_similarity:.3f}"
                    ])
            except Exception as exc:
                # Selhání IRIS nesmí shodit celý podklad; tvrzení ale nelze označit jako ověřené.
                log.warning("Grounding v2 nedostupný: %s", exc)
                result = GroundingResult(False, ["sémantickou podobnost se nepodařilo ověřit"])
        item = {**claim, "verification": "verified" if result.verified else "unverified"}
        if result.reasons:
            item["_grounding"] = result.reasons
        out.append(item)
    return out
