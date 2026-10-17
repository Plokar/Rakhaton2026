"""AI zapisovatel (BON-3, T-305, ARCHITEKTURA §5.6).

Nahrávka nebo přepis diskuse komise → přepis s mluvčími a časy → `DocumentReference/Pxx-mdtNN-prepis` v IRIS
→ **draft** závěru (`Decision` §8.4) s citacemi na úseky přepisu (`Pxx-mdtNN-prepis#n`) a fakta pacienta.
Nic se nestane oficiálním záznamem: draft edituje a potvrzuje předseda (FR-C3).

Rozhraní jobu (T-107): `generate_scribe(case, params, progress) -> {"result_id": Decision.pk, ...}`, kde
`params` je `{"audio_b64", "mime_type"}`, `{"segments": [...]}` nebo `{"transcript": "text"}`.
"""
from __future__ import annotations

import base64
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from apps.copilot.schemas import Decision as DecisionSchema
from services.ai.abbreviations import prompt_rules
from services.ai.context_builder import PatientContext, context_from_resources, load_resources
from services.ai_service import BaseAIProvider, get_ai_provider, transcription_provider

log = logging.getLogger(__name__)

SPEAKER_ROLES = {"předseda": "chair", "onkolog": "oncologist", "chirurg": "surgeon", "radiolog": "radiologist",
                 "patolog": "pathologist", "radiační onkolog": "radiation_oncologist", "radioterapeut": "radiation_oncologist",
                 "pneumolog": "pulmonologist", "kardiolog": "cardiologist", "pacient": "patient"}
LINE = re.compile(r"^\s*(?:\[?(\d{1,2}:\d{2})\]?\s*)?([^:]{2,40}):\s*(.+)$")
INTENT = {"C": "kurativni", "P": "paliativni"}

PROMPT = """Jsi zapisovatel multidisciplinární onkologické komise. Z přepisu diskuse vytvoř návrh záznamu MDT
ve struktuře záznamu z datasetu. Zapisuj jen to, co v diskusi zaznělo; nic nedomýšlej a nic nedoporučuj sám.
Každé tvrzení cituj Evidence ID úseku přepisu z hranatých závorek (např. P03-mdt02-prepis#4), u faktů pacienta
i ID z kontextu. Úkoly: popis, vlastník (role nebo LEK-…), termín YYYY-MM-DD, jen pokud zazněl. Re-MDT jen když
zaznělo datum. Léčebný záměr: kurativni / paliativni / odlozeno podle závěru komise."""


class CitedLine(BaseModel):
    text: str
    citations: list[str] = Field(default_factory=list)


class ScribeRecommendation(BaseModel):
    modality: str = Field(description="mdt-modalita: chirurgie, chemoterapie, cilena, imunoterapie, hormonalni, rt, diagnostika, jina-systemova")
    text: str
    citations: list[str] = Field(default_factory=list)


class ScribeTask(BaseModel):
    description: str
    owner: str = Field(description="Role nebo LEK-…")
    due_date: str | None = Field(default=None, description="YYYY-MM-DD, jen pokud zazněl")
    citations: list[str] = Field(default_factory=list)


class ScribeTrial(BaseModel):
    text: str
    study_ids: list[str] = Field(default_factory=list)


class ScribeReMdt(BaseModel):
    date: str = Field(description="YYYY-MM-DD")
    reason: str


class ScribeDraft(BaseModel):
    mdt_type: Literal["primarni", "progrese", "restaging"] = "restaging"
    assessment: CitedLine
    intent: Literal["kurativni", "paliativni", "odlozeno"]
    recommendation: list[ScribeRecommendation] = Field(default_factory=list)
    extra_diagnostics: CitedLine | None = None
    trial: ScribeTrial | None = None
    re_mdt: ScribeReMdt | None = None
    conclusion: CitedLine
    tasks: list[ScribeTask] = Field(default_factory=list)


# ── přepis ────────────────────────────────────────────────────────────────────
def parse_transcript(text: str) -> list[dict]:
    """Textový přepis „[MM:SS] mluvčí: text“ (čas volitelný) → segmenty; řádek bez mluvčího patří k předchozímu."""
    segments: list[dict] = []
    for raw in (text or "").splitlines():
        if not raw.strip():
            continue
        match = LINE.match(raw)
        if match and (segments == [] or match.group(2).strip().lower() in SPEAKER_ROLES or match.group(1)):
            segments.append({"speaker": match.group(2).strip(), "start": match.group(1) or "", "text": match.group(3).strip()})
        elif segments:
            segments[-1]["text"] += " " + raw.strip()
        else:
            segments.append({"speaker": "neuvedeno", "start": "", "text": raw.strip()})
    return segments


class SpeakerLabels(BaseModel):
    speakers: list[str] = Field(description="Role mluvčího každého úseku ve stejném pořadí a počtu jako úseky")


