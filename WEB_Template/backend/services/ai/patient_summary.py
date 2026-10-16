"""Shrnutí pro pacienta v laickém jazyce (BON-4, T-306).

Vzniká až z **potvrzeného** závěru (`Composition/Pxx-mdtNN` v IRIS) a zohlední, co pacient v dotazníku uvedl
jako prioritu (`priorita`: délka vs. kvalita života) a co chce, aby lékaři věděli (`postoj`). Každá věta má
citaci (odstavec zápisu nebo dotazník) a projde grounding validátorem. Uloží se jako
`DocumentReference/Pxx-mdtNN-pacient` a do `Decision.patient_summary`; je v PDF i FHIR exportu.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, Field

from services.ai.context_builder import PatientContext, context_from_resources, load_resources
from services.ai.grounding import verify_claims
from services.ai_service import BaseAIProvider, get_ai_provider
from services.rules.red_flags import PatientData

PROMPT = """Napiš shrnutí výsledku onkologické komise pro pacienta: česky, laicky, vlídně, bez latinských
zkratek a bez čísel, která pacient nepotřebuje. 3 až 6 krátkých vět: co komise zjistila, jaký je cíl léčby,
co se navrhuje, co bude následovat a kdy se případ znovu projedná. Zohledni, co je pro pacienta důležité
(priorita a jeho přání z dotazníku). Vycházej jen ze zápisu komise a dotazníku, nic nepřidávej, nic
neslibuj. Ke každé větě uveď Evidence ID z hranatých závorek."""
INTENT_LAY = {
    "kurativni": "Cílem léčby je nemoc vyléčit.",
    "paliativni": "Cílem léčby je zmírnit obtíže, zpomalit nemoc a zachovat co nejlepší kvalitu života.",
    "odlozeno": "Rozhodnutí o léčbě komise odložila, než se doplní potřebná vyšetření.",
}
PRIORITY_LAY = {
    "delka": "V dotazníku jste uvedl(a), že je pro vás nejdůležitější co nejdelší život.",
    "kvalita": "V dotazníku jste uvedl(a), že je pro vás nejdůležitější kvalita života.",
    "oboji": "V dotazníku jste uvedl(a), že je pro vás stejně důležitá délka i kvalita života.",
    "nevim": "V dotazníku jste uvedl(a), že prioritu léčby chcete probrat s lékařem.",
}


class SummarySentence(BaseModel):
    text: str
    citations: list[str] = Field(description="Evidence ID odstavců zápisu komise nebo dotazníku")


class PatientSummaryOutput(BaseModel):
    items: list[SummarySentence]


def _section_ids(context: PatientContext, composition_id: str) -> dict[str, str]:
    """Název sekce zápisu („Léčebný záměr“) → Evidence ID jejího odstavce (`P03-mdt02#3`)."""
    out = {}
    for line in context.evidence:
        if line.resource_id == composition_id and "#" in line.id:
            out.setdefault(line.text.split(":", 1)[0].strip(), line.id)
    return out


def _fallback(decision: dict, sections: dict[str, str], proms: dict | None) -> list[dict]:
    """Bez LLM: věty ze schváleného zápisu (bez domýšlení), cíl léčby a priorita pacienta laicky."""
    s, items = decision["sections"], []
    if "Léčebný záměr" in sections:
        items.append((INTENT_LAY[s["intent"]], [sections["Léčebný záměr"]]))
    if s["recommendation"] and "Doporučený postup" in sections:
        items.append(("Komise navrhuje: " + "; ".join(r["text"] for r in s["recommendation"]) + ".",
                      [sections["Doporučený postup"]]))
    if s.get("re_mdt") and "Plánované re-MDT" in sections:
        items.append((f"Komise váš případ znovu projedná {s['re_mdt']['date']}.", [sections["Plánované re-MDT"]]))
    if proms and proms.get("priorita") in PRIORITY_LAY:
        items.append((PRIORITY_LAY[proms["priorita"]], [proms["id"]]))
    return [{"kind": "claim", "text": text, "citations": cites, "_computed": True} for text, cites in items]


def build_patient_summary(decision: dict, resources: list[dict], studies: list[dict], provider: BaseAIProvider,
                          log_call: Callable[[str, dict], Any]) -> list[dict]:
    """Čisté jádro: potvrzený závěr + resources z IRIS (s Composition) → ověřená tvrzení shrnutí."""
    composition_id = decision["fhir_ids"]["composition"]
    pid = composition_id.rsplit("-mdt", 1)[0]
    context = context_from_resources(pid, resources, studies=studies)
    sections = _section_ids(context, composition_id)
    data = PatientData(resources)
    last = data.proms[-1] if data.proms else None
    proms = {**data.answers(last), "id": last["id"]} if last else None

    items: list[dict] = []
    if not provider.is_mock or "PatientSummaryOutput" in getattr(provider, "responses", {}):
        lines = [f"[{line.id}] {line.text}" for line in context.evidence if line.resource_id == composition_id and "#" in line.id]
        if proms:
            lines.append(f"[{proms['id']}] Dotazník: priorita {proms.get('priorita', '–')}; přání: {proms.get('postoj', '–')}")
        result = provider.generate("\n".join(lines), system_prompt=PROMPT, response_schema=PatientSummaryOutput,
                                   temperature=0.2)
        log_call("patient_summary", result)
        allowed = set(sections.values()) | ({proms["id"]} if proms else set())
        for item in (result.get("data") or {}).get("items") or [] if result.get("status") == "success" else []:
            cites = [c for c in dict.fromkeys(item.get("citations") or []) if c in allowed]
            if item.get("text", "").strip() and cites:
                items.append({"kind": "claim", "text": item["text"].strip(), "citations": cites})
    if not items:
        items = _fallback(decision, sections, proms)
    items = [{"id": f"patient-summary-{i:02d}", **item} for i, item in enumerate(items, 1)]
    return [{k: v for k, v in c.items() if not k.startswith("_")} for c in verify_claims(items, context)]


def store_summary(patient_id: str, composition_id: str, items: list[dict]) -> str:
    from services.fhir import client as fhir

    rid = f"{composition_id}-pacient"
    text = "\n\n".join(i["text"] for i in items)
    fhir.put({
        "resourceType": "DocumentReference", "id": rid, "status": "current",
        "type": {"text": "Shrnutí MDT pro pacienta"}, "subject": {"reference": f"Patient/{patient_id}"},
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "content": [{"attachment": {"contentType": "text/plain; charset=utf-8",
                                    "data": base64.b64encode(text.encode("utf-8")).decode(), "title": f"{rid}.txt"}}],
        "context": {"related": [{"reference": f"Composition/{composition_id}"}]},
        "meta": {"tag": [{"system": "https://rakathon.example.org/fhir/CodeSystem/ai-generated", "code": "ai"}]},
    })
    return rid


def generate_patient_summary(case, params: dict, progress: Callable[[int], None], *,
                             provider: BaseAIProvider | None = None,
                             log_call: Callable[[str, dict], Any] | None = None) -> dict:
    """Job (T-107): potvrzený závěr → shrnutí → IRIS + `Decision.content.patient_summary`."""
    from apps.copilot.schemas import Decision as DecisionSchema
    from apps.mdt.models import Decision
    from services.ai.brief import _llm_call_log

    decision = Decision.objects.get(case=case)
    if decision.status != "confirmed" or not (decision.content.get("fhir_ids") or {}).get("composition"):
        raise RuntimeError("Shrnutí pro pacienta vzniká až z potvrzeného závěru (FR-C3).")
    progress(10)
    resources, studies = load_resources(case.patient_fhir_id)
    progress(40)
    items = build_patient_summary(decision.content, resources, studies, provider or get_ai_provider(),
                                  log_call or _llm_call_log)
    composition_id = decision.content["fhir_ids"]["composition"]
    rid = store_summary(case.patient_fhir_id, composition_id, items)
    content = {**decision.content,
               "patient_summary": {"items": items, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                   "document_reference": rid},
               "fhir_ids": {**decision.content["fhir_ids"], "document_reference_patient": rid}}
    decision.content = DecisionSchema.model_validate(content).model_dump(mode="json")
    decision.fhir_ids = {**decision.fhir_ids, "document_reference_patient": rid}       # export čte model
    decision.save(update_fields=["content", "fhir_ids", "updated_at"])
    progress(100)
    return {"result_id": decision.pk, "document_reference": rid}

