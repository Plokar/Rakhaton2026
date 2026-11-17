"""Worker generování (T-383): `manage.py run_job_worker` bere joby z Redisu (`MDT_JOB_BACKEND=redis`).

Běží jako samostatná služba (docker-compose profil `worker`). SIGTERM dokončí rozběhnutý job a skončí.
"""
import signal

from django.core.management.base import BaseCommand

from apps.copilot import jobs


class Command(BaseCommand):
    help = 'Spouští joby generování z fronty v Redisu (MDT_JOB_BACKEND=redis).'

    def handle(self, *args, **options):
        stopping = {'now': False}

        def stop(*_):
            stopping['now'] = True
            self.stdout.write('Worker končí po rozběhnutém jobu…')

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        jobs.fail_stale()                       # joby po pádu předchozího workeru → error (T-368)
        self.stdout.write(f'Worker generování čeká na joby ({jobs.QUEUE}).')
        done = jobs.work_forever(lambda: stopping['now'])
        self.stdout.write(f'Worker skončil, zpracováno {done} jobů.')
