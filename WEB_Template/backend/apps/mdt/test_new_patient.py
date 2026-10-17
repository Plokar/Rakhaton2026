"""Nový pacient z rodného čísla (T-323): návrh → náhledy → úpravy → potvrzení do IRIS. RČ se nikde nevrací."""
import io
import json
from datetime import date

import pytest
from django.core.management import call_command
from django.test import override_settings

from apps.copilot import schemas
from apps.mdt.models import MdtCase, MdtSession, PatientDraft
from apps.mdt.test_roles import as_user
from services import rc as rc_module
from services.fhir import client

pytestmark = pytest.mark.django_db

REPORT = """Onkologická ambulance – vstupní vyšetření 2. 10. 2026

Dg.: C18.7 – adenokarcinom sigmatu G2, jaterní metastázy (C78.7).

Histologie a grade: adenokarcinom sigmatu G2 (biopsie 20. 9. 2026), KRAS G12D, MMR nevyšetřeno.

Staging CT 25. 9. 2026: cT3 cN1 cM1a, stadium IVA.

Předchozí onkologická léčba: dosud žádná.

Objektivně: ECOG 1, hmotnost 78 kg.

Otázka pro MDT: Je vhodná primární resekce jaterních metastáz, nebo nejdřív systémová léčba?"""


def make_rc(born: date, female: bool = False) -> str:
    """Platné desetimístné RČ (ženy +50, kontrolní číslice dělitelná 11)."""
    head = f"{born:%y}{born.month + (50 if female else 0):02d}{born:%d}"
    for tail in range(10000):
        if int(f"{head}{tail:04d}") % 11 == 0 and tail % 10 != 0:
            return f"{head}/{tail:04d}"
    raise AssertionError


RC = make_rc(date(1959, 3, 15))


@pytest.fixture
def board(fake_fhir_dataset, fake_iris):
    call_command('seed_mdt')
    return MdtSession.objects.get(title__startswith='GIT')


def _create(user='onkolog', **extra):
    return as_user(user).post('/api/mdt/patient-drafts/', {'rc': RC, 'text': REPORT, **extra}, format='json')


def _no_rc(response) -> None:
    raw = json.dumps(response.json(), ensure_ascii=False)
    assert RC not in raw and RC.replace('/', '') not in raw


# ── rodné číslo ───────────────────────────────────────────────────────────────
def test_rc_parse():
    man = rc_module.parse(RC)
    assert (man.birth_date, man.gender, man.masked) == (date(1959, 3, 15), 'male', '******/' + RC[-4:])
    woman = rc_module.parse(make_rc(date(1972, 11, 2), female=True))
    assert (woman.birth_date, woman.gender) == (date(1972, 11, 2), 'female')
    assert rc_module.parse('535123/123').birth_date == date(1953, 1, 23)            # devítimístné, žena
    reserve = make_rc(date(2005, 4, 9)).replace('/', '')
    plus20 = f"{reserve[:2]}{int(reserve[2:4]) + 20:02d}{reserve[4:6]}"
    assert rc_module.parse(make_rc_from_head(plus20)).birth_date == date(2005, 4, 9)   # rezervní řada +20
    for bad in ('590315/1235', '591315/0000', '12345', '800230/0000'):
        with pytest.raises(rc_module.RcError):
            rc_module.parse(bad)


def make_rc_from_head(head: str) -> str:
    tail = next(t for t in range(1, 10000) if int(f"{head}{t:04d}") % 11 == 0)
    return f"{head}/{tail:04d}"


