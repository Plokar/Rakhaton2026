"""Šablony projektoru, doporučené údaje a pohled odbornosti ze znalostní báze `data/onko` (T-317 → T-318, T-319).

Referenční logika je v `data/onko/q.py` (`pick_template`, `recommend`, `role_view`). Tady dostane dokumenty
a fakta z FHIR resources pacienta (za běhu z IRIS), ne z bundlu datasetu. Bez báze (`ONKO_KB_DIR`) vrací
`None` nebo prázdný seznam a aplikace jede dál jen s povinnými údaji z `intake.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from services.rules.onko_kb import q

# Údaje báze, které už hlídá formulář zařazení (`intake.py`: pole) nebo red flags (`red_flags.py`).
# Povinný údaj báze (`P`) se v tom případě znovu nehlásí, jinak by lékař viděl dvě varování o tomtéž.
INTAKE_FIELDS = {
    "obc.otazka": "mdt.question", "obc.histologie": "dx.histology", "obc.tnm": "staging.tnm",
    "obc.zobrazeni": "staging.imaging", "obc.ecog": "ecog.physician", "obc.proms": "ecog.patient",
    "obc.komorbidity": "comorbidities", "obc.lecba": "treatment.history", "obc.preference": "preferences",
    "obc.alergie": "allergies", "obc.hmotnost": "weight", "obc.g8": "geri.g8",
    "pli.ct": "staging.chest_ct", "pli.pet": "staging.pet", "pli.mr_mozku": "staging.brain_mr",
    "pli.ebus": "staging.ebus", "pli.egfr": "bm.egfr", "pli.alk": "bm.alk", "pli.pdl1": "bm.pdl1",
    "pli.vo2max": "spiro.vo2max", "pli.sodik": "lab.na",
    "prs.receptory": "bm.her2", "prs.esr1": "bm.esr1", "prs.pik3ca": "bm.pik3ca", "prs.gbrca": "bm.gbrca",
    "krc.ras": "bm.ras", "krc.braf": "bm.braf", "krc.mmr": "bm.mmr", "krc.restaging": "staging.chest_ct",
    "krc.mr_jater": "staging.liver_mr", "krc.flr": "liver.flr", "krc.neuropatie": "tox.neuropathy",
}
# hlídá je pravidlo red flags, které běží u každého pacienta (`RF-MED`, `RF-PALIATIVE`, `RF-STEROID`, `RF-GENETIC`,
# `RF-LESION`, `RF-PRIOR-PROC`)
RED_FLAG_ITEMS = {"obc.medikace", "obc.paliativni", "obc.kortikoidy", "obc.rodinna_anamneza", "obc.histologie_loziska",
                  "obc.mozek", "obc.predchozi_vykony", "pli.lozisko"}


def _ids(column: str) -> list[str]:
    """Sloupec `zdroj` báze → Evidence ID (`PLI-2.1`, `RKT-04`, `EXT-…`)."""
    return [s for s in column.split(",") if s and s != "-"]


@dataclass
class PatientKb:
    """Podklady pacienta ve tvaru, se kterým počítá `q.py`: dokumenty (písmeno typu, ID, datum, název, text),
    kódy diagnóz, fakta pro podmínky `kdy` a datum MDT (věk dokumentu se počítá k němu)."""
    docs: list[dict]
    dg_codes: list[str]
    facts: dict
    mdt: str | None

    @classmethod
    def from_resources(cls, resources: Iterable[dict]) -> PatientKb | None:
        kb = q()
        if kb is None:
            return None
        resources = list(resources)
        docs = []
        for r in resources:
            letter = kb.FHIR_LETTER.get(r["resourceType"])
            if letter:
                label, body = kb._label_body(r)
                docs.append({"t": letter, "id": r["id"], "date": kb._date(r), "label": label, "body": body})
        raw = kb.bundle_facts(resources)
        mdt = raw.pop("_mdt", "") or None
        facts = {k: v if k == "dg" else kb.value(v) for k, v in raw.items()}
        return cls(docs, kb.codes(str(facts.pop("dg", ""))), facts, mdt)

    def items(self) -> list[dict]:
        return q().recommend(self.dg_codes, self.facts, self.docs, self.mdt)


def template_presets() -> list[dict]:
    """Všechny šablony báze jako presety `BriefConfig` (§8.5) pro `ensure_presets`."""
    kb = q()
    return [kb.template_config(t) for t in kb.kb()["sablony"]] if kb else []


def _projector_item(udaj: str, item: dict | None) -> dict:
    if item is None:                                   # údaj šablony pro tohoto pacienta neplatí (např. M1 vs. M0)
        row = next((u for u in q().kb()["udaje"] if u["udaj"] == udaj), {})
        return {"id": udaj, "label": row.get("nazev", udaj), "status": "not_applicable", "citations": []}
    out = {"id": udaj, "label": item["nazev"], "status": item["status"],
           "citations": list(item.get("ids", []))}
    if item.get("age") is not None:
        out["age_days"] = item["age"]
    return out


def case_template(resources: Iterable[dict]) -> dict | None:
    """Doporučená šablona projektoru podle diagnózy a situace pacienta (`CaseTemplate`, ARCH §6.3)."""
    patient = PatientKb.from_resources(resources)
    if patient is None or not patient.dg_codes:
        return None
    kb = q()
    template = kb.pick_template(patient.dg_codes, patient.facts)
    items = {i["udaj"]: i for i in patient.items()}
    return {
        "template_id": template["sablona"],
        "name": template["nazev"],
        "specialties": template["odbornosti"],
        "sources": _ids(template["zdroj"]),
        "config": kb.template_config(template),
        "projector": [_projector_item(u, items.get(u)) for u in template["zobrazit"].split(",") if u],
        "trials": [] if template["studie"] == "-" else template["studie"].split(","),
        "warnings": [i["warning"] for i in items.values() if "warning" in i],
    }


def recommended_warnings(resources: Iterable[dict], *, fields: Iterable[str] = (), skipped: Iterable[str] = ()) -> list[dict]:
    """Varování z katalogu údajů (`IntakeWarning`, §8.6) do formuláře zařazení.

    - `DOP:*` = doporučený údaj, který v podkladech chybí nebo je tam jen zmínka (severity `low`);
    - `CHYBI:*` = povinný údaj báze jen tam, kde ho ještě nehlídá pole formuláře (`fields` = jejich ID) ani red
      flag (severity `moderate`);
    - údaj v `skipped` (ID z báze, např. `pli.ros1`) lékař přeskočil, nehlásí se.
    Do readiness se nepočítají (počítá jen pole formuláře).
    """
    patient = PatientKb.from_resources(resources)
    if patient is None or not patient.dg_codes:
        return []
    field_ids, skipped = set(fields), set(skipped)
    out = []
    for item in patient.items():
        warning = item.get("warning")
        if warning is None or item["udaj"] in skipped:
            continue
        if item["uroven"] == "P" and (INTAKE_FIELDS.get(item["udaj"]) in field_ids or item["udaj"] in RED_FLAG_ITEMS):
            continue
        out.append(warning)
    return out


def view_for(role: str, resources: Iterable[dict]) -> dict | None:
    """Co jde lékaři dané odbornosti nahoru (T-319, `odbornosti.tsv`): sekce, jeho údaje a postupy.

    Souhrn zůstává první (ARCH §7.3); hlavička se neřadí, je vždy nahoře.
    """
    patient = PatientKb.from_resources(resources)
    if patient is None or not patient.dg_codes:
        return None
    kb = q()
    view = kb.role_view(role, patient.dg_codes, patient.facts, patient.items())
    mine = view["moje"]
    tags = ",".join(view["tagy"])
    return {
        "role": role,
        "template_id": view["sablona"],
        "sections": view["sekce"],
        "items": [{**_projector_item(i["udaj"], i), **({"warning": i["warning"]} if "warning" in i else {})}
                  for i in view["udaje"] if i["udaj"] in mine],
        "procedures": [{"id": p["postup"], "title": p["nazev"],
                        "sources": _ids(p["zdroj"])}
                       for p in view["postupy"] if kb.tag_match(tags, p["tagy"].split(","))],
        "interests": [{"specialty": o["odbornost"], "what": o["zajima"], "why": o["proc"],
                       "sources": _ids(o["zdroj"])} for o in view["zajima"]],
    }
