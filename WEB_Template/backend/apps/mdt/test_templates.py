"""Šablony projektoru, doporučené údaje (T-318) a odbornost uživatele s pohledem „pro mě“ (T-319)."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.copilot import schemas
from apps.mdt import config as cfg
from apps.mdt.models import BriefConfig, MdtCase
from apps.mdt.test_roles import as_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(fake_fhir_dataset):
    call_command('seed_mdt')


def _case(pid: str) -> int:
    return MdtCase.objects.get(patient_fhir_id=pid).pk


# ── T-318 ─────────────────────────────────────────────────────────────────────
def test_template_presets_are_valid_brief_configs(seeded):
    presets = BriefConfig.objects.filter(is_preset=True, name__startswith='Šablona: ')
    assert presets.count() == 31
    for preset in presets:
        cfg.validated(preset.snapshot())                   # projde validací BriefConfig (§8.5)
    call_command('seed_mdt')
    assert BriefConfig.objects.filter(is_preset=True, name__startswith='Šablona: ').count() == 31   # idempotentní


def test_p04_template_for_projector(seeded):
    """DoD: u P04 konfigurátor nabídne „NSCLC I–III: operabilita vs. CHRT“ s klíčovými údaji na projektor."""
    t = as_user('chirurg').get(f"/api/mdt/cases/{_case('P04')}/template/").json()
    schemas.CaseTemplate.model_validate(t)
    assert t['template_id'] == 'sab-pli-radikalni' and t['name'].startswith('NSCLC I–III')
    assert t['config']['name'] == f"Šablona: {t['name']}" and t['config_id'] is not None
    assert BriefConfig.objects.get(pk=t['config_id']).name == t['config']['name']
    assert t['trials'] == ['RKT-04'] and 'PLI-3.1' in t['sources']
    projector = {p['id']: p for p in t['projector']}
    assert projector['obc.tnm']['status'] == 'present' and projector['obc.tnm']['citations']
    assert projector['pli.vo2max']['status'] == 'mention' and 'P04-doc06' in projector['pli.vo2max']['citations']


def test_template_differs_by_situation(seeded):
    names = {pid: as_user('predseda').get(f'/api/mdt/cases/{_case(pid)}/template/').json()['template_id']
             for pid in ('P03', 'P04')}
    assert names == {'P03': 'sab-krc-jatra', 'P04': 'sab-pli-radikalni'}


def test_p04_intake_has_recommended_and_missing_items(seeded):
    """DoD: při zařazení P04 „Chybí: Zátěžový test … P04-doc06“ a „Doporučeno: Stanovisko radiačního onkologa“."""
    d = as_user('pneumolog').get('/api/mdt/patients/P04/intake/').json()
    warnings = {w['id']: w for w in d['warnings']}
    rt = warnings['DOP:pli.radioterapeut']
    assert rt['title'] == 'Doporučeno: Stanovisko radiačního onkologa' and rt['severity'] == 'low' and rt['kind'] == 'missing'
    vo2 = warnings['missing:spiro.vo2max']                  # zmínka „doporučena spiroergometrie“, výsledek chybí
    assert vo2['title'].startswith('Chybí: Zátěžový test') and 'P04-doc06#5' in vo2['citations']
    assert 'CHYBI:pli.vo2max' not in warnings                # hlídá ho pole formuláře spiro.vo2max (bez duplicity)
    assert 'CHYBI:pli.siadh' in warnings                     # povinné podle báze, formulář ho nehlídá
    skipped = as_user('pneumolog').get('/api/mdt/patients/P04/intake/?skipped=pli.radioterapeut').json()
    assert 'DOP:pli.radioterapeut' not in {w['id'] for w in skipped['warnings']}


def test_recommended_warnings_do_not_change_readiness(seeded):
    r = as_user('onkolog').get(f"/api/mdt/cases/{_case('P03')}/readiness/").json()
    assert not any(f['id'].startswith(('DOP:', 'CHYBI:')) for f in r['unresolved'])


def test_acknowledged_recommended_warning_goes_to_iris(seeded):
    from services.fhir import client
    case = MdtCase.objects.get(patient_fhir_id='P04')
    r = as_user('pneumolog').patch(f'/api/mdt/cases/{case.pk}/', {'acknowledge': ['DOP:pli.radioterapeut']}, format='json')
    assert r.status_code == 200, r.json()
    issue = client.read('DetectedIssue', f'P04-case{case.pk:02d}-w01')
    assert issue['code']['text'] == 'Doporučeno: Stanovisko radiačního onkologa'


# ── T-319 ─────────────────────────────────────────────────────────────────────
def test_register_requires_specialty_and_sees_all_patients(seeded):
    body = {'username': 'novy-chirurg', 'email': 'novy@mdt.local', 'password': 'Silne-heslo-123',
            'password2': 'Silne-heslo-123'}
    client = APIClient()
    assert 'specialty' in client.post('/api/auth/register/', body, format='json').json()
    assert client.post('/api/auth/register/', {**body, 'specialty': 'patient'}, format='json').status_code == 400
    assert client.post('/api/auth/register/', {**body, 'specialty': 'surgeon'}, format='json').status_code == 201

    me = schemas.Me.model_validate(as_user('novy-chirurg').get('/api/mdt/me/').json()).model_dump()
    assert (me['role'], me['specialty']) == ('mdt_viewer', 'surgeon')
    # každý přihlášený vidí všechny pacienty a případy; role omezují jen úpravy
    viewer = as_user('novy-chirurg')
    assert {p['id'] for p in viewer.get('/api/patients/').json()} >= {f'P0{i}' for i in range(1, 7)}
    sessions = viewer.get('/api/mdt/sessions/').json()
    assert sorted(p for s in sessions for p in s['patients']) == [f'P0{i}' for i in range(1, 7)]
    for s in sessions:
        assert viewer.get(f"/api/mdt/sessions/{s['id']}/").status_code == 200
    assert viewer.patch(f"/api/mdt/cases/{_case('P03')}/", {'ecog': 1}, format='json').status_code == 403


def test_chair_manages_roles_and_specialty(seeded):
    chirurg = get_user_model().objects.get(username='chirurg')
    assert as_user('chirurg').get('/api/mdt/users/').status_code == 403      # člen komise jen ke čtení
    assert as_user('onkolog').get('/api/mdt/users/').status_code == 200      # lékař vybírá spolupracovníky (T-326)
    predseda = get_user_model().objects.get(username='predseda')
    assert as_user('onkolog').patch(f'/api/mdt/users/{predseda.pk}/', {'role': 'mdt_viewer'}, format='json').status_code == 403
    users = {u['username']: u for u in as_user('predseda').get('/api/mdt/users/').json()}
    assert users['chirurg']['specialty'] == 'surgeon' and users['predseda']['role'] == 'mdt_admin'
    r = as_user('predseda').patch(f'/api/mdt/users/{chirurg.pk}/', {'role': 'mdt_doctor', 'specialty': 'radiologist'},
                                  format='json')
    assert r.json() | {'user_id': 0} == {'user_id': 0, 'username': 'chirurg', 'name': 'Chirurg', 'role': 'mdt_doctor',
                                         'specialty': 'radiologist', 'practitioner_id': 'LEK-APP-chirurg',
                                         'first_name': 'Chirurg', 'last_name': '', 'title_before': '', 'title_after': ''}
    assert list(chirurg.groups.values_list('name', flat=True)) == ['mdt_doctor']
    assert as_user('predseda').patch(f'/api/mdt/users/{chirurg.pk}/', {'specialty': 'patient'},
                                     format='json').status_code == 400
    predseda = get_user_model().objects.get(username='predseda')
    assert as_user('predseda').patch(f'/api/mdt/users/{predseda.pk}/', {'role': 'mdt_viewer'},
                                     format='json').status_code == 400


def test_for_me_surgeon_p03(seeded):
    """DoD: chirurg u P03 má nahoře FLR, MR jater, zastaralé CT hrudníku a resekci jater."""
    v = as_user('chirurg').get(f"/api/mdt/cases/{_case('P03')}/for-me/").json()
    schemas.SpecialtyView.model_validate(v)
    assert v['role'] == 'surgeon' and v['sections'][0] == 'summary' and v['sections'][1] == 'role_views'
    items = {i['id']: i for i in v['items']}
    assert list(items)[:3] == ['krc.flr', 'krc.mr_jater', 'krc.restaging']
    assert items['krc.flr']['status'] == 'present' and items['krc.restaging']['status'] == 'stale'
    assert items['krc.restaging']['warning']['citations']
    assert v['procedures'][0]['id'] == 'krc-resekce-jater'
    assert any('FLR' in i['what'] for i in v['interests'])


def test_for_me_needs_specialty(seeded):
    get_user_model().objects.create_user('bez-odbornosti', password='x')
    client = as_user('bez-odbornosti')
    assert client.get(f"/api/mdt/cases/{_case('P03')}/for-me/").status_code == 400
    radiolog = client.get(f"/api/mdt/cases/{_case('P03')}/for-me/?specialty=radiologist").json()
    assert radiolog['role'] == 'radiologist'