# ── návrh a náhledy ───────────────────────────────────────────────────────────
def test_draft_prefills_nomination_and_previews(board):
    r = _create(session=board.pk)
    assert r.status_code == 201, r.json()
    d = r.json()
    schemas.PatientDraft.model_validate(d)                                  # kontrakt §8.6
    _no_rc(r)
    assert d['patient_id'] == 'P07' and d['patient'] == {'rc_masked': '******/' + RC[-4:], 'sex': 'male',
                                                        'birth_year': 1959, 'age': d['patient']['age']}
    f = d['fields']
    assert [x['code'] for x in f['diagnoses']] == ['C18.7', 'C78.7']
    assert f['diagnoses'][0]['text'] == 'adenokarcinom sigmatu G2' and f['diagnoses'][1]['text'] == 'jaterní metastázy'
    assert f['diagnoses'][0]['citation'] == 'P07-imp01#2'
    assert f['tnm']['text'] == 'cT3 cN1 cM1a, stadium IVA' and f['ecog']['value'] == 1
    assert f['question']['text'].startswith('Je vhodná primární resekce') and f['history']['text'] == 'dosud žádná.'
    assert d['missing_for_confirm'] == [] and d['ai']['used'] is False      # AI_PROVIDER=mock: jen pravidla z textu

    detail, narrow = d['preview']['detail'], d['preview']['narrow']
    schemas.Brief.model_validate(detail)
    schemas.Brief.model_validate(narrow)
    assert detail['header']['display_name'] == 'P07 · muž · 67 let'
    assert detail['header']['diagnosis']['icd10'] == 'C18.7'
    assert len(detail['sections']) > len(narrow['sections'])                 # úzký pás = šablona projektoru
    assert d['preview']['template']['template_id'].startswith('sab-krc')
    warnings = {w['id'] for w in d['preview']['intake']['warnings']}
    assert any(w.startswith('RF-MISSING') or w.startswith('missing:bm.mmr') for w in warnings), warnings


def test_doctor_edits_then_confirms_into_iris(board):
    draft_id = _create(session=board.pk).json()['id']
    r = as_user('onkolog').patch(f'/api/mdt/patient-drafts/{draft_id}/', {'fields': {
        'question': 'Resekabilita jaterních metastáz: jednodobě, nebo dvoudobě?', 'ecog': 0,
        'diagnoses': [{'code': 'C18.7', 'text': 'Adenokarcinom sigmatu G2'}, {'code': 'C78.7'}]}}, format='json')
    assert r.status_code == 200, r.json()
    fields = r.json()['fields']
    assert fields['question'] == {'text': 'Resekabilita jaterních metastáz: jednodobě, nebo dvoudobě?', 'citation': None}
    assert fields['diagnoses'][1]['citation'] == 'P07-imp01#2'          # beze změny textu zůstává citace dokumentu
    assert r.json()['preview']['detail']['header']['ecog']['physician']['value'] == 0

    r = as_user('onkolog').post(f'/api/mdt/patient-drafts/{draft_id}/confirm/')
    assert r.status_code == 201, r.json()
    _no_rc(r)
    written = r.json()['fhir_written']
    assert {'Patient/P07', 'DocumentReference/P07-imp01', 'ServiceRequest/P07-zad01', 'Task/P07-zad01-task',
            'Condition/P07-dg1', 'Observation/P07-tnm01', 'Observation/P07-ecog01', 'Provenance/P07-zad01-prov'} <= set(written)
    patient = client.read('Patient', 'P07')
    assert {'system': rc_module.SYSTEM, 'value': RC} in patient['identifier'] and patient['gender'] == 'male'
    assert client.read('ServiceRequest', 'P07-zad01')['reasonCode'][0]['text'].startswith('Resekabilita')
    ecog = client.read('Observation', 'P07-ecog01')
    assert ecog['valueInteger'] == 0 and ecog['extension'][0]['valueReference'] == {'reference': 'ServiceRequest/P07-zad01'}

    case = MdtCase.objects.get(patient_fhir_id='P07')
    assert case.session == board and list(board.cases.values_list('patient_fhir_id', flat=True))[-1] == 'P07'
    draft = PatientDraft.objects.get(pk=draft_id)
    assert draft.status == 'confirmed' and draft.rc == '' and 'text' not in json.dumps(draft.content)

    listed = as_user('chirurg').get('/api/patients/')
    _no_rc(listed)
    assert next(p for p in listed.json() if p['id'] == 'P07')['display_name'] == 'P07 · muž · 67 let'
    _no_rc(as_user('chirurg').get('/api/patients/P07/'))
    intake = as_user('onkolog').get('/api/mdt/patients/P07/intake/').json()      # běžné zařazení funguje
    assert {f['id']: f['status'] for f in intake['fields']}['mdt.question'] == 'present'

    with override_settings(MDT_JOBS_SYNC=True):
        job = as_user('onkolog').post(f'/api/mdt/cases/{case.pk}/brief/', {}, format='json')
    assert job.status_code == 202
    brief = as_user('chirurg').get(f'/api/mdt/cases/{case.pk}/brief/').json()
    assert brief['header']['display_name'] == 'P07 · muž · 67 let'
    assert RC not in json.dumps(brief, ensure_ascii=False)


