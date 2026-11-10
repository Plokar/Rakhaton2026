"""Obnova hesla (T-371): odkaz vede na adresu aplikace, ne na podvržený Origin; odpověď neprozradí, zda účet existuje."""
import pytest
from django.core import mail

pytestmark = pytest.mark.django_db
URL = '/api/auth/forgot-password/'


@pytest.fixture
def doctor(django_user_model):
    return django_user_model.objects.create_user('novak', email='novak@nemocnice.test', password='x')


def test_link_uses_configured_frontend(api_client, doctor, settings):
    settings.DEBUG = False
    settings.MDT_FRONTEND_URL = 'https://mdt.example.cz/'
    r = api_client.post(URL, {'email': doctor.email}, format='json', HTTP_ORIGIN='https://utocnik.example')
    assert r.status_code == 200
    body = mail.outbox[0].body
    assert 'https://mdt.example.cz/reset-password?uid=' in body and 'utocnik' not in body
    assert mail.outbox[0].subject == 'Obnova hesla do MDTcore'


def test_untrusted_origin_is_ignored_without_config(api_client, doctor, settings):
    settings.DEBUG = False
    settings.MDT_FRONTEND_URL = ''
    settings.CORS_ALLOWED_ORIGINS = ['https://app.example.cz']
    api_client.post(URL, {'email': doctor.email}, format='json', HTTP_ORIGIN='https://utocnik.example')
    assert 'https://app.example.cz/reset-password' in mail.outbox[0].body


def test_same_answer_for_unknown_email(api_client, doctor):
    known = api_client.post(URL, {'email': doctor.email}, format='json').json()
    unknown = api_client.post(URL, {'email': 'nikdo@nikde.test'}, format='json').json()
    assert known == unknown and len(mail.outbox) == 1