SPEAKER_PROMPT = """Přepis diskuse onkologické komise je bez mluvčích. Každému úseku [n] přiřaď roli mluvčího podle obsahu
a návaznosti: předseda, onkolog, chirurg, radiolog, patolog, radiační onkolog, pneumolog, kardiolog, pacient.
Předseda uvádí pacienta, řídí diskusi a shrnuje závěr. Když roli nejde poznat, napiš „neuvedeno“; nic nedomýšlej.
Vrať seznam rolí ve stejném pořadí a počtu jako úseky."""


def label_speakers(segments: list[dict], provider: BaseAIProvider, log_call: Callable[[str, dict], Any]) -> list[dict]:
    """Role mluvčích k úsekům bez mluvčího (Whisper) z obsahu přes LLM; když se nepovede, „neuvedeno“."""
    labels: list[str] = []
    if not provider.is_mock or "SpeakerLabels" in getattr(provider, "responses", {}):
        result = provider.generate("\n".join(f"[{i}] {s['start']} {s['text']}" for i, s in enumerate(segments, 1)),
                                   system_prompt=SPEAKER_PROMPT, response_schema=SpeakerLabels, temperature=0.0)
        log_call("scribe.speakers", result)
        labels = (result.get("data") or {}).get("speakers") or [] if result.get("status") == "success" else []
    if len(labels) != len(segments):
        labels = [""] * len(segments)
    return [{**s, "speaker": label.strip().lower() or "neuvedeno"} for s, label in zip(segments, labels)]


def transcript_text(segments: list[dict]) -> str:
    """Text `DocumentReference` přepisu: úsek = odstavec, takže `#n` = n-tý úsek (services/ai/text.py)."""
    return "\n\n".join(f"{s.get('start') or '--:--'} {s['speaker']}: {s['text']}" for s in segments)


def store_transcript(patient_id: str, transcript_id: str, service_request_id: str, segments: list[dict]) -> None:
    """Přepis jako `DocumentReference` navázaný na nominaci (`Composition` vznikne až potvrzením, T-209)."""
    from services.fhir import client as fhir

    data = base64.b64encode(transcript_text(segments).encode("utf-8")).decode()
    fhir.put({
        "resourceType": "DocumentReference", "id": transcript_id, "status": "current",
        "type": {"text": "Přepis diskuse MDT"}, "subject": {"reference": f"Patient/{patient_id}"},
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),   # FHIR instant
        "content": [{"attachment": {"contentType": "text/plain; charset=utf-8", "data": data,
                                    "title": f"{transcript_id}.txt"}}],
        "context": {"related": [{"reference": f"ServiceRequest/{service_request_id}"}]},
        "meta": {"tag": [{"system": "https://rakathon.example.org/fhir/CodeSystem/ai-generated", "code": "ai"}]},
    })


# ── draft závěru ──────────────────────────────────────────────────────────────
def build_draft(case_id: str, question: str, intent_letter: str | None, segments: list[dict], transcript_id: str,
                context: PatientContext | None, provider: BaseAIProvider, log_call: Callable[[str, dict], Any],
                mdt_date: date | None = None) -> dict:
    """Čisté jádro: segmenty přepisu → validní draft `Decision` (§8.4). Citace mimo přepis a kontext se zahodí."""
    seg_ids = [f"{transcript_id}#{i}" for i in range(1, len(segments) + 1)]
    allowed = set(seg_ids) | (context.allowed_ids if context else set())
    prompt = "\n".join(f"[{sid}] {s.get('start', '')} {s['speaker']}: {s['text']}" for sid, s in zip(seg_ids, segments))
    if context:
        prompt += "\n\n## Kontext pacienta\n" + context.render()
    draft = None
    # Mock bez zaregistrované odpovědi by vrátil prázdnou kostru („mock“), proto rovnou fallback.
    if not provider.is_mock or "ScribeDraft" in getattr(provider, "responses", {}):
        result = provider.generate(prompt, system_prompt=f"{PROMPT}\n\n{prompt_rules()}", response_schema=ScribeDraft,
                                   temperature=0.1)
        log_call("scribe.decision", result)
        draft = result.get("data") if result.get("status") == "success" else None
    if not draft or not (draft.get("conclusion") or {}).get("text", "").strip():
        draft = _fallback_draft(segments, seg_ids, intent_letter)

    def cites(items):
        return [c for c in dict.fromkeys(items or []) if c in allowed]

    re_mdt = draft.get("re_mdt") if _is_date((draft.get("re_mdt") or {}).get("date")) else None
    default_due = (re_mdt or {}).get("date") or ((mdt_date or date.today()) + timedelta(days=14)).isoformat()
    sections = {
        "question": {"text": question, "source": "human"},
        "assessment": {"text": draft["assessment"]["text"], "source": "ai",
                       "citations": cites(draft["assessment"].get("citations")) or seg_ids[:1]},
        "intent": draft["intent"],
        "recommendation": [{"modality": r["modality"], "text": r["text"], "source": "ai"}
                           for r in draft.get("recommendation") or []],
        "conclusion": {"text": draft["conclusion"]["text"], "source": "ai"},
    }
    if (draft.get("extra_diagnostics") or {}).get("text"):
        sections["extra_diagnostics"] = {"text": draft["extra_diagnostics"]["text"], "source": "ai"}
    if (draft.get("trial") or {}).get("text"):
        sections["trial"] = {"text": draft["trial"]["text"], "source": "ai",
                             "study_ids": [s for s in draft["trial"].get("study_ids") or [] if re.match(r"^RKT-\d{2}$", s)]}
    if re_mdt:
        sections["re_mdt"] = {"date": re_mdt["date"], "reason": re_mdt.get("reason", "")}
    tasks = [{"id": f"task{i:02d}", "description": t["description"], "owner": t["owner"],
              "due_date": t["due_date"] if _is_date(t.get("due_date")) else default_due,
              "status": "requested", "source": "ai"}
             for i, t in enumerate(draft.get("tasks") or [], 1) if t.get("description", "").strip()]
    decision = {
        "case_id": case_id, "status": "draft", "mdt_type": draft.get("mdt_type") or "restaging",
        "attendees": _attendees(segments), "patient_present": any(s["speaker"].lower() == "pacient" for s in segments),
        "sections": sections, "tasks": tasks, "red_flags_acknowledged": [], "transcript_ref": transcript_id,
        "confirmed_by": None, "confirmed_at": None, "fhir_ids": None,
    }
    return DecisionSchema.model_validate(decision).model_dump(mode="json")


