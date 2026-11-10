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
    assert chair_client.get(f'/api/mdt/cases/{case.pk}/brief/').status_code == 204


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


# ── T-368: job přerušený restartem nezůstane „running“ ──

def _age(job, minutes):
    from datetime import timedelta

    from django.utils import timezone
    GenerationJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=minutes))


def test_stale_running_job_becomes_error_on_poll(chair_client, case):
    job = GenerationJob.objects.create(case=case, kind='brief', status='running', progress=40)
    _age(job, 20)
    body = chair_client.get(f'/api/jobs/{job.pk}/').json()
    assert body['status'] == 'error' and body['error'] == jobs.STALE_ERROR


def test_fresh_running_job_stays_running(chair_client, case):
    job = GenerationJob.objects.create(case=case, kind='brief', status='running')
    _age(job, 5)
    assert chair_client.get(f'/api/jobs/{job.pk}/').json()['status'] == 'running'


def test_timeout_from_settings_and_new_job_clears_old(chair_client, case, sync, settings):
    settings.MDT_JOB_TIMEOUT_MINUTES = 2
    old = GenerationJob.objects.create(case=case, kind='brief', status='queued')
    _age(old, 3)
    assert chair_client.post(f'/api/mdt/cases/{case.pk}/brief/', {}, format='json').status_code == 202
    old.refresh_from_db()
    assert old.status == 'error'


def test_progress_keeps_job_fresh(case, sync):
    job = GenerationJob.objects.create(case=case, kind='brief', params={'config': {'name': 'Výchozí'}})
    jobs.run(job.pk)
    job.refresh_from_db()
    assert job.status == 'done'
    assert jobs.fail_stale() == 0
