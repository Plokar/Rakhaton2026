import pytest


@pytest.mark.django_db
def test_db_from_env(django_user_model):
    """Testovací DB se založí z env POSTGRES_* (kontejner i CI)."""
    django_user_model.objects.create_user(username='smoke', password='x')
    assert django_user_model.objects.filter(username='smoke').exists()
