"""Chatbot u zasedání (T-338): soukromý rozhovor s AI po boardech, odpověď s citacemi, uzavřený board jen ke čtení."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.copilot.models import LlmCallLog
from apps.mdt import chatbot
from apps.mdt.models import ChatbotMessage, MdtCase, MdtSession
from services.ai import chatbot as ai_chatbot
from services.ai_service import MockAIProvider

ANSWER = {"claims": [{"text": "Poslední CEA je 13,9 µg/l.", "citations": ["P03-lab06-cea"]},
                     {"text": "Pacient je po resekci jater.", "citations": ["P03-neexistuje"]}],
          "missing": [{"text": "Výsledek PET/CT", "expected_source": "zobrazovací vyšetření"}],
          "uncertain": []}


@pytest.fixture
def seeded(fake_fhir_dataset, fake_iris, db, monkeypatch):
    call_command('seed_mdt')
    provider = MockAIProvider(responses={'ChatbotOutput': ANSWER})
    # s pacientem odpovídá „LLM“, bez pacienta mock bez odpovědi (poznámka + nejbližší místa)
    monkeypatch.setattr(ai_chatbot, 'chatbot_provider',
                        lambda resources: (provider if resources is not None else MockAIProvider(), None))


def as_user(username):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


def url(sid):
    return f'/api/mdt/sessions/{sid}/chatbot/'


def p03():
    return MdtCase.objects.get(patient_fhir_id='P03')


@pytest.mark.django_db
def test_question_about_patient_gets_cited_answer(seeded):
    case = p03()
    r = as_user('onkolog').post(url(case.session_id), {'text': '  Jaké je poslední CEA?  ', 'case_id': case.pk},
                                format='json')
    assert r.status_code == 201
    question, answer = r.json()
    label = {'id': case.pk, 'patient_id': 'P03'}
    assert question | {'id': 0, 'created_at': ''} == {
        'id': 0, 'session': case.session_id, 'role': 'user', 'case': label, 'text': 'Jaké je poslední CEA?',
        'claims': [], 'uncertain': [], 'model': None, 'created_at': ''}
    assert (answer['role'], answer['case'], answer['text'], answer['model']) == ('ai', label, '', 'mock')
    assert [(c['kind'], c['citations'], c['verification']) for c in answer['claims']] == [
        ('claim', ['P03-lab06-cea'], 'verified'),
        ('claim', ['P03-neexistuje'], 'unverified'),
        ('missing', [], 'verified')]
    assert LlmCallLog.objects.filter(purpose='chatbot').count() == 1

    # rozhovor je soukromý: autor ho vidí, jiný lékař téhož boardu ne
    assert [m['role'] for m in as_user('onkolog').get(url(case.session_id)).json()] == ['user', 'ai']
    assert as_user('chirurg').get(url(case.session_id)).json() == []


@pytest.mark.django_db
def test_general_question_without_patient(seeded):
    s = p03().session
    question, answer = as_user('onkolog').post(url(s.pk), {'text': 'Kdy je nutný restaging před resekcí jater?'},
                                               format='json').json()
    assert question['case'] is None and answer['case'] is None
    # bez Gemini (mock) a bez guidelines v IRIS: poznámka, nic se nevymýšlí
    assert answer['text'].startswith('Jazykový model není zapnutý')
    assert answer['model'] is None


@pytest.mark.django_db
def test_history_of_same_patient_goes_to_llm(seeded, monkeypatch):
    calls = []
    monkeypatch.setattr(ai_chatbot, 'answer', lambda text, pid, history: calls.append((text, pid, history)) or
                        {'text': 'ok', 'claims': [], 'uncertain': [], 'model': None})
    case, client = p03(), as_user('onkolog')
    client.post(url(case.session_id), {'text': 'Obecně?'}, format='json')
    client.post(url(case.session_id), {'text': 'První', 'case_id': case.pk}, format='json')
    client.post(url(case.session_id), {'text': 'Druhá', 'case_id': case.pk}, format='json')
    assert [(t, pid) for t, pid, _ in calls] == [('Obecně?', None), ('První', 'P03'), ('Druhá', 'P03')]
    assert [(m['role'], m['text']) for m in calls[2][2]] == [('user', 'První'), ('ai', 'ok')]


@pytest.mark.django_db
def test_failed_answer_keeps_question(seeded, monkeypatch):
    def boom(*_):
        raise RuntimeError('neočekávaná chyba')
    monkeypatch.setattr(ai_chatbot, 'answer', boom)
    case = p03()
    r = as_user('onkolog').post(url(case.session_id), {'text': 'CEA?', 'case_id': case.pk}, format='json')
    assert r.status_code == 201
    assert r.json()[1]['text'] == 'AI se teď nepodařilo odpovědět.'
    assert ChatbotMessage.objects.count() == 2


@pytest.mark.django_db
def test_invalid_questions_and_closed_board(seeded):
    s = p03().session
    foreign = MdtCase.objects.exclude(session=s).first()
    doctor = as_user('onkolog')
    for body in ({'text': '   '}, {'text': 'x' * 2001}, {'text': 'ok', 'case_id': foreign.pk},
                 {'text': 'ok', 'case_id': str(p03().pk)}):
        assert doctor.post(url(s.pk), body, format='json').status_code == 400, body
    assert doctor.post(url(9999), {'text': 'ok'}, format='json').status_code == 404
    assert APIClient().get(url(s.pk)).status_code == 401
    assert not ChatbotMessage.objects.exists()

    MdtSession.objects.filter(pk=s.pk).update(status='closed')
    r = doctor.post(url(s.pk), {'text': 'ok'}, format='json')
    assert (r.status_code, r.json()) == (409, chatbot.CLOSED_CHATBOT)
    assert doctor.get(url(s.pk)).status_code == 200
