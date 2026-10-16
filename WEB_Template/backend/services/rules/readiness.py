"""Deterministické skóre připravenosti MDT podle OBC-1.1/OBC-1.2 (T-303)."""
from __future__ import annotations

import re
from collections.abc import Iterable

from services.rules.intake import intake_prefill

CORE_FIELDS = {
    "mdt.question", "dx.histology", "staging.tnm", "staging.imaging",
    "ecog.physician", "ecog.patient", "comorbidities", "treatment.history", "preferences",
}
STAGING_RULES = {"OBC-1.2", "KRC-2.4"}
STALE_AGE = re.compile(r"\b(\d+)\s*dní\b", re.IGNORECASE)


def evaluate_readiness(resources: Iterable[dict], skipped_fields: Iterable[str] = ()) -> dict:
    """Vyhodnotí core checklist, biomarkery a staging; skóre je počet přítomných polí.

    Přeskočené hodnoty zůstávají v checklistu a počítají se jako nedoplněné.
    Výstup je určený pro badge agendy a nevytváří ani nemění oficiální záznam.
    """
    prefill = intake_prefill(resources, skipped_fields=skipped_fields)
    fields = prefill["fields"]
    required = [
        field for field in fields
        if field["id"] in CORE_FIELDS
        or field["id"].startswith("bm.")
        or (field["id"] in {"staging.chest_ct", "staging.liver_mr"})
    ]
    complete = [field for field in required if field["status"] == "present"]
    unresolved = [field for field in required if field["status"] != "present"]
    stale_staging = []
    for field in required:
        if field["id"] != "staging.imaging" and not field["id"].startswith("staging."):
            continue
        match = STALE_AGE.search(field.get("value") or "")
        if match and int(match.group(1)) > 42:
            stale_staging.append({"id": field["id"], "age_days": int(match.group(1)),
                                  "citation": field.get("citation")})

    total = len(required)
    present = len(complete)
    percent = round(present / total * 100) if total else 100
    return {
        "patient_id": prefill["patient_id"],
        "status": "ready" if not unresolved else "incomplete",
        "score": {"present": present, "total": total, "percent": percent},
        "unresolved": unresolved,
        "stale_staging": stale_staging,
    }
