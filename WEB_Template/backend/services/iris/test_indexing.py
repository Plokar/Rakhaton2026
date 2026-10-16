"""Řádky vektorových tabulek z datasetu (T-102 odstavce, T-203 guidelines a kritéria studií). Bez IRIS."""
from collections import Counter

from services.ai.text import resource_text
from services.fhir import ingest
from services.fhir.ids import parse_evidence_id
from services.iris import indexing


def _patient(root, pid):
    return ingest.load_patient(root, pid)


def test_evidence_chunks_match_text_module_offsets(dataset_root):
    """Odstavec = přesně výřez z ``resource_text`` (stejné číslování jako context builder a resolver)."""
    resources = _patient(dataset_root, 'P03')
    by_id = {r['id']: r for r in resources}
    chunks = indexing.evidence_chunks('P03', resources)
    assert len({c.EvidenceId for c in chunks}) == len(chunks)
    for c in chunks:
        assert c.EvidenceId == f'{c.ResourceId}#{c.ChunkIndex}'
        assert resource_text(by_id[c.ResourceId])[c.CharStart:c.CharEnd] == c.Text
        assert c.PatientId == 'P03' and c.ResourceType in indexing.TEXT_TYPES
    img03 = [c for c in chunks if c.ResourceId == 'P03-img03']
    assert 'hrudník nebyl požadován' in img03[0].Text
    assert img03[0].DocDate == '2026-09-21' and img03[0].Department.startswith('RDG')
    assert not any(c.ResourceId.startswith('P03-lab') for c in chunks)        # LAB nemá text


def test_evidence_chunks_whole_dataset(dataset_root):
    total = Counter()
    for pid in ingest.patient_ids(dataset_root):
        for c in indexing.evidence_chunks(pid, _patient(dataset_root, pid)):
            total[c.ResourceType] += 1
            assert len(c.Text) <= 10000 and c.Text.strip()
    assert total['DocumentReference'] + total['DiagnosticReport'] == 555        # odstavce zpráv, ARCH §4.5 (T-105)
    assert total == {'DocumentReference': 329, 'DiagnosticReport': 226, 'Composition': 81, 'ServiceRequest': 29}


def test_guideline_chunks(dataset_root):
    chunks = indexing.guideline_chunks(dataset_root)
    assert indexing.guideline_count_warnings(chunks) == []
    assert len(chunks) == 42
    by_id = {c.EvidenceId: c for c in chunks}
    assert by_id['KRC-2.3'].IcdPrefixes == 'C18,C19,C20' and '6 týdnů' in by_id['KRC-2.3'].Text
    assert by_id['OBC-1.2'].IcdPrefixes == '*'
    assert by_id['PRS-3.4'].IcdPrefixes == 'C50' and by_id['PLI-3.1'].IcdPrefixes == 'C34'
    assert by_id['KRC-2.4'].Title == 'Restaging před resekcí'
    assert all(c.Region == 'CZ' and c.Source.startswith('Rakathon 2026 – Výtah') for c in chunks)
    assert [c.EvidenceId for c in chunks][:3] == ['KRC-1.1', 'KRC-1.2', 'KRC-2.1']


def test_trial_criteria(dataset_root):
    criteria = indexing.trial_criteria(ingest.load_studies(dataset_root))
    by_id = {c.EvidenceId: c for c in criteria}
    assert len({c.StudyId for c in criteria}) == 6
    assert by_id['RKT-03/V3'].Kind == 'exclusion' and 'neuropat' in by_id['RKT-03/V3'].Text.lower()
    assert by_id['RKT-03/Z1'].Kind == 'inclusion'
    assert by_id['RKT-06/Z4'].StudyId == 'RKT-06'


def test_external_chunks_catalog():
    """T-504: katalog EXT-… z docs/POZADAVKY_LEKARE.md §5.3 / §6.1 / §13 (D-016)."""
    chunks = indexing.external_chunks()
    ids = [c.EvidenceId for c in chunks]
    assert len(ids) == len(set(ids)) == 13
    assert {'EXT-EMA-DPD-2020', 'EXT-LUNGRADS-2022'} <= set(ids)                   # ID z ARCH §5.2 a POZADAVKY §6.1
    for c in chunks:
        assert parse_evidence_id(c.EvidenceId).kind == 'external'
        assert c.GuidelineSet == 'EXT' and c.Url.startswith('https://') and len(c.Url) <= 500
        assert len(c.Source) <= 200 and len(c.Title) <= 300 and '[' in c.Text      # stav ověření a pravidla


def test_every_ext_cited_by_rules_is_in_catalog():
    """Spoj T-504 ↔ T-503: každé EXT-… citované pravidly semaforu jde resolvovat (jinak 404 u citace)."""
    import re
    from pathlib import Path
    rules = Path(indexing.__file__).resolve().parents[1] / 'rules' / 'data' / 'compatibility_rules.yaml'
    if not rules.exists():
        return
    cited = set(re.findall(r'EXT-[A-Z0-9][A-Z0-9.-]*[A-Z0-9]', rules.read_text(encoding='utf-8')))
    assert cited and cited <= {c.EvidenceId for c in indexing.external_chunks()}
