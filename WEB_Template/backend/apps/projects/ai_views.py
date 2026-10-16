import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from services.ai_service import get_ai_provider


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_generate(request):
    """
    POST /api/ai/generate/
    {
        "prompt": "Napiš mi funkci pro...",
        "system_prompt": "Jsi zkušený architekt...",
        "provider": "gemini" | "openai" | "ollama" | "mock",
        "model": "gemini-1.5-flash",
        "temperature": 0.7
    }
    """
    prompt = request.data.get('prompt')
    if not prompt:
        return Response({'error': 'Pole "prompt" je povinné.'}, status=status.HTTP_400_BAD_REQUEST)

    system_prompt = request.data.get('system_prompt', '')
    provider_name = request.data.get('provider')
    model = request.data.get('model')
    temperature = float(request.data.get('temperature', 0.7))

    provider = get_ai_provider(provider_name)
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
    return Response({
        'providers': [
            {
                'id': 'mock',
                'name': 'Hackathon Mock (Zero-Config)',
                'is_configured': True,
                'default_model': 'mock-gpt-v1',
                'models': ['mock-gpt-v1', 'mock-fast-v1'],
                'description': 'Nevyžaduje žádný klíč, okamžitě vrací realistické simulované odpovědi.'
            },
            {
                'id': 'gemini',
                'name': 'Google Gemini',
                'is_configured': bool(os.environ.get('GEMINI_API_KEY')),
                'default_model': 'gemini-1.5-flash',
                'models': ['gemini-1.5-flash', 'gemini-1.5-pro'],
                'description': 'Google Gemini Flash a Pro modely.'
            },
            {
                'id': 'openai',
                'name': 'OpenAI',
                'is_configured': bool(os.environ.get('OPENAI_API_KEY')),
                'default_model': 'gpt-4o-mini',
                'models': ['gpt-4o-mini', 'gpt-4o'],
                'description': 'OpenAI GPT-4o a GPT-4o-mini.'
            },
            {
                'id': 'ollama',
                'name': 'Ollama (Local)',
                'is_configured': True,
                'default_model': 'llama3.2',
                'models': ['llama3.2', 'mistral', 'codellama'],
                'description': 'Lokální běh modelů přes Ollama.'
            }
        ]
    })
