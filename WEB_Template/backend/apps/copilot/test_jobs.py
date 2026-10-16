"""Joby generování podkladu (T-107) s podvrženým generátorem (T-106 dodá skutečný)."""
import time
from datetime import datetime, timezone

import pytest

from apps.copilot import jobs
from apps.copilot.models import GenerationJob, LlmCallLog
from apps.mdt.models import BriefConfig, MdtCase, MdtSession


def fake_generate(case, config, progress):
    progress(50)
    return {'case_id': str(case.pk), 'patient_id': case.patient_fhir_id, 'model': 'fake', 'config_name': config['name']}


def failing_generate(case, config, progress):
    raise ValueError('LLM nevrátil validní JSON')


@pytest.fixture
def case(db):
    session = MdtSession.objects.create(date=datetime(2026, 10, 21, 12, tzinfo=timezone.utc), title='GIT')
    return MdtCase.objects.create(session=session, patient_fhir_id='P03', service_request_fhir_id='P03-zad01')


@pytest.fixture
def sync(settings, monkeypatch):
    settings.MDT_JOBS_SYNC = True
    monkeypatch.setitem(jobs.GENERATORS, 'brief', 'apps.copilot.test_jobs.fake_generate')


def test_generate_then_poll_then_read_brief(chair_client, case, sync):
    r = chair_client.post(f'/api/mdt/cases/{case.pk}/brief/', {}, format='json')
    assert r.status_code == 202
    job = chair_client.get(f"/api/jobs/{r.json()['job_id']}/").json()
    assert (job['status'], job['progress'], job['error']) == ('done', 100, None)
    brief = chair_client.get(f'/api/mdt/cases/{case.pk}/brief/').json()
    assert brief['patient_id'] == 'P03' and brief['brief_id'] == job['result_id'] and brief['config_name'] == 'Výchozí'


def test_config_preset_and_inline(chair_client, case, sync):
    preset = BriefConfig.objects.create(name='Chirurg', roles_present=['surgeon'])
    chair_client.post(f'/api/mdt/cases/{case.pk}/brief/', {'config_id': preset.pk}, format='json')
    assert case.briefs.first().config_snapshot['roles_present'] == ['surgeon']
    chair_client.post(f'/api/mdt/cases/{case.pk}/brief/', {'config': {'name': 'Ad hoc'}}, format='json')
    assert case.briefs.first().config_snapshot == {**jobs_default(), 'name': 'Ad hoc'}
    assert chair_client.post(f'/api/mdt/cases/{case.pk}/brief/', {'config': 'x'}, format='json').status_code == 400


def jobs_default():
    from apps.mdt.views import DEFAULT_CONFIG
    return DEFAULT_CONFIG


@pytest.mark.parametrize('path, message', [
    ('apps.copilot.test_jobs.failing_generate', 'LLM nevrátil validní JSON'),
    ('services.ai.neexistuje.generate_brief', 'zatím není k dispozici'),
])
def test_generator_errors_end_in_error_state(chair_client, case, settings, monkeypatch, path, message):
    settings.MDT_JOBS_SYNC = True
    monkeypatch.setitem(jobs.GENERATORS, 'brief', path)
    job_id = chair_client.post(f'/api/mdt/cases/{case.pk}/brief/', {}, format='json').json()['job_id']
    job = chair_client.get(f'/api/jobs/{job_id}/').json()
    assert job['status'] == 'error' and message in job['error']
    assert chair_client.get(f'/api/mdt/cases/{case.pk}/brief/').status_code == 404


@pytest.mark.django_db(transaction=True)
def test_runs_in_background_thread(chair_client, case, settings, monkeypatch):
    settings.MDT_JOBS_SYNC = False
    monkeypatch.setitem(jobs.GENERATORS, 'brief', 'apps.copilot.test_jobs.fake_generate')
    job_id = chair_client.post(f'/api/mdt/cases/{case.pk}/brief/', {}, format='json').json()['job_id']
    for _ in range(50):
        if GenerationJob.objects.get(pk=job_id).status in ('done', 'error'):
            break
        time.sleep(0.1)
    assert GenerationJob.objects.get(pk=job_id).status == 'done'


def test_requires_login(api_client, case):
    assert api_client.post(f'/api/mdt/cases/{case.pk}/brief/', {}, format='json').status_code in (401, 403)
    assert api_client.get('/api/jobs/1/').status_code in (401, 403)


def test_llm_call_log_record(db):
    row = LlmCallLog.record('brief.summary', {'status': 'success', 'provider': 'mock', 'model': 'm', 'prompt_hash': 'h',
                                              'tokens_in': 10, 'tokens_out': 5, 'latency_ms': 7})
    assert (row.ok, row.tokens_in, row.provider) == (True, 10, 'mock')
    assert LlmCallLog.record('x', {'status': 'error', 'error': 'timeout', 'provider': 'gemini'}).ok is False
