"""Úkoly po zasedání (T-511, FR-P3) z FHIR `Task/Pxx-mdtNN-taskNN` v IRIS (zapisuje je T-209)."""
import re

from services.fhir import client as fhir
from services.fhir.writeback import RE_MDT
from services.fhir.values import ref_id

TASK_ID = re.compile(r'^(P\d{2})-(mdt\d+)-task\d+$')
STATUSES = ('requested', 'in-progress', 'completed')


def _re_mdt(plan: dict | None) -> dict | None:
    for a in (plan or {}).get('activity', []):
        d = a.get('detail', {})
        if d.get('code', {}).get('text') == RE_MDT:
            return {'date': d.get('scheduledPeriod', {}).get('start'), 'reason': d.get('description', '')}
    return None


def _item(t: dict, plans: dict, names: dict) -> dict:
    pid, mdt = TASK_ID.match(t['id']).groups()
    owner = t.get('owner', {})
    oid = ref_id(owner) if owner.get('reference') else None
    return {
        'id': t['id'], 'patient_id': pid, 'mdt_record': f'{pid}-{mdt}', 'description': t.get('description', ''),
        'owner': {'id': oid, 'name': names.get(oid) or owner.get('display') or oid},
        'due_date': t.get('restriction', {}).get('period', {}).get('end'), 'status': t['status'],
        'authored_on': t.get('authoredOn'),
        're_mdt': _re_mdt(plans.get(ref_id((t.get('basedOn') or [{}])[0]))),
    }


def _context(tasks: list[dict]) -> tuple[dict, dict]:
    plans = {p['id']: p for p in fhir.search('CarePlan') if re.search(r'-mdt\d+-careplan$', p['id'])}
    lek = sorted({ref_id(t['owner']) for t in tasks if t.get('owner', {}).get('reference', '').startswith('Practitioner/')})
    names = {}
    if lek:
        # IRIS neznámé parametry ignoruje, proto filtr i u klienta
        names = {p['id']: (p.get('name') or [{}])[0].get('text', p['id'])
                 for p in fhir.search('Practitioner', _id=','.join(lek)) if p['id'] in lek}
    return plans, names


def list_tasks(status: str | None = None, patient_id: str | None = None) -> list[dict]:
    tasks = [t for t in fhir.search('Task') if TASK_ID.match(t['id'])
             and (not status or t['status'] == status) and (not patient_id or t['id'].startswith(f'{patient_id}-'))]
    plans, names = _context(tasks)
    order = {s: i for i, s in enumerate(STATUSES)}
    return sorted((_item(t, plans, names) for t in tasks),
                  key=lambda x: (order.get(x['status'], 9), x['due_date'] or '9999', x['id']))


def set_status(task_id: str, status: str) -> dict:
    if not TASK_ID.match(task_id) or status not in STATUSES:
        raise ValueError(f'Úkol {task_id!r} / stav {status!r}')
    task = fhir.read('Task', task_id)
    task['status'] = status
    fhir.put(task)
    plans, names = _context([task])
    return _item(task, plans, names)
