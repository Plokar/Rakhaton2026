"""Ingest datasetu (T-101) proti in-memory FHIR serveru. Proti IRIS viz test_ingest_integration.py."""
import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from services.fhir import client, ingest
from services.fhir.testing import _bad_value


def _all(report):
    return [r for part in report.parts for r in part.resources]


def _raw_bundle(root, pid):
    return json.loads((root / 'pacienti' / pid / f'{pid}_bundle.json').read_text(encoding='utf-8'))


# ── sanitizace ──

def test_sanitize_fixes_ids_references_and_empty_strings(dataset_root):
    resources = {r['id']: r for r in _all(ingest.collect(dataset_root))}
    hb_f = [rid for rid in resources if rid.endswith('-hb-f')]
    assert len(hb_f) == 26                                       # DATASET §3
    assert not any('_' in rid for rid in resources)
    assert 'Observation/P01-lab01-hb-f' in json.dumps(resources['P01-lab01'])
    item = next(i for i in resources['P03-prom02']['item'] if i['linkId'] == 'bolest-misto')
    assert 'answer' not in item                                  # "" pryč i s prázdným answer
    for r in resources.values():
        assert _bad_value(r) is None, r['id']
        assert any(t['code'] == 'fiktivni-data' for t in r['meta']['tag'])


def test_sanitize_keeps_falsy_values_and_does_not_mutate(dataset_root):
    raw = _raw_bundle(dataset_root, 'P03')
    before = json.dumps(raw, sort_keys=True)
    resources = {r['id']: r for r in ingest.prepare_bundle(raw)}
    assert json.dumps(raw, sort_keys=True) == before
    assert resources['P03-ecog03']['valueInteger'] == 0          # ECOG 0 není „prázdný“
    studies = {r['id']: r for r in ingest.load_studies(dataset_root)}
    assert studies['RKT-03-kriteria']['characteristic'][0]['exclude'] is False


def test_collect_matches_dataset_counts(dataset_root):
    report = ingest.collect(dataset_root)
    assert report.warnings == []
    assert {p.label: len(p.resources) for p in report.parts} == {
        'Questionnaire': 1, 'studie': 12, **ingest.EXPECTED_PATIENT_TOTALS,
    }
    assert report.unique_resources == ingest.EXPECTED_TOTAL


def test_collect_unknown_patient(dataset_root):
    with pytest.raises(ingest.DatasetError, match='P99'):
        ingest.collect(dataset_root, ['P99'])


def test_dataset_dir_from_env(monkeypatch, tmp_path, dataset_root):
    monkeypatch.delenv('DATASET_DIR', raising=False)
    with pytest.raises(ingest.DatasetError, match='DATASET_DIR'):
        ingest.dataset_dir()
    with pytest.raises(ingest.DatasetError, match='pacienti'):
        ingest.dataset_dir(tmp_path)
    monkeypatch.setenv('DATASET_DIR', str(dataset_root))
    assert ingest.dataset_dir() == dataset_root


# ── transaction bundle ──

def test_to_transaction_puts_with_dataset_ids(dataset_root):
    resources = ingest.load_patient(dataset_root, 'P03')
    bundle = ingest.to_transaction(resources)
    assert bundle['type'] == 'transaction' and len(bundle['entry']) == 171
    for e in bundle['entry']:
        assert e['request'] == {'method': 'PUT', 'url': ingest.key(e['resource'])}
        assert e['fullUrl'].endswith(ingest.key(e['resource']))
    order = [ingest.key(e['resource']) for e in bundle['entry']]
    assert order.index('Patient/P03') < order.index('Observation/P03-ecog03')
    assert order.index('DocumentReference/P03-doc07') < order.index('Observation/P03-ecog03')   # derivedFrom


def test_order_by_references_handles_cycles():
    a = {'resourceType': 'Observation', 'id': 'a', 'derivedFrom': [{'reference': 'DiagnosticReport/b'}]}
    b = {'resourceType': 'DiagnosticReport', 'id': 'b', 'result': [{'reference': 'Observation/a'}]}
    c = {'resourceType': 'Patient', 'id': 'c'}
    assert [r['id'] for r in ingest.order_by_references([a, b, c])] == ['c', 'a', 'b']


