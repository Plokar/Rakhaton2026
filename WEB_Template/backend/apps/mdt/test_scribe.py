"""AI zapisovatel (BON-3, T-305): přepis diskuse → DocumentReference přepisu v IRIS → draft závěru s citacemi úseků."""
import json
import os
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from apps.copilot import schemas
from apps.mdt.models import Decision, MdtCase
from apps.mdt.test_roles import as_user
from services.ai import scribe
from services.ai_service import MockAIProvider
from services.fhir import client

pytestmark = pytest.mark.django_db
_REPO = next((p for p in Path(__file__).resolve().parents if (p / 'data' / 'audio').is_dir()), None)
AUDIO = Path(os.environ.get('AUDIO_DIR') or (_REPO / 'data' / 'audio' if _REPO else '/nonexistent'))


@pytest.fixture
def transcript():
    path = AUDIO / 'P03_mdt02_transcript.json'
    if not path.is_file():
        pytest.skip('chybí data/audio/P03_mdt02_transcript.json (T-314)')
    return json.loads(path.read_text(encoding='utf-8'))['segments']


@pytest.fixture
def case(fake_fhir_dataset, settings):
    settings.MDT_JOBS_SYNC = True
    call_command('seed_mdt')
    return MdtCase.objects.get(patient_fhir_id='P03')


LLM_DRAFT = {
    'mdt_type': 'restaging',
    'assessment': {'text': 'Parciální odpověď po 8 cyklech, FLR 38 %, chybí CT hrudníku.',
                   'citations': ['P03-mdt02-prepis#3', 'P03-img04#3', 'P03-neexistuje']},
    'intent': 'kurativni',
    'recommendation': [{'modality': 'chirurgie', 'text': 'Dvoudobá resekce jater.', 'citations': ['P03-mdt02-prepis#9']}],
    're_mdt': {'date': '2026-11-04', 'reason': 'po CT hrudníku a volumetrii'},
    'conclusion': {'text': 'Dvoudobá resekce jater, podmínkou je CT hrudníku.', 'citations': ['P03-mdt02-prepis#12']},
    'tasks': [{'description': 'CT hrudníku (doplnění restagingu)', 'owner': 'radiolog', 'due_date': '2026-10-23'},
              {'description': 'Genetické poradenství', 'owner': 'onkolog', 'due_date': None}],
    'trial': {'text': 'RKT-03 zatím nelze rozhodnout', 'study_ids': ['RKT-03', 'XYZ']},
}


def test_build_draft_filters_citations_and_fills_due_date(transcript):
    provider = MockAIProvider(responses={'ScribeDraft': LLM_DRAFT})
    d = scribe.build_draft('7', 'Resekabilita?', 'C', transcript, 'P03-mdt02-prepis', None, provider, lambda *a: None)
    schemas.Decision.model_validate(d)
    assert d['status'] == 'draft' and d['transcript_ref'] == 'P03-mdt02-prepis'
    assert d['sections']['assessment']['citations'] == ['P03-mdt02-prepis#3']       # mimo přepis a kontext pryč
    assert d['sections']['re_mdt'] == {'date': '2026-11-04', 'reason': 'po CT hrudníku a volumetrii'}
    assert [t['due_date'] for t in d['tasks']] == ['2026-10-23', '2026-11-04']     # bez termínu → re-MDT
    assert all(t['source'] == 'ai' for t in d['tasks']) and d['sections']['trial']['study_ids'] == ['RKT-03']
    assert {a['role'] for a in d['attendees']} >= {'chair', 'oncologist', 'surgeon', 'radiologist'}


def test_build_draft_without_llm_invents_nothing(transcript):
    d = scribe.build_draft('7', 'Resekabilita?', 'C', transcript, 'P03-mdt02-prepis', None, MockAIProvider(), lambda *a: None)
    assert d['tasks'] == [] and d['sections']['intent'] == 'kurativni'
    last_chair = max(i for i, s in enumerate(transcript, 1) if s['speaker'] == 'předseda')
    assert d['sections']['conclusion']['text'] == transcript[last_chair - 1]['text']


def test_parse_text_transcript():
    segments = scribe.parse_transcript('00:00 předseda: Pokračujeme P03.\n00:13 onkolog: Osm cyklů FOLFOX.\npokračování věty.')
    assert [(s['speaker'], s['start']) for s in segments] == [('předseda', '00:00'), ('onkolog', '00:13')]
    assert segments[1]['text'].endswith('pokračování věty.')


def test_scribe_api_stores_transcript_and_draft(case, transcript):
    url = f'/api/mdt/cases/{case.pk}/scribe/'
    assert as_user('radiolog').post(url, {'segments': transcript}, format='json').status_code == 403
    assert as_user('predseda').post(url, {}, format='json').status_code == 400
    r = as_user('predseda').post(url, {'segments': transcript}, format='json')
    assert r.status_code == 202
    job = as_user('predseda').get(f"/api/jobs/{r.json()['job_id']}/").json()
    assert job['status'] == 'done', job['error']
    decision = Decision.objects.get(case=case)
    assert job['result_id'] == decision.pk and decision.status == 'draft'
    assert decision.content['transcript_ref'] == 'P03-mdt02-prepis'
    doc = client.read('DocumentReference', 'P03-mdt02-prepis')
    assert doc['context']['related'] == [{'reference': 'ServiceRequest/P03-zad01'}]
    source = as_user('predseda').get('/api/evidence/?id=P03-mdt02-prepis%233').json()       # citace úseku přepisu
    assert source['text'] and transcript[2]['text'] in source['text'][source['highlight']['start']:source['highlight']['end']]


def test_scribe_api_accepts_audio(case):
    audio = SimpleUploadedFile('p03.m4a', b'\x00\x01', content_type='audio/mp4')
    r = as_user('onkolog').post(f'/api/mdt/cases/{case.pk}/scribe/', {'audio': audio}, format='multipart')
    job = as_user('onkolog').get(f"/api/jobs/{r.json()['job_id']}/").json()
    assert job['status'] == 'done', job['error']                                       # mock přepis
    assert Decision.objects.get(case=case).content['transcript_ref'] == 'P03-mdt02-prepis'
