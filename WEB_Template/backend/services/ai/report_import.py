"""Vstup PDF nebo vloženého textu → FHIR (BON-7, T-510).

1. **Návrh** (`propose`): text zprávy (vložený, nebo z PDF: `services/ai/pdf_text.py`, sken přes OCR) → `DocumentReference/Pxx-impNN`
   s odstavci → LLM vytáhne hodnoty (laboratoř, biomarkery, ECOG, TNM, hmotnost) s číslem odstavce →
   každá hodnota se ověří proti svému odstavci (číslo i datum musí být ve zdroji). Nic se nezapisuje.
2. **Potvrzení lékařem** (`confirm`): klient pošle návrh zpět (případně jen vybrané hodnoty); server ho znovu
   ověří proti textu dokumentu a zapíše jednou transakcí `DocumentReference` + `Observation[]` (`derivedFrom`
   → dokument) + `Provenance` (lékař + MDT Copilot). Neověřitelné hodnoty se nezapíšou nikdy.
"""
from __future__ import annotations

import base64
import hashlib
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from services.ai import pdf_text as pdf_parser
from services.ai.grounding import _numbers
from services.ai.text import split_paragraphs
from services.ai_service import AIProviderError, BaseAIProvider, get_ai_provider

AI_TAG = {"system": "https://rakathon.example.org/fhir/CodeSystem/ai-generated", "code": "ai"}
CATEGORY = {"lab": "laboratory", "biomarker": "laboratory", "ecog": "survey", "tnm": "exam", "vital": "vital-signs"}
ID_KIND = {"lab": "lab", "biomarker": "bm", "ecog": "ecog", "tnm": "tnm", "vital": "vit"}   # druh v ID jako v datasetu
LOINC = {"ecog": ("89247-1", "ECOG Performance Status score")}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PROMPT = """Z lékařské zprávy vytěž strukturované hodnoty pro onkologickou komisi: laboratoř, nádorové markery,
biomarkery (ER, PR, HER2, Ki-67, KRAS, BRAF, MMR/MSI, EGFR, ALK, PD-L1…), funkční vyšetření (FEV1, FVC, DLCO, LVEF),
ECOG, TNM a hmotnost. Ke každé hodnotě uveď číslo odstavce z hranatých závorek, odkud pochází, datum vyšetření
(YYYY-MM-DD, jen pokud je ve zprávě), hodnotu přesně jako ve zprávě (value_text) a u číselných hodnot i číslo
(value_number, desetinná tečka) a jednotku. Řádek tabulky „název | hodnota | jednotka | rozmezí“ je jedna hodnota.
Nic nedomýšlej a nepřepočítávej; co ve zprávě není, nevracej."""

