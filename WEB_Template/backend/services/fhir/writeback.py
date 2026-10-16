"""Zápisy aplikace do IRIS FHIR (ARCH §4.3 výstupy)."""
from datetime import datetime

from services.fhir import client as fhir
from services.patients import _ref_id


def nomination_task(patient_id: str, service_request_id: str) -> dict:
    """`Task` nominace (stav žádanky + termín MDT), `Task.focus` → `ServiceRequest`."""
    # IRIS neznámé parametry ignoruje, proto i filtr na focus u klienta
    task = next((t for t in fhir.search('Task', patient=patient_id)
                 if _ref_id(t.get('focus')) == service_request_id), None)
    if task is None:
        raise LookupError(f'Task pro {service_request_id} v IRIS není')
    return task


def set_mdt_date(patient_id: str, service_request_id: str, start: datetime) -> dict:
    """Přesun mezi boardy / změna termínu (FR-P1): `Task.restriction.period.start` = datum zasedání."""
    task = nomination_task(patient_id, service_request_id)
    task.setdefault('restriction', {}).setdefault('period', {})['start'] = start.isoformat()
    return fhir.put(task)
