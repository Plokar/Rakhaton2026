"""Boardy a případy z nominací v IRIS (T-109, ARCH §6.2): `ServiceRequest.category` + `Task.restriction.period.start`."""
import re
from datetime import datetime

from services.fhir import client as fhir
from services.patients import _code, _ref_id

_FOCUS_PREFIX = 'Požadované zaměření MDT:'
# ponytail: základ komise z textu datasetu ("Mamární komise – karcinom prsu, s účastí…" → "Mamární komise");
# jiný text zaměření vytvoří vlastní board, což je správně
_FOCUS_DETAIL = re.compile(r',? s účastí.*$| – karcinom prsu.*$')


def board_title(request: dict) -> str:
    focus = next((c.get('text', '') for c in request.get('category', []) if c.get('text')), '')
    focus = _FOCUS_DETAIL.sub('', focus.replace(_FOCUS_PREFIX, '').strip()).strip() or 'MDT'
    return f'{focus} (urgentní)' if request.get('priority') in ('urgent', 'asap', 'stat') else focus


def nominations(requests: list[dict], tasks: list[dict]) -> list[dict]:
    """Nominace (ServiceRequest `mdt-typ-projednani`) s termínem z navázaného Task, seřazené podle pacienta."""
    start_by_request = {_ref_id(t.get('focus')): t.get('restriction', {}).get('period', {}).get('start') for t in tasks}
    out = []
    for r in requests:
        start = start_by_request.get(r['id'])
        if not _code(r.get('code'), 'mdt-typ-projednani') or not start:
            continue
        out.append({
            'patient_id': _ref_id(r.get('subject')), 'service_request_id': r['id'],
            'question': (r.get('reasonCode') or [{}])[0].get('text', ''),
            'date': datetime.fromisoformat(start), 'title': board_title(r),
        })
    return sorted(out, key=lambda n: (n['date'], n['title'], n['patient_id']))


def load_nominations() -> list[dict]:
    return nominations(fhir.search('ServiceRequest'), fhir.search('Task'))
