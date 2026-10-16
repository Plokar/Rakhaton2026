"""API pacientů nad in-memory FHIR serverem s celým datasetem (bez IRIS)."""
import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def api(authenticated_client, fake_fhir_dataset):
    return authenticated_client


def test_requires_login(api_client, fake_fhir_dataset):
    assert api_client.get('/api/patients/').status_code in (401, 403)


def test_list_has_all_six(api):
    data = api.get('/api/patients/').json()
    assert [p['id'] for p in data] == ['P01', 'P02', 'P03', 'P04', 'P05', 'P06']
    p03 = data[2]
    assert p03['display_name'] == 'P03 · muž · 67 let'
    assert p03['diagnosis'] == {'text': p03['diagnosis']['text'], 'icd10': 'C18.7', 'citation': 'P03-dg1'}
    assert p03['mdt_date'].startswith('2026-10-21') and p03['mdt_question_citation'] == 'P03-zad01'


def test_detail_ecog_physician_vs_patient(api):
    d = api.get('/api/patients/P03/').json()
    assert d['ecog']['physician'] == {'value': 0, 'date': '2026-10-05', 'citation': 'P03-ecog03'}
    assert d['ecog']['patient']['value'] == 1 and d['ecog']['patient']['citation'] == 'P03-prom02'
    assert 'P03-kom1' in [c['citation'] for c in d['comorbidities']]
    assert d['tnm'][0]['citation'] == 'P03-tnm01' and 'cM1a' in d['tnm'][0]['text']


def test_timeline_sorted_with_citations(api):
    events = api.get('/api/patients/P03/timeline/').json()
    assert [e['date'] for e in events] == sorted(e['date'] for e in events)
    by_id = {e['citation']: e['type'] for e in events}
    assert by_id['P03-img03'] == 'imaging' and by_id['P03-mdt01'] == 'mdt' and by_id['P03-lab06'] == 'lab'


def test_observations_filter_by_code(api):
    series = api.get('/api/patients/P03/observations/?code=2039-6,proms:brneni').json()
    cea, brneni = series
    assert cea['code'] == '2039-6' and brneni['code'] == 'proms:brneni'
    assert [(p['citation'], p['value']) for p in cea['points']][-2:] == [('P03-lab05-cea', 9.1), ('P03-lab06-cea', 13.9)]
    assert brneni['points'][-1] == {'date': '2026-10-04', 'value': 6, 'citation': 'P03-prom02'}


@pytest.mark.parametrize('pid', ['P99', 'P03%3F_id=P01'])
def test_unknown_or_invalid_pid_is_404(api, pid):
    assert api.get(f'/api/patients/{pid}/').status_code == 404
