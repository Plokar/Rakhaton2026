"""Kategorie klíčových údajů, oblasti šablon lékaře a BMI (T-338, T-341, docs/SABLONY_LEKARE.md, D-024, D-025).

- Kategorie určuje systém (ne lékař): stejný údaj je u každého pacienta a každého lékaře na stejném místě
  a výstupy dotazníků se nepletou s výsledky vyšetření. Jediné místo přiřazení pro backend i UI
  (`IntakeField.category`, `IntakeWarning.category`).
- Oblast šablony (`PLI`, `PRS`, `KRC`, `OBC`) se určuje stejným pravidlem jako sada guidelines.
- Klíč údaje v šabloně je stabilní napříč pacienty (`bm.egfr`, `lab:718-7`, `alert:RF-LAB`).
"""
from __future__ import annotations

import re
from typing import Iterable

# Pořadí = jak se o pacientovi rozhoduje: co to je → co to řídí → rozsah → zvládne léčbu → co už měl → laboratoř
# → co říká pacient → co chybí.
CATEGORIES: tuple[tuple[str, str], ...] = (
    ("staging", "Diagnóza a staging"),
    ("molecular", "Molekulární genetika a biomarkery"),
    ("imaging", "Zobrazení a invazivní vyšetření"),
    ("function", "Funkční stav a výkonnost"),
    ("history", "Anamnéza a dosavadní léčba"),
    ("lab", "Laboratoř"),
    ("patient", "Pacient: dotazníky a preference"),
    ("alerts", "Upozornění a chybějící údaje"),
)
CATEGORY_IDS = tuple(c for c, _ in CATEGORIES)

_EXPLICIT = {
    "staging.tnm": "staging",
    "weight": "function",
    "lvef": "function",
    "smoking": "history",
    "comorbidities": "history",
    "allergies": "history",
    "preferences": "patient",
}
_PREFIX = (
    ("dx.", "staging"), ("bm.", "molecular"), ("staging.", "imaging"), ("liver.", "imaging"),
    ("spiro.", "function"), ("geri.", "function"), ("treatment.", "history"), ("tox.", "history"),
    ("lab.", "lab"),
)
# Varování z dotazníků PROMs (pacient sám uvádí) patří k pacientovi, ne mezi výsledky vyšetření.
_PROMS_CITATION = re.compile(r"^P\d{2}-prom\d+")


def field_category(field_id: str) -> str:
    """Kategorie pole formuláře zařazení (`IntakeField.id`). Neznámé pole: podle prefixu, jinak Anamnéza."""
    if field_id in _EXPLICIT:
        return _EXPLICIT[field_id]
    return next((cat for prefix, cat in _PREFIX if field_id.startswith(prefix)), "history")


def warning_category(warning_id: str, citations: Iterable[str]) -> str:
    """Varování, které nepatří k žádnému řádku: z dotazníku → Pacient, jinak Upozornění."""
    own = warning_id.split(":", 1)[1] if ":" in warning_id else ""
    if any(_PROMS_CITATION.match(c or "") for c in [own, *citations]):
        return "patient"
    return "alerts"


def alert_key(warning_id: str) -> str:
    """Klíč upozornění do šablony bez ID pacienta: `RF-LAB:P04-lab05-cea` → `alert:RF-LAB`,
    `DOP:obc.hbv` → `alert:DOP`, `missing:spiro.vo2max` → `alert:missing`."""
    return f"alert:{warning_id.split(':', 1)[0]}"


# ── Oblasti šablon ─────────────────────────────────────────────────────────────
AREAS: dict[str, str] = {"PLI": "Plíce", "PRS": "Prs", "KRC": "Kolorektum", "OBC": "Ostatní diagnózy"}
# Ukázková diagnóza oblasti pro katalog údajů (pole šablony se počítají z diagnózy, viz template_catalog)
AREA_SAMPLE_ICD = {"PLI": ["C34.1"], "PRS": ["C50.4"], "KRC": ["C18.7"], "OBC": ["C61", "C64"]}


def area_for_icd10(codes: Iterable[str]) -> str:
    """Oblast šablony podle diagnóz pacienta (stejné pravidlo jako sada guidelines); jinak `OBC`."""
    from services.rules.guideline_sets import guideline_sets_for

    sets = [s for s in guideline_sets_for(codes) if s != "OBC"]
    return sets[0] if sets else "OBC"


# ── Laboratoř v katalogu šablony (LOINC z datasetu) ────────────────────────────
LAB_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("718-7", "Hemoglobin", "Hb"), ("6690-2", "Leukocyty", "Leu"), ("751-8", "Neutrofily absolutně", "Neu"),
    ("777-3", "Trombocyty", "Tr"), ("14682-9", "Kreatinin", "Kreat"), ("2951-2", "Sodík", "Na"),
    ("2823-3", "Draslík", "K"), ("14631-6", "Bilirubin celkový", "Bili"), ("1742-6", "ALT", "ALT"),
    ("1920-8", "AST", "AST"), ("6768-6", "ALP", "ALP"), ("1751-7", "Albumin", "Alb"), ("14804-9", "LD", "LD"),
    ("15074-8", "Glukóza", "Glu"), ("1988-5", "CRP", "CRP"), ("2039-6", "CEA", "CEA"),
    ("6875-3", "CA 15-3", "CA 15-3"), ("24108-3", "CA 19-9", "CA 19-9"),
)
# Typy upozornění v katalogu (klíč `alert_key`): pravidla red flags + skupiny bez ID pacienta.
ALERT_GROUPS: tuple[tuple[str, str], ...] = (
    ("CHYBI", "Chybí údaj z báze (např. DPD, Na)"),
    ("DOP", "Doporučené vyšetření nebo stanovisko"),
    ("missing", "Chybí povinný údaj formuláře"),
    ("out_of_range", "Laboratoř mimo referenční rozmezí"),
    ("ai_uncertain", "Nejistota AI (rozmezí, nejasný údaj)"),
)

# ── BMI (T-341) ───────────────────────────────────────────────────────────────
# Modrá kniha ČOS, oddíl 31.3 (kritéria malnutrice GLIM): BMI < 20 kg/m2 ve věku < 70 roků, < 22 kg/m2 od 70 let.
BMI_SOURCE = "EXT-MK-31.3-2"


def bmi_threshold(age: int | None) -> float:
    return 22.0 if age is not None and age >= 70 else 20.0


def bmi(weight_kg: float, height: float, unit: str | None) -> float | None:
    """BMI z hmotnosti a výšky (cm nebo m podle jednotky; bez jednotky podle velikosti). Nesmyslná výška → None."""
    meters = height / 100 if (unit or "").strip().lower() in ("cm", "[cm]") or (not unit and height > 3) else height
    if not 1.0 <= meters <= 2.5 or weight_kg <= 0:
        return None
    return round(weight_kg / (meters * meters), 1)
