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
from services.ai_service import BaseAIProvider, provider_for_patient
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
GP_PROMPT = """Napiš stručnou zprávu pro praktického (odesílajícího) lékaře o výsledku onkologické komise: česky,
odborně a věcně, 3 až 6 vět: co komise posoudila, léčebný záměr a doporučený postup, doplňující vyšetření,
co má zajistit ošetřující lékař a kdy se případ znovu projedná. Vycházej jen ze zápisu komise, nic nepřidávej
a nic neslibuj. Ke každé větě uveď Evidence ID z hranatých závorek."""
INTENT_GP = {"kurativni": "kurativní", "paliativni": "paliativní", "odlozeno": "odloženo do doplnění diagnostiky"}
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


class GpReportOutput(BaseModel):
    """Zpráva pro praktického lékaře (BONUS C, T-332)."""
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


def _gp_fallback(decision: dict, sections: dict[str, str]) -> list[dict]:
    """Bez LLM: zpráva pro praktického lékaře ze schváleného zápisu, věta po sekci, bez domýšlení."""
    s, items = decision["sections"], []

    def add(text: str, section: str) -> None:
        if section in sections and text.strip():
            items.append({"kind": "claim", "text": text, "citations": [sections[section]], "_computed": True})

    add(f"Komise projednala: {s['question']['text'].strip().rstrip('.')}.", "Projednaná otázka")
    add(f"Léčebný záměr: {INTENT_GP[s['intent']]}.", "Léčebný záměr")
    if s["recommendation"]:
        add("Postup podle komise: " + "; ".join(r["text"].strip().rstrip(".") for r in s["recommendation"]) + ".",
            "Doporučený postup")
    if s.get("extra_diagnostics"):
        add(f"Doplňující diagnostika: {s['extra_diagnostics']['text'].strip()}", "Doplňující diagnostika")
    if s.get("re_mdt"):
        add(f"Opětovné projednání komisí {s['re_mdt']['date']}: {s['re_mdt']['reason'].strip()}", "Plánované re-MDT")
    add(f"Závěr MDT: {s['conclusion']['text'].strip()}", "Závěr MDT")
    return items


def _composition_items(decision: dict, resources: list[dict], studies: list[dict], provider: BaseAIProvider,
                       log_call: Callable[[str, dict], Any], *, prompt: str, schema: type[BaseModel], purpose: str,
                       prefix: str, with_proms: bool,
                       fallback: Callable[[dict, dict[str, str], dict | None], list[dict]]) -> list[dict]:
    """Společné jádro shrnutí ze zápisu komise: LLM jen nad odstavci zápisu (a dotazníkem), citace jen z nich,
    jinak věty bez LLM; vše přes grounding validátor."""
    composition_id = decision["fhir_ids"]["composition"]
    pid = composition_id.rsplit("-mdt", 1)[0]
    context = context_from_resources(pid, resources, studies=studies)
    sections = _section_ids(context, composition_id)
    data = PatientData(resources)
    last = data.proms[-1] if data.proms and with_proms else None
    proms = {**data.answers(last), "id": last["id"]} if last else None

    items: list[dict] = []
    if not provider.is_mock or schema.__name__ in getattr(provider, "responses", {}):
        lines = [f"[{line.id}] {line.text}" for line in context.evidence if line.resource_id == composition_id and "#" in line.id]
        if proms:
            lines.append(f"[{proms['id']}] Dotazník: priorita {proms.get('priorita', '–')}; přání: {proms.get('postoj', '–')}")
        result = provider.generate("\n".join(lines), system_prompt=prompt, response_schema=schema, temperature=0.2)
        log_call(purpose, result)
        allowed = set(sections.values()) | ({proms["id"]} if proms else set())
        for item in (result.get("data") or {}).get("items") or [] if result.get("status") == "success" else []:
            cites = [c for c in dict.fromkeys(item.get("citations") or []) if c in allowed]
            if item.get("text", "").strip() and cites:
                items.append({"kind": "claim", "text": item["text"].strip(), "citations": cites})
    if not items:
        items = fallback(decision, sections, proms)
    items = [{"id": f"{prefix}-{i:02d}", **item} for i, item in enumerate(items, 1)]
    return [{k: v for k, v in c.items() if not k.startswith("_")} for c in verify_claims(items, context)]


def build_patient_summary(decision: dict, resources: list[dict], studies: list[dict], provider: BaseAIProvider,
                          log_call: Callable[[str, dict], Any]) -> list[dict]:
    """Čisté jádro: potvrzený závěr + resources z IRIS (s Composition) → ověřená tvrzení shrnutí."""
    return _composition_items(decision, resources, studies, provider, log_call, prompt=PROMPT,
                              schema=PatientSummaryOutput, purpose="patient_summary", prefix="patient-summary",
                              with_proms=True, fallback=_fallback)


def build_gp_report(decision: dict, resources: list[dict], studies: list[dict], provider: BaseAIProvider,
                    log_call: Callable[[str, dict], Any]) -> list[dict]:
    """Zpráva pro praktického lékaře (T-332): odborná, ze stejného potvrzeného zápisu, každá věta s citací."""
    return _composition_items(decision, resources, studies, provider, log_call, prompt=GP_PROMPT,
                              schema=GpReportOutput, purpose="gp_report", prefix="gp-report", with_proms=False,
                              fallback=lambda d, s, _proms: _gp_fallback(d, s))


def store_summary(patient_id: str, composition_id: str, items: list[dict], *, suffix: str = "pacient",
                  title: str = "Shrnutí MDT pro pacienta") -> str:
    from services.fhir import client as fhir

    rid = f"{composition_id}-{suffix}"
    text = "\n\n".join(i["text"] for i in items)
    fhir.put({
        "resourceType": "DocumentReference", "id": rid, "status": "current",
        "type": {"text": title}, "subject": {"reference": f"Patient/{patient_id}"},
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
    provider = provider or provider_for_patient(resources)
    items = build_patient_summary(decision.content, resources, studies, provider, log_call or _llm_call_log)
    progress(65)
    gp_items = build_gp_report(decision.content, resources, studies, provider, log_call or _llm_call_log)
    composition_id = decision.content["fhir_ids"]["composition"]
    rid = store_summary(case.patient_fhir_id, composition_id, items)
    gp_rid = store_summary(case.patient_fhir_id, composition_id, gp_items, suffix="pl",
                           title="Zpráva MDT pro praktického lékaře")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    content = {**decision.content,
               "patient_summary": {"items": items, "generated_at": now, "document_reference": rid},
               "gp_report": {"items": gp_items, "generated_at": now, "document_reference": gp_rid},
               "fhir_ids": {**decision.content["fhir_ids"], "document_reference_patient": rid,
                            "document_reference_gp": gp_rid}}
    decision.content = DecisionSchema.model_validate(content).model_dump(mode="json")
    decision.fhir_ids = {**decision.fhir_ids, "document_reference_patient": rid,
                         "document_reference_gp": gp_rid}                       # export čte model
    decision.save(update_fields=["content", "fhir_ids", "updated_at"])
    progress(100)
    return {"result_id": decision.pk, "document_reference": rid}

