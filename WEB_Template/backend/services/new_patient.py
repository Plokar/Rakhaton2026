"""Nový pacient z rodného čísla a podkladů (T-323, ARCHITEKTURA §5.10, §6.3).

Postup: RČ → vložený text nebo soubory → **návrh** (nic v IRIS) s předvyplněnou nominací (otázka, diagnóza
MKN-10, TNM, ECOG, histologie, předchozí léčba…) a citacemi odstavců → **náhled** detailní i úzkého pásu
(podklad bez LLM nad návrhem) → úpravy lékařem → **potvrzení**: jedna FHIR transakce do IRIS s `Provenance`,
vektory a případ na boardu.

- RČ je jen v `Patient.identifier` (IRIS). Ve výstupech je maskované a do LLM se nedostane: context builder
  identifikátory nečte a pseudonymizace RČ ve volném textu nahradí.
- Údaj z dokumentu cituje svůj odstavec (`P07-imp01#3`). Co lékař dopíše, je text nominace (`P07-zad01#n`).
- Nic se nedomýšlí: rozmezí „ECOG 0–1“ se nepředvyplní (kontrola úplnosti z něj udělá NEJISTOTA AI) a diagnóza
  vznikne jen z kódu MKN-10 v textu nebo od lékaře.
- LLM (hodnoty jako u BON-7, sken PDF) jen tam, kde to D-021 dovolí (`ai_service.provider_for_patient`).
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date, datetime
from typing import Callable, Iterable

from services import rc as rc_module
from services.ai.report_import import AI_TAG, _document, _observation
from services.ai.text import split_paragraphs
from services.fhir.ingest import FICTIONAL_TAG

TAG_SYSTEM = FICTIONAL_TAG["system"]
SOURCE_TAG = {"system": TAG_SYSTEM, "code": "zadano-v-aplikaci", "display": "Zadáno lékařem v MDT Copilot"}
EXT = "https://rakathon.example.org/fhir/StructureDefinition"
NOMINATION_TYPES = {"primarni": "Primární projednání", "restaging": "Restaging / hodnocení odpovědi",
                    "progrese": "Progrese / recidiva"}
# pole nominace, která jdou do `ServiceRequest.note` (stejné nadpisy jako v datasetu, čte je intake i screening studií)
NOTE_FIELDS = (("histology", "Histologie a grade"), ("history", "Předchozí onkologická léčba"),
               ("comorbidities", "Relevantní komorbidity a současný stav"), ("preferences", "Preference a omezení pacienta"))
TEXT_FIELDS = ("question",) + tuple(f for f, _ in NOTE_FIELDS)
FIELD_HEADS = {
    "question": re.compile(r"^(?:Otázka|Dotaz)(?:\s+pro\s+(?:MDT|komisi))?\s*:\s*", re.I),
    "histology": re.compile(r"^Histologie(?:\s+a\s+grade)?\s*:\s*", re.I),
    "history": re.compile(r"^(?:Předchozí(?:\s+onkologická)?\s+léčba|Dosavadní(?:\s+onkologická)?\s+léčba)\s*:\s*", re.I),
    "comorbidities": re.compile(r"^(?:Relevantní\s+)?komorbidity(?:\s+a\s+současný\s+stav)?\s*:\s*", re.I),
    "preferences": re.compile(r"^Preference(?:\s+a\s+omezení\s+pacienta)?\s*:\s*", re.I),
}
ICD10 = re.compile(r"(?<![\w.])([CD]\d{2}(?:\.\d{1,2})?)(?![\w])")
TNM = re.compile(r"(?<!\w)[cpyr]{0,2}T(?:[0-4][a-d]?|is|x|X)\s*[cpyr]{0,2}N(?:[0-3][a-c]?|x|X)\s*[cpyr]{0,2}M(?:[01][a-c]?|x|X)"
                 r"(?:,?\s*(?:klinické\s+)?stadium\s+[0IV]+[ABC]?\d?)?")
ECOG = re.compile(r"\bECOG(?:\s*PS)?\s*[:=]?\s*([0-4])\b(?!\s*[–-]\s*[0-4])")
DATE = re.compile(r"\b(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})\b")


class DraftError(ValueError):
    pass


def is_oncologic_code(code: str) -> bool:
    """MKN-10 zhoubný nádor (C00–C97), in situ (D00–D09), nejistého chování (D37–D48)."""
    letter, number = code[0], int(code[1:3])
    return letter == "C" or (letter == "D" and (number <= 9 or 37 <= number <= 48))


# ── dokumenty ────────────────────────────────────────────────────────────────
def _first_date(text: str) -> str | None:
    for d, m, y in DATE.findall(text):
        try:
            return date(int(y), int(m), int(d)).isoformat()
        except ValueError:
            continue
    return None


def make_document(patient_id: str, number: int, text: str, source: str) -> dict:
    """Vstup (vložený text, soubor) → dokument návrhu `Pxx-impNN` (název = první řádek, datum = první datum)."""
    text = text.replace("\r\n", "\n").strip()
    if not split_paragraphs(text):
        raise DraftError(f"{source}: dokument je prázdný.")
    first = next(line.strip() for line in text.splitlines() if line.strip())
    return {"id": f"{patient_id}-imp{number:02d}", "title": first[:120], "date": _first_date(text), "text": text,
            "source": source}


# ── předvyplnění nominace z dokumentů (deterministicky, s citací odstavce) ─────
def _diagnosis_text(paragraph: str, match: re.Match) -> str:
    """Text u kódu: za kódem do konce věty / další závorky, jinak před ním („jaterní metastázy (C78.7)“)."""
    after = re.match(r"\s*[–:\-)]?\s*([^.;,()\n]+)", paragraph[match.end():])
    text = after[1].strip(" ,–-") if after else ""
    if not text or ICD10.match(text):
        parts = [x for x in re.split(r"[,:;\n(]", paragraph[:match.start()]) if x.strip(" –-")]
        text = parts[-1].strip(" ,–-(") if parts else ""
    return text or match[1]


def prefill(documents: Iterable[dict], fields: dict | None = None, edited: Iterable[str] = ()) -> dict:
    """Doplní prázdná a lékařem neupravená pole nominace z dokumentů. Každý údaj nese citaci odstavce."""
    fields = {k: v for k, v in (fields or {}).items()}
    edited = set(edited)
    diagnoses = list(fields.get("diagnoses") or [])
    known_codes = {d["code"] for d in diagnoses}
    for doc in documents:
        for p in split_paragraphs(doc["text"]):
            citation = f"{doc['id']}#{p.index}"
            for name, head in FIELD_HEADS.items():
                m = head.match(p.text)
                if m and name not in edited and not fields.get(name) and p.text[m.end():].strip():
                    fields[name] = {"text": p.text[m.end():].strip(), "citation": citation}
            if "diagnoses" not in edited:
                for m in ICD10.finditer(p.text):
                    if is_oncologic_code(m[1]) and m[1] not in known_codes:
                        known_codes.add(m[1])
                        diagnoses.append({"code": m[1], "text": _diagnosis_text(p.text, m), "citation": citation})
            if "tnm" not in edited and not fields.get("tnm") and (m := TNM.search(p.text)):
                fields["tnm"] = {"text": m[0].strip(), "citation": citation, "date": doc.get("date")}
            if "ecog" not in edited and not fields.get("ecog") and (m := ECOG.search(p.text)):
                fields["ecog"] = {"value": int(m[1]), "citation": citation, "date": doc.get("date")}
    fields["diagnoses"] = diagnoses
    fields.setdefault("nomination_type", "primarni")
    return fields


# ── FHIR resources návrhu ─────────────────────────────────────────────────────
def _ref(rtype: str, rid: str) -> dict:
    return {"reference": f"{rtype}/{rid}"}


def _source(citation: str | None, request_id: str) -> tuple[str, str]:
    """(typ, ID) zdroje údaje: dokument z citace, jinak nominace (údaj dopsal lékař)."""
    if citation and "-imp" in citation:
        return "DocumentReference", citation.split("#")[0]
    return "ServiceRequest", request_id


def _derived_from(obs: dict, citation: str | None, request_id: str) -> dict:
    rtype, rid = _source(citation, request_id)
    if rtype == "DocumentReference":
        obs["derivedFrom"] = [_ref(rtype, rid)]
    else:       # R4 derivedFrom nepovoluje ServiceRequest → extension jako u ingestu (Q15)
        obs.setdefault("extension", []).append({"url": f"{EXT}/derived-from", "valueReference": _ref(rtype, rid)})
    if citation:
        obs["note"] = [{"text": f"Zdroj: {citation}"}]
    return obs


def build_resources(draft: dict, now: datetime) -> list[dict]:
    """Návrh → FHIR resources pacienta (Patient, dokumenty, nominace, diagnózy, TNM, ECOG, hodnoty, Provenance)."""
    if draft.get("bundle"):
        return _bundle_resources(draft, now)
    pid, fields = draft["patient_id"], draft.get("fields") or {}
    rc = rc_module.parse(draft["rc"])
    meta = {"tag": [SOURCE_TAG] + ([FICTIONAL_TAG] if draft.get("synthetic") else [])}
    session = draft.get("session")
    mdt_day = datetime.fromisoformat(session["date"]).date() if session else now.date()
    request_id, today = f"{pid}-zad01", now.date().isoformat()
    requester = {"display": draft.get("requester") or "zadávající lékař"}

    out: list[dict] = [{
        "resourceType": "Patient", "id": pid, "meta": meta,
        "identifier": [{"system": rc_module.SYSTEM, "value": rc.value},
                       {"system": "https://rakathon.example.org/fhir/sid/pacient", "value": pid}],
        "gender": rc.gender, "birthDate": rc.birth_date.isoformat(),
        "extension": [{"url": f"{EXT}/vek-k-datu-mdt", "valueInteger": rc.age_at(mdt_day)}],
    }]
    docs = [{**_document(pid, d["id"], d["text"], d["title"], d.get("date")), "meta": meta,
             "description": f"Podklad k nominaci ({d['source']})"} for d in draft.get("documents", [])]
    out += docs

    diagnoses = fields.get("diagnoses") or []
    conditions = []
    for i, dg in enumerate(diagnoses, 1):
        rtype, rid = _source(dg.get("citation"), request_id)
        condition = {
            "resourceType": "Condition", "id": f"{pid}-dg{i}", "meta": meta,
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                                               "code": "confirmed"}]},
            "category": [{"text": "onkologická diagnóza"}],
            "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": dg["code"], "display": dg["text"]}],
                     "text": dg["text"]},
            "subject": _ref("Patient", pid), "evidence": [{"detail": [_ref(rtype, rid)]}],
        }
        if dg.get("citation"):
            condition["note"] = [{"text": f"Zdroj: {dg['citation']}"}]
        conditions.append(condition)
    out += conditions

    question = (fields.get("question") or {}).get("text")
    nomination_type = fields.get("nomination_type") or "primarni"
    if nomination_type not in NOMINATION_TYPES:
        raise DraftError(f"Typ projednání jen {', '.join(NOMINATION_TYPES)}.")
    notes = []
    for name, label in NOTE_FIELDS:
        text = (fields.get(name) or {}).get("text")
        if text:
            notes.append({"text": f"{label}:\n{text}" if text.lstrip().startswith("-") else f"{label}: {text}"})
    request = {
        "resourceType": "ServiceRequest", "id": request_id, "meta": meta, "status": "active", "intent": "order",
        "identifier": [{"system": "https://rakathon.example.org/fhir/sid/mdt-zadanka", "value": request_id}],
        "category": [{"text": f"Požadované zaměření MDT: {session['title']}"}] if session else [],
        "code": {"coding": [{"system": "https://rakathon.example.org/fhir/CodeSystem/mdt-typ-projednani",
                             "code": nomination_type, "display": NOMINATION_TYPES[nomination_type]}]},
        "priority": "routine", "subject": _ref("Patient", pid), "authoredOn": now.isoformat(timespec="seconds"),
        "requester": requester, "reasonReference": [_ref("Condition", c["id"]) for c in conditions],
        "supportingInfo": [_ref("DocumentReference", d["id"]) for d in docs], "note": notes,
    }
    if question:
        request["reasonCode"] = [{"text": question}]
    task = {
        "resourceType": "Task", "id": f"{request_id}-task", "meta": meta, "status": "accepted" if session else "requested",
        "intent": "order", "focus": _ref("ServiceRequest", request_id), "for": _ref("Patient", pid),
        "authoredOn": now.isoformat(timespec="seconds"), "requester": requester,
    }
    if session:
        task["restriction"] = {"period": {"start": session["date"]}}
        task["businessStatus"] = {"coding": [{"system": "https://rakathon.example.org/fhir/CodeSystem/mdt-stav-zadanky",
                                              "code": "naplanovana", "display": "Naplánovaná"}]}
    out += [request, task]

    if fields.get("tnm"):
        tnm = fields["tnm"]
        obs = {"resourceType": "Observation", "id": f"{pid}-tnm01", "meta": meta, "status": "final",
               "subject": _ref("Patient", pid), "effectiveDateTime": tnm.get("date") or today,
               "category": [{"text": "Staging"}], "code": {"text": "TNM (klinické)"}, "valueString": tnm["text"]}
        if conditions:
            obs["focus"] = [_ref("Condition", conditions[0]["id"])]
        out.append(_derived_from(obs, tnm.get("citation"), request_id))
    if fields.get("ecog") is not None and fields["ecog"].get("value") is not None:
        ecog = fields["ecog"]
        obs = {"resourceType": "Observation", "id": f"{pid}-ecog01", "meta": meta, "status": "final",
               "subject": _ref("Patient", pid), "effectiveDateTime": ecog.get("date") or today,
               "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                         "code": "survey"}]}],
               "code": {"coding": [{"system": "http://loinc.org", "code": "89247-1",
                                    "display": "ECOG Performance Status score"}], "text": "ECOG – hodnoceno lékařem"},
               "valueInteger": int(ecog["value"]), "performer": [requester]}
        out.append(_derived_from(obs, ecog.get("citation"), request_id))

    values = draft.get("values") or []
    by_doc: dict[str, int] = {}
    for value in values:                       # hodnoty z BON-7 (LLM, ověřené proti odstavci)
        doc_id = value["citation"].split("#")[0]
        by_doc[doc_id] = by_doc.get(doc_id, 0) + 1
        doc_date = next((d.get("date") for d in draft.get("documents", []) if d["id"] == doc_id), None)
        obs = _observation(pid, doc_id, by_doc[doc_id], value, doc_date)
        obs["meta"] = {"tag": meta["tag"] + [AI_TAG]}
        out.append(obs)

    agents = [{"type": {"text": "zadal lékař"}, "who": requester}]
    if values:
        agents.append({"type": {"text": "vytěžil AI asistent"}, "who": _ref("Device", "mdt-copilot")})
    out = [_prune(r) for r in out]
    out.append({
        "resourceType": "Provenance", "id": f"{request_id}-prov", "recorded": now.isoformat(timespec="seconds"),
        "target": [_ref(r["resourceType"], r["id"]) for r in out],
        "activity": {"text": "Založení nového pacienta a nominace na MDT"}, "agent": agents,
        "entity": [{"role": "source", "what": _ref("DocumentReference", d["id"])} for d in docs],
    })
    return out


def _prune(value):
    """Bez prázdných polí a řetězců (IRIS je odmítne stejně jako ingest datasetu, DATASET §6.2)."""
    if isinstance(value, dict):
        return {k: v for k, v in ((k, _prune(v)) for k, v in value.items()) if v not in ([], {}, "", None)}
    if isinstance(value, list):
        return [v for v in (_prune(v) for v in value) if v not in ([], {}, "", None)]
    return value


# ── import z FHIR JSON (T-335) ────────────────────────────────────────────────
# Bundle (collection / transaction / searchset), jeden resource nebo seznam resources s jedním pacientem.
# Sanitizace jako ingest datasetu, přečíslování na volné `Pnn` a ID podle konvence datasetu (citace, resolver),
# kontrola referencí a RČ. Nominace se předvyplní ze strukturovaných dat, citací je ID resource.
JSON_SUFFIXES = (".json",)
IMPORT_TAG = {"system": TAG_SYSTEM, "code": "import-fhir-json", "display": "Importováno z FHIR JSON v MDT Copilot"}
PATIENT_SID = "https://rakathon.example.org/fhir/sid/pacient"
SHARED_TYPES = frozenset({"Organization", "Practitioner", "PractitionerRole", "Location", "Medication",
                          "Questionnaire", "ResearchStudy", "Group", "Device"})
_DATASET_PID = re.compile(r"P\d{2}")
_ECOG_LOINC = "89247-1"


def is_json_upload(name: str, content_type: str | None) -> bool:
    return name.lower().endswith(JSON_SUFFIXES) or (content_type or "").split(";")[0] in (
        "application/json", "application/fhir+json")


def fhir_resources(data: bytes, name: str) -> tuple[list[dict], dict[str, str], list[dict]]:
    """JSON souboru → (resources, `fullUrl` → `Type/id`, `meta.tag` bundlu). Neplatný obsah → DraftError."""
    try:
        doc = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise DraftError(f"{name}: soubor není platný JSON ({getattr(e, 'msg', e)}).") from None
    resources, full_urls, tags = [], {}, []
    for item in doc if isinstance(doc, list) else [doc]:
        if not isinstance(item, dict) or not item.get("resourceType"):
            raise DraftError(f"{name}: očekáván FHIR Bundle nebo resource (chybí resourceType).")
        if item["resourceType"] == "Bundle":
            tags += (item.get("meta") or {}).get("tag") or []
            for entry in item.get("entry") or []:
                r = (entry or {}).get("resource")
                if not isinstance(r, dict) or not r.get("resourceType") or not r.get("id"):
                    raise DraftError(f"{name}: položka bundlu bez resource nebo bez id.")
                resources.append(r)
                if entry.get("fullUrl"):
                    full_urls[entry["fullUrl"]] = f"{r['resourceType']}/{r['id']}"
        elif not item.get("id"):
            raise DraftError(f"{name}: {item['resourceType']} nemá id.")
        else:
            resources.append(item)
    if not resources:
        raise DraftError(f"{name}: soubor neobsahuje žádný resource.")
    return resources, full_urls, tags


def _code(resource: dict, system_part: str) -> str | None:
    return next((c.get("code") for c in (resource.get("code") or {}).get("coding") or []
                 if system_part in (c.get("system") or "") and c.get("code")), None)


def _category_text(resource: dict) -> str:
    return " ".join(f"{c.get('text') or ''} {' '.join((x.get('code') or '') + ' ' + (x.get('display') or '') for x in c.get('coding') or [])}"
                    for c in resource.get("category") or []).lower()


def _new_id(resource: dict, pid: str, old_pid: str, counters: dict[str, int]) -> str:
    """Nové ID podle konvence datasetu (`services/fhir/ids.py`), aby šlo citovat a resolver poznal typ."""
    from services.fhir.ids import resource_type_for_id, sanitize_id

    rtype, rid = resource["resourceType"], sanitize_id(resource["id"])
    if rtype == "Patient":
        return pid
    if _DATASET_PID.fullmatch(old_pid):                    # dataset: `P07-dg1`, `LEK-P07-01` → jen jiné Pnn
        swapped = re.sub(rf"(?<![A-Za-z0-9]){old_pid}(?![0-9])", pid, rid)
        if resource_type_for_id(swapped) == rtype:
            return swapped
    if rtype in SHARED_TYPES and resource_type_for_id(rid) == rtype:
        return rid                                         # sdílený resource v konvenci (ORG-FN, LEK-…)

    def nxt(prefix: str) -> int:
        counters[prefix] = counters.get(prefix, 0) + 1
        return counters[prefix]

    if rtype == "Practitioner":
        return f"LEK-{pid}-{nxt('LEK'):02d}"
    if rtype == "Organization":
        return f"ORG-{pid}-{nxt('ORG')}"
    if rtype == "Condition":
        return f"{pid}-dg{nxt('dg')}"
    if rtype == "DocumentReference":
        return f"{pid}-doc{nxt('doc'):02d}"
    if rtype == "DiagnosticReport":
        cat = _category_text(resource)
        kind = "img" if re.search(r"rad|imag|zobraz|\bct\b|\bmr\b", cat) else "pat" if re.search(r"pat|histol", cat) else "lab"
        return f"{pid}-{kind}{nxt(kind):02d}"
    if rtype == "Observation":
        if _code(resource, "loinc") == _ECOG_LOINC:
            return f"{pid}-ecog{nxt('ecog'):02d}"
        text = ((resource.get("code") or {}).get("text") or "").lower()
        if "tnm" in text or "stad" in text or "stage" in text:
            return f"{pid}-tnm{nxt('tnm'):02d}"
        return f"{pid}-lab90-o{nxt('obs')}"
    simple = {"MedicationRequest": "med", "MedicationStatement": "med", "Procedure": "proc",
              "ServiceRequest": "zad", "QuestionnaireResponse": "prom"}
    if rtype in simple:
        return f"{pid}-{simple[rtype]}{nxt(simple[rtype]):02d}"
    if rtype == "ImagingStudy":
        return f"{pid}-img{nxt('imgs') + 80:02d}-study"
    if rtype == "MedicationAdministration":
        return f"{pid}-tx-imp-{nxt('tx')}"
    if rtype == "Task":
        return f"{pid}-zad{nxt('task'):02d}-task"
    return f"{pid}-x{rtype.lower()[:12]}{nxt('x' + rtype)}"   # typ mimo konvence: uloží se, citace bez typu


def _rewrite_refs(node, mapping: dict[str, str]):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == "reference" and isinstance(v, str):
                bare = v.split("/_history/")[0].rstrip("/")
                tail = "/".join(bare.split("/")[-2:])
                v = mapping.get(v) or mapping.get(bare) or mapping.get(tail) or v
            out[k] = _rewrite_refs(v, mapping)
        return out
    if isinstance(node, list):
        return [_rewrite_refs(v, mapping) for v in node]
    return node


def renumber_resources(resources: list[dict], old_pid: str, pid: str, full_urls: dict[str, str] | None = None
                       ) -> list[dict]:
    """ID a reference resources na nové `pid` (Patient, `Pxx-…`, mimo konvenci podle typu)."""
    counters: dict[str, int] = {}
    mapping, ids = {}, {}
    for r in resources:
        new = _new_id(r, pid, old_pid, counters)
        ids[id(r)] = new
        mapping[f"{r['resourceType']}/{r['id']}"] = f"{r['resourceType']}/{new}"
    for url, ref in (full_urls or {}).items():
        if ref in mapping:
            mapping[url] = mapping[ref]
    out = []
    for r in resources:
        new = _rewrite_refs(copy.deepcopy(r), mapping)
        new["id"] = ids[id(r)]
        out.append(new)
    if _DATASET_PID.fullmatch(old_pid) and old_pid != pid:          # „Pacient P07 (fiktivní)“ v textu jména
        for r in out:
            if r["resourceType"] in ("Patient", "Practitioner"):
                for name in r.get("name") or []:
                    if name.get("text"):
                        name["text"] = re.sub(rf"\b{old_pid}\b", pid, name["text"])
    return out


def import_bundle(resources: list[dict], pid: str, rc: "rc_module.RodneCislo | None", synthetic: bool,
                  full_urls: dict[str, str] | None = None, file_tags: Iterable[dict] = (),
                  existing: Callable[[str, str], bool] | None = None) -> tuple[list[dict], dict]:
    """Resources ze souboru → sanitizované a přečíslované resources pacienta `pid` + informace pro návrh.

    Chyby (víc pacientů, RČ nesedí, odkaz mimo soubor a IRIS) → DraftError. `existing(type, id)` ověří odkaz v IRIS."""
    from services.fhir import ingest
    from services.fhir.ids import sanitize_id

    patients = [r for r in resources if r["resourceType"] == "Patient"]
    if len(patients) != 1:
        raise DraftError(f"Soubor musí obsahovat právě jednoho pacienta (Patient), obsahuje {len(patients)}. "
                         "Víc pacientů nahrajte po jednom souboru.")
    old_pid = sanitize_id(patients[0]["id"])
    fictional = synthetic or any(t.get("code") == FICTIONAL_TAG["code"] for t in file_tags) or any(
        t.get("code") == FICTIONAL_TAG["code"] for r in resources for t in (r.get("meta") or {}).get("tag") or [])
    tags = [IMPORT_TAG] + ([FICTIONAL_TAG] if fictional else [])
    clean_urls = {u: ref.split("/")[0] + "/" + sanitize_id(ref.split("/", 1)[1]) for u, ref in (full_urls or {}).items()}
    clean = renumber_resources([ingest.sanitize(r, tags) for r in resources], old_pid, pid, clean_urls)
    seen, out = set(), []
    for r in clean:                                      # duplicitní ID v souboru: poslední vyhrává jako u PUT
        key = f"{r['resourceType']}/{r['id']}"
        if key in seen:
            out = [x for x in out if f"{x['resourceType']}/{x['id']}" != key]
        seen.add(key)
        out.append(r)

    patient = next(r for r in out if r["resourceType"] == "Patient")
    if rc is not None:
        if patient.get("gender") in ("male", "female") and patient["gender"] != rc.gender:
            raise DraftError(f"RČ patří {'muži' if rc.gender == 'male' else 'ženě'}, v souboru je pohlaví "
                             f"{'muž' if patient['gender'] == 'male' else 'žena'}.")
        if patient.get("birthDate") and patient["birthDate"][:4] != str(rc.birth_date.year):
            raise DraftError(f"Rok narození z RČ ({rc.birth_date.year}) nesedí s rokem v souboru ({patient['birthDate'][:4]}).")
        patient["gender"], patient["birthDate"] = rc.gender, rc.birth_date.isoformat()
    identifiers = [i for i in patient.get("identifier") or [] if i.get("system") not in (PATIENT_SID, rc_module.SYSTEM)]
    patient["identifier"] = identifiers + [{"system": PATIENT_SID, "value": pid}]
    if patient.get("gender") not in ("male", "female"):
        raise DraftError("V souboru chybí pohlaví pacienta (Patient.gender) a RČ nebylo zadané.")
    if not patient.get("birthDate"):
        raise DraftError("V souboru chybí datum narození pacienta (Patient.birthDate) a RČ nebylo zadané.")

    present = {f"{r['resourceType']}/{r['id']}" for r in out}
    dangling = sorted({ref for r in out for ref in _refs(r) if ref not in present})
    missing = [ref for ref in dangling if not (ref.split("/")[0] in SHARED_TYPES and existing
                                               and existing(*ref.split("/", 1)))]
    if missing:
        raise DraftError(f"Odkazy na záznamy, které nejsou v souboru ani v IRIS: {', '.join(missing[:5])}"
                         + (f" a dalších {len(missing) - 5}" if len(missing) > 5 else "") + ".")
    counts: dict[str, int] = {}
    for r in out:
        counts[r["resourceType"]] = counts.get(r["resourceType"], 0) + 1
    info = {"renamed_from": old_pid if old_pid != pid else None, "counts": counts, "synthetic": fictional,
            "practitioners": [r["id"] for r in out if r["resourceType"] == "Practitioner"]}
    return out, info


def _refs(node) -> set[str]:
    from services.fhir.ingest import references
    return references(node)


def _sr_notes(request: dict) -> dict[str, str]:
    out = {}
    for note in request.get("note") or []:
        text = (note.get("text") or "").strip()
        for name, head in FIELD_HEADS.items():
            m = head.match(text)
            if m and name != "question" and text[m.end():].strip():
                out[name] = text[m.end():].strip()
    return out


def prefill_from_resources(resources: list[dict]) -> tuple[dict, str | None]:
    """Nominace ze strukturovaných dat souboru (citace = ID resource). Vrací (pole, ID ServiceRequest)."""
    from services.rules.guideline_sets import is_oncologic

    fields: dict = {}
    requests = sorted((r for r in resources if r["resourceType"] == "ServiceRequest"),
                      key=lambda r: r.get("authoredOn") or "", reverse=True)
    request = requests[0] if requests else None
    if request:
        question = next((c.get("text") for c in request.get("reasonCode") or [] if c.get("text")), None)
        if question:
            fields["question"] = {"text": question.strip(), "citation": request["id"]}
        kind = _code(request, "mdt-typ-projednani") or next(
            (c.get("code") for c in (request.get("code") or {}).get("coding") or [] if c.get("code") in NOMINATION_TYPES), None)
        if kind in NOMINATION_TYPES:
            fields["nomination_type"] = kind
        for name, text in _sr_notes(request).items():
            fields[name] = {"text": text, "citation": request["id"]}
    diagnoses = []
    for c in resources:
        if c["resourceType"] != "Condition" or not is_oncologic(c):
            continue
        code = _code(c, "icd-10")
        if code and is_oncologic_code(code.upper()):
            coding = next(x for x in (c.get("code") or {}).get("coding") or [] if x.get("code") == code)
            diagnoses.append({"code": code.upper(), "text": (c.get("code") or {}).get("text") or coding.get("display") or code,
                              "citation": c["id"]})
    fields["diagnoses"] = diagnoses

    def latest(pred):
        found = [r for r in resources if r["resourceType"] == "Observation" and pred(r)]
        return max(found, key=lambda r: r.get("effectiveDateTime") or "", default=None)

    ecog = latest(lambda r: _code(r, "loinc") == _ECOG_LOINC and isinstance(r.get("valueInteger"), int)
                  and "pacient" not in ((r.get("code") or {}).get("text") or "").lower())
    if ecog:
        fields["ecog"] = {"value": ecog["valueInteger"], "citation": ecog["id"], "date": (ecog.get("effectiveDateTime") or "")[:10] or None}
    tnm = latest(lambda r: "tnm" in ((r.get("code") or {}).get("text") or "").lower() or "-tnm" in r["id"])
    if tnm:
        value = tnm.get("valueString") or (tnm.get("valueCodeableConcept") or {}).get("text")
        if value:
            fields["tnm"] = {"text": value, "citation": tnm["id"], "date": (tnm.get("effectiveDateTime") or "")[:10] or None}
    fields.setdefault("nomination_type", "primarni")
    return fields, request["id"] if request else None


def _bundle_resources(draft: dict, now: datetime) -> list[dict]:
    """Návrh z FHIR JSON → resources k zápisu: soubor + úpravy nominace lékařem, podklady navíc, Provenance."""
    pid, fields = draft["patient_id"], draft.get("fields") or {}
    out = copy.deepcopy(draft["bundle"])
    session = draft.get("session")
    requester = {"display": draft.get("requester") or "zadávající lékař"}
    meta_tags = next(r for r in out if r["resourceType"] == "Patient").get("meta", {}).get("tag") or [IMPORT_TAG]
    meta = {"tag": meta_tags}
    patient = next(r for r in out if r["resourceType"] == "Patient")
    if draft.get("rc"):
        rc = rc_module.parse(draft["rc"])
        patient["identifier"] = [i for i in patient.get("identifier") or [] if i.get("system") != rc_module.SYSTEM] + [
            {"system": rc_module.SYSTEM, "value": rc.value}]
        mdt_day = datetime.fromisoformat(session["date"]).date() if session else now.date()
        patient["extension"] = [e for e in patient.get("extension") or [] if not e.get("url", "").endswith("vek-k-datu-mdt")] + [
            {"url": f"{EXT}/vek-k-datu-mdt", "valueInteger": rc.age_at(mdt_day)}]

    request_id = draft.get("service_request_id")
    request = next((r for r in out if r["resourceType"] == "ServiceRequest" and r["id"] == request_id), None)
    if request is None:                                  # soubor bez nominace → nominace z návrhu
        request_id = f"{pid}-zad{_free_number(out, 'zad'):02d}"
        request = {"resourceType": "ServiceRequest", "id": request_id, "meta": meta, "status": "active",
                   "intent": "order", "priority": "routine", "subject": _ref("Patient", pid),
                   "authoredOn": now.isoformat(timespec="seconds"), "requester": requester,
                   "reasonReference": [_ref("Condition", r["id"]) for r in out if r["resourceType"] == "Condition"]}
        out.append(request)
    question = (fields.get("question") or {}).get("text")
    if question:
        coded = [c for c in request.get("reasonCode") or [] if c.get("coding")][:1]
        request["reasonCode"] = [{**(coded[0] if coded else {}), "text": question}]
    kind = fields.get("nomination_type") or "primarni"
    if kind in NOMINATION_TYPES:
        request["code"] = {"coding": [{"system": "https://rakathon.example.org/fhir/CodeSystem/mdt-typ-projednani",
                                       "code": kind, "display": NOMINATION_TYPES[kind]}]}
    if session:
        request["category"] = [{"text": f"Požadované zaměření MDT: {session['title']}"}]
    task = next((r for r in out if r["resourceType"] == "Task"
                 and (r.get("focus") or {}).get("reference") == f"ServiceRequest/{request_id}"), None)
    if task is None:
        task = {"resourceType": "Task", "id": f"{request_id}-task", "meta": meta, "intent": "order",
                "focus": _ref("ServiceRequest", request_id), "for": _ref("Patient", pid),
                "authoredOn": now.isoformat(timespec="seconds"), "requester": requester}
        out.append(task)
    task["status"] = "accepted" if session else (task.get("status") or "requested")
    if session:
        task["restriction"] = {"period": {"start": session["date"]}}
        task["businessStatus"] = {"coding": [{"system": "https://rakathon.example.org/fhir/CodeSystem/mdt-stav-zadanky",
                                              "code": "naplanovana", "display": "Naplánovaná"}]}

    docs = [{**_document(pid, d["id"], d["text"], d["title"], d.get("date")), "meta": meta,
             "description": f"Podklad k nominaci ({d['source']})"} for d in draft.get("documents", [])]
    out += docs
    if docs:
        request["supportingInfo"] = (request.get("supportingInfo") or []) + [_ref("DocumentReference", d["id"]) for d in docs]
    by_doc: dict[str, int] = {}
    for value in draft.get("values") or []:
        doc_id = value["citation"].split("#")[0]
        by_doc[doc_id] = by_doc.get(doc_id, 0) + 1
        doc_date = next((d.get("date") for d in draft.get("documents", []) if d["id"] == doc_id), None)
        obs = _observation(pid, doc_id, by_doc[doc_id], value, doc_date)
        obs["meta"] = {"tag": meta["tag"] + [AI_TAG]}
        out.append(obs)

    out = [_prune(r) for r in out]
    agents = [{"type": {"text": "importoval lékař"}, "who": requester}]
    if draft.get("values"):
        agents.append({"type": {"text": "vytěžil AI asistent"}, "who": _ref("Device", "mdt-copilot")})
    out.append({
        "resourceType": "Provenance", "id": f"{request_id}-prov", "recorded": now.isoformat(timespec="seconds"),
        "target": [_ref(r["resourceType"], r["id"]) for r in out if r["resourceType"] not in SHARED_TYPES],
        "activity": {"text": f"Import pacienta z FHIR JSON ({draft.get('import', {}).get('file') or 'soubor'}) a nominace na MDT"},
        "agent": agents,
    })
    return out


def _free_number(resources: list[dict], kind: str) -> int:
    used = [int(m[1]) for r in resources if (m := re.search(rf"-{kind}(\d+)$", r["id"]))]
    return max(used, default=0) + 1


def transaction(resources: list[dict]) -> dict:
    return {"resourceType": "Bundle", "type": "transaction", "entry": [
        {"resource": r, "request": {"method": "PUT", "url": f"{r['resourceType']}/{r['id']}"}} for r in resources]}


# ── kontroly ──────────────────────────────────────────────────────────────────
def missing_for_confirm(draft: dict) -> list[str]:
    """Co chybí k potvrzení: otázka pro MDT (OBC-1.1) a onkologická diagnóza s kódem MKN-10."""
    fields = draft.get("fields") or {}
    missing = []
    if not (fields.get("question") or {}).get("text", "").strip():
        missing.append("Otázka pro MDT (OBC-1.1)")
    if not fields.get("diagnoses"):
        missing.append("Diagnóza s kódem MKN-10")
    return missing


def next_patient_id(taken: Iterable[str]) -> str:
    """Další volné `Pnn` (konvence ID datasetu, `services/fhir/ids.py`)."""
    numbers = [int(t[1:]) for t in taken if re.fullmatch(r"P\d{2}", t)]
    number = max(numbers, default=0) + 1
    if number > 99:
        raise DraftError("Došla ID pacientů P01–P99.")
    return f"P{number:02d}"


def patient_with_rc(patients: Iterable[dict], rc_value: str) -> str | None:
    """ID pacienta v IRIS se stejným RČ (filtruje se v Pythonu, ne neověřeným search parametrem)."""
    return next((p["id"] for p in patients for i in p.get("identifier", [])
                 if i.get("system") == rc_module.SYSTEM and i.get("value") == rc_value), None)


# ── náhled (bez LLM: z neschváleného návrhu nic neodchází ven) ────────────────
def preview(draft: dict, now: datetime, *, detail_config: dict, narrow_config: dict) -> dict:
    """Detailní náhled (celý podklad) a náhled úzkého pásu (šablona projektoru pro diagnózu, jinak `narrow_config`)."""
    from services.ai.brief import build_brief, guideline_notices
    from services.ai.guidelines import GuidelinesUnavailable, load_guidelines
    from services.ai_service import MockAIProvider
    from services.fhir import client as fhir
    from services.rules.guideline_sets import guideline_sets_for
    from services.rules.intake import intake_prefill
    from services.rules.red_flags import PatientData
    from services.rules.templates import case_template

    resources = build_resources(draft, now)
    sets = guideline_sets_for(PatientData(resources).icd10)
    try:
        passages = load_guidelines(sets)
    except GuidelinesUnavailable:
        passages = []
    template = case_template(resources)
    common = {"studies": fhir.search("ResearchStudy") + fhir.search("Group"), "guidelines": passages,
              "provider": MockAIProvider(), "notices": guideline_notices(sets, passages, resources)}
    roles = (template or {}).get("config", {}).get("roles_present") or detail_config.get("roles_present")
    pid = draft["patient_id"]
    return {
        "detail": build_brief(pid, resources, config={**detail_config, "roles_present": roles}, **common),
        "narrow": build_brief(pid, resources, config=template["config"] if template else narrow_config, **common),
        "template": template,
        "intake": intake_prefill(resources),
    }
