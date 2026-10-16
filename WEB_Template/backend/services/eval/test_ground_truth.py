"""Dev ground truth (T-013): formát a dohledatelnost každé položky v datasetu (ID, pasáže, kritéria, pravidla)."""
import re
from pathlib import Path

import pytest

from services.eval import ground_truth as gtm
from services.fhir import ingest
from services.fhir.ids import parse_evidence_id
from services.iris import indexing

PATIENTS = {'P01', 'P02', 'P03', 'P04', 'P05', 'P06'}


@pytest.fixture(scope='module')
def gts():
    try:
        return gtm.load()
    except FileNotFoundError as e:
        pytest.skip(str(e))


@pytest.fixture(scope='module')
def known(dataset_root):
    report = ingest.collect(dataset_root)
    resources = {r['id'] for part in report.parts for r in part.resources}
    passages = {c.EvidenceId for c in indexing.guideline_chunks(dataset_root) + indexing.external_chunks()}
    criteria = {c.EvidenceId for c in indexing.trial_criteria(ingest.load_studies(dataset_root))}
    return resources, passages, criteria


def test_all_patients_present(gts):
    assert set(gts) == PATIENTS


def test_every_citation_exists_in_dataset(gts, known):
    resources, passages, criteria = known
    errors = []
    for pid, gt in gts.items():
        for eid in sorted(gtm.all_citations(gt)):
            ref = parse_evidence_id(eid)
            if ref is None:
                errors.append(f'{pid}: neplatné Evidence ID {eid}')
            elif ref.kind in ('resource', 'paragraph'):
                if ref.resource_id not in resources:
                    errors.append(f'{pid}: {eid} v datasetu není')
                elif ref.patient_id not in (None, pid) and ref.resource_type != 'ResearchStudy':
                    errors.append(f'{pid}: {eid} patří jinému pacientovi')
            elif ref.kind in ('guideline', 'external') and eid not in passages:
                errors.append(f'{pid}: pasáž {eid} neexistuje')
            elif ref.kind == 'trial_criterion' and eid not in criteria:
                errors.append(f'{pid}: kritérium {eid} neexistuje')
    assert errors == []


def test_red_flags_cite_two_sources_and_a_guideline_or_basis(gts):
    for gt in gts.values():
        ids = [rf.id for rf in gt.red_flags]
        assert len(ids) == len(set(ids))
        for rf in gt.red_flags:
            assert rf.guideline or rf.basis, rf.id
            assert set(rf.also_rules) <= gtm.RED_FLAG_RULES, rf.id


def test_every_study_evaluated(gts, known):
    _, _, criteria = known
    for pid, gt in gts.items():
        assert {t.study_id for t in gt.trials} == {f'RKT-0{i}' for i in range(1, 7)}, pid
        for t in gt.trials:
            assert all(c.criterion_id.startswith(f'{t.study_id}/') for c in t.criteria)
            assert all((c.kind == 'exclusion') == c.criterion_id.split('/')[1].startswith('V') for c in t.criteria)
            assert all(c.missing for c in t.criteria if c.status == 'unknown'), (pid, t.study_id)


def test_recist_arithmetic(gts):
    for pid, gt in gts.items():
        r = gt.recist
        if not r:
            assert gt.recist_note, pid
            continue
        base = (r.current.sum_mm - r.baseline.sum_mm) / r.baseline.sum_mm * 100
        assert abs(base - r.change_from_baseline_pct) < 1, pid
        if r.nadir:
            nadir = (r.current.sum_mm - r.nadir.sum_mm) / r.nadir.sum_mm * 100
            assert abs(nadir - r.change_from_nadir_pct) < 1, pid


def _catalog_rules() -> set[str] | None:
    for parent in Path(__file__).resolve().parents:
        doc = parent / 'docs' / 'POZADAVKY_LEKARE.md'
        if doc.exists():
            return set(re.findall(r'^\| (VS-[A-Z]+-\d+) \|', doc.read_text(encoding='utf-8'), flags=re.M))
    return None


def test_semafor_rules_exist_in_catalog(gts):
    catalog = _catalog_rules()
    if catalog is None:
        pytest.skip('docs/POZADAVKY_LEKARE.md není k dispozici')
    for pid, gt in gts.items():
        used = {r.rule_id for opt in gt.compatibility for r in opt.rules} | {r.rule_id for r in gt.compatibility_rules}
        assert used <= catalog, (pid, used - catalog)
        for opt in gt.compatibility:                    # celková barva = nejhorší z pravidel (ARCH §5.9)
            order = ['green', 'grey', 'orange', 'red']
            worst = max((r.status for r in opt.rules if r.status in order), key=order.index)
            assert opt.overall == worst, (pid, opt.option)


def test_demo_patient_core_findings(gts):
    """P03 = demo (PROGRESS §7): hlavní nálezy, na které stojí finálová ukázka."""
    p03 = gts['P03']
    rules = {rf.rule for rf in p03.red_flags if rf.importance == 'key'}
    assert {'RF-ECOG', 'RF-TOX', 'RF-STALE', 'RF-MISSING'} <= rules
    rkt03 = next(t for t in p03.trials if t.study_id == 'RKT-03')
    status = {c.criterion_id: c.status for c in rkt03.criteria}
    assert status['RKT-03/Z1'] == status['RKT-03/V2'] == 'unknown'
    assert p03.recist.response == 'PR'