# Název hodnoty → LOINC, jaký používají pravidla a dataset (red_flags.LOINC); jen jednoznačné názvy, jinak bez kódu
LABEL_LOINC = [(re.compile(pattern, re.IGNORECASE), code, display) for pattern, code, display in (
    (r"^(hemoglobin|hb)\b", "718-7", "Hemoglobin"), (r"^(sodík|natrium|na)\b", "2951-2", "Sodík"),
    (r"^(glykémie|glukóza|glu)\b", "15074-8", "Glukóza"), (r"^albumin\b", "1751-7", "Albumin"),
    (r"^cea\b", "2039-6", "CEA"), (r"^ca ?19-9\b", "24108-3", "CA 19-9"), (r"^ca ?15-3\b", "6875-3", "CA 15-3"),
    (r"^neutrofil", "751-8", "Neutrofily"), (r"^(trombocyt|plt\b)", "777-3", "Trombocyty"),
    (r"^(kreatinin|krea\b)", "14682-9", "Kreatinin"), (r"^bilirubin", "14631-6", "Bilirubin"),
    (r"^(hmotnost|váha)\b", "29463-7", "Hmotnost"),
)]
LEADING_NUMBER = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(\S[^(]*)?")              # „8,4 10^9/l“, „1,9 l (68 %)“


def _with_number(value: dict) -> dict:
    """Číslo a jednotka z `value_text` („8,4 10^9/l“), když je model nevyplnil; „<5“ zůstane textem."""
    if value.get("value_number") is not None or value["kind"] not in ("lab", "vital", "biomarker"):
        return value
    match = LEADING_NUMBER.match(value.get("value_text") or "")
    if not match:
        return value
    return {**value, "value_number": float(match.group(1).replace(",", ".")),
            "unit": value.get("unit") or (match.group(2) or "").strip() or None}
TEXT_PROMPT = "Přepiš text lékařské zprávy doslova, odstavce odděl prázdným řádkem. Nic nevynechávej a nic nepřidávej."


class ExtractedValue(BaseModel):
    kind: Literal["lab", "biomarker", "ecog", "tnm", "vital"]
    label: str = Field(description="Název, např. CEA, Hemoglobin, HER2 IHC, ECOG")
    value_text: str = Field(description="Hodnota přesně jako ve zprávě, např. „13,9 µg/l“, „3+“")
    value_number: float | None = None
    unit: str | None = None
    date: str | None = Field(default=None, description="YYYY-MM-DD")
    paragraph: int = Field(description="Číslo odstavce, ze kterého hodnota pochází")


class Extraction(BaseModel):
    title: str = Field(description="Název zprávy, např. Laboratoř 12. 10. 2026")
    date: str | None = None
    values: list[ExtractedValue] = Field(default_factory=list)


class DocumentText(BaseModel):
    text: str


def _ocr_provider(provider: BaseAIProvider) -> BaseAIProvider | None:
    """Kdo přečte sken: NVIDIA (`nemotron-parse`, stránka po stránce), jinak Gemini (celé PDF), mock nikdo."""
    if provider.is_mock:
        return None
    for candidate in (provider, get_ai_provider("nvidia"), get_ai_provider("gemini")):
        if not candidate.is_mock and candidate.provider_name in ("nvidia", "gemini"):
            return candidate
    return None


def pdf_text(pdf: bytes, provider: BaseAIProvider, log_call: Callable[[str, dict], Any]) -> str:
    """Text PDF lékařské zprávy (services/ai/pdf_text.py): textová vrstva parserem, skenované stránky přes OCR."""
    pages = pdf_parser.text_layer_pages(pdf)
    scans = [i for i, page in enumerate(pages) if pdf_parser.is_scan(page)]
    if scans:
        ocr = _ocr_provider(provider)
        if ocr is None:
            raise ValueError("PDF nemá textovou vrstvu (sken). Vložte text zprávy, nebo nastavte NVIDIA_API_KEY pro OCR.")
        if ocr.provider_name == "gemini":
            if len(scans) != len(pages):
                raise ValueError("Smíšené PDF (text + sken) čte OCR jen přes NVIDIA. Vložte text zprávy.")
            result = ocr.transcribe(pdf, "application/pdf", prompt=TEXT_PROMPT, response_schema=DocumentText)
            log_call("import.pdf_text", result)
            if result.get("status") != "success":
                raise ValueError(f"Text ze skenu PDF se nepodařilo získat: {result.get('error')}")
            pages = [(result.get("data") or {}).get("text", "")]
        else:
            elements = []
            for i in scans:
                started = time.monotonic()
                png = pdf_parser.render_page(pdf, i)
                try:
                    elements.append(ocr.parse_page_image(png))
                except AIProviderError as exc:
                    raise ValueError(f"OCR stránky {i + 1} se nepovedlo: {exc}") from None
                log_call("import.ocr", ocr._success(text="", data=None, model=pdf_parser.ocr_model(), tokens_in=0,
                                                    tokens_out=0, tokens_total=0, started=started,
                                                    p_hash=hashlib.sha256(png).hexdigest()))
            for i, text in zip(scans, pdf_parser.ocr_pages_text(elements)):
                pages[i] = text
    text = pdf_parser.clean_text(pages)
    if pdf_parser.is_scan(text):
        raise ValueError("Z PDF se nepodařilo získat text.")
    return text


def _check(value: dict, paragraphs: dict[int, str]) -> list[str]:
    """Důvody, proč hodnotu nelze ověřit proti jejímu odstavci (prázdné = ověřeno)."""
    source = paragraphs.get(value.get("paragraph"))
    if source is None:
        return [f"odstavec {value.get('paragraph')} ve zprávě není"]
    reasons = [f"číslo {n} není v odstavci" for n in sorted(_numbers(value["value_text"]) - _numbers(source))]
    if value.get("value_number") is not None and _numbers(f"{value['value_number']:g}") - _numbers(source):
        reasons.append("číselná hodnota neodpovídá textu")
    if value.get("date") and not ISO.match(value["date"]):
        reasons.append("datum není YYYY-MM-DD")
    return reasons


def _document(patient_id: str, doc_id: str, text: str, title: str, date: str | None) -> dict:
    return {
        "resourceType": "DocumentReference", "id": doc_id, "status": "current",
        "type": {"text": title or "Importovaná zpráva"}, "subject": {"reference": f"Patient/{patient_id}"},
        "date": f"{date}T00:00:00+00:00" if date and ISO.match(date) else datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "description": "Zpráva vložená lékařem (BON-7)",
        "content": [{"attachment": {"contentType": "text/plain; charset=utf-8",
                                    "data": base64.b64encode(text.encode("utf-8")).decode(), "title": f"{doc_id}.txt"}}],
    }


def _observation(patient_id: str, doc_id: str, index: int, value: dict, doc_date: str | None) -> dict:
    obs: dict = {
        "resourceType": "Observation", "id": f"{doc_id}-{ID_KIND[value['kind']]}{index:02d}", "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                  "code": CATEGORY[value["kind"]]}]}],
        # hlavička a pravidla poznají TNM podle „TNM“ v názvu (jako dataset)
        "code": {"text": value["label"] if value["kind"] != "tnm" or "TNM" in value["label"].upper() else f"TNM – {value['label']}"},
        "subject": {"reference": f"Patient/{patient_id}"},
        "derivedFrom": [{"reference": f"DocumentReference/{doc_id}"}],
        "note": [{"text": f"Zdroj: {doc_id}#{value['paragraph']}"}], "meta": {"tag": [AI_TAG]},
    }
    if value["kind"] in LOINC:
        code, display = LOINC[value["kind"]]
        obs["code"]["coding"] = [{"system": "http://loinc.org", "code": code, "display": display}]
    elif loinc := next(((c, d) for pattern, c, d in LABEL_LOINC if pattern.match(value["label"].strip())), None):
        obs["code"]["coding"] = [{"system": "http://loinc.org", "code": loinc[0], "display": loinc[1]}]
    date = value.get("date") or doc_date
    if date and ISO.match(date):
        obs["effectiveDateTime"] = date
    if value["kind"] == "ecog" and value.get("value_number") is not None:
        obs["valueInteger"] = int(value["value_number"])
    elif value.get("value_number") is not None and value.get("unit"):
        obs["valueQuantity"] = {"value": value["value_number"], "unit": value["unit"]}
    else:
        obs["valueString"] = value["value_text"]
    return obs


def propose(patient_id: str, doc_id: str, text: str, provider: BaseAIProvider,
            log_call: Callable[[str, dict], Any]) -> dict:
    """Návrh importu (nic se nezapisuje): dokument, ověřené hodnoty s citací odstavce a odmítnuté s důvodem."""
    paragraphs = {p.index: p.text for p in split_paragraphs(text)}
    if not paragraphs:
        raise ValueError("Zpráva je prázdná.")
    prompt = "\n\n".join(f"[{i}] {t}" for i, t in paragraphs.items())
    result = provider.generate(prompt, system_prompt=PROMPT, response_schema=Extraction, temperature=0.0)
    log_call("import.extract", result)
    data = result.get("data") if result.get("status") == "success" else None
    if not data:
        raise ValueError(f"Hodnoty se nepodařilo vytěžit: {result.get('error') or 'prázdná odpověď'}")
    accepted, rejected = [], []
    for value in map(_with_number, data.get("values") or []):
        reasons = _check(value, paragraphs)
        target = rejected if reasons else accepted
        # `source` = znění odstavce, ať ho lékař vidí před potvrzením (dokument ještě v IRIS není)
        target.append({**value, "citation": f"{doc_id}#{value['paragraph']}", "source": paragraphs.get(value["paragraph"]),
                       **({"reasons": reasons} if reasons else {})})
    return {"patient_id": patient_id, "document_id": doc_id, "title": data.get("title") or "Importovaná zpráva",
            "date": data.get("date"), "text": text, "values": accepted, "rejected": rejected}


def confirm(proposal: dict, *, user_name: str) -> list[dict]:
    """Ověří návrh znovu proti textu a vrátí resources pro jednu transakci (DocumentReference, Observation, Provenance)."""
    pid, doc_id, text = proposal["patient_id"], proposal["document_id"], proposal["text"]
    if not re.match(rf"^{re.escape(pid)}-imp\d{{2}}$", doc_id):
        raise ValueError("Neplatné ID dokumentu.")
    paragraphs = {p.index: p.text for p in split_paragraphs(text)}
    if not paragraphs:
        raise ValueError("Zpráva je prázdná.")
    # bez hodnot se zapíše jen zpráva (anamnéza, popis): text je pak v RAG a citovatelný po odstavcích
    values = [v for v in proposal.get("values") or [] if not _check(v, paragraphs)]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    doc = _document(pid, doc_id, text, proposal.get("title", ""), proposal.get("date"))
    observations = [_observation(pid, doc_id, i, v, proposal.get("date")) for i, v in enumerate(values, 1)]
    provenance = {
        "resourceType": "Provenance", "id": f"{doc_id}-prov", "recorded": now,
        "target": [{"reference": f"DocumentReference/{doc_id}"}] + [{"reference": f"Observation/{o['id']}"} for o in observations],
        "agent": [{"type": {"text": "potvrdil lékař"}, "who": {"display": user_name}},
                  {"type": {"text": "vytěžil AI asistent"}, "who": {"reference": "Device/mdt-copilot"}}],
        "entity": [{"role": "source", "what": {"reference": f"DocumentReference/{doc_id}"}}],
    }
    return [doc, *observations, provenance]

