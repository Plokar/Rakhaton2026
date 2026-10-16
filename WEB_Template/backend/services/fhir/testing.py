"""In-memory FHIR server pro testy bez IRIS (fixture ``fake_fhir`` v ``services/conftest.py``).

Nahrazuje ``services.fhir.client.request``, takže funguje ``read``, ``put``, ``search``, ``count``,
``transaction`` i ``patient_everything``. V tom, na čem stavíme, se chová jako IRIS:

- odmítne (400) neplatné ID, prázdný string či prázdný prvek a referenci na neexistující resource;
- ``transaction`` je atomická, ``batch`` vrací stav po položkách;
- search umí ``_id`` (čárky), ``patient``, ``subject``, ``code`` (``system|code``), ``_summary=count``;
  ostatní parametry **tiše ignoruje** jako IRIS (zapíše je do ``ignored_params``).

Použití v testech jiných lanes (např. context builder, T-105)::

    def test_neco(fake_fhir_dataset):          # celý sanitizovaný dataset ve fake serveru
        everything = client.patient_everything('P03')
"""
import re
from pathlib import Path

from services.fhir import client
from services.fhir.ingest import collect, key, references

_ID = re.compile(r'[A-Za-z0-9\-.]{1,64}')
_PATIENT_FIELDS = ('subject', 'patient', 'for')
_KNOWN_PARAMS = {'_id', 'patient', 'subject', 'code', '_summary', '_count'}


def _bad_value(node, path='') -> str | None:
    if node is None or node == '' or node == [] or node == {}:
        return path or '(root)'
    if isinstance(node, dict):
        return next((p for k, v in node.items() if (p := _bad_value(v, f'{path}.{k}'))), None)
    if isinstance(node, list):
        return next((p for i, v in enumerate(node) if (p := _bad_value(v, f'{path}[{i}]'))), None)
    return None


class FakeFhirServer:
    def __init__(self):
        self.store: dict[str, dict] = {}       # "Type/id" → resource
        self.requests: list[tuple] = []        # (method, path, params)
        self.ignored_params: set[str] = set()

    # ── naplnění ──
    def load(self, root: Path, patients=None) -> 'FakeFhirServer':
        """Celý (nebo vybraný) sanitizovaný dataset bez transakcí, rychle pro testy."""
        for part in collect(root, patients).parts:
            for r in part.resources:
                self.store[key(r)] = r
        return self

    # ── náhrada client.request ──
    def request(self, method, path='', body=None, params=None):
        self.requests.append((method, path, params))
        if path.startswith('http'):
            path = path[len(client.base_url()):]
        path = path.strip('/')
        parts = path.split('/') if path else []
        if method == 'POST' and not parts:
            return self._bundle(body)
        if method == 'PUT' and len(parts) == 2:
            return self._put(parts, body)
        if method == 'DELETE' and len(parts) == 2:
            self.store.pop(path, None)
            return None
        if method == 'GET' and parts == ['metadata']:
            return {'resourceType': 'CapabilityStatement', 'fhirVersion': '4.0.1'}
        if method == 'GET' and len(parts) == 2:
            if path not in self.store:
                raise client.FhirError(404, f'{path} nenalezen')
            return self.store[path]
        if method == 'GET' and len(parts) == 1:
            return self._search(parts[0], params or {})
        raise client.FhirError(405, f'{method} {path} fake server neumí')

    # ── zápis ──
    def _validate(self, url_parts, resource) -> str | None:
        if not isinstance(resource, dict) or resource.get('resourceType') != url_parts[0]:
            return 'resourceType nesedí s URL'
        if not _ID.fullmatch(resource.get('id', '')) or resource['id'] != url_parts[1]:
            return f"neplatné nebo nesouhlasné id {resource.get('id')!r}"
        bad = _bad_value(resource)
        if bad:
            return f'prázdná hodnota v {bad}'
        return None

    def _check_refs(self, resources: list[dict], pending: set[str]) -> str | None:
        for r in resources:
            for ref in sorted(references(r)):
                if ref not in self.store and ref not in pending:
                    return f'{key(r)}: reference na neexistující {ref}'
        return None

    def _put(self, url_parts, resource):
        error = self._validate(url_parts, resource) or self._check_refs([resource], {key(resource)})
        if error:
            raise client.FhirError(400, error, _outcome(error))
        self.store[key(resource)] = resource
        return resource

    def _bundle(self, bundle):
        kind = bundle.get('type')
        if kind not in ('transaction', 'batch'):
            raise client.FhirError(400, f'Bundle.type {kind!r} server nezpracuje (čeká transaction/batch)')
        entries = bundle.get('entry', [])
        results = []
        for e in entries:
            req = e.get('request') or {}
            parts = req.get('url', '').split('/')
            error = 'chybí request' if req.get('method') != 'PUT' or len(parts) != 2 else self._validate(parts, e.get('resource'))
            results.append(error)
        if kind == 'transaction':
            pending = {key(e['resource']) for e in entries}
            error = next((r for r in results if r), None) or self._check_refs([e['resource'] for e in entries], pending)
            if error:
                raise client.FhirError(400, error, _outcome(error))
        response = []
        for e, error in zip(entries, results):
            if error:
                response.append({'response': {'status': '400 Bad Request', 'outcome': _outcome(error)}})
                continue
            existed = key(e['resource']) in self.store
            self.store[key(e['resource'])] = e['resource']
            response.append({'response': {'status': '200 OK' if existed else '201 Created'}})
        return {'resourceType': 'Bundle', 'type': f'{kind}-response', 'entry': response}

    # ── search ──
    def _search(self, rtype, params):
        self.ignored_params |= set(params) - _KNOWN_PARAMS
        items = [r for k, r in self.store.items() if k.split('/')[0] == rtype]
        if '_id' in params:
            ids = set(str(params['_id']).split(','))
            items = [r for r in items if r['id'] in ids]
        for name in ('patient', 'subject'):
            if name in params:
                target = str(params[name])
                target = target if '/' in target else f'Patient/{target}'
                items = [r for r in items if any((r.get(f) or {}).get('reference') == target for f in _PATIENT_FIELDS)]
        if 'code' in params:
            items = [r for r in items if _has_code(r, str(params['code']))]
        if params.get('_summary') == 'count':
            return {'resourceType': 'Bundle', 'type': 'searchset', 'total': len(items)}
        return {
            'resourceType': 'Bundle', 'type': 'searchset', 'total': len(items),
            'entry': [{'resource': r, 'search': {'mode': 'match'}} for r in items],
        }


def _has_code(resource, token: str) -> bool:
    system, _, code = token.rpartition('|')
    codings = (resource.get('code') or {}).get('coding', [])
    return any(c.get('code') == code and (not system or c.get('system') == system) for c in codings)


def _outcome(text: str) -> dict:
    return {'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'invalid', 'details': {'text': text}}]}
