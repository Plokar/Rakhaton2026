"""Záloha a reset dema (T-311): `python manage.py demo save|load|reset [P03]`."""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.copilot import demo
from apps.mdt.models import MdtCase


class Command(BaseCommand):
    help = ('save = poslední podklad pacienta do data/demo_cache; load = podklad z cache do případu; '
            'reset = IRIS a případ do stavu před demem (smaže zápisy aplikace, znovu nahraje pacienta, seed_mdt, load).')

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['save', 'load', 'reset'])
        parser.add_argument('patient', nargs='?', default='P03')

    def handle(self, action, patient, **options):
        if action == 'reset':
            result = demo.reset_patient(patient)
            self.stdout.write(f"IRIS: smazáno {len(result['deleted_fhir'])} zápisů aplikace, znovu nahráno "
                              f"{result['reingested']} resources; Postgres: smazáno {result['deleted_cases']} objektů.")
            call_command('seed_mdt', stdout=self.stdout)
        case = MdtCase.objects.filter(patient_fhir_id=patient).first()
        if case is None:
            raise CommandError(f'Případ {patient} neexistuje (spusť seed_mdt).')
        if action == 'save':
            brief = case.briefs.first()
            if brief is None:
                raise CommandError(f'{patient} nemá vygenerovaný podklad.')
            self.stdout.write(self.style.SUCCESS(f'Uloženo: {demo.save_cache(patient, brief.content)} ({brief.model})'))
        elif demo.load_into_case(case):
            self.stdout.write(self.style.SUCCESS(f'Podklad {patient} načten z {demo.cache_path(patient)}.'))
        else:
            self.stdout.write(f'Cache {demo.cache_path(patient)} není, podklad se vygeneruje normálně.')
