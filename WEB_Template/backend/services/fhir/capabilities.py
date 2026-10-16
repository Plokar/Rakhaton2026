"""Co umí náš IRIS FHIR server (T-313, Q7, ARCH §4.6). Spouští ``python manage.py iris_check``.

1. **Search parametry, na kterých aplikace stojí, IRIS opravdu filtruje.** IRIS neznámý parametr tiše
   ignoruje a vrátí všechno. Proto se ptáme hodnotou, která nemůže nic najít: výsledek musí být 0.
   Když není, parametr se ignoruje a kód, který na něm stojí, vrací cizí data.
2. ``Patient/$everything`` (jinak fallback ``client.patient_everything``), mCODE IG (profily
   ``StructureDefinition``) a ``$validate`` (BON-5).

Kontroly potřebují nahraný dataset (``ingest_dataset``).
"""
from dataclasses import dataclass

from services.fhir import client as fhir

NOTHING = 'neexistuje-t313'
MCODE_PROFILE = 'http://hl7.org/fhir/us/mcode/StructureDefinition/mcode-primary-cancer-condition'
CEA = 'http://loinc.org|2039-6'
FICTIONAL_TAG = 'https://rakathon.example.org/fhir/tag|fiktivni-data'


@dataclass
class Check:
    name: str
    status: str          # ok | fail | info
    detail: str
    required: bool = True

    @property
    def failed(self) -> bool:
        return self.required and self.status == 'fail'


def _filters(rtype: str, param: str, value: str, positive: dict | None = None) -> Check:
    """``param`` filtruje: nesmyslná hodnota → 0 (a ``positive`` dotaz → > 0, aby bylo co filtrovat)."""
    name = f'{rtype}?{param}'
    try:
        total = fhir.count(rtype)
        if total == 0:
            return Check(name, 'fail', f'{rtype} je v IRIS prázdný, nejdřív ingest_dataset')
        miss = fhir.count(rtype, **{param: value})
        hit = fhir.count(rtype, **positive) if positive else None
    except fhir.FhirError as e:
        return Check(name, 'fail', f'chyba {e}')
    if miss != 0:
        return Check(name, 'fail', f'IGNORUJE SE: {param}={value} vrátil {miss} z {total}')
    if hit == 0:
        return Check(name, 'fail', f'filtr nic nenajde ani pro {positive}')
    return Check(name, 'ok', f'0 pro nesmysl, {hit if hit is not None else "-"} pro {positive or "-"} (celkem {total})')


def search_checks(patient_id: str) -> list[Check]:
    checks = [_filters(t, 'patient', NOTHING, {'patient': patient_id}) for t in fhir.PATIENT_TYPES]
    checks += [
        _filters('Observation', '_id', NOTHING, {'_id': f'{patient_id}-ecog01,{patient_id}-vaha01'}),
        _filters('Practitioner', '_id', NOTHING, {'_id': f'LEK-{patient_id}-01'}),
        _filters('Observation', 'code', f'http://loinc.org|{NOTHING}', {'patient': patient_id, 'code': CEA}),
        _filters('Observation', 'subject', f'Patient/{NOTHING}', {'subject': f'Patient/{patient_id}'}),
        _filters('Observation', 'category', NOTHING, {'patient': patient_id, 'category': 'laboratory'}),
        _filters('Observation', 'status', NOTHING, {'patient': patient_id, 'status': 'final'}),
        _filters('Observation', 'date', '1900-01-01', {'patient': patient_id, 'date': 'ge2000-01-01'}),
        _filters('Patient', '_tag', f'https://rakathon.example.org/fhir/tag|{NOTHING}', {'_tag': FICTIONAL_TAG}),
    ]
    try:
        ids = fhir.search('Observation', _id=f'{patient_id}-ecog01,{patient_id}-vaha01')
        checks.append(Check('_id=a,b (OR)', 'ok' if len(ids) == 2 else 'fail', f'{len(ids)} resources, čekáno 2'))
        # sestupně: dataset je nahraný chronologicky, vzestupné pořadí by vyšlo i při ignorovaném _sort
        dates = [o.get('effectiveDateTime', '') for o in fhir.search('Observation', patient=patient_id, code=CEA, _sort='-date')]
        ordered = len(set(dates)) > 1 and dates == sorted(dates, reverse=True)
        checks.append(Check('Observation?_sort=-date', 'ok' if ordered else 'fail',
                            f'data: {", ".join(d[:10] for d in dates)}', required=False))
    except fhir.FhirError as e:
        checks.append(Check('_id / _sort', 'fail', str(e)))
    return checks


def everything_check(patient_id: str) -> Check:
    """``Patient/$everything``: podpora a srovnání s fallbackem (paralelní searche)."""
    try:
        bundle = fhir.request('GET', f'Patient/{patient_id}/$everything', params={'_count': 1000})
    except fhir.FhirError as e:
        return Check('Patient/$everything', 'info', f'nepodporováno (HTTP {e.status}), zůstává fallback patient_everything',
                     required=False)
    got = {f"{e['resource']['resourceType']}/{e['resource']['id']}" for e in bundle.get('entry', [])}
    fallback = {f"{r['resourceType']}/{r['id']}" for rs in fhir.patient_everything(patient_id).values() for r in rs}
    paged = any(link.get('relation') == 'next' for link in bundle.get('link', []))
    return Check('Patient/$everything', 'info',
                 f'funguje: {len(got)} resources (fallback {len(fallback)}, chybí {len(fallback - got)}, '
                 f'navíc {len(got - fallback)}{", stránkováno" if paged else ""})', required=False)


def mcode_check() -> Check:
    try:
        bogus = fhir.count('StructureDefinition', url=f'http://example.org/{NOTHING}')
        found = fhir.count('StructureDefinition', url=MCODE_PROFILE)
    except fhir.FhirError as e:
        return Check('mCODE IG', 'info', f'nelze zjistit: {e}', required=False)
    if bogus:
        return Check('mCODE IG', 'info', 'StructureDefinition?url se ignoruje, nelze zjistit', required=False)
    return Check('mCODE IG', 'info', 'nahraný' if found else 'nenahraný (profily mCODE v IRIS nejsou; BON-5 / T-307)',
                 required=False)


def validate_check(patient_id: str) -> Check:
    try:
        resource = fhir.read('Observation', f'{patient_id}-ecog01')
        outcome = fhir.request('POST', 'Observation/$validate', resource) or {}
    except fhir.FhirError as e:
        if e.status in (404, 405, 501):
            return Check('$validate', 'info', f'nepodporováno (HTTP {e.status})', required=False)
        outcome = e.outcome
    errors = [i for i in outcome.get('issue', []) if i.get('severity') in ('error', 'fatal')]
    detail = 'funguje, ECOG Observation bez chyb' if not errors else f'funguje, {len(errors)} chyb: ' + '; '.join(
        (i.get('details') or {}).get('text') or i.get('diagnostics', '') for i in errors[:3])
    return Check('$validate', 'info', detail, required=False)


def run_checks(patient_id: str = 'P03') -> list[Check]:
    meta = fhir.request('GET', 'metadata') or {}
    checks = [Check('metadata', 'ok' if meta.get('fhirVersion', '').startswith('4.0') else 'fail',
                    f"FHIR {meta.get('fhirVersion', '?')}, {meta.get('software', {}).get('name', '')} "
                    f"{meta.get('software', {}).get('version', '')}".strip())]
    checks += search_checks(patient_id)
    checks += [everything_check(patient_id), mcode_check(), validate_check(patient_id)]
    return checks
