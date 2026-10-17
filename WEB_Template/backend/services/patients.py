"""Pacienti z IRIS pro API (T-103, ARCH §6.3, kontrakty §8.2). Každá položka nese citaci = FHIR ID."""
import re
from collections import defaultdict

from services.fhir import client as fhir
from services.rules.guideline_sets import is_oncologic

LOINC_ECOG = '89247-1'
SEX_CS = {'male': 'muž', 'female': 'žena', 'other': 'jiné', 'unknown': 'neuvedeno'}
VALID_ID = re.compile(r'^[A-Za-z0-9\-.]{1,64}$')
_KIND = re.compile(r'^P\d+-([a-z]+)')       # "P02-lvef06" → "lvef" (Observation bez LOINC)


# ── pomocné ──────────────────────────────────────────────────────────────────
def _text(cc: dict | None) -> str:
    cc = cc or {}
    return cc.get('text') or next((c.get('display') for c in cc.get('coding', []) if c.get('display')), '')


def _code(cc: dict | None, system_part: str) -> str:
    return next((c['code'] for c in (cc or {}).get('coding', []) if system_part in c.get('system', '')), '')


def _ref_id(ref: dict | None) -> str:
    return ((ref or {}).get('reference') or '').rsplit('/', 1)[-1]


def _subject(r: dict) -> str:
    return _ref_id(r.get('subject') or r.get('patient') or r.get('for'))


def _categories(r: dict) -> list[dict]:
    cat = r.get('category') or []
    return cat if isinstance(cat, list) else [cat]


def _category_text(r: dict) -> str:
    return ' '.join(_text(c) for c in _categories(r))


def _date(r: dict) -> str:
    for k in ('effectiveDateTime', 'performedDateTime', 'onsetDateTime', 'authored', 'authoredOn', 'date', 'issued'):
        if r.get(k):
            return r[k][:10]
    for k in ('performedPeriod', 'effectivePeriod'):
        if r.get(k, {}).get('start'):
            return r[k]['start'][:10]
    return ''


def _ext(r: dict, name: str):
    for e in r.get('extension', []):
        if e.get('url', '').endswith('/' + name):
            return next((v for k, v in e.items() if k.startswith('value')), None)
    return None


def _nomination(rs: list[dict]) -> tuple[dict, dict]:
    """Nominace na MDT (`ServiceRequest` s `mdt-typ-projednani`) a její `Task` se stavem a termínem."""
    req = next((r for r in rs if r['resourceType'] == 'ServiceRequest' and _code(r.get('code'), 'mdt-typ-projednani')),
               next((r for r in rs if r['resourceType'] == 'ServiceRequest'), {}))
    task = next((r for r in rs if r['resourceType'] == 'Task' and _ref_id(r.get('focus')) == req.get('id')), {})
    return req, task


# ── seznam a detail ──────────────────────────────────────────────────────────
def summary(pid: str, rs: list[dict]) -> dict:
    patient = next(r for r in rs if r['resourceType'] == 'Patient' and r['id'] == pid)
    req, task = _nomination(rs)
    mdt_date = task.get('restriction', {}).get('period', {}).get('start')
    age = _ext(patient, 'vek-k-datu-mdt')
    if age is None and patient.get('birthDate') and mdt_date:
        age = int(mdt_date[:4]) - int(patient['birthDate'][:4])
    sex = patient.get('gender', 'unknown')
    dg = next((c for c in rs if c['resourceType'] == 'Condition' and is_oncologic(c)), None)
    return {
        'id': pid,
        'display_name': f'{pid} · {SEX_CS.get(sex, sex)} · {age} let' if age is not None else f'{pid} · {SEX_CS.get(sex, sex)}',
        'sex': sex,
        'age': age,
        'diagnosis': dg and {'text': _text(dg.get('code')), 'icd10': _code(dg.get('code'), 'icd-10'), 'citation': dg['id']},
        'mdt_question': ((req.get('reasonCode') or [{}])[0].get('text')),
        'mdt_question_citation': req.get('id'),
        'mdt_date': mdt_date,
    }


def detail(pid: str, rs: list[dict]) -> dict:
    conditions = [r for r in rs if r['resourceType'] == 'Condition']
    obs = [r for r in rs if r['resourceType'] == 'Observation']
    ecog = sorted((o for o in obs if _code(o.get('code'), 'loinc') == LOINC_ECOG), key=_date)
    samostatnost = sorted(
        ((qr, it) for qr in rs if qr['resourceType'] == 'QuestionnaireResponse'
         for it in qr.get('item', []) if it.get('linkId') == 'samostatnost' and it.get('answer')),
        key=lambda x: _date(x[0]),
    )
    out = summary(pid, rs)
    out.update({
        'diagnoses': [
            {'text': _text(c.get('code')), 'icd10': _code(c.get('code'), 'icd-10'), 'onset': c.get('onsetDateTime'),
             'verification': _code(c.get('verificationStatus'), 'ver-status'),
             'stage': next((s['summary']['text'] for s in c.get('stage', []) if s.get('summary', {}).get('text')), None),
             'citation': c['id']}
            for c in conditions if is_oncologic(c)
        ],
        'comorbidities': [
            {'text': _text(c.get('code')), 'icd10': _code(c.get('code'), 'icd-10') or None, 'citation': c['id']}
            for c in conditions if not is_oncologic(c)
        ],
        'tnm': [
            {'text': o.get('valueString', ''), 'kind': _text(o.get('code')), 'date': _date(o), 'citation': o['id']}
            for o in sorted(obs, key=_date) if 'TNM' in _text(o.get('code'))
        ],
        'ecog': {'physician': None, 'patient': None},
    })
    if ecog:
        o = ecog[-1]
        out['ecog']['physician'] = {'value': o.get('valueInteger'), 'date': _date(o), 'citation': o['id']}
    if samostatnost:
        qr, item = samostatnost[-1]
        coding = item['answer'][0]['valueCoding']
        out['ecog']['patient'] = {'value': int(coding['code']), 'date': _date(qr), 'citation': qr['id'],
                                  'answer_text': coding.get('display', '')}
    return out


