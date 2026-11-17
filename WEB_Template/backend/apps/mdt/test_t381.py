"""Souhlas přítomných s návrhem závěru (T-381): hlasování, uzamčení po potvrzení, zápis do záznamu MDT."""
import pytest

from apps.mdt.models import DecisionVote, MdtSession
from apps.mdt.test_decision import as_user, case, decision  # noqa: F401  (fixtures)
from services.fhir import client

pytestmark = pytest.mark.django_db


def url(case):
    return f'/api/mdt/cases/{case.pk}/votes/'


def test_votes_only_on_draft_and_disagree_needs_reason(case, decision):  # noqa: F811
    assert as_user('chirurg').put(url(case), {'vote': 'agree'}, format='json').status_code == 409   # návrh ještě není
    as_user('predseda').put(f'/api/mdt/cases/{case.pk}/decision/', decision, format='json')

    assert as_user('chirurg').put(url(case), {'vote': 'agree'}, format='json').json()['agree'] == 1
    assert as_user('radiolog').put(url(case), {'vote': 'disagree'}, format='json').status_code == 400
    assert as_user('radiolog').put(url(case), {'vote': 'maybe'}, format='json').status_code == 400
    assert as_user('radiolog').put(url(case), {'vote': 'disagree', 'comment': 'nar. 4. 1. 1976'},
                                   format='json').status_code == 400                 # osobní údaj do záznamu nesmí
    state = as_user('radiolog').put(url(case), {'vote': 'disagree', 'comment': 'Chybí restaging PET/CT.'},
                                    format='json').json()
    assert (state['agree'], state['disagree'], state['mine']['vote']) == (1, 1, 'disagree')
    # změna názoru a stažení hlasu
    assert as_user('chirurg').put(url(case), {'vote': 'disagree', 'comment': 'Spíš konverzní CHT.'},
                                  format='json').json()['disagree'] == 2
    assert as_user('chirurg').delete(url(case)).json()['mine'] is None
    assert DecisionVote.objects.count() == 1


def test_votes_written_to_record_and_locked_after_confirm(case, decision):  # noqa: F811
    chair = as_user('predseda')
    chair.put(f'/api/mdt/cases/{case.pk}/decision/', decision, format='json')
    as_user('chirurg').put(url(case), {'vote': 'agree'}, format='json')
    as_user('radiolog').put(url(case), {'vote': 'disagree', 'comment': 'Chybí restaging PET/CT.'}, format='json')
    # klient hlasy do závěru podstrčit nemůže
    forged = {**decision, 'sections': {**decision['sections'], 'votes': [
        {'member': 'Někdo', 'vote': 'agree', 'comment': '', 'at': '2026-01-01T00:00:00'}]}}
    assert chair.put(f'/api/mdt/cases/{case.pk}/decision/', forged, format='json').json()['sections']['votes'] == []

    confirmed = chair.post(f'/api/mdt/cases/{case.pk}/decision/confirm/').json()
    votes = confirmed['sections']['votes']
    assert [(v['member'], v['vote']) for v in votes] == [('Chirurg', 'agree'), ('Radiolog', 'disagree')]
    section = next(s for s in client.read('Composition', 'P03-mdt02')['section'] if s['title'] == 'Souhlas přítomných')
    assert 'Souhlasí 1, nesouhlasí 1.' in section['text']['div'] and 'Chybí restaging PET/CT.' in section['text']['div']
    assert as_user('chirurg').put(url(case), {'vote': 'disagree', 'comment': 'x'}, format='json').status_code == 409
    assert as_user('chirurg').get(url(case)).json()['open'] is False


def test_closed_session_stops_voting(case, decision):  # noqa: F811
    as_user('predseda').put(f'/api/mdt/cases/{case.pk}/decision/', decision, format='json')
    MdtSession.objects.filter(pk=case.session_id).update(status='closed')
    assert as_user('chirurg').put(url(case), {'vote': 'agree'}, format='json').status_code == 409
