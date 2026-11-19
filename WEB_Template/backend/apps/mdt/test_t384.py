"""Add-ony (T-384): kalendář .ics, statistiky komise, shrnutí pro pacienta přes odkaz, re-MDT a připomínky."""
from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.mdt.models import Decision, MdtCase, MdtSession, PatientShareLink

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(fake_fhir_dataset):
    call_command('seed_mdt')
    cache.clear()


def as_user(username):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


def confirmed(case, **sections):
    content = {'sections': {'guideline_compliance': {'compliant': True, 'reason': '', 'citations': []}, **sections},
               'patient_summary': {'items': [{'id': 's1', 'kind': 'claim', 'text': 'Komise doporučila operaci.',
                                              'citations': ['P03-mdt02']}],
                                   'generated_at': '2026-11-10T10:00:00', 'document_reference': 'P03-mdt02-pacient'}}
    return Decision.objects.create(case=case, content=content, status='confirmed', confirmed_at=timezone.now())


def test_calendar_ics(seeded):
    s = MdtSession.objects.get(title='Mamární komise')
    r = as_user('onkolog').get(f'/api/mdt/sessions/{s.pk}/calendar.ics')
    body = r.content.decode()
    assert r.status_code == 200, body[:300]
    assert r['Content-Type'].startswith('text/calendar') and body.startswith('BEGIN:VCALENDAR\r\n')
    assert f'UID:mdt-session-{s.pk}@mdtcore' in body and 'SUMMARY:MDT: Mamární komise' in body
    assert 'P01\\, P05\\, P06' in body.replace('\r\n ', '')                 # pacienti jen Pxx, čárky escapované
    assert all(len(line.encode()) <= 75 for line in body.split('\r\n'))   # RFC 5545 řádky

    MdtSession.objects.filter(pk=s.pk).update(date=timezone.now() + timedelta(days=3))
    mine = as_user('onkolog').get('/api/mdt/calendar.ics', {'mine': '1'}).content.decode()
    assert f'mdt-session-{s.pk}@' in mine                                  # onkolog tam má pacienty


def test_stats_only_for_chair(seeded):
    case = MdtCase.objects.get(patient_fhir_id='P03')
    confirmed(case)
    MdtCase.objects.filter(pk=case.pk).update(status='confirmed')
    assert as_user('onkolog').get('/api/mdt/stats/').status_code == 403
    data = as_user('predseda').get('/api/mdt/stats/').json()
    assert data['total']['confirmed'] == 1 and data['total']['guideline_compliance']['compliant'] == 1
    assert data['total']['cases'] == MdtCase.objects.count() and data['by_committee']
    assert as_user('predseda').get('/api/mdt/stats/', {'from': 'x'}).status_code == 400


def test_patient_summary_link(seeded):
    case = MdtCase.objects.get(patient_fhir_id='P03')
    url = f'/api/mdt/cases/{case.pk}/patient-summary/links/'
    assert as_user('chirurg').post(url).status_code == 403
    assert as_user('predseda').post(url).status_code == 409                # shrnutí ještě není
    confirmed(case)
    link = as_user('predseda').post(url).json()
    token = link['url'].rsplit('/', 1)[1]
    public = APIClient().get(f'/api/public/patient-summary/{token}/').json()
    assert public['items'] == [{'text': 'Komise doporučila operaci.'}]
    assert 'P03' not in str(public) and 'citations' not in str(public)     # bez ID pacienta a zdrojů
    assert APIClient().get('/api/public/patient-summary/spatny/').status_code == 404
    assert PatientShareLink.objects.get().views == 1
    as_user('predseda').delete(url)
    assert APIClient().get(f'/api/public/patient-summary/{token}/').status_code == 404


def test_re_mdt_due_and_reminders(seeded, settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    case = MdtCase.objects.get(patient_fhir_id='P03')
    soon = (timezone.localdate() + timedelta(days=10)).isoformat()
    confirmed(case, re_mdt={'date': soon, 'reason': 'restaging po 3 cyklech'})
    MdtCase.objects.filter(patient_fhir_id='P03').update(session=MdtSession.objects.get(title='Mamární komise'))
    MdtSession.objects.filter(title='Mamární komise').update(date=timezone.now() - timedelta(days=20), status='closed')
    items = as_user('onkolog').get('/api/mdt/re-mdt/').json()
    assert [(i['patient_id'], i['date'], i['overdue']) for i in items] == [('P03', soon, False)]
    assert as_user('pneumolog').get('/api/mdt/re-mdt/').json() == []        # cizí pacient

    out = StringIO()
    call_command('mdt_reminders', '--only', 're-mdt', '--dry-run', stdout=out)
    assert '[re-mdt] onkolog: 1' in out.getvalue() and not mail.outbox
    call_command('mdt_reminders', '--only', 're-mdt', stdout=StringIO())
    assert len(mail.outbox) == 1 and 'P03: re-MDT' in mail.outbox[0].body and 'restaging' in mail.outbox[0].body


def test_new_results_notified_once(seeded, settings, monkeypatch):
    from services import followup
    from services.rules import review

    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    MdtSession.objects.filter(title='Mamární komise').update(date=timezone.now() + timedelta(days=2), status='planned')
    found = [{'date': '2026-11-15', 'label': 'CT hrudníku', 'value': ''}]
    monkeypatch.setattr(review, 'review_state', lambda *a, **k: {'new_results': found, 'unseen_count': 1})
    first = followup.new_results()
    assert any('CT hrudníku' in line for lines in first.values() for line in lines)
    assert followup.new_results() == {}                                    # podruhé nic nového


def test_day_before_and_overdue_tasks(seeded, monkeypatch):
    from apps.mdt.models import UserProfile
    from services import followup, tasks

    s = MdtSession.objects.get(title='Mamární komise')
    MdtSession.objects.filter(pk=s.pk).update(date=timezone.now() + timedelta(days=1), status='planned')
    lines = followup.day_before()
    onkolog = get_user_model().objects.get(username='onkolog')
    assert lines and all(line.split(' ')[0] in {'P01', 'P05', 'P06'} for line in lines[onkolog.pk])   # skutečná data

    UserProfile.objects.filter(user=onkolog).update(practitioner_fhir_id='LEK-ONK-01')
    yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
    monkeypatch.setattr(tasks, 'list_tasks', lambda *a, **k: [
        {'id': 'P03-mdt02-task01', 'patient_id': 'P03', 'description': 'CT hrudníku', 'status': 'requested',
         'due_date': yesterday, 'owner': {'id': 'LEK-ONK-01'}},
        {'id': 'P03-mdt02-task02', 'patient_id': 'P03', 'description': 'hotovo', 'status': 'completed',
         'due_date': yesterday, 'owner': {'id': 'LEK-ONK-01'}}])
    assert followup.overdue_tasks() == {onkolog.pk: [f'P03: CT hrudníku (termín {yesterday})']}
