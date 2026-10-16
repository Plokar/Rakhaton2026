"""
Výběr sady guidelines a studií podle diagnózy (ARCHITEKTURA §5.5, DATASET §7).

C50 → PRS · C18–C20 → KRC · C34 → PLI · OBC vždy.
"""
from __future__ import annotations

from typing import Iterable

GUIDELINE_SET_ORDER = ("KRC", "PRS", "PLI", "OBC")
ICD10_PREFIX_TO_SET = {"C18": "KRC", "C19": "KRC", "C20": "KRC", "C50": "PRS", "C34": "PLI"}

# Klíčová slova v `ResearchStudy.condition.text` → sada guidelines. Studie pro „solidní nádory“
# (RKT-05 podpůrná, RKT-06 basket) se nabízí vždy (ARCHITEKTURA §5.5).
TRIAL_CONDITION_KEYWORDS = {"KRC": ("kolorekt",), "PRS": ("prsu",), "PLI": ("plic",)}
TRIAL_ALWAYS_KEYWORDS = ("solidní",)


def guideline_sets_for(icd10_codes: Iterable[str]) -> list[str]:
    """Sady guidelines pro diagnózy pacienta, v pořadí GUIDELINE_SET_ORDER; OBC je vždy."""
    sets = {ICD10_PREFIX_TO_SET.get(code.strip().upper()[:3]) for code in icd10_codes if code}
    sets.discard(None)
    sets.add("OBC")
    return [s for s in GUIDELINE_SET_ORDER if s in sets]


def trial_is_relevant(condition_texts: Iterable[str], guideline_sets: Iterable[str]) -> bool:
    texts = " ".join(condition_texts).lower()
    if any(keyword in texts for keyword in TRIAL_ALWAYS_KEYWORDS):
        return True
    return any(keyword in texts for s in guideline_sets for keyword in TRIAL_CONDITION_KEYWORDS.get(s, ()))
