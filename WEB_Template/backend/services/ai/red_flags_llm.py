"""
RF-LLM: detekce rozporů mezi zdroji pomocí LLM (ARCHITEKTURA §5.4, T-202).

LLM dostane celý kontext pacienta a už nalezené deterministické flagy. Vrací jen nové
rozpory. Citace kontrolujeme: ID mimo `PatientContext.allowed_ids` nebo méně než dva
zdroje → `verification = "unverified"` (UI ho ukáže s varováním, §5.3). Pasáž guidelines
mimo povolená ID se zahodí.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional, Sequence

from pydantic import BaseModel, Field

from services.ai.context_builder import PatientContext
from services.ai_service import BaseAIProvider, get_ai_provider
from services.rules.red_flags import SEVERITY_ORDER, RedFlag

PROMPT = (Path(__file__).parent / "prompts" / "red_flags.md").read_text(encoding="utf-8")


class LlmRedFlag(BaseModel):
    title: str = Field(description="Krátký název rozporu")
    description: str = Field(description="Oba údaje s hodnotami a daty ze zdrojů")
    severity: Literal["high", "moderate", "low"]
    citations: list[str] = Field(description="ID obou zdrojů, které si odporují (aspoň dvě)")
    guideline: Optional[str] = Field(default=None, description="ID pasáže guidelines z podkladů, např. OBC-1.3")


class LlmRedFlags(BaseModel):
    flags: list[LlmRedFlag]


def detect_llm_red_flags(context: PatientContext, provider: BaseAIProvider | None = None,
                         known: Sequence[RedFlag] | None = None) -> tuple[list[RedFlag], dict]:
    """Vrátí (flagy RF-LLM, výsledek volání pro audit `LlmCallLog`). Při chybě volání prázdný seznam."""
    provider = provider or get_ai_provider()
    known = context.red_flags if known is None else known
    prompt = context.render()
    if known and not context.rule_results:
        prompt += "\n## Výsledky deterministických pravidel\n" + "\n".join(f"- {f.render_line()}" for f in known)
    result = provider.generate(prompt, system_prompt=PROMPT, response_schema=LlmRedFlags, temperature=0.1)
    if result.get("status") != "success":
        return [], result

    allowed = context.allowed_ids
    flags = []
    for i, item in enumerate(result["data"]["flags"], 1):
        citations = tuple(dict.fromkeys(c.strip() for c in item["citations"] if c.strip()))
        verified = len(citations) >= 2 and all(c in allowed for c in citations)
        guideline = item.get("guideline")
        flags.append(RedFlag(
            id=f"RF-LLM:{i}",
            rule="RF-LLM",
            severity=item["severity"],
            title=item["title"],
            description=item["description"],
            citations=citations,
            guideline=guideline if guideline in allowed else None,
            verification="verified" if verified else "unverified",
        ))
    flags.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 9))
    return flags, result
