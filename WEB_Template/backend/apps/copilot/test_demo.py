"""Záloha a reset dema (T-311) nad in-memory FHIR s datasetem."""
import json

import pytest
from django.core.management import call_command

from apps.copilot import jobs
from apps.copilot.models import Brief
from apps.mdt.models import Decision, MdtCase
from apps.mdt.test_decision import decision  # noqa: F401  (fixture decision_P03.json)
from apps.mdt.test_roles import as_user
from services.fhir import client

pytestmark = pytest.mark.django_db


@pytest.fixture
def demo_env(fake_fhir_dataset, settings, tmp_path, monkeypatch):
    settings.MDT_JOBS_SYNC = True
    settings.MDT_DEMO_CACHE_DIR = str(tmp_path)
    monkeypatch.setitem(jobs.GENERATORS, 'brief', 'apps.copilot.test_jobs.fake_generate')
    call_command('seed_mdt')
    client.put({'resourceType': 'Device', 'id': 'mdt-copilot', 'deviceName': [{'name': 'MDT Copilot', 'type': 'user-friendly-name'}]})
    return tmp_path


def _generate(case):
    job_id = as_user('predseda').post(f'/api/mdt/cases/{case.pk}/brief/', {}, format='json').json()['job_id']
    return as_user('predseda').get(f'/api/jobs/{job_id}/').json()


def test_save_load_and_offline_brief_without_llm(demo_env, settings, monkeypatch):
    case = MdtCase.objects.get(patient_fhir_id='P03')
    assert _generate(case)['status'] == 'done'
    call_command('demo', 'save', 'P03')
    cached = json.loads((demo_env / 'brief_P03.json').read_text(encoding='utf-8'))
    assert cached['patient_id'] == 'P03' and cached['model'] == 'fake'

    settings.MDT_DEMO_OFFLINE = True
    monkeypatch.setattr('apps.copilot.demo.REAL_GENERATOR', 'neexistuje.generate')   # LLM ani generátor se nevolá
    job = _generate(case)
    assert job['status'] == 'done' and Brief.objects.get(pk=job['result_id']).content['patient_id'] == 'P03'

    Brief.objects.all().delete()
    call_command('demo', 'load', 'P03')
    assert as_user('chirurg').get(f'/api/mdt/cases/{case.pk}/brief/').json()['model'] == 'fake'


def test_offline_without_cache_falls_back_to_generator(demo_env, settings, monkeypatch):
    settings.MDT_DEMO_OFFLINE = True
    monkeypatch.setattr('apps.copilot.demo.REAL_GENERATOR', 'apps.copilot.test_jobs.fake_generate')
    assert _generate(MdtCase.objects.get(patient_fhir_id='P03'))['status'] == 'done'


def test_reset_after_confirmed_demo(demo_env, decision):  # noqa: F811
    case = MdtCase.objects.get(patient_fhir_id='P03')
    as_user('predseda').put(f'/api/mdt/cases/{case.pk}/decision/', decision, format='json')
    assert as_user('predseda').post(f'/api/mdt/cases/{case.pk}/decision/confirm/').status_code == 200
    as_user('onkolog').patch(f'/api/mdt/cases/{case.pk}/', {'ecog': 1}, format='json')
    assert client.read('Task', 'P03-zad01-task')['businessStatus']['coding'][0]['code'] == 'projednana'

    call_command('demo', 'reset', 'P03')
    assert not client.search('Composition', _id='P03-mdt02') and not client.search('Observation', _id=f'P03-ecog-case{case.pk:02d}')
    assert client.read('Composition', 'P03-mdt01')['id'] == 'P03-mdt01'                       # dataset zůstal
    assert client.read('Task', 'P03-zad01-task')['businessStatus']['coding'][0]['code'] == 'naplanovana'
    new = MdtCase.objects.get(patient_fhir_id='P03')
    assert new.status == 'nominated' and new.ecog is None and not Decision.objects.exists()
    assert new.session.title.startswith('GIT')
