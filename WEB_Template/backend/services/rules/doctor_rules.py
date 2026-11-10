"""Požadavky a normy lékaře u pacienta (T-359, T-360, D-028, docs/UCTY_A_PVW.md §3 kroky 3–4).

Deterministické, LLM se tu nevolá:

- `patient_facts(resources, skipped)`: údaje pacienta pod klíči katalogu šablony (pole formuláře zařazení,
  laboratoř `lab:<LOINC>`, věk `patient.age`), každý se stavem, hodnotou a citací (Evidence ID);
- `requirement_items(keys, facts, labels)`: stav vyžadovaných údajů (chybí / je / přeskočeno…);
- `evaluate_norm(norm, facts)`: `met` / `not_met` / `missing` / `not_evaluable`. Chybějící údaj se nedomýšlí;
  rozmezí, nerovnost nebo jiná jednotka v hodnotě = nelze posoudit (NEJISTOTA, nikdy odhad).

Norma lékaře je osobní kritérium s autorem, ne pravidlo semaforu: barvu postupů nemění (D-015).
"""
from __future__ import annotations

import re
from typing import Iterable

from services.fhir.values import fhir_code
from services.rules.fact_categories import AREAS, LAB_CATALOG, area_for_icd10
from services.rules.red_flags import PatientData, _num

OPS = {">=": "≥", "<=": "≤", ">": ">", "<": "<", "==": "="}
AREA_ANY = "*"
AREA_LABELS = {**AREAS, AREA_ANY: "Všechny diagnózy"}

# Číselné údaje, na které jde nastavit normu (klíč, název, obvyklá jednotka). Laboratoř se přidá z LAB_CATALOG.
NUMERIC_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("patient.age", "Věk pacienta", "let"),
    ("ecog.physician", "ECOG (lékař)", ""),
    ("ecog.patient", "ECOG podle pacienta (PROMs)", ""),
    ("weight", "Hmotnost", "kg"),
    ("spiro.fev1", "FEV1", "%"),
    ("spiro.dlco", "DLCO", "%"),
    ("spiro.ppo_fev1", "ppoFEV1", "%"),
    ("spiro.ppo_dlco", "ppoDLCO", "%"),
    ("lvef", "LVEF", "%"),
    ("liver.flr", "Budoucí jaterní remnant (FLR)", "%"),
    ("bm.pdl1", "PD-L1", "%"),
    ("bm.ki67", "Ki-67", "%"),
    ("lab.egfr", "eGFR", ""),
    ("lab.psa", "PSA", "ng/ml"),
    ("lab.testosterone", "Testosteron", "ng/dl"),
)
LAB_UNITS = {"718-7": "g/l", "2951-2": "mmol/l", "14682-9": "µmol/l", "777-3": "10^9/l", "751-8": "10^9/l"}

# číslo, které není součástí kódu (S2, T2N1, 18F-FDG)
NUMBER = re.compile(r"(?<![A-Za-z\d.,])-?\d+(?:[.,]\d+)?(?![A-Za-z\d])")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
UNCERTAIN = re.compile(r"[<>≤≥~±]|\d\s*[–-]\s*\d|\bcca\b|\bpřibl", re.IGNORECASE)


def norm_fields() -> list[dict]:
    """Údaje pro editor norem: číselná pole formuláře, věk a laboratoř z katalogu."""
    out = [{"key": k, "label": label, "unit": unit} for k, label, unit in NUMERIC_FIELDS]
    out += [{"key": f"lab:{loinc}", "label": f"{label} ({abbr})", "unit": LAB_UNITS.get(loinc, "")}
            for loinc, label, abbr in LAB_CATALOG]
    return out


NORM_KEYS = {f["key"] for f in norm_fields()}
NORM_LABELS = {f["key"]: f["label"] for f in norm_fields()}


def patient_area(resources: Iterable[dict]) -> str:
    return area_for_icd10(PatientData(list(resources)).icd10)


