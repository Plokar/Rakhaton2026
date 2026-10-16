"""
Upozornění v hlavičce podkladu (FR-A4, D-018, T-312): alergie, implantáty, předchozí operace a radioterapie.

`header_alerts(resources)` vrátí `Claim[]` pro `Brief.header.alerts` (kontrakt §8.2). Všechno je
deterministické z FHIR (`Procedure`, PROMs `alergie`, odstavce „Alergie:“), každé upozornění má citaci.
"""
from __future__ import annotations

from typing import Iterable

from services.rules.red_flags import PatientData, _cc_text, allergies, prior_procedures

LABELS = {"implant": "Implantát", "surgery": "Předchozí operace", "radiotherapy": "Předchozí radioterapie"}


def header_alerts(resources: Iterable[dict]) -> list[dict]:
    data = PatientData(resources)
    alerts: list[dict] = []
    merged: list[tuple[str, dict]] = []      # stejná alergie z PROMs i ze zprávy = jedno upozornění, obě citace
    for text, evidence_id in allergies(data):
        normalized = text.strip().rstrip(".").lower()
        same = next((alert for known, alert in merged if normalized in known or known in normalized), None)
        if same is not None:
            same["citations"].append(evidence_id)
            continue
        alert = _claim(len(alerts) + 1, f"Alergie: {text.strip().rstrip('.')}", [evidence_id])
        merged.append((normalized, alert))
        alerts.append(alert)
    for kind, procedures in prior_procedures(data).items():
        for p in procedures:
            when = (p.get("performedDateTime") or p.get("performedPeriod", {}).get("start") or "")[:10]
            reports = [r.get("reference", "").rsplit("/", 1)[-1] for r in p.get("report", [])]
            alerts.append(_claim(len(alerts) + 1, f"{LABELS[kind]}: {_cc_text(p.get('code'))}"
                                 + (f" ({when})" if when else ""), [p["id"], *filter(None, reports)]))
    return alerts


def _claim(index: int, text: str, citations: list[str]) -> dict:
    return {"id": f"alert-{index}", "kind": "claim", "text": text, "citations": citations,
            "verification": "verified"}
