"""
Druhá AI: nezávislá kontrola tvrzení první AI (ARCHITEKTURA §5.3 bod 7, T-331).

Grounding validátor (`grounding.py`) hlídá citace, čísla, data a vektorovou podobnost. Neodhalí ale tvrzení,
které má správná čísla a špatný význam („progrese“ místo „parciální odpovědi“, záměna strany, domyšlený závěr).
Proto po groundingu dostane druhý model (`VERIFIER_MODEL`, výchozí `gpt-6-astra` přes APIM) tvrzení napsaná LLM
spolu s plným zněním citovaných zdrojů a vrátí verdikt `supported` / `unsupported` / `uncertain`.

- Kontrolují se jen tvrzení `kind: "claim"`, která grounding ověřil a která psal LLM (ne `_computed`, ne časová osa
  a hlavička z FHIR). Neověřené už varování mají.
- `unsupported` i `uncertain` → `verification: "unverified"` (AI nikdy neodhaduje); důvod jde do `Brief.verifier.issues`.
- Chybějící verdikt nebo selhání volání tvrzení nemění (kontrola je navíc, nesmí shodit podklad); vidět je to
  ve `Brief.verifier.status` a `unchecked`.
- Ověřovatel nikdy text nepřepisuje ani nepřidává tvrzení, jen označuje.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

from pydantic import BaseModel, Field

from services.ai.context_builder import PatientContext
from services.ai.grounding import source_text
from services.ai_service import BaseAIProvider, verifier_model

log = logging.getLogger(__name__)

PROMPT = (Path(__file__).parent / "prompts" / "verifier.md").read_text(encoding="utf-8")
BATCH_SIZE = 20                 # tvrzení na jedno volání (podklad má typicky 20–60 tvrzení z LLM)
SOURCE_LIMIT = 4000             # znaků zdrojů na tvrzení


class Verdict(BaseModel):
    claim_id: str = Field(description="claim_id ze vstupu")
    verdict: Literal["supported", "unsupported", "uncertain"]
    issue: str = Field(default="", description="Co nesedí, jednou větou česky; u supported prázdné")


class VerifierOutput(BaseModel):
    verdicts: list[Verdict]


def checkable(claim: dict) -> bool:
    return claim.get("kind") == "claim" and claim.get("verification") == "verified" and not claim.get("_computed")


def cross_check(claims: Iterable[dict], context: PatientContext, provider: BaseAIProvider | None,
                log_call: Callable[[str, dict], Any] = lambda purpose, result: None) -> dict:
    """Označí tvrzení, která druhá AI nepotvrdila (mění `verification` v místě). Vrátí `Brief.verifier` (§8.2)."""
    targets = [c for c in claims if checkable(c)]
    if provider is None:
        return {"status": "off", "model": None, "checked": 0, "rejected": 0, "unchecked": len(targets), "issues": []}
    model = "mock" if provider.is_mock else (getattr(provider, "model_name", None) or verifier_model())
    if not targets:
        return {"status": "ok", "model": model, "checked": 0, "rejected": 0, "unchecked": 0, "issues": []}

    by_key = {f"c{i}": claim for i, claim in enumerate(targets, 1)}      # id tvrzení nemusí být v podkladu unikátní
    keys = list(by_key)
    batches = [keys[i:i + BATCH_SIZE] for i in range(0, len(keys), BATCH_SIZE)]
    with ThreadPoolExecutor(max_workers=min(4, len(batches))) as pool:
        results = list(pool.map(lambda batch: _check_batch(batch, by_key, context, provider, log_call), batches))

    verdicts: dict[str, dict] = {}
    failed = False
    for result in results:
        if result is None:
            failed = True
            continue
        verdicts.update(result)
    issues = []
    for key, claim in by_key.items():
        verdict = verdicts.get(key)
        if verdict is None or verdict["verdict"] == "supported":
            continue
        claim["verification"] = "unverified"
        reason = verdict.get("issue") or ("druhá AI tvrzení nepotvrdila" if verdict["verdict"] == "unsupported"
                                          else "NEJISTOTA AI: zdroje nejsou jednoznačné")
        claim.setdefault("_grounding", []).append(f"druhá AI ({verdict['verdict']}): {reason}")
        issues.append({"claim_id": claim.get("id", ""), "verdict": verdict["verdict"], "issue": reason})
    checked = len(verdicts)
    return {
        "status": "error" if failed and not checked else "partial" if failed or checked < len(targets) else "ok",
        "model": model,
        "checked": checked,
        "rejected": len(issues),
        "unchecked": len(targets) - checked,
        "issues": issues,
    }


def _check_batch(batch: list[str], by_key: dict[str, dict], context: PatientContext, provider: BaseAIProvider,
                 log_call) -> dict[str, dict] | None:
    prompt = "\n\n".join(_render(key, by_key[key], context) for key in batch)
    result = provider.generate(prompt, system_prompt=PROMPT, response_schema=VerifierOutput, temperature=0.0)
    log_call("brief.verifier", result)
    if result.get("status") != "success":
        log.warning("Druhá AI (ověřovatel) selhala: %s", result.get("error"))
        return None
    wanted = set(batch)
    return {v["claim_id"]: v for v in (result.get("data") or {}).get("verdicts", []) if v.get("claim_id") in wanted}


def _render(key: str, claim: dict, context: PatientContext) -> str:
    sources = "\n".join(text for c in claim.get("citations") or [] if (text := _source(context, c)))
    if len(sources) > SOURCE_LIMIT:
        sources = sources[:SOURCE_LIMIT] + " …"
    return f"claim_id: {key}\ntvrzení: {claim.get('text', '')}\ncitované zdroje:\n{sources or '(žádný text zdroje)'}"


def _source(context: PatientContext, evidence_id: str) -> str:
    text = source_text(context, evidence_id).strip()
    return "\n".join(f"[{evidence_id}] {line}" for line in text.splitlines() if line.strip()) if text else ""
