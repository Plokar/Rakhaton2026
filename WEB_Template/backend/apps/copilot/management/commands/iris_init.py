"""Idempotentně založí FHIR server v IRIS a Device/mdt-copilot (ARCH §4.2, podle kitu fhir_server_setup_native.py)."""
import os
import time

import iris
from django.core.management.base import BaseCommand, CommandError

from services.fhir import client as fhir
from services.iris.db import DEFAULT_PASSWORD, connect

NAMESPACE = 'FHIRSERVER'
ENDPOINT = '/fhir/r4'
# předdefinované účty s výchozím heslem SYS; CSPSystem ne (používá ho web gateway portálu)
PREDEFINED_USERS = ('SuperUser', 'Admin', '_SYSTEM')


class Command(BaseCommand):
    help = 'Založí namespace FHIRSERVER, FHIR endpoint /fhir/r4 a Device/mdt-copilot. Opakované spuštění nic nemění.'

    def add_arguments(self, parser):
        parser.add_argument('--wait', type=int, default=120, help='kolik sekund čekat, než IRIS naběhne')

    def handle(self, *args, wait, **options):
        self._wait_for_iris(wait)
        self._rotate_default_password()

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
        try:                                       # T-309: SQL projekce Observation (pohled nad FHIR úložištěm)
            from services.iris import projections
            projections.ensure_view()
            self.stdout.write(f'SQL pohled {projections.VIEW} je připravený.')
        except Exception as exc:                   # bez pohledu aplikace běží dál (REST cesta)
            self.stderr.write(f'SQL pohled {projections.VIEW} se nepodařilo založit: {exc}')
        self.stdout.write(self.style.SUCCESS('IRIS FHIR server je připravený.'))

    def _wait_for_iris(self, timeout):
        """Čeká na IRIS s heslem z env, nebo s výchozím SYS (čerstvý kontejner před změnou hesla, T-005)."""
        deadline = time.monotonic() + timeout
        while True:
            for password in dict.fromkeys((None, DEFAULT_PASSWORD)):
                try:
                    with connect('%SYS', password=password):
                        return
                except Exception as e:
                    error = e
            if time.monotonic() > deadline:
                raise CommandError(f'IRIS nedostupný po {timeout} s: {error}')
            time.sleep(2)

    def _rotate_default_password(self):
        """Produkce (ARCH §3.4): výchozí heslo SYS → IRIS_PASSWORD u předdefinovaných účtů. Idempotentní."""
        password = os.environ.get('IRIS_PASSWORD', DEFAULT_PASSWORD)
        if password == DEFAULT_PASSWORD:
            return
        try:
            with connect('%SYS'):
                return                              # heslo už platí
        except Exception:
            pass
        with connect('%SYS', password=DEFAULT_PASSWORD) as conn:
            irispy = iris.createIRIS(conn)
            for user in PREDEFINED_USERS:
                if not irispy.classMethodValue('%SYSTEM.Security', 'ChangePassword', user, password, DEFAULT_PASSWORD):
                    raise CommandError(f'IRIS: heslo účtu {user} se nepodařilo změnit.')
        self.stdout.write(f'Výchozí heslo IRIS změněno ({", ".join(PREDEFINED_USERS)}).')

    def _put_device(self):
        fhir.put({
            'resourceType': 'Device',
            'id': 'mdt-copilot',
            'deviceName': [{'name': 'MDT Copilot', 'type': 'user-friendly-name'}],
            'version': [{'value': os.environ.get('AI_MODEL', 'gemini-3.8-flash')}],
        })
        self.stdout.write('PUT Device/mdt-copilot OK')
