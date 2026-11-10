"""Běh jobů generování (D-004): záznam v DB + in-process ThreadPool, FE polluje stav.

Rozhraní generátoru (T-107 ↔ T-106, ARCH §5.1):
    generate_brief(case: MdtCase, config: dict, progress: Callable[[int], None]) -> dict
vrací validní Brief (ARCH §8.2); každé LLM volání loguje `LlmCallLog.record(purpose, result)`.
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from datetime import timedelta

from django.conf import settings
from django.db import close_old_connections, connection
from django.utils import timezone
from django.utils.module_loading import import_string

from .models import Brief, GenerationJob

log = logging.getLogger(__name__)

GENERATORS = {'brief': 'services.ai.brief.generate_brief', 'scribe': 'services.ai.scribe.generate_scribe',
              'patient_summary': 'services.ai.patient_summary.generate_patient_summary'}

# In-process pool: job běžící při restartu backendu by zůstal "running" navždy, proto fail_stale() (T-368).
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='mdt-job')

STALE_ERROR = 'Generování přerušil restart serveru. Spusťte ho znovu.'


def fail_stale(**filters) -> int:
    """Joby `queued` / `running` bez změny déle než `MDT_JOB_TIMEOUT_MINUTES` (výchozí 15) → `error` (T-368).

    `progress()` posouvá `updated_at`, takže živý job s průběhem sem nespadne. Vrací počet ukončených jobů.
    """
    limit = timezone.now() - timedelta(minutes=getattr(settings, 'MDT_JOB_TIMEOUT_MINUTES', 15))
    return GenerationJob.objects.filter(status__in=('queued', 'running'), updated_at__lt=limit, **filters).update(
        status='error', error=STALE_ERROR, updated_at=timezone.now())


def start(job: GenerationJob) -> None:
    fail_stale(case_id=job.case_id)              # starý zaseknutý job stejného případu neblokuje nový
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
        GenerationJob.objects.filter(pk=job_id).update(status='running', updated_at=timezone.now())

        def progress(pct: int) -> None:
            GenerationJob.objects.filter(pk=job_id).update(progress=max(0, min(100, int(pct))), updated_at=timezone.now())

        try:
            path = GENERATORS[job.kind]
            if job.kind == 'brief' and getattr(settings, 'MDT_DEMO_OFFLINE', False):
                path = 'apps.copilot.demo.cached_brief'     # T-311: uložený podklad bez LLM
            generate = import_string(path)
        except (ImportError, KeyError):
            raise RuntimeError(f'Generátor „{job.kind}“ zatím není k dispozici (T-106).') from None

        if job.kind != 'brief':                      # zapisovatel (T-305) ukládá draft Decision sám
            result = generate(job.case, job.params, progress)
            GenerationJob.objects.filter(pk=job_id).update(status='done', progress=100, result_id=result['result_id'],
                                                             updated_at=timezone.now())
            return
        config = job.params.get('config', {})
        feedback = job.params.get('feedback')        # zpětná vazba lékaře jde do promptů dotčených částí (T-323)
        content = generate(job.case, {**config, '_feedback': feedback} if feedback else config, progress)
        brief = Brief.objects.create(case=job.case, config_snapshot=config, content=content,
                                     model=content.get('model', ''))
        GenerationJob.objects.filter(pk=job_id).update(status='done', progress=100, result_id=brief.pk,
                                                         updated_at=timezone.now())
    except Exception as e:
        log.exception('Job %s selhal', job_id)
        GenerationJob.objects.filter(pk=job_id).update(status='error', error=str(e)[:2000], updated_at=timezone.now())
