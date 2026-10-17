"""Lékaři nemocnice z IRIS (FHIR `Practitioner`) pro výběr přítomných, vlastníků úkolů a spolupracovníků (T-328).

IRIS je nemocniční databáze, takže seznam lékařů je v ní. Účet aplikace je s lékařem propojený
(`UserProfile.practitioner_fhir_id`); demo účtům a nově registrovaným se lékař `LEK-APP-…` založí.
"""
from __future__ import annotations

import re
import unicodedata

from services.fhir import client as fhir

APP_PREFIX = "LEK-APP-"
APP_SYSTEM = "https://rakathon.example.org/fhir/sid/uzivatel-mdt-copilot"
# odbornost z textu kvalifikace → RoleId (§8.1); pořadí: specifičtější dřív („radiační onkolog“ před „onkolog“)
ROLE_KEYWORDS = (("radiační onkolog", "radiation_oncologist"), ("radioterap", "radiation_oncologist"),
                 ("onkolog", "oncologist"), ("chirurg", "surgeon"), ("radiolog", "radiologist"),
                 ("patolog", "pathologist"), ("pneumolog", "pulmonologist"), ("kardiolog", "cardiologist"),
                 ("nukleární", "nuclear_medicine"), ("paliativ", "palliative_care"), ("geriatr", "geriatrician"),
                 ("genetik", "geneticist"), ("koordinát", "coordinator"))
ROLE_LABEL = {"oncologist": "klinický onkolog", "surgeon": "chirurg", "radiation_oncologist": "radiační onkolog",
              "radiologist": "radiolog", "pathologist": "patolog", "pulmonologist": "pneumolog",
              "cardiologist": "kardiolog", "nuclear_medicine": "nukleární medicína",
              "palliative_care": "paliativní péče", "geriatrician": "geriatr", "geneticist": "klinický genetik",
              "coordinator": "koordinátor"}


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


def _name(p: dict) -> str:
    name = (p.get("name") or [{}])[0]
    return name.get("text") or " ".join(name.get("given", []) + [name.get("family", "")]).strip() or p["id"]


def _qualification(p: dict) -> str:
    q = (p.get("qualification") or [{}])[0].get("code") or {}
    return q.get("text") or next((c.get("display", "") for c in q.get("coding", [])), "")


def role_for(text: str) -> str | None:
    """Odbornost (RoleId) z textu kvalifikace; neznámá = `None` (lékař ji vybere sám)."""
    low = text.lower()
    return next((role for word, role in ROLE_KEYWORDS if word in low), None)


def entry(p: dict, users: dict[str, dict] | None = None) -> dict:
    specialty = _qualification(p)
    return {"id": p["id"], "name": _name(p), "specialty": specialty, "role": role_for(specialty or _name(p)),
            "user": (users or {}).get(p["id"])}


def directory(users: dict[str, dict] | None = None) -> list[dict]:
    """Všichni lékaři v IRIS; nejdřív ti s účtem v aplikaci, pak podle jména."""
    items = [entry(p, users) for p in fhir.search("Practitioner") if p.get("active", True)]
    return sorted(items, key=lambda x: (x["user"] is None, _plain(x["name"])))


def search(query: str, users: dict[str, dict] | None = None, limit: int = 50) -> list[dict]:
    """Hledání bez ohledu na diakritiku a velikost písmen ve jménu, odbornosti a ID; všechna slova musí sedět."""
    words = [w for w in _plain(query or "").split() if w]
    items = directory(users)
    if words:
        items = [x for x in items if all(w in _plain(f"{x['name']} {x['specialty']} {x['id']}") for w in words)]
    return items[:limit]


def app_practitioner_id(username: str) -> str:
    """ID lékaře pro účet aplikace (`LEK-…` = Practitioner podle konvence ID, `services/fhir/ids.py`)."""
    slug = re.sub(r"[^A-Za-z0-9-]", "-", username).strip("-") or "uzivatel"
    return f"{APP_PREFIX}{slug}"[:64]


def app_practitioner(practitioner_id: str, name: str, role: str | None, username: str) -> dict:
    out = {"resourceType": "Practitioner", "id": practitioner_id, "active": True,
           "identifier": [{"system": APP_SYSTEM, "value": username}], "name": [{"text": name}]}
    if role in ROLE_LABEL:
        out["qualification"] = [{"code": {"text": ROLE_LABEL[role]}}]
    return out


def exists(practitioner_id: str) -> bool:
    try:
        fhir.read("Practitioner", practitioner_id)
    except fhir.FhirError as e:
        if e.status in (404, 410):
            return False
        raise
    return True
