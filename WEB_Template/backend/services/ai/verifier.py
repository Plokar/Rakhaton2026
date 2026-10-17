"""Second-model review of grounded claims; never rewrites text or promotes verification."""
from __future__ import annotations

import json
import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from services.ai.grounding import source_text
from services.ai_service import prompt_hash, verifier_model

log = logging.getLogger(__name__)
PROMPT = (Path(__file__).parent / "prompts" / "verifier.md").read_text(encoding="utf-8")
BATCH_SIZE = 20


class VerifierVerdict(BaseModel):
    claim_id: str
    verdict: Literal["supported", "unsupported", "uncertain"]
    issue: str = ""


class VerifierOutput(BaseModel):
    verdicts: list[VerifierVerdict]


def cross_check(claims, context, provider, log_call):
    """Mutate eligible claims in place, returning coverage and issues for the public Brief."""
    eligible = [c for c in claims if c.get("kind") == "claim" and c.get("verification") == "verified"
                and not c.get("_computed")]
    model = verifier_model()
    summary = {"status": "off" if provider is None else "ok", "model": model,
               "checked": 0, "rejected": 0, "unchecked": len(eligible), "issues": []}
    if provider is None or not eligible:
        return summary

    def review(batch):
        sources = {citation: source_text(context, citation) for c in batch for citation in c.get("citations", [])}
        prompt = json.dumps({"claims": [{"claim_id": c["id"], "text": c["text"],
                                          "citations": c.get("citations", [])} for c in batch],
                             "sources": sources}, ensure_ascii=False)
        try:
            result = provider.generate(prompt, system_prompt=PROMPT, model=model,
                                       temperature=0, response_schema=VerifierOutput)
        except Exception as exc:
            result = {"status": "error", "error": f"Verifier: {type(exc).__name__}", "model": model,
                      "provider": provider.provider_name, "is_mock": provider.is_mock,
                      "prompt_hash": prompt_hash(prompt, PROMPT)}
        try:
            log_call("brief.verifier", result)
        except Exception:
            log.exception("Nepodařilo se zapsat audit brief.verifier")
        if result.get("status") != "success":
            return batch, [], "Volání druhé AI selhalo"
        try:
            verdicts = VerifierOutput.model_validate(result.get("data")).verdicts
        except (ValueError, TypeError):
            return batch, [], "Druhá AI vrátila neplatnou odpověď"
        return batch, verdicts, "Chybí jednoznačný verdikt druhé AI"

    batches = [eligible[i:i + BATCH_SIZE] for i in range(0, len(eligible), BATCH_SIZE)]
    claim_counts = Counter(c["id"] for c in eligible)
    with ThreadPoolExecutor(max_workers=min(4, len(batches))) as pool:
        for batch, verdicts, failure in pool.map(review, batches):
            counts = Counter(v.claim_id for v in verdicts)
            by_id = {v.claim_id: v for v in verdicts if counts[v.claim_id] == 1}
            for claim in batch:
                verdict = by_id.get(claim["id"]) if claim_counts[claim["id"]] == 1 else None
                if verdict is None:
                    summary["issues"].append({"claim_id": claim["id"], "verdict": "unchecked", "issue": failure})
                    continue
                summary["checked"] += 1
                summary["unchecked"] -= 1
                if verdict.verdict == "supported":
                    continue
                issue = verdict.issue.strip() or "Tvrzení nemá jednoznačnou oporu v citovaných zdrojích"
                if verdict.verdict == "uncertain":
                    issue = f"NEJISTOTA AI: {issue}"
                claim["verification"] = "unverified"
                claim["_grounding"] = [*(claim.get("_grounding") or []), f"Druhá AI ({model}): {issue}"]
                summary["rejected"] += 1
                summary["issues"].append({"claim_id": claim["id"], "verdict": verdict.verdict, "issue": issue})
    summary["status"] = ("ok" if not summary["unchecked"] else "partial" if summary["checked"] else "error")
    return summary
