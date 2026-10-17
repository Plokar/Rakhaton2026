"""
Výběr sady guidelines a studií podle diagnózy (ARCHITEKTURA §5.5, DATASET §7).

C50 → PRS · C18–C20 → KRC · C34 → PLI · OBC vždy.
"""
from __future__ import annotations

import re
from typing import Iterable

GUIDELINE_SET_ORDER = ("KRC", "PRS", "PLI", "OBC")
ICD10_PREFIX_TO_SET = {"C18": "KRC", "C19": "KRC", "C20": "KRC", "C50": "PRS", "C34": "PLI"}

# Novotvary podle MKN-10: zhoubné C00–C97, in situ D00–D09, nejistého chování D37–D48 (P06 D41.0)
NEOPLASM_ICD10 = re.compile(r"^(C\d\d|D0\d|D3[7-9]|D4[0-8])")
NON_ONCOLOGIC_CATEGORY = ("komorbid", "nežádoucí")


def is_oncologic(condition: dict) -> bool:
    """Onkologická diagnóza: kategorie „onkologická diagnóza“, nebo kód novotvaru u diagnózy bez kategorie
    komorbidita / nežádoucí účinek léčby (jiný zdrojový systém, T-320). Jediné pravidlo pro výběr guidelines,
    kontext AI, hlavičku i semafor."""
    category = " ".join(c.get("text") or " ".join(x.get("display", "") for x in c.get("coding", []))
                        for c in condition.get("category") or []).lower()
    if "onkolog" in category:
        return True
    if any(word in category for word in NON_ONCOLOGIC_CATEGORY):
        return False
    codes = [x.get("code", "") for x in (condition.get("code") or {}).get("coding", [])
             if "icd-10" in x.get("system", "")]
    return any(NEOPLASM_ICD10.match(code.strip().upper()) for code in codes)

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
