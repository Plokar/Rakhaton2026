"""Běh jobů generování (D-004): záznam v DB + in-process ThreadPool, FE polluje stav.

Rozhraní generátoru (T-107 ↔ T-106, ARCH §5.1):
    generate_brief(case: MdtCase, config: dict, progress: Callable[[int], None]) -> dict
vrací validní Brief (ARCH §8.2); každé LLM volání loguje `LlmCallLog.record(purpose, result)`.
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.db import close_old_connections, connection
from django.utils.module_loading import import_string

from .models import Brief, GenerationJob

log = logging.getLogger(__name__)

GENERATORS = {'brief': 'services.ai.brief.generate_brief', 'scribe': 'services.ai.scribe.generate_scribe'}

# ponytail: in-process pool, joby běžící při restartu backendu zůstanou "running"; Celery/RQ až bude potřeba
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='mdt-job')


def start(job: GenerationJob) -> None:
    if getattr(settings, 'MDT_JOBS_SYNC', False):
        run(job.pk)
    else:
        _pool.submit(_in_thread, job.pk)


def _in_thread(job_id: int) -> None:
    close_old_connections()
    try:
        run(job_id)
    finally:
        connection.close()     # vlákno poolu si drží vlastní spojení


def run(job_id: int) -> None:
    try:
        job = GenerationJob.objects.select_related('case').get(pk=job_id)
        GenerationJob.objects.filter(pk=job_id).update(status='running')

        def progress(pct: int) -> None:
            GenerationJob.objects.filter(pk=job_id).update(progress=max(0, min(100, int(pct))))

        try:
            path = GENERATORS[job.kind]
            if job.kind == 'brief' and getattr(settings, 'MDT_DEMO_OFFLINE', False):
                path = 'apps.copilot.demo.cached_brief'     # T-311: uložený podklad bez LLM
            generate = import_string(path)
        except (ImportError, KeyError):
            raise RuntimeError(f'Generátor „{job.kind}“ zatím není k dispozici (T-106).') from None

        if job.kind != 'brief':                      # zapisovatel (T-305) ukládá draft Decision sám
            result = generate(job.case, job.params, progress)
            GenerationJob.objects.filter(pk=job_id).update(status='done', progress=100, result_id=result['result_id'])
            return
        config = job.params.get('config', {})
        content = generate(job.case, config, progress)
        brief = Brief.objects.create(case=job.case, config_snapshot=config, content=content,
                                     model=content.get('model', ''))
        GenerationJob.objects.filter(pk=job_id).update(status='done', progress=100, result_id=brief.pk)
    except Exception as e:
        log.exception('Job %s selhal', job_id)
        GenerationJob.objects.filter(pk=job_id).update(status='error', error=str(e)[:2000])
