"""NVIDIA (LLM, embeddingy, OCR), Groq (Whisper) a výběr providerů z env (T-323), bez sítě: `_post` je podvržený."""
import pytest
from pydantic import BaseModel

from services import ai_service as ai
from services.ai.scribe import label_speakers
from services.ai_service import MockAIProvider

ENV = ('AI_PROVIDER', 'EMBEDDING_PROVIDER', 'TRANSCRIBE_PROVIDER', 'EMBEDDING_DIM', 'NVIDIA_EMBEDDING_DIM', 'NVIDIA_THINKING',
       'NVIDIA_MODEL', 'AI_MODEL')


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV:
        monkeypatch.delenv(name, raising=False)


class Answer(BaseModel):
    larger: float
    reason: str


def test_nvidia_structured_output(monkeypatch):
    sent = {}

    def fake_post(url, key, **kwargs):
        sent.update(url=url, **kwargs)
        return {'model': 'nvidia/x', 'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15},
                'choices': [{'message': {'content': '```json\n{"larger": 9.8, "reason": "9.8 > 9.11"}\n```'},
                             'finish_reason': 'stop'}]}

    monkeypatch.setattr(ai, '_post', fake_post)
    result = ai.NvidiaProvider(api_key='k').generate('9.11 nebo 9.8?', system_prompt='česky', response_schema=Answer)
    assert result['status'] == 'success' and result['data'] == {'larger': 9.8, 'reason': '9.8 > 9.11'}
    assert result['tokens_used'] == 15 and result['provider'] == 'nvidia'
    body = sent['json']
    assert sent['url'].endswith('/chat/completions') and body['response_format']['json_schema']['name'] == 'Answer'
    assert body['messages'][0] == {'role': 'system', 'content': 'česky'}
    assert body['chat_template_kwargs'] == {'enable_thinking': False}       # výchozí rychlý režim


class Cited(BaseModel):
    text: str
    citations: list[str]


def test_bracketed_citations_are_cleaned(monkeypatch):
    """Model opíše ID i se závorkami z promptu; grounding by je jinak nenašel. Text tvrzení zůstane beze změny."""
    content = '{"text": "[ECOG] 0 podle lékaře", "citations": ["[P03-ecog03]", " P03-prom02 "]}'
    monkeypatch.setattr(ai, '_post', lambda *a, **k: {'choices': [{'message': {'content': content}, 'finish_reason': 'stop'}]})
    data = ai.NvidiaProvider(api_key='k').generate('q', response_schema=Cited)['data']
    assert data == {'text': '[ECOG] 0 podle lékaře', 'citations': ['P03-ecog03', 'P03-prom02']}


@pytest.mark.parametrize('content,finish', [('{"larger": "x"}', 'stop'), ('{"larger": 9.8', 'length'), ('', 'stop')])
def test_nvidia_invalid_truncated_or_empty_output_is_error(monkeypatch, content, finish):
    monkeypatch.setattr(ai, '_post', lambda *a, **k: {'choices': [{'message': {'content': content}, 'finish_reason': finish}]})
    assert ai.NvidiaProvider(api_key='k').generate('q', response_schema=Answer)['status'] == 'error'


def test_nvidia_api_error_is_error_result(monkeypatch):
    def failing(*a, **k):
        raise ai.AIProviderError('HTTP 401: unauthorized')

    monkeypatch.setattr(ai, '_post', failing)
    result = ai.NvidiaProvider(api_key='k').generate('q')
    assert result['status'] == 'error' and '401' in result['error']


def test_nvidia_embeddings_passage_vs_query(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'nvidia')
    calls = []

    def fake_post(url, key, json):
        calls.append(json)
        return {'data': [{'index': i, 'embedding': [3.0, 4.0] + [0.0] * 2046} for i in range(len(json['input']))][::-1]}

    monkeypatch.setattr(ai, '_post', fake_post)
    vectors = ai.NvidiaProvider(api_key='k').embed(['a', 'b'], task_type=ai.TASK_RETRIEVAL_DOCUMENT)
    assert len(vectors) == 2 and len(vectors[0]) == 2048 and vectors[0][:2] == [0.6, 0.8]
    ai.NvidiaProvider(api_key='k').embed(['a'], task_type=ai.TASK_FACT_VERIFICATION)
    assert [c['input_type'] for c in calls] == ['passage', 'query']


def test_groq_whisper_segments(monkeypatch):
    sent = {}

    def fake_post(url, key, files, data):
        sent.update(url=url, files=files, data=data)
        return {'text': '…', 'segments': [
            {'start': 0.0, 'text': ' Dobrý den, pacient P03.', 'no_speech_prob': 0.01},
            {'start': 75.4, 'text': ' Resekce je možná dvoudobě.', 'no_speech_prob': 0.02},
            {'start': 170.0, 'text': ' Titulky vytvořil…', 'no_speech_prob': 0.95}]}     # halucinace na tichu

    monkeypatch.setattr(ai, '_post', fake_post)
    result = ai.GroqProvider(api_key='k').transcribe(b'audio', 'audio/webm;codecs=opus')
    assert result['status'] == 'success'
    assert result['data']['segments'] == [{'speaker': '', 'start': '00:00', 'text': 'Dobrý den, pacient P03.'},
                                          {'speaker': '', 'start': '01:15', 'text': 'Resekce je možná dvoudobě.'}]
    assert sent['url'].endswith('/audio/transcriptions') and sent['files']['file'][0] == 'audio.webm'
    assert sent['data']['response_format'] == 'verbose_json' and sent['data']['language'] == 'cs'


def test_providers_from_env(monkeypatch):
    for key in ('NVIDIA_API_KEY', 'GROQ_API_KEY', 'GEMINI_API_KEY'):
        monkeypatch.setenv(key, 'x')
    monkeypatch.setenv('AI_PROVIDER', 'nvidia')
    assert ai.get_ai_provider().provider_name == 'nvidia' and ai.ai_model() == ai.DEFAULT_NVIDIA_MODEL
    assert ai.embedding_provider().provider_name == 'nvidia' and ai.embedding_dim() == 2048
    assert ai.transcription_provider().provider_name == 'groq'
    monkeypatch.setenv('EMBEDDING_PROVIDER', 'gemini')
    assert ai.embedding_provider().provider_name == 'gemini' and ai.embedding_dim() == 1536
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    assert ai.ai_model() == ai.DEFAULT_MODEL
    monkeypatch.setenv('AI_PROVIDER', 'mock')                        # mock = vše offline, i s klíči v .env
    assert ai.embedding_provider().is_mock and ai.transcription_provider().is_mock
    assert ai.embedding_dim() == ai.DEFAULT_EMBEDDING_DIM
    monkeypatch.delenv('NVIDIA_API_KEY')
    assert ai.get_ai_provider('nvidia').is_mock                      # bez klíče mock, záměna je vidět


def test_label_speakers_from_llm_never_guesses():
    segments = [{'speaker': '', 'start': '00:00', 'text': 'Dobrý den.'}, {'speaker': '', 'start': '00:10', 'text': 'Resekce.'}]
    llm = MockAIProvider(responses={'SpeakerLabels': {'speakers': ['Předseda', 'chirurg']}})
    assert [s['speaker'] for s in label_speakers(segments, llm, lambda *a: None)] == ['předseda', 'chirurg']
    wrong = MockAIProvider(responses={'SpeakerLabels': {'speakers': ['předseda']}})     # jiný počet → nic nepřiřadí
    assert [s['speaker'] for s in label_speakers(segments, wrong, lambda *a: None)] == ['neuvedeno', 'neuvedeno']
