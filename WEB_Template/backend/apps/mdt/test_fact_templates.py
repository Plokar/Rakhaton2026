"""Kategorie údajů, šablona lékaře, zakládání lékaře a BMI (T-338, T-341, docs/SABLONY_LEKARE.md)."""
import pytest
from django.core.management import call_command

from apps.copilot import schemas
from apps.mdt.models import FactTemplate, MdtCase
from apps.mdt.test_roles import as_user
from services.rules import fact_templates as ft
from services.rules.fact_categories import CATEGORY_IDS, alert_key, area_for_icd10, bmi, field_category
from services.rules.intake import intake_prefill
from services.tests.dataset import load_patient

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(fake_fhir_dataset):
    call_command('seed_mdt')


# ── kategorie (D-024) ─────────────────────────────────────────────────────────
def test_every_intake_field_and_warning_has_category():
    """Každé pole formuláře zařazení všech pacientů má kategorii; dotazníky nejsou mezi vyšetřeními."""
    for pid in ('P01', 'P02', 'P03', 'P04', 'P05', 'P06'):
        prefill = intake_prefill(load_patient(pid))
        schemas.IntakePrefill.model_validate(prefill)
        assert all(f['category'] in CATEGORY_IDS for f in prefill['fields'])
        assert all(w['category'] in ('patient', 'alerts') for w in prefill['warnings'])
    p04 = intake_prefill(load_patient('P04'))
    by_id = {f['id']: f['category'] for f in p04['fields']}
    assert by_id['staging.tnm'] == 'staging' and by_id['bm.egfr'] == 'molecular' and by_id['staging.pet'] == 'imaging'
    assert by_id['spiro.fev1'] == 'function' and by_id['smoking'] == 'history' and by_id['lab.na'] == 'lab'
    proms = {w['id']: w['category'] for w in p04['warnings']}
    assert proms['RF-PROMS:P04-prom02'] == 'patient' and proms['RF-GERI:P04'] == 'alerts'
    assert field_category('bm.neco_noveho') == 'molecular' and field_category('neznamy') == 'history'
    assert alert_key('RF-LAB:P04-lab05-cea') == 'alert:RF-LAB' and alert_key('DOP:obc.hbv') == 'alert:DOP'
    assert [area_for_icd10([c]) for c in ('C34.1', 'C50.4', 'C20', 'C61')] == ['PLI', 'PRS', 'KRC', 'OBC']


# ── BMI (T-341) ───────────────────────────────────────────────────────────────
def _height(pid: str, value: float, unit: str = 'cm') -> dict:
    return {'resourceType': 'Observation', 'id': f'{pid}-vyska01', 'status': 'final', 'effectiveDateTime': '2026-10-06',
            'code': {'coding': [{'system': 'http://loinc.org', 'code': '8302-2'}], 'text': 'Výška'},
            'valueQuantity': {'value': value, 'unit': unit}, 'subject': {'reference': f'Patient/{pid}'}}


def test_bmi_only_from_measured_height():
    resources = load_patient('P04')                                   # 71 kg, výška v datasetu není
    weight = next(f for f in intake_prefill(resources)['fields'] if f['id'] == 'weight')
    assert weight['value'].startswith('71 kg') and weight['value'].endswith('BMI: chybí výška')
    with_height = intake_prefill(resources + [_height('P04', 176)])
    weight = next(f for f in with_height['fields'] if f['id'] == 'weight')
    assert weight['value'].endswith('BMI 22,9') and not any(w['id'].startswith('RF-BMI') for w in with_height['warnings'])
    thin = intake_prefill(resources + [_height('P04', 1.92, 'm')])    # 71 / 1,92² = 19,3; P04 má 70 let → hranice 22
    flag = next(w for w in thin['warnings'] if w['id'].startswith('RF-BMI'))
    assert flag['citations'] == ['P04-vaha03', 'P04-vyska01', 'EXT-MK-31.3-2']     # i oddíl Modré knihy (GLIM)
    assert bmi(71, 0.5, 'm') is None and bmi(71, 176, None) == 22.9


