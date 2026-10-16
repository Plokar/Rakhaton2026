"""Nahraje dataset do IRIS: FHIR + vektorové tabulky MDT.* (T-101, T-102, T-203; DATASET §6, ARCH §4.4–4.5)."""
import re

from django.core.management.base import BaseCommand, CommandError

from services import ai_service
from services.fhir import client as fhir
from services.fhir import ingest
from services.iris import indexing
from services.iris import vector_store as vs


class Command(BaseCommand):
    help = (
        'Dataset → IRIS: FHIR (sanitizace, transaction s PUT, kontrola počtů; Questionnaire → studie → pacienti), '
        'pak vektorové tabulky MDT.EvidenceChunk, MDT.GuidelineChunk a MDT.TrialCriterion.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--patients', help='jen vybraní pacienti, např. P03,P05 (výchozí všichni)')
        parser.add_argument('--dataset-dir', help='kořen datasetu (výchozí env DATASET_DIR)')
        parser.add_argument('--dry-run', action='store_true', help='nic neposílá: sanitizace, počty, odstavce')
        parser.add_argument('--skip-fhir', action='store_true', help='FHIR přeskočit (data už v IRIS jsou), jen vektory')
        parser.add_argument('--skip-vectors', action='store_true', help='bez vektorových tabulek (bez embeddingů)')
        parser.add_argument(
            '--if-empty', action='store_true',
            help='pro start kontejneru: FHIR jen když v IRIS něco chybí, vektory jen když chybí pro aktuální model',
        )
        parser.add_argument(
            '--recreate-vector-tables', action='store_true',
            help='zahodit a založit tabulky MDT.* znovu (např. po změně EMBEDDING_DIM)',
        )
        parser.add_argument(
            '--bundle-type', choices=['transaction', 'batch'], default='transaction',
            help='batch = chyby po jednotlivých resources (ladění, když IRIS transakci odmítne)',
        )

    def handle(self, *args, **opts):
        offline = opts['dry_run']
        self.if_empty = opts['if_empty'] and not offline
        try:
            root = ingest.dataset_dir(opts['dataset_dir'])
            patients = [p.strip() for p in opts['patients'].split(',')] if opts['patients'] else None
            skip_fhir = opts['skip_fhir']
            report = ingest.collect(root, patients)
            if self.if_empty and not skip_fhir and ingest.is_loaded(report):
                self.stdout.write(f'FHIR: všech {report.unique_resources} resources už v IRIS je, přeskakuji (--if-empty).')
                skip_fhir = True
            if not (offline or skip_fhir):
                report = ingest.ingest(root, patients, opts['bundle_type'], log=self.stdout.write)
            self._fhir_summary(report, sent=not (offline or skip_fhir))
            if report.errors:
                raise CommandError(f'FHIR ingest skončil s {len(report.errors)} chybami (viz výše).')
            if not opts['skip_vectors']:
                try:
                    self._vectors(root, report, offline, opts['recreate_vector_tables'])
                except (CommandError, ai_service.AIProviderError, fhir.FhirError, ingest.DatasetError):
                    raise
                except Exception as e:      # driver iris: chyba spojení / SQL
                    raise CommandError(f'Vektorové tabulky v IRIS SQL selhaly: {e}. FHIR část je hotová, '
                                       f'vektory zopakuj: ingest_dataset --skip-fhir')
        except ingest.DatasetError as e:
            raise CommandError(str(e))
        except fhir.FhirError as e:
            hint = '' if opts['bundle_type'] == 'batch' else ' Pro chyby po položkách: --bundle-type batch.'
            raise CommandError(f'IRIS FHIR odmítl požadavek: {e}.{hint}')
        except ai_service.AIProviderError as e:
            raise CommandError(f'Embeddingy selhaly: {e}. Bez vektorů: --skip-vectors.')
        except OSError as e:
            raise CommandError(f'IRIS nedostupný ({fhir.base_url()}): {e}. Běží iris a proběhl iris_init?')

    # ── FHIR ──
    def _fhir_summary(self, report, sent):
        for warning in report.warnings:
            self.stdout.write(self.style.WARNING(f'⚠ {warning}'))
        for part in report.parts:
            self.stdout.write(f'  {part.label:<14} {len(part.resources):>4} resources')
        for error in report.errors:
            self.stdout.write(self.style.ERROR(f'✗ {error}'))
        verb = 'nahráno a ověřeno' if sent else 'připraveno (nic neodesláno)'
        style = self.style.ERROR if report.errors else self.style.SUCCESS
        self.stdout.write(style(f'FHIR: celkem {report.unique_resources} unikátních resources {verb}.'))

    # ── vektory ──
    def _vectors(self, root, report, offline, recreate):
        patients = [p for p in report.parts if re.fullmatch(r'P\d{2}', p.label)]
        studies = next((p.resources for p in report.parts if p.label == 'studie'), [])
        guidelines = indexing.guideline_chunks(root)
        for warning in indexing.guideline_count_warnings(guidelines):
            self.stdout.write(self.style.WARNING(f'⚠ {warning}'))
        guidelines += indexing.external_chunks()        # EXT-… pro semafor (T-504, D-016)
        paragraphs = {p.label: len(indexing.evidence_chunks(p.label, p.resources)) for p in patients}
        expected = {                                    # kolik řádků z datasetu vznikne (zápisy aplikace přidají další)
            f'{vs.SCHEMA}.EvidenceChunk': sum(paragraphs.values()),
            f'{vs.SCHEMA}.GuidelineChunk': len(guidelines),
            f'{vs.SCHEMA}.TrialCriterion': len(indexing.trial_criteria(studies)),
        }
        if offline:
            self.stdout.write(
                f'Vektory (nic neodesláno): odstavce {paragraphs} = {sum(paragraphs.values())}, '
                f'guidelines {len(guidelines)} (z toho EXT {sum(g.GuidelineSet == "EXT" for g in guidelines)}), '
                f'kritéria studií {expected[f"{vs.SCHEMA}.TrialCriterion"]}.'
            )
            return

        provider = ai_service.get_ai_provider()
        model = vs.embedding_model_id(provider)
        if self.if_empty:
            have = {table: by_model.get(model, 0) for table, by_model in vs.counts().items()}
            if all(have.get(table, 0) >= n for table, n in expected.items()):
                self.stdout.write(f'Vektory ({model}) už v IRIS jsou, přeskakuji (--if-empty): {have}')
                return
        if provider.is_mock:
            self.stdout.write(self.style.WARNING(
                '⚠ AI_PROVIDER=mock: vektory jsou hashované (jen lexikální podobnost). Pro Gemini nastav '
                'AI_PROVIDER=gemini + GEMINI_API_KEY (placený tier, Q9) a spusť znovu s --skip-fhir.'
            ))
        changes = vs.ensure_schema(recreate)
        if changes:
            self.stdout.write(f'Schéma {vs.SCHEMA}.*: založeno / doplněno {", ".join(changes)}')
        for part in patients:
            n = indexing.index_patient(part.label, provider=provider)       # čte z IRIS FHIR
            self.stdout.write(f'  MDT.EvidenceChunk {part.label}: {n} odstavců')
        per_set = indexing.index_guidelines(guidelines, provider)
        self.stdout.write(f'  MDT.GuidelineChunk: {per_set}')
        criteria = indexing.trial_criteria(indexing.trial_resources_from_fhir())
        per_study = indexing.index_trials(criteria, provider)
        self.stdout.write(f'  MDT.TrialCriterion: {sum(per_study.values())} kritérií ve {len(per_study)} studiích')
        totals = {table: by_model.get(model, 0) for table, by_model in vs.counts().items()}
        self.stdout.write(self.style.SUCCESS(f'Vektory ({model}): {totals}'))
