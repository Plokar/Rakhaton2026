"""FHIR REST klient nad IRIS (ARCH §4.6). Jen stdlib, Basic auth, fhir+json."""
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# Typy s parametrem `patient` pro načtení celého pacienta bez $everything (DATASET §6.3)
PATIENT_TYPES = (
    'Condition', 'DocumentReference', 'DiagnosticReport', 'ImagingStudy', 'Observation',
    'MedicationRequest', 'MedicationAdministration', 'Procedure', 'QuestionnaireResponse',
    'ServiceRequest', 'Task', 'Composition', 'CarePlan', 'CareTeam',
)


class FhirError(Exception):
    def __init__(self, status: int, message: str, outcome: dict | None = None):
        super().__init__(f'HTTP {status}: {message}')
        self.status = status
        self.outcome = outcome or {}


def base_url() -> str:
    return os.environ.get('FHIR_BASE_URL', 'http://iris:52773/fhir/r4').rstrip('/')


def request(method: str, path: str = '', body: dict | None = None, params: dict | None = None) -> dict | None:
    url = path if path.startswith('http') else f'{base_url()}/{path.lstrip("/")}'.rstrip('/')
    if params:
        url += '?' + urllib.parse.urlencode(params, doseq=True)
    auth = f"{os.environ.get('IRIS_USER', 'SuperUser')}:{os.environ.get('IRIS_PASSWORD', 'SYS')}"
    req = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        method=method,
        headers={
            'Accept': 'application/fhir+json',
            'Content-Type': 'application/fhir+json',
            'Authorization': 'Basic ' + base64.b64encode(auth.encode()).decode(),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            outcome = json.loads(raw)
        except ValueError:
            outcome = {}
        msg = '; '.join(
            i.get('details', {}).get('text') or i.get('diagnostics', '') for i in outcome.get('issue', [])
        )
        raise FhirError(e.code, msg or e.reason, outcome) from None
    return json.loads(raw) if raw else None


def read(rtype: str, rid: str) -> dict:
    return request('GET', f'{rtype}/{rid}')


def put(resource: dict) -> dict:
    return request('PUT', f"{resource['resourceType']}/{resource['id']}", resource)


def delete(rtype: str, rid: str) -> None:
    request('DELETE', f'{rtype}/{rid}')


def transaction(bundle: dict) -> dict:
    return request('POST', '', bundle)


def search(rtype: str, **params) -> list[dict]:
    """Všechny výsledky přes stránkování (`link[relation=next]`). Neznámé parametry IRIS tiše ignoruje!"""
    params.setdefault('_count', 500)
    bundle = request('GET', rtype, params=params)
    out = []
    while bundle:
        out += [e['resource'] for e in bundle.get('entry', []) if e.get('search', {}).get('mode', 'match') == 'match']
        nxt = next((link['url'] for link in bundle.get('link', []) if link['relation'] == 'next'), None)
        bundle = request('GET', nxt) if nxt else None
    return out


def count(rtype: str, **params) -> int:
    return request('GET', rtype, params={**params, '_summary': 'count'})['total']


def patient_everything(pid: str) -> dict[str, list[dict]]:
    """Fallback místo `Patient/$everything` (Q7): paralelní searche přes PATIENT_TYPES."""
    # ponytail: 8 vláken, IRIS CE má limit spojení; víc až když to bude pomalé
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(zip(PATIENT_TYPES, pool.map(lambda t: search(t, patient=pid), PATIENT_TYPES)))
    return {'Patient': [read('Patient', pid)], **results}