# ── šablona lékaře (D-025) ───────────────────────────────────────────────────
def test_pulmonologist_preset_is_doctors_list():
    preset = ft.preset_for('pulmonologist', 'PLI')
    assert preset['id'] == 'pneumolog-plice'
    layout = preset['layout']
    assert layout['categories']['hidden'] == ['patient', 'alerts']
    assert layout['facts']['order'][:5] == ['staging.tnm', 'dx.histology', 'bm.egfr', 'bm.alk', 'bm.pdl1']
    assert {'spiro.vo2max', 'spiro.ppo_fev1', 'spiro.ppo_dlco', 'lab:777-3'} <= set(layout['facts']['hidden'])
    assert ft.preset_for('surgeon', 'PLI')['id'] == 'vychozi' and ft.preset_for('pulmonologist', 'PRS')['id'] == 'vychozi'
    catalog = {f['key'] for f in ft.catalog('PLI')['facts']}
    assert set(layout['facts']['order']) | set(layout['facts']['hidden']) <= catalog   # preset jen z existujících údajů


def test_catalog_lists_categories_and_conditional_fields():
    krc = ft.catalog('KRC')
    keys = {f['key']: f['category'] for f in krc['facts']}
    assert [c['id'] for c in krc['categories']] == list(CATEGORY_IDS)
    assert keys['liver.flr'] == 'imaging' and keys['bm.ras'] == 'molecular' and keys['lab:2039-6'] == 'lab'
    assert keys['alert:RF-LAB'] == 'alerts' and keys['geri.g8'] == 'function' and 'mdt.question' not in keys


def test_catalog_is_public_and_has_area_presets(seeded):
    from rest_framework.test import APIClient
    r = APIClient().get('/api/mdt/templates/catalog/?area=PLI')
    assert r.status_code == 200 and [p['id'] for p in r.json()['presets']] == ['pneumolog-plice', 'vychozi']
    assert APIClient().get('/api/mdt/templates/catalog/?area=XX').status_code == 400
    assert APIClient().get('/api/mdt/templates/').status_code in (401, 403)          # moje šablony jen přihlášený


def test_template_api_save_reset_and_requester_layout(seeded):
    client = as_user('pneumolog')
    listing = client.get('/api/mdt/templates/').json()
    assert [t['area'] for t in listing['templates']] == ['PLI', 'PRS', 'KRC', 'OBC']
    assert listing['presets'][0]['id'] == 'pneumolog-plice' and listing['suggested']['PLI'] == 'pneumolog-plice'
    layout = ft.preset_for('pulmonologist', 'PLI')['layout']
    saved = client.put('/api/mdt/templates/PLI/', {'layout': layout, 'preset': 'pneumolog-plice'}, format='json')
    assert saved.status_code == 200 and saved.json()['layout'] == layout
    assert client.put('/api/mdt/templates/PLI/', {'layout': {'categories': {'order': ['nic']}}}, format='json').status_code == 400
    assert client.put('/api/mdt/templates/XYZ/', {'layout': {}}, format='json').status_code == 400

    p04 = MdtCase.objects.get(patient_fhir_id='P04')                  # zadal pneumolog, C34.1
    agenda = as_user('chirurg').get(f'/api/mdt/sessions/{p04.session_id}/').json()
    item = next(c for c in agenda['cases'] if c['id'] == p04.pk)
    assert item['requester_layout'] == layout and item['projector_layout'] == {}
    # úprava u případu dál platí přednostně; kategorie jsou v ní povolené
    case_layout = {'categories': {'order': ['molecular'], 'hidden': []}}
    assert client.patch(f'/api/mdt/cases/{p04.pk}/', {'projector_layout': case_layout}, format='json').status_code == 200
    assert client.delete('/api/mdt/templates/PLI/').json()['layout'] is None
    agenda = as_user('chirurg').get(f'/api/mdt/sessions/{p04.session_id}/').json()
    assert next(c for c in agenda['cases'] if c['id'] == p04.pk)['requester_layout'] is None
    FactTemplate.objects.create(user=p04.created_by, area='OBC', layout={'facts': {'hidden': ['allergies']}})
    agenda = as_user('chirurg').get(f'/api/mdt/sessions/{p04.session_id}/').json()   # bez šablony oblasti platí „Ostatní“
    assert next(c for c in agenda['cases'] if c['id'] == p04.pk)['requester_layout'] == {'facts': {'hidden': ['allergies']}}


