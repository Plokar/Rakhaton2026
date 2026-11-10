"""Hledání pacienta při zařazení podle RČ, jména nebo Pxx (T-356, ARCH §6.3).

Jméno a RČ vrací jen tento endpoint pro dialog přidání pacienta (lékař ověří, že přidává správného člověka).
Hlavička případu, projektor, podklad, chat i export dál ukazují `Pxx · pohlaví · věk` (D-018).
RČ nesmí do URL ani do logů: frontend posílá dotaz v těle `POST /api/patients/search/`, `GET ?q=` RČ odmítne.

Hledá se ve FHIR přes IRIS (`Patient?identifier=`, `Patient?name=`). IRIS neznámé search parametry tiše
ignoruje, a proto se každý výsledek ještě ověří v kódu (přesná shoda RČ, všechna slova dotazu ve jméně).
"""
from __future__ import annotations

import re
import unicodedata

from services import rc as rc_module
from services.fhir import client as fhir
from services.fhir.client import FhirError
from services.fhir.values import ext_value

LIMIT = 20
SEX_CS = {'male': 'muž', 'female': 'žena', 'other': 'jiné', 'unknown': 'neuvedeno'}
_PID = re.compile(r'^[Pp]\s*0*(\d{1,3})$')
_RC_DIGITS = re.compile(r'^\d{9,10}$')
# Pacientovi stačí Patient: jméno, identifikátory, pohlaví a věk (víc nepotřebujeme a nenačítáme)
_ELEMENTS = 'id,name,identifier,gender,birthDate,extension'     # IRIS bez `id` v seznamu vrací resource bez id


class QueryKind:
    PID, RC, NAME = 'pid', 'rc', 'name'


def fold(text: str) -> str:
    """Malá písmena bez diakritiky („Nováková“ → „novakova“)."""
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold()) if not unicodedata.combining(c))


def looks_like_rc(q: str) -> bool:
    """Dotaz vypadá jako RČ (číslice, případně s lomítkem a mezerami): takový nesmí do URL ani do logu."""
    return bool(re.fullmatch(r'[\d\s/]+', q or '')) and sum(c.isdigit() for c in q) >= 6


def classify(q: str) -> tuple[str, str] | None:
    """(druh, normalizovaný dotaz), nebo None, když je dotaz moc krátký na hledání."""
    q = (q or '').strip()
    if m := _PID.match(q):
        return QueryKind.PID, f'P{int(m[1]):02d}'
    digits = re.sub(r'[\s/]', '', q)
    if digits.isdigit():
        return (QueryKind.RC, f'{digits[:6]}/{digits[6:]}') if _RC_DIGITS.match(digits) else None
    words = fold(q).split()
    return (QueryKind.NAME, ' '.join(words)) if len(''.join(words)) >= 2 else None


def search(q: str) -> list[dict]:
    """Nejvýš `LIMIT` pacientů podle RČ (s lomítkem i bez), části jména (bez diakritiky a velikosti písmen) nebo Pxx."""
    parsed = classify(q)
    if not parsed:
        return []
    kind, value = parsed
    if kind == QueryKind.PID:
        try:
            found = [fhir.read('Patient', value)]
        except FhirError as e:
            if e.status in (404, 410):
                return []
            raise
        match = lambda p: p.get('id') == value                                       # noqa: E731
    elif kind == QueryKind.RC:
        found = fhir.search('Patient', identifier=value, _elements=_ELEMENTS)
        match = lambda p: rc_value(p) == value                                       # noqa: E731
    else:
        words = value.split()
        # IRIS: `name` = začátek slova jména, bez ohledu na velikost písmen; diakritiku dotazu pro jistotu zkusíme
        # i bez ní a výsledky dofiltrujeme v kódu (všechna slova dotazu musí být ve jméně bez diakritiky)
        longest = max(words, key=len)
        found = fhir.search('Patient', name=longest, _elements=_ELEMENTS)
        if not found:
            found = _all_patients()
        match = lambda p: all(w in fold(name_text(p)) for w in words)              # noqa: E731
    out = [item(p) for p in found if p.get('resourceType') == 'Patient' and match(p)]
    out.sort(key=lambda r: (r['name'] or '', _pid_key(r['id'])))
    return out[:LIMIT]


def _all_patients() -> list[dict]:
    # ponytail: když IRIS nenajde jméno (jiná diakritika než v dotazu), projdeme Patient bez dalších dat; demo má
    # stovky pacientů, při desítkách tisíc by to chtělo index jména bez diakritiky (SQL pohled nad HSFHIR)
    return fhir.search('Patient', _elements=_ELEMENTS)


def name_text(patient: dict) -> str:
    for n in patient.get('name', []):
        text = n.get('text') or ' '.join([*n.get('given', []), n.get('family', '')]).strip()
        if text:
            return text
    return ''


def rc_value(patient: dict) -> str | None:
    """RČ z `Patient.identifier` (ÚZIS i fiktivní systém demo dat), normalizované `RRMMDD/XXXX`."""
    for i in patient.get('identifier', []):
        if i.get('system') in rc_module.SYSTEMS and i.get('value'):
            digits = re.sub(r'\D', '', i['value'])
            return f'{digits[:6]}/{digits[6:]}'
    return None


def item(patient: dict) -> dict:
    pid, sex = patient['id'], patient.get('gender', 'unknown')
    age = ext_value(patient, 'vek-k-datu-mdt')
    label = f'{pid} · {SEX_CS.get(sex, sex)}' + (f' · {age} let' if age is not None else '')
    return {'id': pid, 'display_name': label, 'sex': sex, 'age': age,
            'name': name_text(patient) or None, 'rc': rc_value(patient), 'birth_date': patient.get('birthDate')}


def _pid_key(pid: str) -> tuple:
    return (0, int(pid[1:]), '') if re.fullmatch(r'P\d+', pid) else (1, 0, pid)
