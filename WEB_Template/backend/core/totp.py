"""TOTP (RFC 6238) pro dvoufázové přihlášení (T-383): 6 číslic, krok 30 s, HMAC-SHA1 jako Google/Microsoft
Authenticator. Bez další závislosti; tajemství se ukládá šifrované (`core.crypto.EncryptedCharField`)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

STEP = 30
DIGITS = 6
WINDOW = 1          # ±1 krok (hodiny telefonu se mohou o desítky sekund lišit)


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')


def code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret + '=' * (-len(secret) % 8), casefold=True)
    digest = hmac.new(key, struct.pack('>Q', step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10 ** DIGITS).zfill(DIGITS)


def verify(secret: str, code: str, *, last_step: int | None = None, now: float | None = None) -> int | None:
    """Krok, ke kterému kód patří, nebo `None`. Kód z kroku ≤ `last_step` se odmítne (nejde použít dvakrát)."""
    code = (code or '').replace(' ', '')
    if not secret or len(code) != DIGITS or not code.isdigit():
        return None
    current = int((now if now is not None else time.time()) // STEP)
    for step in range(current - WINDOW, current + WINDOW + 1):
        if (last_step is None or step > last_step) and hmac.compare_digest(code_at(secret, step), code):
            return step
    return None


def otpauth_uri(secret: str, account: str, issuer: str = 'MDTcore') -> str:
    return (f'otpauth://totp/{quote(issuer)}:{quote(account)}?secret={secret}&issuer={quote(issuer)}'
            f'&algorithm=SHA1&digits={DIGITS}&period={STEP}')
