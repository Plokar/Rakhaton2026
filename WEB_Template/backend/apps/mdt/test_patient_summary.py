"""Shrnutí pro pacienta (BON-4, T-306): z potvrzeného závěru, s citacemi, v IRIS a v exportu."""
import json

import pytest

from apps.copilot import schemas
from apps.mdt.test_decision import case, decision  # noqa: F401  (fixtures)
from apps.mdt.test_roles import as_user
from services.ai import patient_summary
from services.ai.text import resource_text
from services.ai_service import MockAIProvider
from services.fhir import client

pytestmark = pytest.mark.django_db


@pytest.fixture
def confirmed(case, decision, settings):  # noqa: F811
    settings.MDT_JOBS_SYNC = True
    as_user('predseda').put(f'/api/mdt/cases/{case.pk}/decision/', decision, format='json')
    as_user('predseda').post(f'/api/mdt/cases/{case.pk}/decision/confirm/')
    return case


def test_summary_only_after_confirmation(case, decision, settings):  # noqa: F811
    settings.MDT_JOBS_SYNC = True
    url = f'/api/mdt/cases/{case.pk}/patient-summary/'
    assert as_user('predseda').get(url).status_code == 404
    as_user('predseda').put(f'/api/mdt/cases/{case.pk}/decision/', decision, format='json')
    assert as_user('predseda').post(url).status_code == 409                        # jen draft


def test_summary_from_confirmed_decision_in_iris_and_export(confirmed):
    url = f'/api/mdt/cases/{confirmed.pk}/patient-summary/'
    assert as_user('radiolog').post(url).status_code == 403
    r = as_user('onkolog').post(url)
    job = as_user('onkolog').get(f"/api/jobs/{r.json()['job_id']}/").json()
    assert job['status'] == 'done', job['error']
    summary = as_user('radiolog').get(url).json()
    schemas.PatientSummary.model_validate(summary)
    texts = [i['text'] for i in summary['items']]
    assert texts[0] == patient_summary.INTENT_LAY['kurativni']                        # P03: kurativní záměr
    assert any(t.startswith('V dotazníku jste uvedl(a)') for t in texts)              # priorita z PROMs
    assert all(i['verification'] == 'verified' and i['citations'] for i in summary['items'])
    assert summary['items'][0]['citations'][0].startswith('P03-mdt02#')
    doc = client.read('DocumentReference', 'P03-mdt02-pacient')
    assert resource_text(doc).startswith(texts[0])
    bundle = json.loads(as_user('chirurg').get(f'/api/mdt/cases/{confirmed.pk}/export.fhir.json').content)
    assert 'DocumentReference/P03-mdt02-pacient' in {e['fullUrl'].split('/fhir/', 1)[1] for e in bundle['entry']}
    assert as_user('chirurg').get(f'/api/mdt/cases/{confirmed.pk}/export.pdf').content.startswith(b'%PDF')


def test_llm_sentences_keep_only_allowed_citations(confirmed):
    resources = [r for items in client.patient_everything('P03').values() for r in items]
    llm = {'items': [{'text': 'Komise doporučila operaci jater ve dvou krocích.', 'citations': ['P03-mdt02#4', 'P03-xx']},
                     {'text': 'Bez citace.', 'citations': ['P03-neexistuje']}]}
    d = confirmed.decision.content
    items = patient_summary.build_patient_summary(d, resources, [], MockAIProvider(responses={'PatientSummaryOutput': llm}),
                                                  lambda *a: None)
    assert [(i['text'], i['citations']) for i in items] == [('Komise doporučila operaci jater ve dvou krocích.', ['P03-mdt02#4'])]
