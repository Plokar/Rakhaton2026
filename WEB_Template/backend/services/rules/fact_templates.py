"""Šablony klíčových údajů lékaře (T-338, docs/SABLONY_LEKARE.md R2–R5, D-025).

- `validate_layout`: tvar rozložení (šablona lékaře i úprava u případu T-333) → ValueError s českou zprávou.
- `presets()` / `preset_for(specialty, area)`: presety z `data/template_presets.yaml`.
- `catalog(area)`: kategorie a všechny údaje, které se v oblasti mohou objevit (editor šablony).
- `template_for(user, area)`: šablona lékaře pro oblast, jinak jeho šablona `OBC`, jinak `None` (výchozí pořadí).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from services.rules.fact_categories import (
    ALERT_GROUPS, AREA_SAMPLE_ICD, AREAS, CATEGORIES, CATEGORY_IDS, LAB_CATALOG, field_category,
)

PRESETS_FILE = Path(__file__).resolve().parent / "data" / "template_presets.yaml"
BLOCKS = ("anamnesis", "facts", "treatments")
# Pole, která panel ukazuje jinde (hlavička, dolní pás), nejsou mezi údaji šablony.
ELSEWHERE = {"mdt.question", "ecog.physician", "ecog.patient"}
# Pole, která formulář zařazení přidá jen za podmínky (věk, HER2, jaterní metastázy, ppo < 60 %…):
# z „prázdného“ pacienta je katalog nepozná, proto jsou tu (ID a název jako v services/rules/intake.py).
CONDITIONAL_FIELDS = {
    "*": [("geri.g8", "Geriatrický screening G8 (od 70 let)")],
    "PLI": [("spiro.vo2max", "Zátěžový test (VO2max), ppo < 60 %")],
    "PRS": [("lvef", "LVEF ≤ 3 měsíce")],
    "KRC": [("staging.chest_ct", "CT hrudníku ≤ 6 týdnů"), ("staging.liver_mr", "MR jater ≤ 6 týdnů"),
            ("liver.flr", "Budoucí jaterní remnant (FLR)"), ("treatment.bevacizumab", "Poslední dávka bevacizumabu")],
    "OBC": [("lab.testosterone", "Testosteron (kastrační hladina < 50 ng/dl)"), ("bm.hrr", "HRR / BRCA2 (NGS)")],
}


def _ids(value, allowed=None) -> bool:
    return (isinstance(value, list) and len(value) <= 300 and len(set(value)) == len(value)
            and all(isinstance(x, str) and 0 < len(x) <= 120 and (allowed is None or x in allowed) for x in value))


def validate_layout(layout) -> dict:
    """`{categories?, facts?, blocks?}`, každá část `{order: [id], hidden: [id]}`; jinak ValueError."""
    if not isinstance(layout, dict) or set(layout) - {"categories", "facts", "blocks"}:
        raise ValueError("Objekt s klíči categories, facts a blocks.")
    for key, allowed in (("categories", CATEGORY_IDS), ("blocks", BLOCKS), ("facts", None)):
        part = layout.get(key)
        if part is None:
            continue
        if not isinstance(part, dict) or set(part) - {"order", "hidden"} \
                or not all(_ids(part.get(k, []), allowed) for k in ("order", "hidden")):
            raise ValueError(f"{key}: {{order: [id], hidden: [id]}}" + (f", jen {', '.join(allowed)}" if allowed else "")
                             + ", bez opakování.")
    return layout


@lru_cache(maxsize=1)
def presets() -> tuple[dict, ...]:
    items = yaml.safe_load(PRESETS_FILE.read_text(encoding="utf-8"))["presets"]
    for item in items:
        validate_layout(item["layout"])
    return tuple(items)


def preset_for(specialty: str | None, area: str) -> dict:
    """Preset pro profesi a oblast; jinak výchozí (`vychozi`)."""
    for item in presets():
        if specialty in item["specialties"] and item["area"] in (area, "*"):
            return item
    return next(p for p in presets() if p["id"] == "vychozi")


@lru_cache(maxsize=8)
def catalog(area: str) -> dict:
    """Kategorie a údaje oblasti pro editor šablony: pole formuláře zařazení pro ukázkovou diagnózu
    (+ podmíněná pole), laboratoř z datasetu a typy upozornění."""
    from services.rules.intake import intake_prefill
    from services.rules.red_flags import RULE_CATALOG

    if area not in AREAS:
        raise ValueError(f"Oblast jen {', '.join(AREAS)}.")
    facts: dict[str, dict] = {}
    for icd in AREA_SAMPLE_ICD[area]:
        resources = [{"resourceType": "Patient", "id": "P99", "gender": "male", "birthDate": "1950-01-01"},
                     {"resourceType": "Condition", "id": "P99-dg1", "category": [{"text": "onkologická diagnóza"}],
                      "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": icd}]},
                      "subject": {"reference": "Patient/P99"}}]
        for field in intake_prefill(resources)["fields"]:
            if field["id"] not in ELSEWHERE:
                facts.setdefault(field["id"], {"key": field["id"], "label": field["label"], "category": field["category"]})
    for key, label in CONDITIONAL_FIELDS["*"] + CONDITIONAL_FIELDS.get(area, []):
        facts.setdefault(key, {"key": key, "label": label, "category": field_category(key)})
    for loinc, label, abbr in LAB_CATALOG:
        facts.setdefault(f"lab:{loinc}", {"key": f"lab:{loinc}", "label": label, "abbr": abbr, "category": "lab"})
    for rule, (title, _source) in RULE_CATALOG.items():
        facts.setdefault(f"alert:{rule}", {"key": f"alert:{rule}", "label": title, "category": "alerts"})
    for group, title in ALERT_GROUPS:
        facts.setdefault(f"alert:{group}", {"key": f"alert:{group}", "label": title, "category": "alerts"})
    order = {c: i for i, c in enumerate(CATEGORY_IDS)}
    return {
        "area": area, "area_label": AREAS[area],
        "categories": [{"id": c, "label": label} for c, label in CATEGORIES],
        "facts": sorted(facts.values(), key=lambda f: order[f["category"]]),
    }


def template_for(user, area: str) -> dict | None:
    """Rozložení lékaře pro oblast (`FactTemplate`), jinak jeho `OBC`, jinak `None`."""
    if user is None:
        return None
    from apps.mdt.models import FactTemplate

    rows = {t.area: t.layout for t in FactTemplate.objects.filter(user=user, area__in=[area, "OBC"])}
    return rows.get(area) or rows.get("OBC")
