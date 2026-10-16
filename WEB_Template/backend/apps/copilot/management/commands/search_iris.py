"""Ruční ověření vektorového hledání v IRIS (T-102, T-203): co najde dotaz a s jakým skóre."""
from django.core.management.base import BaseCommand, CommandError

from services.iris import vector_store as vs
from services.rules.guideline_sets import guideline_sets_for


class Command(BaseCommand):
    help = 'Vektorové hledání v MDT.EvidenceChunk / GuidelineChunk / TrialCriterion, např. search_iris "neuropatie" --patient P03'

    def add_arguments(self, parser):
        parser.add_argument('query')
        parser.add_argument('--kind', choices=['evidence', 'guidelines', 'trials'], default='evidence')
        parser.add_argument('--patient', help='povinné pro --kind evidence (filtr na pacienta)')
        parser.add_argument('--icd10', help='u guidelines: diagnózy pacienta, např. C18.7,C78.7 (+ OBC vždy)')
        parser.add_argument('--study', help='u trials: např. RKT-03')
        parser.add_argument('--top', type=int, default=5)

    def handle(self, *args, query, kind, patient, icd10, study, top, **opts):
        if kind == 'evidence':
            if not patient:
                raise CommandError('--kind evidence vyžaduje --patient (hledá se jen v datech pacienta)')
            rows = vs.search_evidence(patient, query, top)
        elif kind == 'guidelines':
            sets = guideline_sets_for(icd10.split(',')) if icd10 else None
            rows = vs.search_guidelines(query, sets, top)
        else:
            rows = vs.search_trial_criteria(query, [study] if study else None, top)
        if not rows:
            self.stdout.write(self.style.WARNING(
                f'Nic nenalezeno. Tabulky podle modelu: {vs.counts()}; aktuální model {vs.embedding_model_id()}.'
            ))
        for row in rows:
            text = ' '.join(row['Text'].split())
            self.stdout.write(f"{row['Score']:.3f}  [{row['EvidenceId']}]  {text[:140]}")
