"""Záloha a reset dema (T-311).

- cache podkladu `data/demo_cache/brief_Pxx.json` (předgenerovaný, nejlépe s Gemini);
- `MDT_DEMO_OFFLINE=True`: generování podkladu vrátí cache bez volání LLM (když cache chybí, běžný generátor);
- reset pacienta: z IRIS pryč jen resources vytvořené aplikací (dataset zůstane), pacient znovu z datasetu,
  případ zpět na původní board ve stavu „nominován“.
"""
import json
import logging
from pathlib import Path

from django.conf import settings
from django.utils.module_loading import import_string

from apps.mdt.models import MdtCase
from services.fhir import client as fhir
from services.fhir import ingest

from .models import Brief

log = logging.getLogger(__name__)

REAL_GENERATOR = 'services.ai.brief.generate_brief'
# pořadí mazání: nejdřív co odkazuje (Provenance, úkoly…), pak odkazované
APP_TYPES = ('Provenance', 'DetectedIssue', 'Task', 'ResearchSubject', 'DocumentReference', 'Composition',
             'CarePlan', 'CareTeam', 'Observation')


def cache_path(patient_id: str) -> Path:
    return Path(settings.MDT_DEMO_CACHE_DIR) / f'brief_{patient_id}.json'


def save_cache(patient_id: str, content: dict) -> Path:
    path = cache_path(patient_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding='utf-8')
    return path


def load_cache(patient_id: str) -> dict | None:
    path = cache_path(patient_id)
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None


def cached_brief(case, config: dict, progress, *, physician_guidance=None) -> dict:
    """Generátor jobu v offline demu: uložený podklad místo LLM; bez cache běžný generátor."""
    content = load_cache(case.patient_fhir_id)
    if content is None:
        log.warning('Offline demo: cache %s chybí, generuji normálně', cache_path(case.patient_fhir_id))
        return import_string(REAL_GENERATOR)(case, config, progress, physician_guidance=physician_guidance or [])
    progress(100)
    return {**content, 'case_id': str(case.pk)}


def load_into_case(case: MdtCase) -> Brief | None:
    content = load_cache(case.patient_fhir_id)
    if content is None:
        return None
    return Brief.objects.create(case=case, config_snapshot=content.get('config') or {},
                                content={**content, 'case_id': str(case.pk)}, model=content.get('model', ''))


def reset_patient(patient_id: str) -> dict:
    """IRIS: smaže resources pacienta, které nejsou v datasetu, a pacienta nahraje znovu (vrátí nominaci i Task).
    Postgres: smaže případy pacienta (s podklady a závěrem); `seed_mdt` je pak založí znovu."""
    root = ingest.dataset_dir()
    resources = ingest.load_patient(root, patient_id)
    keep = {ingest.key(r) for r in resources}
    deleted = []
    for rtype in APP_TYPES:
        for r in fhir.search(rtype):
            ref = f"{rtype}/{r['id']}"
            if r['id'].startswith(f'{patient_id}-') and ref not in keep:
                fhir.delete(rtype, r['id'])
                deleted.append(ref)
    result = ingest.upload(resources, patient_id)
    if not result.ok:
        raise RuntimeError(f'Re-ingest {patient_id} selhal: {result.errors[:3]}')
    try:
        from services.iris import indexing
        indexing.index_patient(patient_id)
    except Exception:
        log.warning('Reindex vektorů %s po resetu selhal (ručně: ingest_dataset --skip-fhir --patients %s)',
                    patient_id, patient_id, exc_info=True)
    cases, _ = MdtCase.objects.filter(patient_fhir_id=patient_id).delete()
    return {'deleted_fhir': deleted, 'reingested': result.sent, 'deleted_cases': cases}
