"""
Pytest configuration for Django tests.
"""
import pytest

# Testovací DB zakládá pytest-django jako test_<POSTGRES_DB> z env POSTGRES_* (settings.py),
# takže to funguje v kontejneru (db) i v CI (localhost).


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
