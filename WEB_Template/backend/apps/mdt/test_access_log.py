"""Záznam přístupů k pacientům (T-370): kdo, kdy, kterého pacienta, bez osobních údajů."""
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.mdt import roles
from apps.mdt.models import AccessLog, MdtCase, UserProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(fake_fhir_dataset):
    call_command('seed_mdt')
    cache.clear()
    return fake_fhir_dataset


def as_user(username):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


def test_view_logged_once_per_window(seeded):
    case = MdtCase.objects.filter(patient_fhir_id='P03').first()
    client = as_user('onkolog')
    assert client.get(f'/api/mdt/cases/{case.pk}/readiness/').status_code == 200
    client.get(f'/api/mdt/cases/{case.pk}/for-me/')            # stejný pacient do 5 min → bez nového řádku
    entries = list(AccessLog.objects.all())
    assert len(entries) == 1
    entry = entries[0]
    assert (entry.username, entry.patient_fhir_id, entry.case_id, entry.action, entry.status_code) == \
        ('onkolog', 'P03', case.pk, 'view', 200)
    as_user('chirurg').get(f'/api/mdt/cases/{case.pk}/readiness/')   # jiný lékař ano
    assert AccessLog.objects.count() == 2


def test_export_always_logged(seeded):
    case = MdtCase.objects.filter(patient_fhir_id='P03').first()
    client = as_user('predseda')
    client.get(f'/api/mdt/cases/{case.pk}/export.fhir.json')
    client.get(f'/api/mdt/cases/{case.pk}/export.fhir.json')
    assert AccessLog.objects.filter(action='export', patient_fhir_id='P03').count() == 2


def test_search_logs_found_patients_not_query(seeded):
    as_user('predseda').post('/api/patients/search/', {'q': 'P03'}, format='json')
    entries = list(AccessLog.objects.all())
    assert [e.patient_fhir_id for e in entries] == ['P03']
    assert 'P03' not in entries[0].path and entries[0].action == 'write'    # POST hledání, výraz se neukládá


def test_unrelated_api_not_logged(seeded):
    as_user('predseda').get('/api/mdt/sessions/')
    as_user('predseda').get('/api/mdt/me/')
    assert not AccessLog.objects.exists()


def test_endpoint_only_for_manager_and_filters(seeded):
    case = MdtCase.objects.filter(patient_fhir_id='P03').first()
    as_user('onkolog').get(f'/api/mdt/cases/{case.pk}/readiness/')
    as_user('chirurg').get('/api/patients/P04/')
    assert as_user('onkolog').get('/api/mdt/access-log/').status_code == 403
    body = as_user('predseda').get('/api/mdt/access-log/?patient=p03').json()
    assert body['count'] == 1 and body['results'][0]['username'] == 'onkolog'
    assert body['results'][0]['patient_id'] == 'P03' and body['page_size'] == 50
    chirurg = get_user_model().objects.get(username='chirurg')
    assert as_user('predseda').get(f'/api/mdt/access-log/?user={chirurg.pk}').json()['count'] == 1


def test_rejected_external_doctor_is_logged(seeded):
    from rest_framework_simplejwt.tokens import RefreshToken

    user = get_user_model().objects.create_user('externi', password='x')
    UserProfile.objects.update_or_create(user=user, defaults={'is_external': True, 'organization': 'Nemocnice Jih'})
    roles.ensure_demo_users()
    client = APIClient()
    client.cookies['access_token'] = str(RefreshToken.for_user(user).access_token)
    case = MdtCase.objects.filter(patient_fhir_id='P03').first()
    assert client.get(f'/api/mdt/cases/{case.pk}/readiness/').status_code == 403
    entry = AccessLog.objects.get()
    assert (entry.username, entry.patient_fhir_id, entry.status_code) == ('externi', 'P03', 403)


def test_prod_settings_keep_scope_and_access_log():
    """settings_prod přepisuje MIDDLEWARE: rozsah externích lékařů (T-362) a záznam přístupů nesmí chybět."""
    import ast
    from pathlib import Path

    tree = ast.parse((Path(__file__).resolve().parents[2] / 'config' / 'settings_prod.py').read_text(encoding='utf-8'))
    middleware = next(ast.literal_eval(node.value) for node in tree.body
                      if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'MIDDLEWARE')
    assert middleware.index('apps.mdt.access_log.AccessLogMiddleware') \
        < middleware.index('apps.mdt.scope.ExternalScopeMiddleware')
