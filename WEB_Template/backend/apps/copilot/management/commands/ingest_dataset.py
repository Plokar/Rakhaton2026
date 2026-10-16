"""Nahraje dataset do IRIS FHIR a ověří počty (T-101, DATASET §6, ARCH §4.4)."""
from django.core.management.base import BaseCommand, CommandError

from services.fhir import client as fhir
from services.fhir import ingest


class Command(BaseCommand):
    help = (
        'Dataset → IRIS FHIR: sanitizace, transaction s PUT (idempotentní), kontrola počtů. '
        'Pořadí Questionnaire → studie → pacienti.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--patients', help='jen vybraní pacienti, např. P03,P05 (výchozí všichni)')
        parser.add_argument('--dataset-dir', help='kořen datasetu (výchozí env DATASET_DIR)')
        parser.add_argument('--dry-run', action='store_true', help='nic neposílá: jen sanitizace a kontrola souborů')
        parser.add_argument('--skip-fhir', action='store_true', help='FHIR část přeskočit (data už v IRIS jsou)')
        parser.add_argument(
            '--bundle-type', choices=['transaction', 'batch'], default='transaction',
            help='batch = chyby po jednotlivých resources (ladění, když IRIS transakci odmítne)',
        )

    def handle(self, *args, **opts):
        try:
            root = ingest.dataset_dir(opts['dataset_dir'])
            patients = [p.strip() for p in opts['patients'].split(',')] if opts['patients'] else None
            if opts['dry_run'] or opts['skip_fhir']:
                report = ingest.collect(root, patients)
            else:
                report = ingest.ingest(root, patients, opts['bundle_type'], log=self.stdout.write)
        except ingest.DatasetError as e:
            raise CommandError(str(e))
        except fhir.FhirError as e:
            hint = '' if opts['bundle_type'] == 'batch' else ' Pro chyby po položkách: --bundle-type batch.'
            raise CommandError(f'IRIS FHIR odmítl bundle: {e}.{hint}')
        except OSError as e:
            raise CommandError(f'IRIS FHIR nedostupný ({fhir.base_url()}): {e}. Běží iris a proběhl iris_init?')

        self._summary(report, sent=not (opts['dry_run'] or opts['skip_fhir']))
        if report.errors:
            raise CommandError(f'Ingest dokončen s {len(report.errors)} chybami (viz výše).')

    def _summary(self, report, sent):
        for warning in report.warnings:
            self.stdout.write(self.style.WARNING(f'⚠ {warning}'))
        for part in report.parts:
            self.stdout.write(f'  {part.label:<14} {len(part.resources):>4} resources')
        for error in report.errors:
            self.stdout.write(self.style.ERROR(f'✗ {error}'))
        verb = 'nahráno a ověřeno' if sent else 'připraveno (nic neodesláno)'
        style = self.style.ERROR if report.errors else self.style.SUCCESS
        self.stdout.write(style(f'Celkem {report.unique_resources} unikátních resources {verb}.'))