def test_duplicate_rc_and_permissions(board):
    assert _create(user='chirurg').status_code == 403                      # prohlížející nezakládá
    first = _create()
    assert _create().json()['draft_id'] == first.json()['id']               # rozpracovaný návrh se stejným RČ
    assert as_user('pneumolog').get(f"/api/mdt/patient-drafts/{first.json()['id']}/").status_code == 403
    assert as_user('predseda').get(f"/api/mdt/patient-drafts/{first.json()['id']}/").status_code == 200
    as_user('onkolog').post(f"/api/mdt/patient-drafts/{first.json()['id']}/confirm/")
    again = _create()
    assert again.status_code == 409 and again.json()['patient_id'] == 'P07'
    assert as_user('onkolog').post('/api/mdt/patient-drafts/', {'rc': '590315/1235'}, format='json').status_code == 400


def test_confirm_needs_question_and_diagnosis(board):
    draft = as_user('onkolog').post('/api/mdt/patient-drafts/', {'rc': RC, 'text': 'Kontrola 1. 10. 2026: bez potíží.'},
                                    format='json').json()
    assert draft['missing_for_confirm'] == ['Otázka pro MDT (OBC-1.1)', 'Diagnóza s kódem MKN-10']
    r = as_user('onkolog').post(f"/api/mdt/patient-drafts/{draft['id']}/confirm/")
    assert r.status_code == 400 and len(r.json()['missing']) == 2
    with pytest.raises(Exception):
        client.read('Patient', draft['patient_id'])
    bad = as_user('onkolog').patch(f"/api/mdt/patient-drafts/{draft['id']}/", {'fields': {'diagnoses': [{'code': 'I25.2'}]}},
                                   format='json')
    assert bad.status_code == 400


def test_files_text_and_pdf(board):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    pdf.drawString(72, 750, 'Dg.: C50.4 - invazivni karcinom prsu NST G2.')
    pdf.drawString(72, 730, 'ECOG 0.')
    pdf.save()
    buf.seek(0)
    buf.name = 'zprava.pdf'
    txt = io.BytesIO('Otázka pro MDT: Adjuvantní léčba?'.encode('utf-8'))
    txt.name = 'nominace.txt'
    r = as_user('onkolog').post('/api/mdt/patient-drafts/', {'rc': RC, 'files': [buf, txt]}, format='multipart')
    assert r.status_code == 201, r.json()
    d = r.json()
    assert [doc['source'] for doc in d['documents']] == ['soubor zprava.pdf', 'soubor nominace.txt']
    assert d['fields']['diagnoses'][0]['code'] == 'C50.4' and d['fields']['ecog']['value'] == 0
    assert d['fields']['question']['citation'] == 'P07-imp02#1'

    more = io.BytesIO(b'Komorbidity: hypertenze.')
    more.name = 'doplneni.txt'
    r = as_user('onkolog').post(f"/api/mdt/patient-drafts/{d['id']}/documents/", {'files': [more]}, format='multipart')
    assert r.json()['documents'][-1]['id'] == 'P07-imp03' and r.json()['fields']['comorbidities']['text'] == 'hypertenze.'
    r = as_user('onkolog').patch(f"/api/mdt/patient-drafts/{d['id']}/", {'remove_documents': ['P07-imp01']}, format='json')
    assert r.json()['fields']['diagnoses'] == [] and 'ecog' not in r.json()['fields']

    blank = io.BytesIO(b'%PDF-1.4 nic')
    blank.name = 'sken.pdf'
    bad = as_user('onkolog').post(f"/api/mdt/patient-drafts/{d['id']}/documents/", {'files': [blank]}, format='multipart')
    assert bad.status_code == 400 and 'files' in bad.json()


def test_real_patient_data_never_go_to_llm(monkeypatch):
    """D-021: bez tagu `fiktivni-data` a bez AI_REAL_PATIENT_DATA se místo Gemini použije mock."""
    from services import ai_service
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test')
    monkeypatch.delenv('AI_REAL_PATIENT_DATA', raising=False)
    real = [{'resourceType': 'Patient', 'id': 'P07', 'meta': {'tag': []}}]
    synthetic = [{'resourceType': 'Patient', 'id': 'P03', 'meta': {'tag': [{'code': 'fiktivni-data'}]}}]
    assert ai_service.provider_for_patient(real).is_mock
    assert not ai_service.provider_for_patient(synthetic).is_mock
    monkeypatch.setenv('AI_REAL_PATIENT_DATA', 'True')
    assert not ai_service.provider_for_patient(real).is_mock


