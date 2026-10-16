import pytest

from services.fhir import ingest
from services.fhir.ids import (
    EvidenceRef, parse_evidence_id, patient_id_for, resource_type_for_id, sanitize_id, sanitize_reference,
)


def test_sanitize_id_and_reference():
    assert sanitize_id('P01-lab01-hb_f') == 'P01-lab01-hb-f'
    assert sanitize_reference('Observation/P01-lab01-hb_f') == 'Observation/P01-lab01-hb-f'
    assert sanitize_reference('https://x.org/fhir/Observation/P01-lab01-hb_f') == 'https://x.org/fhir/Observation/P01-lab01-hb-f'
    assert sanitize_reference('Observation/P01-lab01-hb_f/_history/2') == 'Observation/P01-lab01-hb-f/_history/2'
    assert sanitize_reference('urn:uuid:a_b') == 'urn:uuid:a_b'
    assert sanitize_reference('#contained_1') == '#contained_1'


def test_every_dataset_id_maps_to_its_type(dataset_root):
    """Index ID → ResourceType (T-101) sedí pro všech 1 091 resources datasetu."""
    report = ingest.collect(dataset_root)
    resources = [r for part in report.parts for r in part.resources]
    wrong = [ingest.key(r) for r in resources if resource_type_for_id(r['id']) != r['resourceType']]
    assert wrong == []
    assert len({ingest.key(r) for r in resources}) == ingest.EXPECTED_TOTAL


@pytest.mark.parametrize('rid, rtype', [
    ('P03-mdt02', 'Composition'),
    ('P03-mdt02-careplan', 'CarePlan'),
    ('P03-mdt02-careteam', 'CareTeam'),
    ('P03-mdt02-task01', 'Task'),
    ('P03-mdt02-rf01', 'DetectedIssue'),
    ('P03-mdt02-rs01', 'ResearchSubject'),
    ('P03-mdt02-prov', 'Provenance'),
    ('P03-mdt02-prepis', 'DocumentReference'),
    ('P03-mdt02-pdf', 'DocumentReference'),
    ('P03-ecog-case01', 'Observation'),
    ('P03-case01-w01', 'DetectedIssue'),
    ('mdt-copilot', 'Device'),
    ('P01-lab01-hb-f', 'Observation'),
    ('P01-lab01-hb_f', None),          # citace vždy se sanitizovaným ID
    ('P99-neco', None),
])
def test_output_ids_from_architecture(rid, rtype):
    """Výstupy aplikace (ARCH §4.3) dodržují konvenci, aby šly citovat stejně jako dataset."""
    assert resource_type_for_id(rid) == rtype


def test_patient_id_for():
    assert patient_id_for('P03-img03') == 'P03'
    assert patient_id_for('LEK-P03-01') == 'P03'
    assert patient_id_for('P03') == 'P03'
    assert patient_id_for('KRC-2.4') is None


@pytest.mark.parametrize('eid, expected', [
    ('P03-img03', EvidenceRef('P03-img03', 'resource', 'DiagnosticReport', 'P03-img03', None, 'P03')),
    ('P03-img03#2', EvidenceRef('P03-img03#2', 'paragraph', 'DiagnosticReport', 'P03-img03', 2, 'P03')),
    ('P03-mdt02-prepis#12', EvidenceRef('P03-mdt02-prepis#12', 'paragraph', 'DocumentReference', 'P03-mdt02-prepis', 12, 'P03')),
    ('KRC-2.4', EvidenceRef('KRC-2.4', 'guideline')),
    ('RKT-03', EvidenceRef('RKT-03', 'resource', 'ResearchStudy', 'RKT-03')),
    ('RKT-03/V3', EvidenceRef('RKT-03/V3', 'trial_criterion', study_id='RKT-03', criterion='V3')),
    ('EXT-EMA-DPD-2020', EvidenceRef('EXT-EMA-DPD-2020', 'external')),
    ('LEK-P03-01', EvidenceRef('LEK-P03-01', 'resource', 'Practitioner', 'LEK-P03-01', None, 'P03')),
    ('P03-img03#0', None),
    ('P03-img03#', None),
    ('[P03-img03]', None),
    ('KRC 2.4', None),
    ('', None),
])
def test_parse_evidence_id(eid, expected):
    assert parse_evidence_id(eid) == expected