# ── časová osa (TimelineEvent, §8.2) ─────────────────────────────────────────
_REPORT_TYPES = {'RAD': 'imaging', 'SP': 'pathology', 'LAB': 'lab'}


def _event(r: dict) -> tuple[str, str] | None:
    t = r['resourceType']
    if t == 'Condition':
        suffix = '' if is_oncologic(r) else ' (komorbidita)'
        return 'diagnosis', _text(r.get('code')) + suffix
    if t == 'Procedure':
        return 'procedure', _text(r.get('code'))
    if t in ('MedicationAdministration', 'MedicationRequest'):
        note = ' · '.join(n['text'] for n in r.get('note', []) if n.get('text'))
        return 'medication', _text(r.get('medicationCodeableConcept')) + (f' ({note})' if note else '')
    if t == 'DiagnosticReport':
        kind = next((_REPORT_TYPES[c] for cat in _categories(r) if (c := _code(cat, 'v2-0074')) in _REPORT_TYPES), 'document')
        return kind, _text(r.get('code'))
    if t == 'QuestionnaireResponse':
        return 'proms', 'Dotazník pacienta (PROMs)'
    if t == 'Composition':
        return 'mdt', r.get('title') or _text(r.get('type'))
    if t == 'DocumentReference':
        return 'document', _text(r.get('type')) or r.get('description', '')
    if t == 'ServiceRequest' and _code(r.get('code'), 'mdt-typ-projednani'):
        return 'mdt', 'Nominace na MDT: ' + (r.get('reasonCode') or [{}])[0].get('text', '')
    return None     # ponytail: Observation, ImagingStudy, CarePlan… jsou v detailu a grafech, osa by se zahltila


def timeline(rs: list[dict]) -> list[dict]:
    events = []
    for r in rs:
        ev, date = _event(r), _date(r)
        if ev and date:
            events.append({'date': date, 'type': ev[0], 'label': ev[1], 'citation': r['id']})
    for r in rs:     # termín zasedání z Task nominace
        if r['resourceType'] == 'Task' and (start := r.get('restriction', {}).get('period', {}).get('start')):
            events.append({'date': start[:10], 'type': 'mdt', 'label': 'Zasedání MDT (plánováno)', 'citation': r['id']})
    return sorted(events, key=lambda e: (e['date'], e['citation']))


# ── časové řady pro grafy ────────────────────────────────────────────────────
def observations(rs: list[dict], codes: set[str] | None = None) -> list[dict]:
    """Číselné řady: Observation (klíč = LOINC, jinak druh z ID, např. `lvef`) a PROMs (`proms:<linkId>`)."""
    series: dict[str, dict] = defaultdict(lambda: {'points': []})
    for o in (r for r in rs if r['resourceType'] == 'Observation'):
        q = o.get('valueQuantity') or {}
        value = q.get('value', o.get('valueInteger'))
        if value is None:
            continue
        key = _code(o.get('code'), 'loinc') or (m.group(1) if (m := _KIND.match(o['id'])) else o['id'])
        s = series[key]
        s.setdefault('label', _text(o.get('code')))
        s.setdefault('unit', q.get('unit'))
        rng = (o.get('referenceRange') or [{}])[0]
        point = {'date': _date(o), 'value': value, 'citation': o['id']}
        if rng:
            point.update(ref_low=rng.get('low', {}).get('value'), ref_high=rng.get('high', {}).get('value'))
        if (interp := _code((o.get('interpretation') or [{}])[0], 'ObservationInterpretation')):
            point['interpretation'] = interp
        s['points'].append(point)
    for qr in (r for r in rs if r['resourceType'] == 'QuestionnaireResponse'):
        for it in qr.get('item', []):
            for a in it.get('answer', [])[:1]:
                value = a.get('valueInteger', a.get('valueDecimal'))
                if value is None and it['linkId'] == 'samostatnost':
                    value = int(a['valueCoding']['code'])
                if value is None:
                    continue
                s = series[f"proms:{it['linkId']}"]
                s.setdefault('label', f"PROMs: {it['linkId']}")
                s.setdefault('unit', 'kg' if it['linkId'].startswith('hmotnost') else None)
                s['points'].append({'date': _date(qr), 'value': value, 'citation': qr['id']})
    return [
        {'code': k, 'label': s['label'], 'unit': s['unit'], 'points': sorted(s['points'], key=lambda p: (p['date'], p['citation']))}
        for k, s in sorted(series.items()) if not codes or k in codes
    ]


# ── načtení z IRIS ───────────────────────────────────────────────────────────
def load_patient(pid: str) -> list[dict]:
    """Všechny resources pacienta z IRIS (bez `$everything`, viz `fhir.patient_everything`)."""
    return [r for items in fhir.patient_everything(pid).values() for r in items]


def list_patients() -> list[dict]:
    by_pid: dict[str, list[dict]] = defaultdict(list)
    for rtype in ('Patient', 'Condition', 'ServiceRequest', 'Task'):
        for r in fhir.search(rtype):
            by_pid[r['id'] if rtype == 'Patient' else _subject(r)].append(r)
    return [summary(pid, rs) for pid, rs in sorted(by_pid.items())
            if any(r['resourceType'] == 'Patient' for r in rs)]
