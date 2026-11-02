"""GET /api/ai/providers/ vrací jen providery, které umí generovat text (Groq je jen přepis)."""
import pytest
from rest_framework.test import APIClient

from services.ai_service import SUPPORTED_PROVIDERS


@pytest.mark.django_db
def test_providers_list_covers_llm_providers(monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'x')
    response = APIClient().get('/api/ai/providers/')
    assert response.status_code == 200
    ids = [p['id'] for p in response.json()['providers']]
    assert ids == [p for p in SUPPORTED_PROVIDERS if p != 'groq']
    nvidia = next(p for p in response.json()['providers'] if p['id'] == 'nvidia')
    assert nvidia['is_configured'] is True and nvidia['default_model'] in nvidia['models']
