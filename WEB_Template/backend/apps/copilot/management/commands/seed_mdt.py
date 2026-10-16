"""Boardy (MdtSession) a případy (MdtCase) z nominací v IRIS (T-109, ARCH §6.2). Idempotentní."""
from django.core.management.base import BaseCommand

from apps.mdt.models import MdtCase, MdtSession
from services.mdt_seed import load_nominations


class Command(BaseCommand):
    help = 'Založí zasedání MDT a případy z ServiceRequest + Task v IRIS. Přesunutý případ nechá na novém boardu.'

    def handle(self, *args, **options):
        created_sessions = created_cases = 0
        for order, n in enumerate(load_nominations()):
            session, new = MdtSession.objects.get_or_create(date=n['date'], title=n['title'])
            created_sessions += new
            _, new = MdtCase.objects.get_or_create(
                service_request_fhir_id=n['service_request_id'],
                defaults={'session': session, 'patient_fhir_id': n['patient_id'], 'question': n['question'],
                          'order': order},
            )
            created_cases += new
        self.stdout.write(self.style.SUCCESS(
            f'Boardy: {MdtSession.objects.count()} (nové {created_sessions}), '
            f'případy: {MdtCase.objects.count()} (nové {created_cases}).'
        ))
