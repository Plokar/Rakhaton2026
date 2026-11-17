"""Hodnocení odpovědí AI lékaři (T-382) do JSONL pro eval (docs/EVAL.md): `manage.py export_ai_feedback out.jsonl`.

Řádek = `{id, kind, patient_id, question, answer, rating, comment, created_at}`; bez jména lékaře (jen jeho role),
pacient jen jako `Pxx`. `--rating down` jen špatné odpovědi (sada pro ladění promptů).
"""
import json

from django.core.management.base import BaseCommand

from apps.mdt import roles
from apps.mdt.models import AiFeedback


class Command(BaseCommand):
    help = 'Export hodnocení odpovědí AI do JSONL (eval, ladění promptů).'

    def add_arguments(self, parser):
        parser.add_argument('out', help='cílový soubor .jsonl')
        parser.add_argument('--rating', choices=['up', 'down'])

    def handle(self, *args, out, rating, **options):
        items = AiFeedback.objects.select_related('user').order_by('created_at')
        if rating:
            items = items.filter(rating=rating)
        count = 0
        with open(out, 'w', encoding='utf-8') as fh:
            for f in items:
                fh.write(json.dumps({'id': f.pk, 'kind': f.kind, 'patient_id': f.patient_fhir_id, 'question': f.question,
                                     'answer': f.answer, 'rating': f.rating, 'comment': f.comment,
                                     'specialty': roles.specialty(f.user) if f.user else None,
                                     'created_at': f.created_at.isoformat()}, ensure_ascii=False) + '\n')
                count += 1
        self.stdout.write(f'Zapsáno {count} hodnocení do {out}.')
