"""Eval podkladu proti ground truth (T-301, ARCH §5.8): `python manage.py eval_ground_truth [--gt DIR] [--model ID]`.

Pro každého pacienta vygeneruje podklad stejnou cestou jako job (data z IRIS, guidelines, vektory pro grounding)
a porovná ho s ground truth (`services/eval/evaluate.py`). Výstup je markdown pro docs/EVAL.md (stdout nebo --out).
Gemini jen s klíčem (free tier smí nad syntetickým datasetem, D-021); bez klíče běží mock.
"""
import os
import time
from datetime import datetime

from django.core.management.base import BaseCommand

from services.ai.brief import build_brief
from services.ai.context_builder import context_from_resources, load_resources
from services.ai.guidelines import GuidelinesUnavailable, load_guidelines
from services.ai_service import ai_model, ai_provider_name, get_ai_provider
from services.eval import ground_truth
from services.eval.evaluate import report, score
from services.rules import red_flags as rules
from services.rules.guideline_sets import guideline_sets_for
from services.rules.intake import intake_prefill


class Command(BaseCommand):
    help = 'Eval podkladu P01–P06 proti dev ground truth → markdown pro docs/EVAL.md'

    def add_arguments(self, parser):
        parser.add_argument('--gt', help='adresář s Pxx.json (výchozí data/dev_ground_truth)')
        parser.add_argument('--patients', help='např. P03,P05 (výchozí všichni z ground truth)')
        parser.add_argument('--model', help='model LLM pro tento běh (např. nvidia/nemotron-3-ultra-550b-a55b)')
        parser.add_argument('--out', help='soubor pro markdown (výchozí stdout)')

    def handle(self, *args, **opts):
        if opts['model']:            # model aktivního provideru (NVIDIA_MODEL / AI_MODEL)
            os.environ['NVIDIA_MODEL' if ai_provider_name() == 'nvidia' else 'AI_MODEL'] = opts['model']
        gts = ground_truth.load(opts['gt'] or os.environ.get('GROUND_TRUTH_DIR') or None)
        wanted = opts['patients'].split(',') if opts['patients'] else list(gts)
        provider = get_ai_provider()
        results = []
        for pid in wanted:
            started = time.monotonic()
            resources, studies = load_resources(pid)
            try:
                passages = load_guidelines(guideline_sets_for(rules.PatientData(resources).icd10))
            except GuidelinesUnavailable:
                passages = []
            brief = build_brief(pid, resources, studies=studies, guidelines=passages, provider=provider, case_id='eval')
            context = context_from_resources(pid, resources, studies=studies, guidelines=passages)
            result = score(gts[pid], brief, intake_prefill(resources), context)
            result['seconds'] = time.monotonic() - started
            results.append(result)
            self.stderr.write(f"{pid}: RF key {result['red_flags_key']}, neověřeno {result['unverified']} "
                              f"({result['seconds']:.0f} s)")
        model = 'mock' if provider.is_mock else ai_model()
        title = f"Běh {datetime.now():%d. %m. %Y %H:%M} · {provider.provider_name} · {model}"
        markdown = report(results, title)
        if opts['out']:
            with open(opts['out'], 'a', encoding='utf-8') as fh:
                fh.write('\n' + markdown)
        else:
            self.stdout.write(markdown)
