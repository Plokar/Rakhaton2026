"""Klíče VAPID pro push oznámení (T-383): `manage.py vapid_keys` vypíše řádky do `.env` (soukromý klíč necommitovat)."""
from cryptography.hazmat.primitives import serialization
from django.core.management.base import BaseCommand
from py_vapid import Vapid01, b64urlencode


class Command(BaseCommand):
    help = 'Vytvoří pár klíčů VAPID pro Web Push (VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY).'

    def handle(self, *args, **options):
        vapid = Vapid01()
        vapid.generate_keys()
        public = b64urlencode(vapid.public_key.public_bytes(serialization.Encoding.X962,
                                                           serialization.PublicFormat.UncompressedPoint))
        private = b64urlencode(vapid.private_key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                                                               serialization.NoEncryption()))
        self.stdout.write('# do .env backendu (VAPID_PRIVATE_KEY je tajný, nikdy do gitu)')
        self.stdout.write(f'VAPID_PUBLIC_KEY={public}')
        self.stdout.write(f'VAPID_PRIVATE_KEY={private}')
        self.stdout.write('VAPID_SUBJECT=mailto:spravce@vase-nemocnice.cz')
