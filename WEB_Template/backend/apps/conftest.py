from services.conftest import dataset_root, fake_fhir, fake_fhir_dataset, fake_iris  # noqa: F401  (in-memory FHIR + IRIS SQL pro testy apps/)

import pytest  # noqa: E402


@pytest.fixture
def chair_client(authenticated_client, django_user_model):
    """`authenticated_client` s rolí předsedy (`mdt_admin`)."""
    from django.contrib.auth.models import Group
    Group.objects.get_or_create(name='mdt_admin')[0].user_set.add(django_user_model.objects.get(username='testuser'))
    return authenticated_client
