"""Kontrola před zasedáním (T-349): co přibylo v dokumentaci od zařazení a jestli to zadávající lékař viděl.

Čistá funkce nad FHIR resources pacienta (testy bez IRIS a bez Djanga):

- **nové výsledky** = výsledky a zprávy s datem po nominaci (`ServiceRequest.authoredOn`, bez něj po založení
  případu): laboratoř, zobrazení, patologie, zprávy, výkony, podání léčby, dotazníky pacienta. Zápisy aplikace
  (ECOG zadaný při zařazení, vložená zpráva, záznam MDT, odkliknutá varování) se nepočítají, ty zadal lékař sám;
- **stav**: `upcoming` (do zasedání víc než `REVIEW_HOURS`), `due` (okno kontroly běží a lékař kontrolu
  nepotvrdil, nebo po potvrzení přišlo něco nového), `checked`, `missed` (zasedání začalo bez kontroly; pacient
  zůstává na MDT, jen je podsvícený).

Nic nemění v IRIS ani v podkladu; potvrzení kontroly je jen datum a lékař u případu.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Iterable

from services.fhir.values import cc_text

REVIEW_HOURS = 48
RESULT_TYPES = ("Observation", "DiagnosticReport", "DocumentReference", "Procedure", "MedicationAdministration",
                "QuestionnaireResponse", "ImagingStudy")
# zápisy aplikace (services/fhir/ids.py): ty nejsou „nová realita“, zadal je lékař při zařazení nebo na MDT
APP_WRITTEN = re.compile(r"-(ecog-case\d+|imp\d+(-.+)?|mdt\d+(-.+)?|case\d+-.+|zad\d+(-.+)?)$")
TYPE_LABEL = {"Observation": "Výsledek", "DiagnosticReport": "Zpráva", "DocumentReference": "Dokument",
              "Procedure": "Výkon", "MedicationAdministration": "Léčba", "QuestionnaireResponse": "Dotazník pacienta",
              "ImagingStudy": "Zobrazení"}


def resource_date(r: dict) -> str:
    """Datum výsledku (ISO, jak je v FHIR): kdy vznikl, ne kdy se nahrál."""
    period = r.get("performedPeriod") or {}
    return (r.get("effectiveDateTime") or r.get("issued") or r.get("performedDateTime") or period.get("start")
            or r.get("date") or r.get("authored") or r.get("started") or "")


def _day(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


def _value(r: dict) -> str:
    if "valueQuantity" in r:
        q = r["valueQuantity"]
        num = q.get("value")
        text = f"{num:g}".replace(".", ",") if isinstance(num, (int, float)) else str(num)
        return f"{text} {q.get('unit', '')}".strip()
    for key in ("valueString", "valueInteger", "conclusion", "description"):
        if r.get(key) not in (None, ""):
            return str(r[key])
    return ""


def _label(r: dict) -> str:
    rtype = r["resourceType"]
    if rtype == "DocumentReference":
        return cc_text(r.get("type")) or r.get("description") or TYPE_LABEL[rtype]
    if rtype == "MedicationAdministration":
        return cc_text(r.get("category")) or cc_text(r.get("medicationCodeableConcept")) or TYPE_LABEL[rtype]
    if rtype == "QuestionnaireResponse":
        return TYPE_LABEL[rtype]
    return cc_text(r.get("code")) or TYPE_LABEL[rtype]


def nomination_day(resources: Iterable[dict], service_request_id: str | None) -> date | None:
    request = next((r for r in resources if r.get("resourceType") == "ServiceRequest"
                    and (service_request_id is None or r.get("id") == service_request_id)), None)
    return _day(request.get("authoredOn", "")) if request else None


def new_results(resources: Iterable[dict], since: date) -> list[dict]:
    """Výsledky po `since` (bez zápisů aplikace), nejnovější první. `citation` = ID resource (Evidence ID)."""
    out = []
    for r in resources:
        if r.get("resourceType") not in RESULT_TYPES or APP_WRITTEN.search(r.get("id", "")):
            continue
        when = resource_date(r)
        day = _day(when)
        if day is None or day <= since:
            continue
        out.append({"citation": r["id"], "type": r["resourceType"], "kind": TYPE_LABEL[r["resourceType"]],
                    "date": when[:10], "label": _label(r), "value": _value(r)[:200]})
    return sorted(out, key=lambda n: (n["date"], n["citation"]), reverse=True)


def review_state(resources: Iterable[dict], *, service_request_id: str | None, meeting: datetime, now: datetime,
                 created: datetime, checked_at: datetime | None, session_status: str = "planned") -> dict:
    """`CaseReview` (ARCH §8.6): nové výsledky od zařazení a stav kontroly před zasedáním."""
    resources = list(resources)
    since = nomination_day(resources, service_request_id) or created.date()
    found = new_results(resources, since)
    for item in found:
        item["unseen"] = checked_at is None or _day(item["date"]) > checked_at.date()
    unseen = sum(item["unseen"] for item in found)
    due_from = meeting - timedelta(hours=REVIEW_HOURS)
    started = now >= meeting or session_status in ("in_progress", "closed")
    if checked_at is not None and not unseen:
        status = "checked"
    elif started:
        status = "missed"
    elif now >= due_from:
        status = "due"
    else:
        status = "upcoming"
    return {"status": status, "since": since.isoformat(), "due_from": due_from.isoformat(),
            "checked_at": checked_at.isoformat() if checked_at else None,
            "new_results": found, "unseen_count": unseen}
