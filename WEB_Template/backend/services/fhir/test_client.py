"""Integrační testy proti lokálnímu IRIS (dev compose). Bez IRIS se přeskočí."""
import pytest

from services.fhir import client

PID = 'TEST-T006'


def _iris_up():
    try:
        client.request('GET', 'metadata')
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _iris_up(), reason='IRIS FHIR nedostupný (dev.ps1 up + iris_init)'),
]


@pytest.fixture
def patient():
    p = {'resourceType': 'Patient', 'id': PID, 'gender': 'male', 'birthDate': '1959'}
    client.put(p)
    yield p
    for rtype, rid in (('Observation', f'{PID}-o1'), ('Observation', f'{PID}-o2'), ('Patient', PID)):
        try:
            client.delete(rtype, rid)
        except client.FhirError:
            pass


def _obs(n):
    return {
        'resourceType': 'Observation', 'id': f'{PID}-o{n}', 'status': 'final',
        'code': {'text': 'ECOG'}, 'subject': {'reference': f'Patient/{PID}'}, 'valueInteger': n,
    }


def test_put_and_read_patient(patient):
    got = client.read('Patient', PID)
    assert got['id'] == PID and got['birthDate'] == '1959'
    client.put({**patient, 'gender': 'female'})  # PUT = idempotentní upsert
    assert client.read('Patient', PID)['gender'] == 'female'


def test_transaction_search_paging_count(patient):
    bundle = {'resourceType': 'Bundle', 'type': 'transaction', 'entry': [
        {'resource': o, 'request': {'method': 'PUT', 'url': f"Observation/{o['id']}"}} for o in (_obs(1), _obs(2))
    ]}
    assert client.transaction(bundle)['type'] == 'transaction-response'
    found = client.search('Observation', patient=PID, _count=1)  # 2 stránky
    assert sorted(o['id'] for o in found) == [f'{PID}-o1', f'{PID}-o2']
    assert client.count('Observation', patient=PID) == 2
    everything = client.patient_everything(PID)
    assert everything['Patient'][0]['id'] == PID and len(everything['Observation']) == 2


def test_error_has_outcome():
    with pytest.raises(client.FhirError) as e:
        client.read('Patient', 'neexistuje-t006')
    assert e.value.status == 404
