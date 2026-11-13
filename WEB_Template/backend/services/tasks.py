"""Úkoly po zasedání (T-511, FR-P3) z FHIR `Task/Pxx-mdtNN-taskNN` v IRIS (zapisuje je T-209) a úkoly z přípravy
na MDT `Task/Pxx-zadNN-prepNN` (T-350): chybějící údaj nebo varování, které si zadávající lékař při zařazení dal
do svých úkolů (doplní ho před zasedáním)."""
import re
from datetime import datetime

from services.fhir import client as fhir
from services.fhir.writeback import RE_MDT
from services.fhir.values import ref_id

TASK_ID = re.compile(r'^(P\d{2,3})-(mdt\d+)-task\d+$')
PREP_ID = re.compile(r'^(P\d{2,3})-(zad\d+)-prep(\d+)$')
PREP_PREFIX = 'Doplnit před MDT: '


def _is_task(task_id: str) -> bool:
    return bool(TASK_ID.match(task_id) or PREP_ID.match(task_id))
STATUSES = ('requested', 'in-progress', 'completed')


def _re_mdt(plan: dict | None) -> dict | None:
    for a in (plan or {}).get('activity', []):
        d = a.get('detail', {})
        if d.get('code', {}).get('text') == RE_MDT:
            return {'date': d.get('scheduledPeriod', {}).get('start'), 'reason': d.get('description', '')}
    return None


def _item(t: dict, plans: dict, names: dict) -> dict:
    match = TASK_ID.match(t['id'])
    pid, record = match.groups() if match else PREP_ID.match(t['id']).groups()[:2]
    owner = t.get('owner', {})
    oid = ref_id(owner) if owner.get('reference') else None
    return {
        'id': t['id'], 'patient_id': pid, 'mdt_record': f'{pid}-{record}' if match else None,
        'service_request': None if match else f'{pid}-{record}', 'description': t.get('description', ''),
        'owner': {'id': oid, 'name': names.get(oid) or owner.get('display') or oid},
        'due_date': t.get('restriction', {}).get('period', {}).get('end'), 'status': t['status'],
        'authored_on': t.get('authoredOn'),
        're_mdt': _re_mdt(plans.get(ref_id((t.get('basedOn') or [{}])[0]))), 'draft': False,
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


def list_tasks(status: str | None = None, patient_id: str | None = None, owner: str | None = None) -> list[dict]:
    """Úkoly ze záznamů MDT; `owner` = ID lékaře v IRIS („moje úkoly“, T-328)."""
    tasks = [t for t in fhir.search('Task') if _is_task(t['id'])
             and (not status or t['status'] == status) and (not patient_id or t['id'].startswith(f'{patient_id}-'))
             and (not owner or ref_id(t.get('owner')) == owner)]
    plans, names = _context(tasks)
    order = {s: i for i, s in enumerate(STATUSES)}
    return sorted((_item(t, plans, names) for t in tasks),
                  key=lambda x: (order.get(x['status'], 9), x['due_date'] or '9999', x['id']))


def set_status(task_id: str, status: str) -> dict:
    if not _is_task(task_id) or status not in STATUSES:
        raise ValueError(f'Úkol {task_id!r} / stav {status!r}')
    task = fhir.read('Task', task_id)
    task['status'] = status
    fhir.put(task)
    plans, names = _context([task])
    return _item(task, plans, names)


def create_prep_tasks(patient_id: str, service_request_id: str, owner: str, items: list[str], due: datetime) -> list[str]:
    """Úkoly z přípravy na MDT (T-350): `items` = co doplnit („ECOG podle pacienta (PROMs)“). Vlastník = lékař v IRIS
    (`Practitioner/LEK-…`), termín = začátek zasedání. Stejný text u stejné nominace se nezakládá podruhé."""
    existing = [t for t in fhir.search('Task', patient=patient_id)
                if (m := PREP_ID.match(t['id'])) and f'{m[1]}-{m[2]}' == service_request_id]
    have = {t.get('description', '') for t in existing}
    number = max((int(PREP_ID.match(t['id'])[3]) for t in existing), default=0)
    written = []
    for item in dict.fromkeys(items):
        description = f'{PREP_PREFIX}{item}'
        if description in have:
            continue
        number += 1
        task_id = f'{service_request_id}-prep{number:02d}'
        fhir.put({
            'resourceType': 'Task', 'id': task_id, 'status': 'requested', 'intent': 'order',
            'code': {'text': 'Příprava na MDT'}, 'description': description,
            'focus': {'reference': f'ServiceRequest/{service_request_id}'}, 'for': {'reference': f'Patient/{patient_id}'},
            'authoredOn': datetime.now().astimezone().isoformat(timespec='seconds'),
            'owner': {'reference': f'Practitioner/{owner}'},
            'restriction': {'period': {'end': due.isoformat()}},
        })
        written.append(f'Task/{task_id}')
    return written
