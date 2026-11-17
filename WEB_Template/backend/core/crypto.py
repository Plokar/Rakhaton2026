"""Šifrování citlivých polí v Postgresu (T-379): rodné číslo v návrhu pacienta.

Klíč: `MDT_FIELD_KEY` (Fernet, `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`),
jinak odvozený z `SECRET_KEY`. Hledá se přes `digest` (HMAC-SHA256), šifrovaný text se porovnat nedá.
Výměna `SECRET_KEY` bez `MDT_FIELD_KEY` znamená, že staré návrhy RČ nepřečtou: proto v produkci nastavte `MDT_FIELD_KEY`.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

PREFIX = 'enc1:'


def _key() -> bytes:
    raw = os.environ.get('MDT_FIELD_KEY', '').strip()
    if raw:
        return raw.encode()
    return base64.urlsafe_b64encode(hashlib.sha256(f'mdt-field:{settings.SECRET_KEY}'.encode()).digest())


def encrypt(value: str) -> str:
    if not value:
        return ''
    return PREFIX + Fernet(_key()).encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value or not value.startswith(PREFIX):
        return value or ''                         # starý nešifrovaný záznam se přečte, při uložení se zašifruje
    try:
        return Fernet(_key()).decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken:
        return ''                                  # jiný klíč: údaj nejde přečíst, ale aplikace nespadne


def digest(value: str) -> str:
    """Stálý otisk pro vyhledání („je už návrh s tímto RČ?“) bez dešifrování."""
    if not value:
        return ''
    return hmac.new(_key(), value.encode(), hashlib.sha256).hexdigest()


class EncryptedCharField(models.TextField):
    """Text v Postgresu zašifrovaný (Fernet); v Pythonu se pracuje s čistou hodnotou."""

    def from_db_value(self, value, expression, connection):
        return decrypt(value) if value is not None else value

    def to_python(self, value):
        return decrypt(value) if isinstance(value, str) else value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt(value) if value else (value or '')
