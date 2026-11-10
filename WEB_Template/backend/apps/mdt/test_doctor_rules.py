"""Požadavky a normy lékaře (T-358–T-360, D-028, docs/UCTY_A_PVW.md §3)."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.mdt.models import DoctorNorm, MdtCase
from services.rules import doctor_rules as dr
from services.rules.fact_templates import validate_layout

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(fake_fhir_dataset):
    call_command('seed_mdt')
    return fake_fhir_dataset


def as_user(username):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


# ── vyhodnocení normy (bez databáze) ─────────────────────────────────────────
FACTS = {
    'liver.flr': {'status': 'present', 'value': 'Objem levého laloku (S2–S4) odhadem 38 % celkového objemu jater.',
                  'citation': 'P03-img04#3'},
    'spiro.fev1': {'status': 'present', 'value': '1,9 l (58 % náležité hodnoty)', 'citation': 'P04-spiro01'},
    'ecog.physician': {'status': 'present', 'value': '2', 'citation': 'P03-ecog03'},
    'bm.pdl1': {'status': 'present', 'value': 'TPS < 1 %', 'citation': 'P04-bm01'},
    'lab:718-7': {'status': 'present', 'value': '114 g/l (2026-10-05)', 'number': 114.0, 'unit': 'g/l',
                  'citation': 'P03-lab06-hb'},
    'spiro.dlco': {'status': 'skipped', 'value': None, 'citation': None},
}


@pytest.mark.parametrize('norm, status', [
    ({'field': 'liver.flr', 'op': '>=', 'value': 30, 'unit': '%'}, 'met'),          # „S2–S4“ není rozmezí ani číslo
    ({'field': 'liver.flr', 'op': '>=', 'value': 40, 'unit': '%'}, 'not_met'),
    ({'field': 'spiro.fev1', 'op': '>=', 'value': 40, 'unit': '%'}, 'met'),         # číslo v jednotce normy
    ({'field': 'spiro.fev1', 'op': '>=', 'value': 40, 'unit': ''}, 'not_evaluable'),  # 1,9 i 58: nehádá
    ({'field': 'ecog.physician', 'op': '<=', 'value': 1, 'unit': ''}, 'not_met'),
    ({'field': 'bm.pdl1', 'op': '>=', 'value': 1, 'unit': '%'}, 'not_evaluable'),   # nerovnost = NEJISTOTA
    ({'field': 'lab:718-7', 'op': '>=', 'value': 100, 'unit': 'g/l'}, 'met'),
    ({'field': 'lab:718-7', 'op': '>=', 'value': 10, 'unit': 'g/dl'}, 'not_evaluable'),  # jiná jednotka
    ({'field': 'spiro.dlco', 'op': '>=', 'value': 40, 'unit': '%'}, 'missing'),     # přeskočeno
    ({'field': 'lvef', 'op': '>=', 'value': 50, 'unit': '%'}, 'missing'),           # u pacienta není
])
def test_evaluate_norm(norm, status):
    result = dr.evaluate_norm(norm, FACTS)
    assert result['status'] == status, result
    if status in ('met', 'not_met'):
        assert result['citation'] and result['reason'] is None
    else:
        assert result['reason']


def test_norm_text_and_fields():
    assert dr.norm_text({'field': 'liver.flr', 'op': '>=', 'value': 30.0, 'unit': '%'}) == \
        'Budoucí jaterní remnant (FLR) ≥ 30 %'
    assert 'lab:718-7' in dr.NORM_KEYS and 'patient.age' in dr.NORM_KEYS
    assert validate_layout({'blocks': {'order': ['facts', 'norms', 'treatments'], 'hidden': []}})


# ── moje nastavení ───────────────────────────────────────────────────────────
def test_my_requirements_and_norms(seeded):
    client = as_user('radioterapeut')
    r = client.put('/api/mdt/my-rules/requirements/PLI/', {'fields': ['spiro.fev1', 'spiro.dlco'], 'note': 'k RT'},
                   format='json')
    assert r.status_code == 200 and r.json()['fields'] == ['spiro.fev1', 'spiro.dlco']
    assert client.put('/api/mdt/my-rules/requirements/PLI/', {'fields': ['neexistuje']}, format='json').status_code == 400
    assert client.put('/api/mdt/my-rules/requirements/XXX/', {'fields': []}, format='json').status_code == 400
    assert client.put('/api/mdt/my-rules/requirements/*/', {'fields': ['ecog.physician']}, format='json').status_code == 200

    norm = client.post('/api/mdt/my-rules/norms/', {'area': 'PLI', 'field': 'spiro.fev1', 'op': '>=', 'value': '40',
                                                     'unit': '%', 'procedure': 'radikální RT', 'source': 'PLI-3.1'},
                       format='json')
    assert norm.status_code == 201, norm.json()
    assert norm.json()['text'] == 'FEV1 ≥ 40 %'
    for bad in ({'field': 'staging.pet'}, {'op': '=>'}, {'value': 'hodně'}, {'source': 'moje poznámka'}):
        body = {'area': 'PLI', 'field': 'spiro.fev1', 'op': '>=', 'value': 40, **bad}
        assert client.post('/api/mdt/my-rules/norms/', body, format='json').status_code == 400
    rules = client.get('/api/mdt/my-rules/').json()
    assert len(rules['requirements']) == 2 and len(rules['norms']) == 1 and rules['ops']

    nid = norm.json()['id']                             # cizí normu nikdo jiný nemění, ani správce (D-028)
    assert as_user('predseda').put(f'/api/mdt/my-rules/norms/{nid}/', {'field': 'spiro.fev1', 'op': '>=', 'value': 1},
                                   format='json').status_code == 404
    uid = get_user_model().objects.get(username='radioterapeut').pk
    assert len(as_user('predseda').get(f'/api/mdt/users/{uid}/rules/').json()['norms']) == 1
    assert as_user('onkolog').get(f'/api/mdt/users/{uid}/rules/').status_code == 403
    assert client.delete(f'/api/mdt/my-rules/norms/{nid}/').status_code == 204
    assert not DoctorNorm.objects.exists()


# ── u pacienta ───────────────────────────────────────────────────────────────
def test_requirements_and_norms_for_case(seeded):
    case = MdtCase.objects.get(patient_fhir_id='P04')               # karcinom plic, zadává pneumolog
    rt = as_user('radioterapeut')
    rt.put('/api/mdt/my-rules/requirements/PLI/', {'fields': ['spiro.fev1', 'spiro.dlco', 'bm.egfr']}, format='json')
    rt.post('/api/mdt/my-rules/norms/', {'area': '*', 'field': 'spiro.fev1', 'op': '>=', 'value': 40, 'unit': '%'},
            format='json')
    as_user('chirurg').post('/api/mdt/my-rules/norms/', {'area': 'KRC', 'field': 'liver.flr', 'op': '>=', 'value': 30,
                                                          'unit': '%'}, format='json')   # jiná oblast: u P04 ne

    rules = as_user('pneumolog').get(f'/api/mdt/cases/{case.pk}/doctor-rules/').json()
    assert rules['area'] == 'PLI'
    names = [d['name'] for d in rules['doctors']]
    assert names == ['Radiační onkolog']                  # zadávající lékař sám sebe nevidí
    doctor = rules['doctors'][0]
    assert {i['key']: i['status'] for i in doctor['requirement']['items']} == {
        'spiro.fev1': 'present', 'spiro.dlco': 'present', 'bm.egfr': 'pending'}
    assert doctor['requirement']['missing'] == ['bm.egfr']
    assert doctor['norms'][0]['result'] == {'status': 'met', 'value': '1,9 l (58 % náležité hodnoty)',
                                            'citation': 'P04-spiro01', 'reason': None}

    # zadávající lékař rozhodne; záznam se jen přidává (D-019)
    url = f'/api/mdt/cases/{case.pk}/doctor-rules/decision/'
    uid = doctor['user_id']
    assert as_user('chirurg').post(url, {'user_id': uid, 'decision': 'needed'}, format='json').status_code == 403
    assert as_user('pneumolog').post(url, {'user_id': 999, 'decision': 'needed'}, format='json').status_code == 400
    r = as_user('pneumolog').post(url, {'user_id': uid, 'decision': 'needed', 'prep_tasks': True}, format='json')
    assert r.status_code == 200, r.json()
    assert r.json()['fhir_written'] and r.json()['doctors'][0]['decision']['decision'] == 'needed'
    task = seeded.store[r.json()['fhir_written'][0]]
    assert 'EGFR (vyžaduje Radiační onkolog)' in task['description']
    as_user('pneumolog').post(url, {'user_id': uid, 'decision': 'not_needed', 'note': 'stačí'}, format='json')
    case.refresh_from_db()
    assert [d['decision'] for d in case.requirement_decisions] == ['needed', 'not_needed']

    # vyřazený z komise u zasedání už pozvaný není
    case.session.excluded.add(get_user_model().objects.get(username='radioterapeut'))
    assert as_user('pneumolog').get(f'/api/mdt/cases/{case.pk}/doctor-rules/').json()['doctors'] == []


def test_session_doctor_rules_at_intake(seeded):
    case = MdtCase.objects.get(patient_fhir_id='P04')
    as_user('radioterapeut').put('/api/mdt/my-rules/requirements/*/', {'fields': ['ecog.physician', 'weight']},
                                 format='json')
    url = f'/api/mdt/sessions/{case.session_id}/doctor-rules/?patient=P04'
    doctors = as_user('pneumolog').get(url).json()['doctors']
    assert [i['status'] for i in doctors[0]['requirement']['items']] == ['present', 'present']
    assert as_user('pneumolog').get(f'/api/mdt/sessions/{case.session_id}/doctor-rules/?patient=x').status_code == 400
    # přihlášený (připravující) lékař sám sebe nevidí
    assert as_user('radioterapeut').get(url).json()['doctors'] == []


def test_intake_decisions_saved_with_case(seeded):
    from apps.mdt.test_roles import resolved_intake
    case = MdtCase.objects.get(patient_fhir_id='P04')
    radio = get_user_model().objects.get(username='radioterapeut')
    body = {'session': case.session_id, 'patient_id': 'P04', **resolved_intake('P04', 'pneumolog'),
            'ecog': 1, 'intent': 'C', 'imaging_recent_checked': True,
            'requirement_decisions': [{'user_id': radio.pk, 'decision': 'not_needed', 'note': 'jen chirurgie'}]}
    r = as_user('pneumolog').post('/api/mdt/cases/', body, format='json')
    assert r.status_code in (200, 201), r.json()
    case.refresh_from_db()
    assert case.requirement_decisions[-1] | {'at': None} == {
        'user_id': radio.pk, 'decision': 'not_needed', 'note': 'jen chirurgie', 'by': 'Pneumolog', 'at': None}
    bad = {**body, 'requirement_decisions': [{'user_id': radio.pk, 'decision': 'mozna'}]}
    assert as_user('pneumolog').post('/api/mdt/cases/', bad, format='json').status_code == 400
