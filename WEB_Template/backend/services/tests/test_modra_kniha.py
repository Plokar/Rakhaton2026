"""Modrá kniha ČOS (národní doporučené postupy): pasáže, indexace do IRIS, výběr k pacientovi a citace v podkladu."""
import pytest

from apps.copilot.schemas import Brief
from services.ai import brief as brief_module
from services.ai.context_builder import context_from_resources
from services.ai.guidelines import NATIONAL_SET, national_passages
from services.fhir.ids import parse_evidence_id
from services.iris import indexing
from services.tests.dataset import load_patient


@pytest.fixture(scope='module')
def chunks():
    rows = indexing.modra_kniha_chunks()
    if not rows:
        pytest.skip('data/onko/modra_kniha/pasaze.jsonl chybí (python3 data/onko/modra_kniha/stahni.py)')
    return rows


def test_passages_are_citable_external_sources(chunks):
    assert len(chunks) > 1000
    assert len({c.EvidenceId for c in chunks}) == len(chunks)
    for c in chunks:
        ref = parse_evidence_id(c.EvidenceId)
        assert ref is not None and ref.kind == 'external' and c.EvidenceId.startswith('EXT-MK-')
        assert c.GuidelineSet == NATIONAL_SET and 0 < len(c.Text) <= 5000 and c.Url.startswith('https://www.linkos.cz/')
    colorectal = {c.EvidenceId: c for c in chunks if c.EvidenceId.startswith('EXT-MK-4.')}
    assert colorectal['EXT-MK-4.6.3'].IcdPrefixes == 'C18,C19,C20'
    assert any(c.IcdPrefixes == '*' for c in chunks)                 # obecné kapitoly (podpůrná léčba…)


def test_national_passages_follow_patient_diagnosis(fake_iris, chunks):
    indexing.index_guidelines(chunks)
    found = national_passages(['C18.7'], 'Jsou jaterní metastázy resekabilní po FOLFOX + bevacizumab?')
    tumor = [p for p in found if p.evidence_id.startswith('EXT-MK-4.')]
    assert len(tumor) == 3 and len(found) == 4
    assert all(p.guideline_set == NATIONAL_SET and p.url for p in found)
    assert national_passages([], 'cokoli') == [] and national_passages(['C18.7'], ' ') == []


def test_brief_cites_modra_kniha(fake_iris, chunks):
    """Pasáže jsou v kontextu AI (smí se citovat) a podklad je vypíše v `national_guidelines`."""
    indexing.index_guidelines(chunks)
    resources = load_patient('P03')
    passages = national_passages(['C18.7'], 'resekce jaterních metastáz')
    context = context_from_resources('P03', resources, guidelines=passages)
    assert {p.evidence_id for p in passages} <= context.allowed_ids
    assert passages[0].evidence_id in context.render()
    brief = brief_module.build_brief('P03', resources, guidelines=passages)
    Brief.model_validate(brief)
    assert [g['evidence_id'] for g in brief['national_guidelines']] == [p.evidence_id for p in sorted(passages, key=lambda p: p.sort_key)]
    assert brief['national_guidelines'][0]['url'].startswith('https://www.linkos.cz/')
