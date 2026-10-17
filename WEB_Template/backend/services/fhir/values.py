"""Čtení hodnot z FHIR resources: jedno místo pro pomocné funkce, které dřív měl každý modul po svém (T-321)."""
from typing import Any


def ref_id(ref: dict | None) -> str:
    """`{"reference": "Observation/P03-ecog03"}` → `P03-ecog03`; bez odkazu prázdný řetězec."""
    return ((ref or {}).get("reference") or "").rsplit("/", 1)[-1]


def fhir_code(cc: dict | None, system_part: str) -> str:
    """Kód z CodeableConcept, jehož `system` obsahuje `system_part` (`icd-10`, `loinc.org`, `atc`…)."""
    return next((c.get("code", "") for c in (cc or {}).get("coding", []) if system_part in c.get("system", "")), "")


def cc_text(cc: dict | None) -> str:
    """Text CodeableConcept: `text`, jinak `display` (nebo kód) první kódovací položky."""
    if not cc:
        return ""
    return cc.get("text") or next((c.get("display") or c.get("code", "") for c in cc.get("coding", [])), "")


def ext_value(resource: dict, name: str) -> Any:
    """Hodnota `value[x]` extension, jejíž URL končí `/name` (`mdt-lecebny-zamer`, `icd-o-3-morfologie`…)."""
    for ext in resource.get("extension", []):
        if ext.get("url", "").endswith("/" + name):
            return next((v for k, v in ext.items() if k.startswith("value")), None)
    return None