def patient_facts(resources: Iterable[dict], skipped: Iterable[str] = ()) -> dict[str, dict]:
    """`{klíč: {label, status, value, citation, number?}}` pro požadavky a normy."""
    from services.rules.intake import intake_prefill

    resources = list(resources)
    data = PatientData(resources)
    facts: dict[str, dict] = {}
    for f in intake_prefill(resources, skipped)["fields"]:
        facts[f["id"]] = {"label": f["label"], "status": f["status"], "value": f.get("value"),
                          "citation": f.get("citation")}
    for loinc, label, abbr in LAB_CATALOG:
        series = [o for o in data.observations
                  if fhir_code(o.resource.get("code"), "loinc.org") == loinc and isinstance(o.value, (int, float))]
        key = f"lab:{loinc}"
        if series:
            last = series[-1]
            unit = (last.resource.get("valueQuantity") or {}).get("unit") or ""
            facts[key] = {"label": f"{label} ({abbr})", "status": "present", "number": float(last.value),
                          "value": f"{_num(last.value)}{' ' + unit if unit else ''} ({last.date})",
                          "unit": unit, "citation": last.id}
        else:
            facts[key] = {"label": f"{label} ({abbr})", "status": "missing", "value": None, "citation": None}
    if data.age is not None and data.patient_id:
        facts["patient.age"] = {"label": "Věk pacienta", "status": "present", "number": float(data.age),
                                "value": f"{data.age} let", "unit": "let", "citation": data.patient_id}
    return facts


def requirement_items(keys: Iterable[str], facts: dict[str, dict], labels: dict[str, str]) -> list[dict]:
    """Stav vyžadovaných údajů. Údaj, který u pacienta formulář nezná (jiná diagnóza), je `missing`."""
    out = []
    for key in dict.fromkeys(keys):
        fact = facts.get(key)
        out.append({"key": key, "label": (fact or {}).get("label") or labels.get(key) or key,
                    "status": fact["status"] if fact else "missing",
                    "value": (fact or {}).get("value"), "citation": (fact or {}).get("citation")})
    return out


def _parse(fact: dict, norm_unit: str) -> tuple[float | None, str | None]:
    """(číslo, důvod, proč nejde posoudit). Z textu jen jednoznačné číslo: s jednotkou normy to musí být jediné
    číslo v té jednotce („1,9 l (58 % náležité)“ + „%“ → 58), bez jednotky jediné číslo v textu."""
    if fact.get("number") is not None:
        if not _same_unit(norm_unit, fact.get("unit", "")):
            return None, f"Jiná jednotka u pacienta ({fact.get('unit')}) než v normě ({norm_unit})."
        return fact["number"], None
    text = DATE.sub("", str(fact.get("value") or ""))
    if UNCERTAIN.search(text):
        return None, "Hodnota je rozmezí nebo nerovnost (NEJISTOTA), norma se neodhaduje."
    found = [(m.group(), text[m.end():]) for m in NUMBER.finditer(text)]
    if norm_unit:
        found = [(n, rest) for n, rest in found if _unit_follows(rest, norm_unit)]
    numbers = {float(n.replace(",", ".")) for n, _ in found}
    if len(numbers) != 1:
        unit = f" v jednotce {norm_unit}" if norm_unit else ""
        return None, (f"V hodnotě není číslo{unit}." if not numbers
                      else f"V hodnotě je víc čísel{unit}, norma se neodhaduje.")
    return numbers.pop(), None


def _unit_follows(rest: str, unit: str) -> bool:
    return rest.lstrip().lower().startswith(unit.strip().lower())


def _compare(number: float, op: str, value: float) -> bool:
    return {">=": number >= value, "<=": number <= value, ">": number > value, "<": number < value,
            "==": abs(number - value) < 1e-9}[op]


def _same_unit(a: str, b: str) -> bool:
    norm = lambda u: u.strip().lower().replace(" ", "")          # noqa: E731
    return not a or not b or norm(a) == norm(b)


def evaluate_norm(norm: dict, facts: dict[str, dict]) -> dict:
    """`{status, value, citation, reason}` normy `{field, op, value, unit}` u pacienta."""
    fact = facts.get(norm["field"])
    if not fact or fact.get("status") != "present":
        status = (fact or {}).get("status")
        reason = "Údaj přeskočil lékař." if status == "skipped" else "Údaj u pacienta chybí."
        return {"status": "missing", "value": (fact or {}).get("value"), "citation": (fact or {}).get("citation"),
                "reason": reason}
    number, reason = _parse(fact, norm.get("unit", "") or "")
    if reason:
        return {"status": "not_evaluable", "value": fact.get("value"), "citation": fact.get("citation"),
                "reason": reason}
    met = _compare(number, norm["op"], float(norm["value"]))
    return {"status": "met" if met else "not_met", "value": fact.get("value"), "citation": fact.get("citation"),
            "reason": None}


def norm_text(norm: dict) -> str:
    """„FLR ≥ 30 %“."""
    label = NORM_LABELS.get(norm["field"], norm["field"])
    unit = f" {norm['unit']}" if norm.get("unit") else ""
    return f"{label} {OPS[norm['op']]} {_num(norm['value'])}{unit}"
