"""Rodné číslo (RČ): kontrola a odvození data narození a pohlaví (nový pacient, T-322).

RČ se zadává jen při založení pacienta. V IRIS je jako `Patient.identifier` (systém ÚZIS), aplikace ho ve
výstupech ukazuje jen maskované a do LLM se nedostane (`pseudonymize`, context builder identifikátory nečte).

Pravidla (zákon 133/2000 Sb.): `RRMMDD/XXX` do roku 1953, `RRMMDD/XXXX` od roku 1954. Ženy mají měsíc +50,
od roku 2004 smí být měsíc ještě +20 (vyčerpaná řada). Desetimístné číslo je dělitelné 11; výjimka do roku 1985:
zbytek prvních devíti číslic po dělení 11 je 10 a kontrolní číslice 0.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

SYSTEM = "https://ncez.mzcr.cz/fhir/sid/rcis"        # identifikátor RČ v českém FHIR (ÚZIS)
_FORMAT = re.compile(r"^\s*(\d{6})\s*/?\s*(\d{3,4})\s*$")


class RcError(ValueError):
    pass


@dataclass(frozen=True)
class RodneCislo:
    value: str                  # normalizované „RRMMDD/XXXX“
    birth_date: date
    gender: str                 # FHIR: "male" | "female"

    @property
    def masked(self) -> str:
        """Pro výstupy API: jen poslední 4 číslice („******/1234“)."""
        return "******/" + self.value.split("/")[1]

    def age_at(self, day: date) -> int:
        return day.year - self.birth_date.year - ((day.month, day.day) < (self.birth_date.month, self.birth_date.day))


def parse(raw: str) -> RodneCislo:
    """`RodneCislo` z textu, nebo `RcError` s důvodem (česky, jde rovnou do odpovědi API)."""
    m = _FORMAT.match(raw or "")
    if not m:
        raise RcError("Rodné číslo má tvar RRMMDD/XXXX (do roku 1953 RRMMDD/XXX).")
    head, tail = m[1], m[2]
    yy, mm, dd = int(head[:2]), int(head[2:4]), int(head[4:6])
    if len(tail) == 3:
        if yy >= 54:
            raise RcError("Devítimístné rodné číslo mají jen lidé narození do roku 1953.")
        year = 1900 + yy
    else:
        year = 2000 + yy if yy < 54 else 1900 + yy
        number = int(head + tail)
        if number % 11 and not (int(head + tail[:3]) % 11 == 10 and tail[3] == "0" and year < 1986):
            raise RcError("Rodné číslo nemá platnou kontrolní číslici.")
    gender = "female" if mm > 50 else "male"
    month = mm - 50 if mm > 50 else mm
    if month > 20 and year >= 2004:
        month -= 20
    try:
        born = date(year, month, dd)
    except ValueError:
        raise RcError("Rodné číslo neobsahuje platné datum narození.") from None
    if born > date.today():
        raise RcError("Datum narození z rodného čísla je v budoucnosti.")
    return RodneCislo(f"{head}/{tail}", born, gender)


def is_valid(raw: str) -> bool:
    try:
        parse(raw)
    except RcError:
        return False
    return True
