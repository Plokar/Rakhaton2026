"""Backend bez Dockeru a bez IRIS (T-367): Django + FHIR a IRIS SQL v paměti, mock AI.

Jen pro lokální vývoj, proklikání a E2E testy (T-378). Potřebuje Postgres a Redis (výchozí 127.0.0.1).
Stav FHIR a vektorů je v paměti procesu, proto jeden proces a ``runserver --noreload``.

    cd WEB_Template/backend && python scripts/run_local.py        # nebo ./dev.sh local

Proměnné prostředí: ``POSTGRES_*``, ``REDIS_URL``, ``LOCAL_PORT`` (výchozí 8000), ``LOCAL_PATIENTS``
(např. ``P01,P03`` pro rychlejší start; výchozí všichni včetně demo pacientů).
"""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

DEFAULTS = {
    'DJANGO_SETTINGS_MODULE': 'config.settings_dev',
    'DJANGO_DEBUG': 'True',
    'DJANGO_SECRET_KEY': 'dev-secret-key-change-in-production-min-50-chars-long',
    'POSTGRES_DB': 'appdb_dev',
    'POSTGRES_USER': 'appuser',
    'POSTGRES_PASSWORD': 'devpassword123',
    'POSTGRES_HOST': '127.0.0.1',
    'POSTGRES_PORT': '5432',
    'REDIS_URL': 'redis://:devredispass@127.0.0.1:6379',
    'IRIS_HOST': 'in-memory',
}
for name, value in DEFAULTS.items():
    os.environ.setdefault(name, value)
# Nic nesmí odejít ven ani s klíči v .env (AGENTS.md): vynuceno, ne jen výchozí.
os.environ['AI_PROVIDER'] = 'mock'
os.environ['VERIFIER_PROVIDER'] = 'off'

if os.environ['DJANGO_SETTINGS_MODULE'] != 'config.settings_dev':
    sys.exit('run_local.py běží jen s config.settings_dev (data v paměti nejsou pro pilot ani produkci).')


def main() -> None:
    import django
    django.setup()

    from django.conf import settings
    from django.core.management import call_command

    settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'   # bez Mailhogu: pozvánky do výpisu

    from services.fhir import client
    from services.fhir.testing import FakeFhirServer
    from services.iris import db
    from services.iris.testing import FakeIris

    fhir, iris = FakeFhirServer(), FakeIris()
    client.request = fhir.request
    db.connect = iris.connect

    call_command('migrate', interactive=False, verbosity=0)
    ingest = {'patients': os.environ['LOCAL_PATIENTS']} if os.environ.get('LOCAL_PATIENTS') else {}
    call_command('ingest_dataset', **ingest)
    call_command('seed_mdt')
    from apps.mdt.models import MdtCase
    orphans = sorted({c for c in MdtCase.objects.values_list('patient_fhir_id', flat=True)
                      if f'Patient/{c}' not in fhir.store})
    if orphans:      # Postgres přežívá restart, FHIR v paměti ne: případy z dřívějšího běhu s víc pacienty
        print(f'POZOR: {len(orphans)} pacientů má případ v Postgresu, ale není ve FHIR (např. {orphans[0]}); '
              'jejich obrazovky vrátí 404. Spusťte bez LOCAL_PATIENTS, nebo s čistou databází.', flush=True)
    print(f'FHIR v paměti: {len(fhir.store)} záznamů. Přihlášení: predseda / demo123456', flush=True)
    call_command('runserver', f"0.0.0.0:{os.environ.get('LOCAL_PORT', '8000')}", '--noreload')


if __name__ == '__main__':
    main()
