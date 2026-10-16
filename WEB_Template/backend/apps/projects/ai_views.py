import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from services.ai_service import SUPPORTED_PROVIDERS, ai_model, ai_model_strong, get_ai_provider


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_generate(request):
    """
    POST /api/ai/generate/
    {
        "prompt": "Napiš mi funkci pro...",
        "system_prompt": "Jsi zkušený architekt...",
        "provider": "gemini" | "mock",
        "model": "gemini-3.8-flash",
        "temperature": 0.7
    }
    Data pacientů smí jen do Gemini v placeném tieru (ARCHITEKTURA §5.7), proto jen mock a gemini.
    """
    prompt = request.data.get('prompt')
    if not prompt:
        return Response({'error': 'Pole "prompt" je povinné.'}, status=status.HTTP_400_BAD_REQUEST)

    system_prompt = request.data.get('system_prompt', '')
    provider_name = request.data.get('provider')
    model = request.data.get('model')
    temperature = float(request.data.get('temperature', 0.7))

    try:
        provider = get_ai_provider(provider_name)
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    result = provider.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
    )

    if result.get('status') == 'error':
        return Response(result, status=status.HTTP_502_BAD_GATEWAY)

    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def ai_providers_list(request):
    """
    GET /api/ai/providers/
    Vrátí seznam podporovaných providerů a zda je nastaven jejich API klíč.
    """
    models = list(dict.fromkeys([ai_model(), ai_model_strong()]))
    providers = {
        'mock': {
            'id': 'mock',
            'name': 'Mock (bez sítě)',
            'is_configured': True,
            'default_model': 'mock',
            'models': ['mock'],
            'description': 'Deterministické odpovědi bez API klíče. Výchozí pro vývoj, testy a CI.'
        },
        'gemini': {
            'id': 'gemini',
            'name': 'Google Gemini',
            'is_configured': bool(os.environ.get('GEMINI_API_KEY')),
            'default_model': models[0],
            'models': models,
            'description': 'Google AI Studio (Gemini API), jen placený tier.'
        },
    }
    return Response({'providers': [providers[p] for p in SUPPORTED_PROVIDERS]})
