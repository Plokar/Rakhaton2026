"""Idempotentně založí FHIR server v IRIS a Device/mdt-copilot (ARCH §4.2, podle kitu fhir_server_setup_native.py)."""
import os
import time

import iris
from django.core.management.base import BaseCommand, CommandError

from services.fhir import client as fhir
from services.iris.db import connect

NAMESPACE = 'FHIRSERVER'
ENDPOINT = '/fhir/r4'


class Command(BaseCommand):
    help = 'Založí namespace FHIRSERVER, FHIR endpoint /fhir/r4 a Device/mdt-copilot. Opakované spuštění nic nemění.'

    def add_arguments(self, parser):
        parser.add_argument('--wait', type=int, default=120, help='kolik sekund čekat, než IRIS naběhne')

    def handle(self, *args, wait, **options):
        self._wait_for_iris(wait)

        with connect('HSLIB') as conn:
            irispy = iris.createIRIS(conn)
            if not irispy.classMethodBoolean('%SYS.Namespace', 'Exists', NAMESPACE):
                self.stdout.write(f'Zakládám namespace {NAMESPACE}…')
                irispy.classMethodVoid('HS.Util.Installer.Foundation', 'Install', NAMESPACE)

        with connect(NAMESPACE) as conn:
            irispy = iris.createIRIS(conn)
            if irispy.classMethodBoolean('HS.FHIRServer.ServiceInstance', 'ExistsByUrl', ENDPOINT):
                self.stdout.write(f'FHIR endpoint {ENDPOINT} už existuje.')
            else:
                self.stdout.write(f'Zakládám FHIR endpoint {ENDPOINT} (trvá 1–2 min)…')
                irispy.classMethodVoid('HS.FHIRServer.Installer', 'InstallNamespace')
                irispy.classMethodVoid(
                    'HS.FHIRServer.Installer', 'InstallInstance', ENDPOINT,
                    'HS.FHIRServer.Storage.JsonAdvSQL.InteractionsStrategy', 'hl7.fhir.r4.core@4.0.1',
                )

        self._put_device()
        self.stdout.write(self.style.SUCCESS('IRIS FHIR server je připravený.'))

    def _wait_for_iris(self, timeout):
        deadline = time.monotonic() + timeout
        while True:
            try:
                with connect('%SYS'):
                    return
            except Exception as e:
                if time.monotonic() > deadline:
                    raise CommandError(f'IRIS nedostupný po {timeout} s: {e}')
                time.sleep(2)

    def _put_device(self):
        fhir.put({
            'resourceType': 'Device',
            'id': 'mdt-copilot',
            'deviceName': [{'name': 'MDT Copilot', 'type': 'user-friendly-name'}],
            'version': [{'value': os.environ.get('AI_MODEL', 'gemini-3.8-flash')}],
        })
        self.stdout.write('PUT Device/mdt-copilot OK')
