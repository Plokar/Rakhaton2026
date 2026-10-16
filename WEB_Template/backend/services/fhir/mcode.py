"""mCODE v exportu (BON-5, T-307): `meta.profile` + kódy LOINC pro TNM a biomarkery, které jsou v datasetu jen textem.

Mění se jen **kopie** resources v exportovaném document Bundle, data v IRIS zůstávají beze změny.
Kód se přidá jen tam, kde si jsme jistí významem (ER, PR, HER2, skupina stadia TNM klinicky / patologicky);
ostatní biomarkery mají profil a původní text. Validace proti mCODE IG v IRIS je stretch (IG nenahraný, Q7).
"""
from __future__ import annotations

import copy
import re

MCODE = "http://hl7.org/fhir/us/mcode/StructureDefinition"
LOINC = "http://loinc.org"
# ponytail: jen kódy s jistým významem; Ki-67, KRAS, BRAF, MMR/MSI, EGFR, ALK, PD-L1 doplnit po ověření v LOINC
MARKER_CODES = (
    (re.compile(r"^ER\b|estrogen", re.I), "16112-5", "Estrogen receptor [Interpretation] in Tissue"),
    (re.compile(r"^PR\b|progesteron", re.I), "16113-3", "Progesterone receptor [Interpretation] in Tissue"),
    (re.compile(r"^HER2\b", re.I), "48676-1", "HER2 [Interpretation] in Tissue"),
)
STAGE_GROUP = {"clinical": ("21908-9", "Stage group.clinical Cancer"),
               "pathological": ("21902-2", "Stage group.pathology Cancer")}
SECONDARY_ICD = re.compile(r"^C7[7-9]")


def _profile(resource: dict, name: str) -> None:
    profiles = resource.setdefault("meta", {}).setdefault("profile", [])
    if f"{MCODE}/{name}" not in profiles:
        profiles.append(f"{MCODE}/{name}")


def _add_coding(resource: dict, code: str, display: str) -> None:
    concept = resource.setdefault("code", {})
    if not any(c.get("code") == code for c in concept.get("coding", [])):
        concept.setdefault("coding", []).append({"system": LOINC, "code": code, "display": display})


def _category_text(resource: dict) -> str:
    categories = resource.get("category") or []
    if isinstance(categories, dict):                       # Procedure.category je v R4 jeden CodeableConcept
        categories = [categories]
    return " ".join(c.get("text", "") for c in categories if isinstance(c, dict)).lower()


def _icd10(resource: dict) -> str:
    return next((c.get("code", "") for c in (resource.get("code") or {}).get("coding", [])
                 if "icd" in c.get("system", "").lower()), "")


def apply_profiles(resource: dict) -> dict:
    """Kopie resource s mCODE profilem (a kódem), když resource do mCODE patří; jinak beze změny."""
    rtype, rid = resource.get("resourceType"), resource.get("id", "")
    out = copy.deepcopy(resource)
    if rtype == "Patient":
        _profile(out, "mcode-cancer-patient")
    elif rtype == "Condition" and "onkolog" in _category_text(resource):
        _profile(out, "mcode-secondary-cancer-condition" if SECONDARY_ICD.match(_icd10(resource))
                 else "mcode-primary-cancer-condition")
    elif rtype == "Observation" and any(c.get("code") == "89247-1" for c in (resource.get("code") or {}).get("coding", [])):
        _profile(out, "mcode-ecog-performance-status")
    elif rtype == "Observation" and re.search(r"-bm\d", rid):
        _profile(out, "mcode-tumor-marker-test")
        text = (resource.get("code") or {}).get("text", "")
        for pattern, code, display in MARKER_CODES:
            if pattern.search(text):
                _add_coding(out, code, display)
                break
    elif rtype == "Observation" and re.search(r"-tnm\d", rid):
        _profile(out, "mcode-tnm-stage-group")
        value = str(resource.get("valueString") or "")
        kind = "pathological" if re.match(r"^\s*y?p", value) or "patolog" in (resource.get("code") or {}).get("text", "").lower() \
            else "clinical"
        _add_coding(out, *STAGE_GROUP[kind])
    elif rtype == "MedicationAdministration":
        _profile(out, "mcode-cancer-related-medication-administration")
    elif rtype == "MedicationRequest" and "-tx" in rid:
        _profile(out, "mcode-cancer-related-medication-request")
    elif rtype == "Procedure" and re.search(r"chirurg|resekc|ektomi|operac", _category_text(resource) + " "
                                            + (resource.get("code") or {}).get("text", "").lower()):
        _profile(out, "mcode-cancer-related-surgical-procedure")
    return out
