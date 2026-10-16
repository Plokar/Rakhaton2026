"""Ověří chování IRIS FHIR serveru, na kterém aplikace stojí (T-313, Q7). Výstup jde rovnou do ARCH §4.6."""
from django.core.management.base import BaseCommand, CommandError

from services.fhir import capabilities
from services.fhir import client as fhir

ICONS = {'ok': '✓', 'fail': '✗', 'info': 'ℹ'}


class Command(BaseCommand):
    help = ('Kontrola IRIS FHIR: search parametry opravdu filtrují (IRIS neznámé tiše ignoruje), '
            'Patient/$everything, mCODE IG, $validate. Spouštět po ingest_dataset.')

    def add_arguments(self, parser):
        parser.add_argument('--patient', default='P03')

    def handle(self, *args, patient, **opts):
        try:
            checks = capabilities.run_checks(patient)
        except (OSError, fhir.FhirError) as e:
            raise CommandError(f'IRIS FHIR nedostupný ({fhir.base_url()}): {e}')
        self.stdout.write('| Kontrola | Výsledek | Detail |\n|---|---|---|')
        for c in checks:
            line = f'| `{c.name}` | {ICONS[c.status]} {c.status} | {c.detail} |'
            self.stdout.write(self.style.ERROR(line) if c.failed else line)
        failed = [c for c in checks if c.failed]
        if failed:
            raise CommandError(f'{len(failed)} kontrol selhalo: {", ".join(c.name for c in failed)}')
        self.stdout.write(self.style.SUCCESS('Všechny povinné kontroly prošly. Tabulku zapiš do ARCH §4.6 (T-313).'))