def _is_date(value: str | None) -> bool:
    return bool(value and re.match(r"^\d{4}-\d{2}-\d{2}$", value))


def _attendees(segments: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for s in segments:
        role = SPEAKER_ROLES.get(s["speaker"].lower())
        if role and role != "patient" and s["speaker"] not in seen:
            seen[s["speaker"]] = {"user_id": "", "name": s["speaker"], "role": role}
    return list(seen.values())


def _fallback_draft(segments: list[dict], seg_ids: list[str], intent_letter: str | None) -> dict:
    """Bez LLM (mock, chyba): nic se nevymýšlí, závěr = poslední slovo předsedy s citací, zbytek doplní předseda."""
    chair = [i for i, s in enumerate(segments) if s["speaker"].lower() == "předseda"] or [len(segments) - 1]
    last = chair[-1]
    return {
        "assessment": {"text": "Návrh z přepisu bez AI; klinické zhodnocení doplní předseda.", "citations": seg_ids[:1]},
        "intent": INTENT.get(intent_letter or "", "odlozeno"),
        "conclusion": {"text": segments[last]["text"], "citations": [seg_ids[last]]},
    }


# ── job ───────────────────────────────────────────────────────────────────────
def generate_scribe(case, params: dict, progress: Callable[[int], None], *, provider: BaseAIProvider | None = None,
                    log_call: Callable[[str, dict], Any] | None = None) -> dict:
    from apps.mdt.models import Decision
    from services.ai.brief import _llm_call_log
    from services.fhir import writeback

    provider = provider or get_ai_provider()
    log_call = log_call or _llm_call_log
    progress(5)
    segments = params.get("segments") or parse_transcript(params.get("transcript", ""))
    if params.get("audio_b64"):
        result = transcription_provider(provider).transcribe(base64.b64decode(params["audio_b64"]),
                                                              params.get("mime_type") or "audio/mp4")
        log_call("scribe.transcribe", result)
        if result.get("status") != "success":
            raise RuntimeError(f"Přepis nahrávky selhal: {result.get('error')}")
        segments = (result.get("data") or {}).get("segments") or []
    if not segments:
        raise ValueError("Přepis je prázdný.")
    progress(30)
    if not any(s["speaker"].strip() for s in segments):            # Whisper (Groq) mluvčí nerozlišuje
        segments = label_speakers(segments, provider, log_call)
    progress(40)
    pid = case.patient_fhir_id
    mdt_id = writeback.next_mdt_id(pid)
    transcript_id = f"{mdt_id}-prepis"
    store_transcript(pid, transcript_id, case.service_request_fhir_id, segments)
    resources, studies = load_resources(pid)
    context = context_from_resources(pid, resources, studies=studies)
    progress(60)
    content = build_draft(str(case.pk), case.question, case.intent, segments, transcript_id, context, provider,
                          log_call, mdt_date=case.session.date.date() if case.session_id else None)
    existing = Decision.objects.filter(case=case).first()
    if existing and existing.status == "confirmed":
        raise RuntimeError("Závěr je potvrzený, zapisovatel ho nemůže přepsat.")
    decision, _ = Decision.objects.update_or_create(case=case, defaults={"content": content, "status": "draft"})
    progress(100)
    return {"result_id": decision.pk, "transcript_ref": transcript_id, "segments": len(segments)}
