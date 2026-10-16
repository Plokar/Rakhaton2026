"""Boardy (MdtSession) a případy (MdtCase) z nominací v IRIS (T-109, ARCH §6.2). Idempotentní."""
from django.core.management.base import BaseCommand

from apps.mdt import roles
from apps.mdt.models import MdtCase, MdtSession
from services.mdt_seed import load_nominations


class Command(BaseCommand):
    help = 'Demo účty a role, zasedání MDT a případy z ServiceRequest + Task v IRIS. Přesunutý případ nechá na novém boardu.'

    def handle(self, *args, **options):
        users = roles.ensure_demo_users()
        created_sessions = created_cases = 0
        for order, n in enumerate(load_nominations()):
            session, new = MdtSession.objects.get_or_create(date=n['date'], title=n['title'],
                                                            defaults={'chair': users['predseda']})
            created_sessions += new
            requester = users[roles.REQUESTER_BY_PATIENT.get(n['patient_id'], roles.DEFAULT_REQUESTER)]
            _, new = MdtCase.objects.get_or_create(
                service_request_fhir_id=n['service_request_id'],
                defaults={'session': session, 'patient_fhir_id': n['patient_id'], 'question': n['question'],
                          'order': order, 'created_by': requester},
            )
            created_cases += new
        # doplní chybějící (případy a boardy z dřívějšího běhu bez demo účtů), nic nepřepisuje
        MdtSession.objects.filter(chair__isnull=True).update(chair=users['predseda'])
        for case in MdtCase.objects.filter(created_by__isnull=True):
            case.created_by = users[roles.REQUESTER_BY_PATIENT.get(case.patient_fhir_id, roles.DEFAULT_REQUESTER)]
            case.save(update_fields=['created_by'])
        self.stdout.write(self.style.SUCCESS(
            f'Boardy: {MdtSession.objects.count()} (nové {created_sessions}), '
            f'případy: {MdtCase.objects.count()} (nové {created_cases}).'
        ))