def test_chair_creates_doctor_with_titles_and_template(seeded):
    body = {'username': 'novak', 'password': 'Silne-heslo-123', 'email': 'novak@mdt.local', 'first_name': 'Petr',
            'last_name': 'Novák', 'title_before': 'MUDr.', 'title_after': 'Ph.D.', 'specialty': 'pulmonologist',
            'role': 'mdt_doctor', 'preset': 'pneumolog-plice',
            'templates': {'PLI': ft.preset_for('pulmonologist', 'PLI')['layout']}}
    assert as_user('onkolog').post('/api/mdt/users/', body, format='json').status_code == 403
    r = as_user('predseda').post('/api/mdt/users/', body, format='json')
    assert r.status_code == 201, r.json()
    me = r.json()
    assert me['name'] == 'MUDr. Petr Novák, Ph.D.' and me['role'] == 'mdt_doctor' and me['specialty'] == 'pulmonologist'
    assert FactTemplate.objects.get(user__username='novak', area='PLI').preset == 'pneumolog-plice'
    assert as_user('predseda').post('/api/mdt/users/', body, format='json').status_code == 400     # jméno obsazené
    bad = {**body, 'username': 'jiny', 'templates': {'PLI': {'facts': 'x'}}}
    assert 'templates' in as_user('predseda').post('/api/mdt/users/', bad, format='json').json()
    renamed = as_user('predseda').patch(f"/api/mdt/users/{me['user_id']}/", {'title_before': 'doc. MUDr.'}, format='json')
    assert renamed.json()['name'] == 'doc. MUDr. Petr Novák, Ph.D.'


def test_registration_with_titles_and_template(seeded):
    from rest_framework.test import APIClient
    body = {'username': 'svoboda', 'email': 'svoboda@mdt.local', 'password': 'Silne-heslo-123',
            'password2': 'Silne-heslo-123', 'first_name': 'Jana', 'last_name': 'Svobodová', 'specialty': 'oncologist',
            'title_before': 'MUDr.', 'templates': {'PRS': {'categories': {'order': list(CATEGORY_IDS), 'hidden': ['alerts']}}}}
    r = APIClient().post('/api/auth/register/', body, format='json')
    assert r.status_code == 201, r.json()
    assert as_user('svoboda').get('/api/mdt/me/').json()['name'] == 'MUDr. Jana Svobodová'
    assert FactTemplate.objects.get(user__username='svoboda', area='PRS').layout['categories']['hidden'] == ['alerts']


def test_brief_from_before_t340_shows_modra_kniha(seeded):
    """Podklad uložený bez `national` dostane oporu v Modré knize při čtení (mapování je statické, ne AI)."""
    from apps.copilot.models import Brief

    case = MdtCase.objects.get(patient_fhir_id='P04')
    option = {'id': 'pli-imunoterapie', 'compatibility': {'rules': [{'rule_id': 'VS-PLI-07'}, {'rule_id': 'VS-PLI-01'}]}}
    Brief.objects.create(case=case, content={'decision_support': {'treatment_options': [option]}})
    rules = as_user('chirurg').get(f'/api/mdt/cases/{case.pk}/brief/').json()['decision_support']['treatment_options'][0]['compatibility']['rules']
    assert rules[0]['national_status'] == 'prah' and rules[0]['national'][0]['evidence_id'] == 'EXT-MK-8.1.3.2-2'
    assert rules[1]['national_status'] == 'neuvadi'


def test_doctor_edits_own_titles(seeded):
    r = as_user('pneumolog').patch('/api/mdt/me/', {'title_before': 'MUDr.', 'title_after': 'Ph.D.'}, format='json')
    assert r.status_code == 200 and r.json()['name'] == 'MUDr. Pneumolog, Ph.D.'
    assert as_user('pneumolog').patch('/api/mdt/me/', {'title_before': 'x' * 41}, format='json').status_code == 400