# ── nahrání a kontrola počtů ──

def test_ingest_all_into_fhir_and_rerun_is_idempotent(fake_fhir, dataset_root):
    report = ingest.ingest(dataset_root)
    assert report.errors == []
    assert len(fake_fhir.store) == ingest.EXPECTED_TOTAL
    p03 = next(p for p in report.parts if p.label == 'P03')
    assert p03.upload.statuses == {'201': 170, '200': 1}                                     # ORG-FN sdílená (už z P01)
    assert any(c.what == 'Observation?patient=P03' and c.actual == 85 for c in p03.checks)   # ARCH §10

    again = ingest.ingest(dataset_root)
    assert again.errors == []
    assert len(fake_fhir.store) == ingest.EXPECTED_TOTAL                                       # 2. běh bez duplikátů
    assert next(p for p in again.parts if p.label == 'P03').upload.statuses == {'200': 171}
    assert fake_fhir.ignored_params == set()


def test_raw_dataset_bundle_is_rejected(fake_fhir, dataset_root):
    """Bez sanitizace server bundle odmítne (DATASET §0): fake server kontroluje totéž co IRIS."""
    raw = _raw_bundle(dataset_root, 'P01')
    bundle = {'resourceType': 'Bundle', 'type': 'transaction', 'entry': [
        {'resource': e['resource'], 'request': {'method': 'PUT', 'url': f"{e['resource']['resourceType']}/{e['resource']['id']}"}}
        for e in raw['entry']
    ]}
    with pytest.raises(client.FhirError) as err:
        client.transaction(bundle)
    assert err.value.status == 400 and 'hb_f' in str(err.value)


def test_batch_reports_errors_per_resource(fake_fhir):
    good = {'resourceType': 'Patient', 'id': 'P98'}
    bad = {'resourceType': 'Observation', 'id': 'P98-x', 'status': '', 'subject': {'reference': 'Patient/P98'}}
    result = ingest.upload([good, bad], 'test', bundle_type='batch')
    assert result.statuses == {'201': 1, '400': 1}
    assert result.errors and result.errors[0].startswith('Observation/P98-x: 400')


def test_verify_reports_missing_and_tolerates_extra(fake_fhir_dataset, dataset_root):
    resources = ingest.load_patient(dataset_root, 'P03')
    del fake_fhir_dataset.store['Observation/P03-ecog03']
    fake_fhir_dataset.store['Composition/P03-mdt02'] = {
        'resourceType': 'Composition', 'id': 'P03-mdt02', 'subject': {'reference': 'Patient/P03'},
    }
    bad = [c for c in ingest.verify(resources, 'P03', 'P03') if not c.ok]
    assert [(c.what, c.expected, c.actual) for c in bad] == [
        ('Observation (_id)', 85, 84), ('Observation?patient=P03', 85, 84),
    ]


# ── management command ──

def test_command_dry_run(dataset_root):
    out = StringIO()
    call_command('ingest_dataset', '--dry-run', dataset_dir=str(dataset_root), stdout=out)
    assert 'Celkem 1091 unikátních resources připraveno' in out.getvalue()


def test_command_ingests_selected_patients(fake_fhir, dataset_root):
    out = StringIO()
    call_command('ingest_dataset', patients='P03,P05', dataset_dir=str(dataset_root), stdout=out)
    assert 'nahráno a ověřeno' in out.getvalue()
    assert len([k for k in fake_fhir.store if k.startswith('Patient/')]) == 2
    assert 'ResearchStudy/RKT-03' in fake_fhir.store and 'Questionnaire/MDT-PROMS-1' in fake_fhir.store


def test_command_explains_rejected_transaction(fake_fhir, dataset_root, monkeypatch):
    def reject(bundle):
        raise client.FhirError(400, 'nelíbí se mi')
    monkeypatch.setattr(client, 'transaction', reject)
    with pytest.raises(CommandError, match='--bundle-type batch'):
        call_command('ingest_dataset', patients='P03', dataset_dir=str(dataset_root), stdout=StringIO())
