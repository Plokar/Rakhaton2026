"""Karta Lung-RADS / Fleischner s kontrolou použitelnosti (BON-6, T-508, docs/POZADAVKY_LEKARE.md §6.1).

Nejdřív se deterministicky rozhodne, jestli se škála smí použít:

- **Lung-RADS v2022** jen pro nález ze screeningového nízkodávkového CT plic (EXT-LUNGRADS-2022);
- **Fleischner 2017** jen pro náhodně zjištěný plicní uzel u dospělého ≥ 35 let bez známého nádoru a mimo
  screening (EXT-FLEISCHNER-2017).

Všech 6 pacientů datasetu má známý nádor a žádné screeningové CT, takže dostanou „nelze použít“ s důvodem.
Kategorie Lung-RADS se počítá jen u solidního uzlu s velikostí uvedenou ve zprávě; tabulka Fleischner zatím
není převzatá, proto je výsledek „nelze posoudit“ (⚪). Imunosuprese se zatím nekontroluje.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

from services.rules.red_flags import PatientData

CHEST_CT = re.compile(r"\bCT\b.*(hrudník|plic)", re.IGNORECASE)
SCREENING = re.compile(r"screening", re.IGNORECASE)
LOW_DOSE = re.compile(r"nízkodávk|\bLDCT\b", re.IGNORECASE)
NODULE_MM = re.compile(r"(?:uzel|uzl\w*|ložisk\w*)\D{0,30}?(\d+(?:[,.]\d+)?)\s*mm", re.IGNORECASE)
LUNG_RADS_SOLID = ((6, "2"), (8, "3"), (15, "4A"), (float("inf"), "4B"))     # horní mez (mm) → kategorie


def _date(resource: dict) -> str:
    return resource.get("effectiveDateTime") or resource.get("issued") or ""


def _text(report: dict, data: PatientData) -> str:
    """Název vyšetření (`code.text`, např. „CT hrudníku… – staging“) + text zprávy."""
    return f"{(report.get('code') or {}).get('text', '')}\n{data.texts.get(report['id'], '')}"


def evaluate_scales(resources: Iterable[dict]) -> list[dict]:
    """`[{scale, applicable, category, reason, patient_citations, rule_citation}]` pro Lung-RADS a Fleischner."""
    data = PatientData(resources)
    reports = sorted(data.by_type.get("DiagnosticReport", []), key=_date)
    texts = {r["id"]: _text(r, data) for r in reports}
    chest_ct = [r for r in reports if CHEST_CT.search(texts[r["id"]])]
    screening = [r for r in chest_ct if SCREENING.search(texts[r["id"]]) and LOW_DOSE.search(texts[r["id"]])]
    cancer = data.oncologic[0] if data.oncologic else None
    cancer_text = (cancer.get("code") or {}).get("text", "") if cancer else ""
    return [_lung_rads(data, chest_ct, screening, texts), _fleischner(data, chest_ct, screening, cancer, cancer_text, texts)]


def _lung_rads(data: PatientData, chest_ct: list[dict], screening: list[dict], texts: dict[str, str]) -> dict:
    out = {"scale": "Lung-RADS", "rule_citation": "EXT-LUNGRADS-2022", "category": None}
    if not screening:
        cites = [chest_ct[-1]["id"]] if chest_ct else [c["id"] for c in data.oncologic[:1]]
        return {**out, "applicable": False, "patient_citations": cites,
                "reason": "platí jen pro screeningové nízkodávkové CT plic, takové v podkladech není"}
    report = screening[-1]
    size = NODULE_MM.search(texts[report["id"]])
    if not size:
        return {**out, "applicable": True, "patient_citations": [report["id"]],
                "reason": "screeningové CT, ale velikost uzlu ve zprávě není → nelze zařadit"}
    mm = float(size.group(1).replace(",", "."))
    category = next(cat for limit, cat in LUNG_RADS_SOLID if mm < limit)
    return {**out, "applicable": True, "category": category, "patient_citations": [report["id"]],
            "reason": f"screeningové CT, solidní uzel {size.group(1)} mm → kategorie {category}"}


def _fleischner(data: PatientData, chest_ct: list[dict], screening: list[dict], cancer: dict | None,
                cancer_text: str, texts: dict[str, str]) -> dict:
    out = {"scale": "Fleischner", "rule_citation": "EXT-FLEISCHNER-2017", "category": None}
    if cancer:
        return {**out, "applicable": False, "patient_citations": [cancer["id"]],
                "reason": f"známý nádor ({cancer_text}), na onkologického pacienta se Fleischner nevztahuje"}
    if screening:
        return {**out, "applicable": False, "patient_citations": [screening[-1]["id"]],
                "reason": "uzel ze screeningového CT patří do Lung-RADS, ne do Fleischner"}
    if data.age is not None and data.age < 35:
        return {**out, "applicable": False, "patient_citations": [data.patient_id],
                "reason": "pacient je mladší 35 let"}
    nodule = next((r for r in reversed(chest_ct) if NODULE_MM.search(texts[r["id"]])), None)
    if nodule is None:
        return {**out, "applicable": False, "patient_citations": [chest_ct[-1]["id"]] if chest_ct else [],
                "reason": "v podkladech není CT s plicním uzlem"}
    return {**out, "applicable": True, "patient_citations": [nodule["id"]],
            "reason": "náhodně zjištěný uzel; tabulka intervalů Fleischner zatím není převzatá → nelze posoudit"}


def scale_claims(resources: Iterable[dict], role: str) -> list[dict]:
    """Tvrzení do sekce radiologa (a pneumologa): výsledek škály s citací faktu pacienta, sestavené kódem."""
    claims = []
    for i, result in enumerate(evaluate_scales(resources), 1):
        if not result["patient_citations"]:
            continue
        verdict = (f"kategorie {result['category']}" if result["category"] else "lze použít") \
            if result["applicable"] else "nelze použít"
        source = "ACR Lung-RADS" if result["scale"] == "Lung-RADS" else "Fleischner Society"
        claims.append({"id": f"{role}-scale-{i:02d}", "kind": "claim",
                       "text": f"{result['scale']}: {verdict} – {result['reason']} (zdroj: {source}).",
                       "citations": result["patient_citations"], "_computed": True,
                       # Čísla z pravidla (35 let, kategorie) nejsou fakt pacienta (`_derived`).
                       "_derived": ["35"] + (re.findall(r"\d+", result["reason"]) if result["applicable"] else [])})
    return claims