# ── import z FHIR JSON (T-335) ────────────────────────────────────────────────
def _json_file(data, name='pacient.json'):
    f = io.BytesIO(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    f.name = name
    return f


def _dataset_bundle(pid='P07'):
    from pathlib import Path
    root = Path(__file__).resolve().parents[4] / 'data' / 'dataset_test' / 'pacienti'
    return json.loads((root / pid / f'{pid}_bundle.json').read_text(encoding='utf-8'))


def test_json_bundle_prefills_nomination_and_confirms_into_iris(board):
    """Bundle P07 z data/dataset_test bez RČ → návrh s nominací ze strukturovaných dat → zápis do IRIS + případ."""
    r = as_user('onkolog').post('/api/mdt/patient-drafts/', {'files': [_json_file(_dataset_bundle(), 'P07_bundle.json')],
                                                             'session': board.pk}, format='multipart')
    assert r.status_code == 201, r.json()
    d = r.json()
    assert d['patient_id'] == 'P07' and d['synthetic'] and d['import']['file'] == 'P07_bundle.json'
    assert d['import']['counts']['Observation'] == 12 and d['import']['practitioners'] == ['LEK-P07-01', 'LEK-P07-02', 'LEK-P07-03']
    assert d['patient'] == {'rc_masked': None, 'sex': 'female', 'birth_year': 1967, 'age': d['patient']['age']}
    f = d['fields']
    assert f['question']['citation'] == 'P07-zad01' and 'jaterními metastázami' in f['question']['text']
    assert [x['code'] for x in f['diagnoses']][:1] == ['C20'] and f['diagnoses'][0]['citation'] == 'P07-dg1'
    assert f['ecog']['citation'] == 'P07-ecog01' and f['tnm']['citation'] == 'P07-tnm01'
    assert d['missing_for_confirm'] == [] and d['preview']['detail']['patient_id'] == 'P07'

    locked = as_user('onkolog').patch(f"/api/mdt/patient-drafts/{d['id']}/", {'fields': {'ecog': 2}}, format='json')
    assert locked.status_code == 400
    edited = as_user('onkolog').patch(f"/api/mdt/patient-drafts/{d['id']}/",
                                      {'fields': {'question': 'Pořadí léčby: nejdřív játra, nebo rektum?'}}, format='json')
    assert edited.status_code == 200 and 'question' in edited.json()['edited']

    done = as_user('onkolog').post(f"/api/mdt/patient-drafts/{d['id']}/confirm/")
    assert done.status_code == 201, done.json()
    assert 'Practitioner/LEK-P07-01' in done.json()['fhir_written'] and 'Provenance/P07-zad01-prov' in done.json()['fhir_written']
    request = client.read('ServiceRequest', 'P07-zad01')
    assert request['reasonCode'][0]['text'] == 'Pořadí léčby: nejdřív játra, nebo rektum?'
    assert any(t['code'] == 'import-fhir-json' for t in client.read('Patient', 'P07')['meta']['tag'])
    case = MdtCase.objects.get(patient_fhir_id='P07')
    assert case.session == board and case.service_request_fhir_id == 'P07-zad01'
    assert as_user('onkolog').get('/api/mdt/patients/P07/intake/').json()['service_request_id'] == 'P07-zad01'


def test_json_generic_bundle_renumbers_ids_and_references(board):
    """Export mimo konvenci datasetu (UUID, `urn:uuid` reference) → ID podle konvence a funkční reference."""
    rc = make_rc(date(1961, 6, 1), female=True)
    bundle = {'resourceType': 'Bundle', 'type': 'collection', 'entry': [
        {'fullUrl': 'urn:uuid:aaa', 'resource': {'resourceType': 'Patient', 'id': 'aaa', 'gender': 'female', 'birthDate': '1961-06-01'}},
        {'fullUrl': 'urn:uuid:bbb', 'resource': {
            'resourceType': 'Condition', 'id': 'bbb', 'category': [{'text': 'onkologická diagnóza'}],
            'code': {'coding': [{'system': 'http://hl7.org/fhir/sid/icd-10', 'code': 'C50.4', 'display': 'karcinom prsu'}]},
            'subject': {'reference': 'urn:uuid:aaa'}}},
        {'fullUrl': 'urn:uuid:ccc', 'resource': {
            'resourceType': 'Observation', 'id': 'ccc', 'status': 'final',
            'code': {'coding': [{'system': 'http://loinc.org', 'code': '89247-1'}], 'text': 'ECOG'},
            'valueInteger': 1, 'subject': {'reference': 'Patient/aaa'}}},
        {'resource': {'resourceType': 'ServiceRequest', 'id': 'ddd', 'status': 'active', 'intent': 'order',
                      'subject': {'reference': 'Patient/aaa'}, 'reasonReference': [{'reference': 'urn:uuid:bbb'}],
                      'reasonCode': [{'text': 'Adjuvantní léčba?'}]}},
    ]}
    r = as_user('onkolog').post('/api/mdt/patient-drafts/', {'rc': rc, 'files': [_json_file(bundle)]}, format='multipart')
    assert r.status_code == 201, r.json()
    d = r.json()
    _no_rc_value(r, rc)
    assert d['import']['renamed_from'] == 'aaa' and d['patient']['rc_masked'].endswith(rc[-4:])
    f = d['fields']
    assert f['diagnoses'][0] == {'code': 'C50.4', 'text': 'karcinom prsu', 'citation': 'P07-dg1'}
    assert f['ecog'] == {'value': 1, 'citation': 'P07-ecog01', 'date': None} and f['question']['citation'] == 'P07-zad01'
    done = as_user('onkolog').post(f"/api/mdt/patient-drafts/{d['id']}/confirm/")
    assert done.status_code == 201, done.json()
    assert client.read('Condition', 'P07-dg1')['subject'] == {'reference': 'Patient/P07'}
    assert client.read('ServiceRequest', 'P07-zad01')['reasonReference'] == [{'reference': 'Condition/P07-dg1'}]
    patient = client.read('Patient', 'P07')
    assert {'system': rc_module.SYSTEM, 'value': rc} in patient['identifier']


def _no_rc_value(response, rc):
    raw = json.dumps(response.json(), ensure_ascii=False)
    assert rc not in raw and rc.replace('/', '') not in raw


def test_json_upload_errors(board):
    post = lambda data, **extra: as_user('onkolog').post(  # noqa: E731
        '/api/mdt/patient-drafts/', {'files': [_json_file(data)], **extra}, format='multipart')
    bundle = _dataset_bundle()
    man = make_rc(date(1967, 1, 5))                                       # P07 je žena
    assert 'pohlaví' in post(bundle, rc=man).json()['files']
    woman_other_year = make_rc(date(1970, 1, 5), female=True)
    assert 'Rok narození' in post(bundle, rc=woman_other_year).json()['files']
    both = {'resourceType': 'Bundle', 'entry': [
        {'resource': {'resourceType': 'Patient', 'id': 'a', 'gender': 'male', 'birthDate': '1950'}},
        {'resource': {'resourceType': 'Patient', 'id': 'b', 'gender': 'male', 'birthDate': '1950'}},
        {'resource': {'resourceType': 'Observation', 'id': 'o', 'subject': {'reference': 'Patient/a'},
                      'focus': [{'reference': 'Patient/b'}]}}]}
    assert 'víc pacientů' in post(both).json()['files']
    assert 'právě jednoho pacienta' in post({'resourceType': 'Observation', 'id': 'x'}).json()['files']
    dangling = {'resourceType': 'Bundle', 'entry': [
        {'resource': {'resourceType': 'Patient', 'id': 'a', 'gender': 'male', 'birthDate': '1950'}},
        {'resource': {'resourceType': 'Condition', 'id': 'c', 'subject': {'reference': 'Patient/a'},
                      'evidence': [{'detail': [{'reference': 'DiagnosticReport/neni'}]}]}}]}
    assert 'nejsou v souboru ani v IRIS' in post(dangling).json()['files']
    broken = io.BytesIO(b'{"resourceType": ')
    broken.name = 'rozbity.json'
    r = as_user('onkolog').post('/api/mdt/patient-drafts/', {'files': [broken]}, format='multipart')
    assert r.status_code == 400 and 'platný JSON' in r.json()['files']
    assert as_user('onkolog').post('/api/mdt/patient-drafts/', {'text': 'Dg.: C50.4'}, format='multipart').status_code == 400  # bez JSON je RČ povinné


def _dataset_file(pid, kind):
    from services.fhir import ingest
    path = ingest.repo_dataset() / 'pacienti' / pid / f'{pid}_{kind}'
    return path.read_bytes()


def test_json_with_transcript_md_and_rc(board):
    """DoD T-335: P01 bundle + přepis `.md` s RČ → návrh bez chyb validace, otázka, 3 diagnózy, TNM a ECOG z resources."""
    rc = make_rc(date(1963, 2, 11), female=True)
    md = _dataset_file('P01', 'pacient.md').decode('utf-8').replace(
        '**rok narození:** 1963', f'**rok narození:** 1963 · **RČ:** {rc}', 1)
    bundle = io.BytesIO(_dataset_file('P01', 'bundle.json'))
    bundle.name = 'P01_bundle.json'
    transcript = io.BytesIO(md.encode('utf-8'))
    transcript.name = 'P01_pacient.md'
    r = as_user('onkolog').post('/api/mdt/patient-drafts/', {'files': [bundle, transcript]}, format='multipart')
    assert r.status_code == 201, r.json()
    _no_rc_value(r, rc)
    d = r.json()
    assert d['import']['transcript'] == 'P01_pacient.md' and d['import']['validation'] == []
    assert d['patient']['rc_masked'].endswith(rc[-4:]) and d['documents'] == []          # přepis není podklad
    f = d['fields']
    new = d['patient_id']
    assert d['import']['renamed_from'] == 'P01' and new == 'P07'
    assert [x['code'] for x in f['diagnoses']] == ['C50.4', 'C78.7', 'C79.5']
    assert f['question']['citation'] == f'{new}-zad01' and f['tnm'] and f['ecog']['value'] == 1

    changed = md.replace('**C78.7**', '**C78.8**', 1)
    transcript = io.BytesIO(changed.encode('utf-8'))
    transcript.name = 'P01_pacient.md'
    bundle = io.BytesIO(_dataset_file('P01', 'bundle.json'))
    bundle.name = 'P01_bundle.json'
    rc2 = make_rc(date(1963, 3, 12), female=True)
    other = as_user('onkolog').post('/api/mdt/patient-drafts/', {'rc': rc2, 'files': [bundle, transcript]}, format='multipart')
    assert other.status_code == 201
    assert any('C78.8' in issue for issue in other.json()['import']['validation'])


def test_json_with_more_patients_creates_draft_for_each(board):
    """Soubor se 2 pacienty → návrh pro každého; sdílené lékaře a organizaci dostane každý, kdo je odkazuje."""
    entries = _dataset_bundle('P10')['entry'] + _dataset_bundle('P11')['entry']
    seen, unique = set(), []
    for e in entries:                                   # ORG-FN je v obou bundlech
        k = (e['resource']['resourceType'], e['resource']['id'])
        if k not in seen:
            seen.add(k)
            unique.append(e)
    r = as_user('onkolog').post('/api/mdt/patient-drafts/', {
        'files': [_json_file({'resourceType': 'Bundle', 'type': 'collection', 'entry': unique}, 'dva.json')]}, format='multipart')
    assert r.status_code == 201, r.json()
    batch = r.json()['batch']
    assert [(b['patient_id'], b['renamed_from']) for b in batch] == [('P07', 'P10'), ('P08', 'P11')]
    second = as_user('onkolog').get(f"/api/mdt/patient-drafts/{batch[1]['id']}/").json()
    assert second['fields']['diagnoses'][0]['code'] == 'C21.1' and second['import']['practitioners']
    assert {x['patient_id'] for x in as_user('onkolog').get('/api/mdt/patient-drafts/').json()} >= {'P07', 'P08'}
    rc = make_rc(date(1960, 1, 1))
    mixed = as_user('onkolog').post('/api/mdt/patient-drafts/', {
        'rc': rc, 'files': [_json_file({'resourceType': 'Bundle', 'entry': unique}, 'dva.json')]}, format='multipart')
    assert mixed.status_code == 400 and '2 pacienty' in mixed.json()['files']


@pytest.mark.parametrize('name, patients', [('dva_pacienti_P10_P11.json', 2), ('obecny_export_uuid.json', 1)])
def test_import_examples_stay_valid(board, name, patients):
    """Ukázkové soubory v data/import_ukazky jdou naimportovat (README tamtéž)."""
    from pathlib import Path
    path = Path(__file__).resolve().parents[4] / 'data' / 'import_ukazky' / name
    f = io.BytesIO(path.read_bytes())
    f.name = name
    r = as_user('onkolog').post('/api/mdt/patient-drafts/', {'files': [f]}, format='multipart')
    assert r.status_code == 201, r.json()
    assert len(r.json().get('batch') or [r.json()]) == patients and r.json()['missing_for_confirm'] == []
