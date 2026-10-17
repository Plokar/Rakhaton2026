"""
Pseudonymizace volného textu před odesláním do LLM (ARCHITEKTURA §5.7, NFR-3).

Dataset PII neobsahuje (pacient = ID, lékaři = kódy `LEK-…`), pipeline ale stavíme jako
pro reálná data. Strukturovaná pole s PII (jméno, RČ, datum narození, adresa, kontakty)
context builder vůbec nečte; tady se čistí volný text zpráv, poznámek a dotazníků:

- známá jména (pacient, lékaři) → jejich ID (`P03`, `LEK-P03-01`);
- rodné číslo, e-mail, telefon, datum narození → zástupný text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from services import rc

_RC_SLASH = re.compile(r"(?<![\d/])\d{6}\s?/\s?\d{3,4}(?![\d/])")
_RC_PLAIN = re.compile(r"(?<!\d)\d{10}(?!\d)")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_PHONE = re.compile(r"(?<![\d+])(?:\+420[ -]?)?[2-7]\d{2}[ -]\d{3}[ -]\d{3}(?!\d)|\+420\d{9}(?!\d)")
_BIRTH = re.compile(r"\b(?:nar\.|narozen[aáý]?|datum narození)\s*:?\s*\d{1,2}\.\s?\d{1,2}\.\s?\d{4}", re.IGNORECASE)
MIN_NAME_LENGTH = 5     # kratší „jména“ by nahrazovala běžná slova


def _valid_rc(digits: str) -> bool:
    """Desetimístné číslo je platné RČ (kontrolní číslice, datum, ženy +50, řady +20; `services/rc.py`)."""
    return rc.is_valid(digits)


@dataclass
class Pseudonymizer:
    """Nahrazuje známá jména jejich ID a vzory PII zástupným textem; počítá náhrady (audit)."""

    names: dict[str, str] = field(default_factory=dict)   # jméno → ID
    replacements: int = 0

    def add_name(self, name: str | None, replacement: str) -> None:
        if name and len(name.strip()) >= MIN_NAME_LENGTH:
            self.names[name.strip()] = replacement

    def __call__(self, text: str | None) -> str:
        if not text:
            return text or ""
        for name in sorted(self.names, key=len, reverse=True):
            text = self._sub(re.compile(re.escape(name), re.IGNORECASE), self.names[name], text)
        text = self._sub(_BIRTH, "[datum narození]", text)
        text = self._sub(_RC_SLASH, "[RČ]", text)
        text = self._sub(_RC_PLAIN, lambda m: "[RČ]" if _valid_rc(m.group(0)) else m.group(0), text)
        text = self._sub(_EMAIL, "[e-mail]", text)
        text = self._sub(_PHONE, "[telefon]", text)
        return text

    def _sub(self, pattern: re.Pattern, repl, text: str) -> str:
        def replace(match: re.Match) -> str:
            new = repl(match) if callable(repl) else repl
            if new != match.group(0):
                self.replacements += 1
            return new
        return pattern.sub(replace, text)


def pseudonymize_text(text: str | None, names: dict[str, str] | None = None) -> str:
    pseudonymizer = Pseudonymizer()
    for name, replacement in (names or {}).items():
        pseudonymizer.add_name(name, replacement)
    return pseudonymizer(text)
