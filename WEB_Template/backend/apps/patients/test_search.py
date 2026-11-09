"""Hledání pacienta podle RČ, jména nebo Pxx (T-356) nad fake FHIR serverem, který jako IRIS neznámé a
neimplementované search parametry (`identifier`, `name`) tiše ignoruje: filtr musí vrátit jen správného pacienta."""
import logging

import pytest

from services import patient_search
from services.fhir import ingest
from services.fhir.testing import key

pytestmark = pytest.mark.django_db
DEMO = ingest.demo_dataset_dir()
needs_demo = pytest.mark.skipif(DEMO is None, reason='data/demo_pacienti není k dispozici')
DEMO_IDS = ['P13', 'P14', 'P17', 'P21', 'P100', 'P172']


@pytest.fixture
def api(authenticated_client, fake_fhir_dataset):
    for pid in DEMO_IDS if DEMO else ():          # jen pacienti, sdílené soubory (dotazník) má dataset
        for r in ingest.load_patient(DEMO, pid):
            fake_fhir_dataset.store[key(r)] = r
    return authenticated_client


def demo(pid: str) -> dict:
    return patient_search.item(next(r for r in ingest.load_patient(DEMO, pid) if r['resourceType'] == 'Patient'))


def search(api, q):
    response = api.post('/api/patients/search/', {'q': q}, format='json')
    assert response.status_code == 200, response.content
    return response.json()


def test_requires_login(api_client, fake_fhir_dataset):
    assert api_client.post('/api/patients/search/', {'q': 'P03'}, format='json').status_code in (401, 403)


@needs_demo
def test_rc_with_and_without_slash_returns_only_that_patient(api, fake_fhir_dataset):
    target = demo('P100')
    assert target['rc'] and target['name'].endswith('(fiktivní)')
    for q in (target['rc'], target['rc'].replace('/', ''), f"  {target['rc'][:6]} / {target['rc'][7:]} "):
        found = search(api, q)
        assert [p['id'] for p in found] == ['P100'], q
    # IRIS by parametr ignoroval stejně jako fake server: filtr dělá kód, ne FHIR server
    assert 'identifier' in fake_fhir_dataset.ignored_params
    assert found[0] == {**target, 'display_name': found[0]['display_name']}
    assert found[0]['display_name'].startswith('P100 · ')


@needs_demo
def test_unknown_or_partial_rc_finds_nobody(api):
    rc = demo('P13')['rc']
    other = f"{rc[:6]}/{(int(rc[7:]) + 11) % 10000:04d}"      # formálně jiné RČ ze stejného dne
    assert search(api, other) == []
    assert search(api, rc[:6]) == []                       # neúplné RČ nehledá (žádný seznam podle data narození)


@needs_demo
def test_name_ignores_diacritics_and_case(api):
    target = demo('P17')
    family = target['name'].split()[1]
    folded = patient_search.fold(family)
    for q in (family, folded.upper(), folded[:4], f"{target['name'].split()[0]} {folded}"):
        ids = [p['id'] for p in search(api, q)]
        assert 'P17' in ids, q
        assert all(folded[:4] in patient_search.fold(p['name']) for p in search(api, q))
    assert [p['id'] for p in search(api, f"{target['name'].split()[0]} {folded}")] == ['P17']


def test_pxx_and_limit(api):
    assert [p['id'] for p in search(api, 'p3')] == ['P03']
    assert [p['id'] for p in search(api, 'P03')] == ['P03']
    assert search(api, 'P999') == []
    assert search(api, 'x') == []                           # moc krátké na hledání
    assert len(search(api, 'fiktiv')) <= patient_search.LIMIT


def test_get_q_rejects_rc_in_url(api):
    response = api.get('/api/patients/?q=6553151234')
    assert response.status_code == 400 and 'POST' in response.json()['detail']
    assert [p['id'] for p in api.get('/api/patients/?q=P03').json()] == ['P03']
    assert len(api.get('/api/patients/').json()) >= 6        # bez q dál celý seznam


@needs_demo
def test_rc_not_logged(api, caplog):
    rc = demo('P14')['rc']
    with caplog.at_level(logging.DEBUG):
        search(api, rc)
        api.get(f"/api/patients/?q={rc.replace('/', '')}")
    assert rc not in caplog.text and rc.replace('/', '') not in caplog.text


@needs_demo
def test_patient_list_keeps_pseudonymous_display(api):
    """Seznam pacientů a hlavičky dál bez jména a RČ (D-018)."""
    items = api.get('/api/patients/').json()
    p100 = next(p for p in items if p['id'] == 'P100')
    assert 'name' not in p100 and 'rc' not in p100 and p100['display_name'].startswith('P100 · ')
    assert [p['id'] for p in items].index('P99' if any(p['id'] == 'P99' for p in items) else 'P21') < \
        [p['id'] for p in items].index('P100')                 # číselné pořadí
