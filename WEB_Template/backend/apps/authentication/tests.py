"""Obnova přihlášení z httpOnly cookie (T-336): access cookie platí 15 min, refresh 7 dní."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
REFRESH = '/api/auth/token/refresh/'


@pytest.fixture
def logged_in():
    get_user_model().objects.create_user('doktor', password='heslo-12345')
    client = APIClient()
    assert client.post('/api/auth/token/', {'username': 'doktor', 'password': 'heslo-12345'}, format='json').status_code == 200
    return client


@pytest.mark.parametrize('body', [None, {}])
def test_refresh_from_cookie_sets_new_cookies(logged_in, body):
    old_refresh = logged_in.cookies['refresh_token'].value
    del logged_in.cookies['access_token']                       # access cookie vypršela
    response = logged_in.post(REFRESH, body, format='json') if body is not None else logged_in.post(REFRESH)
    assert response.status_code == 200
    assert response.cookies['access_token'].value and response.cookies['refresh_token'].value != old_refresh
    assert logged_in.get('/api/mdt/me/').status_code == 200    # s novou cookie zase přihlášen


def test_rotated_refresh_cannot_be_reused(logged_in):
    old_refresh = logged_in.cookies['refresh_token'].value
    assert logged_in.post(REFRESH).status_code == 200
    stale = APIClient()
    stale.cookies['refresh_token'] = old_refresh
    assert stale.post(REFRESH).status_code == 401              # blacklist po rotaci


def test_refresh_without_cookie_is_401():
    assert APIClient().post(REFRESH).status_code in (400, 401)
