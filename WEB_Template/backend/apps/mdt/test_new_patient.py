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
