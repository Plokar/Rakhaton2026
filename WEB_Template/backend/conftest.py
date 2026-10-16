"""
Pytest configuration for Django tests.
"""
import pytest

# Testovací DB zakládá pytest-django jako test_<POSTGRES_DB> z env POSTGRES_* (settings.py),
# takže to funguje v kontejneru (db) i v CI (localhost).


@pytest.fixture(autouse=True)
def no_live_iris_sql(request, monkeypatch):
    """Unit testy nesmí sahat na živé IRIS SQL (v CI není): stejné chování lokálně i v CI.

    Vektory dává fixture ``fake_iris`` / ``grounding_vectors`` (services/conftest.py), živé IRIS jen ``-m integration``.
    """
    if request.node.get_closest_marker('integration'):
        return
    from services.fhir import client
    from services.iris import db

    def offline(*args, **kwargs):
        raise ConnectionError('IRIS v unit testech není (CI); použij fixture fake_iris / fake_fhir nebo -m integration')
    monkeypatch.setattr(db, 'connect', offline)
    monkeypatch.setattr(client, 'request', offline)


@pytest.fixture
def api_client():
    """Provide a Django REST Framework API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, django_user_model):
    """Provide an authenticated API client."""
    user = django_user_model.objects.create_user(
        username='testuser',
        password='testpass123'
    )
    api_client.force_authenticate(user=user)
    return api_client
