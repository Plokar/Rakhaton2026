"""Extrakce SLD z radiologických popisů a citované tvrzení RECIST (T-304)."""
from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any, Callable

from pydantic import BaseModel, Field

from services.ai.context_builder import PatientContext
from services.ai_service import BaseAIProvider
from services.rules.recist import evaluate_sld

RECIST_PROMPT = """Z dodaných radiologických popisů vytěž pouze výslovně uvedený součet průměrů cílových
lézí (SLD, v mm). Nevypočítávej součet z jednotlivých ložisek a neodhaduj chybějící hodnoty.
Ke každému součtu vrať datum vyšetření, SLD a přesné Evidence ID zdroje z hranatých závorek.
Vrať jen zprávy s explicitním součtem SLD; neuváděj závěr PR/SD/PD, ten se počítá deterministicky.
"""


class SldMeasurement(BaseModel):
    date: str = Field(description="Datum vyšetření ve formátu YYYY-MM-DD")
    sld_mm: float = Field(ge=0, description="Pouze explicitně uvedený součet průměrů v mm")
    citation: str = Field(description="Evidence ID radiologické zprávy, např. P03-img01")


class SldExtraction(BaseModel):
    measurements: list[SldMeasurement] = Field(default_factory=list)


_EXPLICIT_SLD = re.compile(
    r"součet\s+(?:cílových\s+)?lézí(?:\s*\([^)]*\))?\s*[:=]?\s*(\d+(?:[,.]\d+)?)\s*mm",
    re.IGNORECASE,
)


def _imaging_resources(context: PatientContext) -> list[dict]:
    found: OrderedDict[str, dict] = OrderedDict()
    for line in context.evidence:
        if line.group != "imaging" or line.resource_type != "DiagnosticReport":
            continue
        item = found.setdefault(line.resource_id, {"citation": line.resource_id, "date": line.date, "text": ""})
        item["date"] = item["date"] or line.date
        item["text"] = f"{item['text']}\n{line.text}".strip()     # hlavička + všechny odstavce zprávy
    return list(found.values())


def _valid_measurements(raw: Any, resources: list[dict], context: PatientContext) -> list[dict]:
    allowed = {item["citation"]: item for item in resources if item["citation"] in context.allowed_ids}
    measurements = []
    for item in raw or []:
        citation = item.get("citation")
        source = allowed.get(citation)
        if not source or not isinstance(item.get("sld_mm"), (int, float)):
            continue
        measurements.append({
            "date": source["date"] or item.get("date", ""),
            "sld_mm": item["sld_mm"],
            "citation": citation,
        })
    return measurements


def _reported_totals(resources: list[dict]) -> list[dict]:
    """Offline fallback: accept only an explicit SLD statement in the report text."""
    extracted = []
    for item in resources:
        match = _EXPLICIT_SLD.search(item["text"] or "")
        if match:
            extracted.append({
                "date": item["date"],
                "sld_mm": float(match.group(1).replace(",", ".")),
                "citation": item["citation"],
            })
    return extracted


def recist_claim(context: PatientContext, provider: BaseAIProvider,
                 log_call: Callable[[str, dict], Any]) -> dict | None:
    """Vrátí radiologickou Claim z ≥2 explicitních SLD; jinak None bez odhadu."""
    resources = _imaging_resources(context)
    if len(resources) < 2:
        return None

    prompt = "\n".join(
        f"[{item['citation']}] {item['date']} {item['text']}" for item in resources
    )
    result = provider.generate(prompt, system_prompt=RECIST_PROMPT, response_schema=SldExtraction,
                              temperature=0.0)
    log_call("brief.recist.extract", result)
    output = result.get("data") if result.get("status") == "success" else None
    measurements = _valid_measurements((output or {}).get("measurements"), resources, context)
    if len(measurements) < 2:
        measurements = _reported_totals(resources)

    evaluated = evaluate_sld(measurements)
    if not evaluated:
        return None
    baseline, current, nadir = evaluated["baseline"], evaluated["current"], evaluated["nadir"]
    change = evaluated["change_from_baseline_pct"]
    citations = list(dict.fromkeys([baseline["citation"], nadir["citation"], current["citation"]]))
    text = (
        f"RECIST 1.1, cílové léze: SLD {baseline['sld_mm']:g} → {current['sld_mm']:g} mm "
        f"({change:+.0f} % od baseline), nadir {nadir['sld_mm']:g} mm; odpověď {evaluated['response']}. "
        "Jde o předběžné hodnocení cílových lézí; nové a necílové léze potvrzuje radiolog."
    )
    # Text i citace sestavuje kód z ověřených měření, ne LLM: vektorovou kontrolu přeskočí (`_computed`).
    # Procento je odvozené (ve zdroji není), grounding ho nekontroluje (`_derived`).
    return {"id": "radiologist-recist", "kind": "claim", "text": text, "citations": citations,
            "_computed": True, "_derived": [f"{abs(change):.0f}"]}
