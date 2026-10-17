"""
Testy AI providerů (T-012). Bez sítě: Gemini se testuje přes podvržený klient.
Živý test proti Gemini je opt-in (AI_LIVE_TESTS=1 + GEMINI_API_KEY, jen placený tier, Q9).
"""
import datetime
import json
import math
import os
from typing import Literal, Optional

import pytest
from google.genai import errors, types
from pydantic import BaseModel, Field

from services import ai_service
from services.ai_service import (
    AIProviderError,
    GeminiProvider,
    MockAIProvider,
    Transcript,
    gemini_json_schema,
    get_ai_provider,
)


# ── Testovací schémata (tvarem podobná kontraktům z ARCHITEKTURA §8) ──────────
class Citation(BaseModel):
    evidence_id: str = Field(min_length=3, description="Evidence ID z datasetu")


class Claim(BaseModel):
    id: str
    kind: Literal["claim", "missing"]
    text: str
    citations: list[str] = Field(min_length=1)
    verification: Literal["verified", "unverified"] = "unverified"


class Ecog(BaseModel):
    value: int = Field(ge=0, le=4)
    date: datetime.date
    citation: Citation = Field(description="Zdroj hodnoty")


class Section(BaseModel):
    id: Literal["summary"]
    ai_generated: Literal[True] = True
    title: str
    items: list[Claim]
    ecog: Optional[Ecog] = None
    physician_ecog: Ecog
    score: float = Field(gt=0.5)


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("GEMINI_API_KEY", "AI_MODEL", "AI_MODEL_STRONG", "EMBEDDING_MODEL", "EMBEDDING_DIM",
                 "TRANSCRIBE_MODEL", "AI_THINKING_LEVEL", "NVIDIA_API_KEY", "GROQ_API_KEY", "EMBEDDING_PROVIDER",
                 "TRANSCRIBE_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AI_PROVIDER", "mock")          # výchozí NVIDIA by bez klíče stejně spadla na mock


# ── Mock ──────────────────────────────────────────────────────────────────────
class TestMockProvider:
    def test_generate_text(self):
        result = MockAIProvider().generate("Shrň pacienta P03")
        assert result["status"] == "success"
        assert result["is_mock"] is True
        assert result["data"] is None
        assert "P03" in result["response"]
        assert len(result["prompt_hash"]) == 64

    def test_generate_returns_schema_valid_json(self):
        result = MockAIProvider().generate("x", response_schema=Section)
        assert result["status"] == "success"
        section = Section.model_validate(result["data"])
        assert section.ai_generated is True
        assert len(section.items) == 0
        assert section.physician_ecog.citation.evidence_id
        assert json.loads(result["response"]) == result["data"]

    def test_generate_uses_registered_response(self):
        canned = {"id": "c1", "kind": "claim", "text": "ECOG 0", "citations": ["P03-ecog03"]}
        result = MockAIProvider(responses={"Claim": canned}).generate("x", response_schema=Claim)
        assert result["data"]["citations"] == ["P03-ecog03"]
        assert result["data"]["verification"] == "unverified"

    def test_generate_registered_callable(self):
        provider = MockAIProvider(responses={
            "Claim": lambda prompt: {"id": "c", "kind": "missing", "text": prompt, "citations": ["P03-zad01"]},
        })
        assert provider.generate("MMR chybí", response_schema=Claim)["data"]["text"] == "MMR chybí"

    def test_generate_invalid_registered_response_is_error(self):
        result = MockAIProvider(responses={"Claim": {"id": "c"}}).generate("x", response_schema=Claim)
        assert result["status"] == "error"
        assert "Claim" in result["error"]

    def test_embed_dimension_and_norm(self):
        vectors = MockAIProvider().embed(["Hemoglobin 98 g/l", "únava 8/10"])
        assert len(vectors) == 2
        for vector in vectors:
            assert len(vector) == 1536
            assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, rel_tol=1e-9)

    def test_embed_respects_env_dim(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_DIM", "768")
        assert len(MockAIProvider().embed(["text"])[0]) == 768

    def test_embed_deterministic_and_similarity(self):
        provider = MockAIProvider()
        a, a2, similar, unrelated = provider.embed([
            "CT hrudníku nebylo požadováno",
            "CT hrudníku nebylo požadováno",
            "CT hrudniku nebylo provedeno",
            "Pacientka užívá třezalku",
        ])
        assert a == a2
        assert cosine(a, similar) > cosine(a, unrelated)

    def test_embed_rejects_bad_input(self):
        with pytest.raises(TypeError):
            MockAIProvider().embed("jeden string")
        with pytest.raises(ValueError):
            MockAIProvider().embed(["ok", "  "])

    def test_transcribe(self):
        result = MockAIProvider().transcribe(b"audio", "audio/mp4")
        assert result["status"] == "success"
        transcript = Transcript.model_validate(result["data"])
        assert transcript.segments[0].start == "00:00"


# ── Schéma pro Gemini ─────────────────────────────────────────────────────────
def _assert_supported(node, allowed):
    if isinstance(node, list):
        for sub in node:
            _assert_supported(sub, allowed)
        return
    if "$ref" in node:
        assert all(k.startswith("$") for k in node), node
    assert set(node) <= allowed, set(node) - allowed
    for key, value in node.items():
        if key in ("properties", "$defs"):     # klíče jsou jména, ne klíčová slova
            for sub in value.values():
                _assert_supported(sub, allowed)
        elif key in ("items", "prefixItems", "additionalProperties", "anyOf", "oneOf"):
            _assert_supported(value, allowed)


class TestGeminiSchema:
    def test_only_supported_keywords(self):
        _assert_supported(gemini_json_schema(Section), ai_service._GEMINI_SCHEMA_KEYS | {"propertyOrdering"})

    def test_const_string_becomes_enum_and_ordering(self):
        schema = gemini_json_schema(Section)
        props = schema["properties"]
        assert props["id"]["enum"] == ["summary"]
        assert "const" not in json.dumps(schema)
        assert "default" not in json.dumps(schema)
        assert schema["propertyOrdering"] == list(props)
        assert props["physician_ecog"] == {"$ref": "#/$defs/Ecog"}


# ── Gemini přes podvržený klient ──────────────────────────────────────────────
def _response(text, finish="STOP", usage=(10, 5, 2)):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(
            content=types.Content(role="model", parts=[types.Part(text=text)]),
            finish_reason=finish,
        )],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=usage[0], candidates_token_count=usage[1], thoughts_token_count=usage[2],
            total_token_count=sum(usage),
        ),
    )


class FakeModels:
    def __init__(self, response=None, error=None, embed_dim=1536):
        self.response, self.error, self.embed_dim = response, error, embed_dim
        self.calls, self.embed_calls = [], []

    def generate_content(self, *, model, contents, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error:
            raise self.error
        return self.response

    def embed_content(self, *, model, contents, config=None):
        self.embed_calls.append({"model": model, "contents": contents, "config": config})
        if self.error:
            raise self.error
        return types.EmbedContentResponse(
            embeddings=[types.ContentEmbedding(values=[2.0] * self.embed_dim) for _ in contents])


class FakeClient:
    def __init__(self, **kwargs):
        self.models = FakeModels(**kwargs)


def gemini(**kwargs):
    return GeminiProvider(api_key="test-key", client=FakeClient(**kwargs))


VALID_CLAIM = {"id": "c1", "kind": "claim", "text": "ECOG 0", "citations": ["P03-ecog03"]}


class TestGeminiProvider:
    def test_generate_structured(self, monkeypatch):
        monkeypatch.setenv("AI_MODEL", "gemini-test-model")
        provider = gemini(response=_response(json.dumps(VALID_CLAIM)))
        result = provider.generate("prompt", system_prompt="Jsi asistent MDT.", response_schema=Claim)

        assert result["status"] == "success"
        assert result["data"] == {**VALID_CLAIM, "verification": "unverified"}
        assert (result["tokens_in"], result["tokens_out"], result["tokens_used"]) == (10, 7, 17)
        assert result["is_mock"] is False

        call = provider.client.models.calls[0]
        config = call["config"]
        assert call["model"] == "gemini-test-model"
        assert config.system_instruction == "Jsi asistent MDT."
        assert config.temperature == ai_service.DEFAULT_TEMPERATURE
        assert config.response_mime_type == "application/json"
        assert config.response_json_schema == gemini_json_schema(Claim)
        assert config.response_schema is None

    def test_generate_plain_text_and_thinking(self, monkeypatch):
        monkeypatch.setenv("AI_THINKING_LEVEL", "low")
        provider = gemini(response=_response("Volný text"))
        result = provider.generate("prompt", temperature=0.7, max_tokens=100)
        assert result["response"] == "Volný text" and result["data"] is None
        config = provider.client.models.calls[0]["config"]
        assert config.response_mime_type is None
        assert config.temperature == 0.7 and config.max_output_tokens == 100
        assert config.thinking_config.thinking_level == types.ThinkingLevel.LOW

    @pytest.mark.parametrize("text", ["není json", json.dumps({"id": "c1"})])
    def test_generate_invalid_output_is_error(self, text):
        result = gemini(response=_response(text)).generate("p", response_schema=Claim)
        assert result["status"] == "error"
        assert "Claim" in result["error"]

    def test_generate_truncated_output_is_error(self):
        result = gemini(response=_response('{"id": "c1", ', finish="MAX_TOKENS")).generate("p", response_schema=Claim)
        assert result["status"] == "error"
        assert "MAX_TOKENS" in result["error"]

    def test_generate_api_error(self):
        error = errors.APIError(429, {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}})
        result = gemini(error=error).generate("p")
        assert result["status"] == "error"
        assert "429" in result["error"]

    def test_missing_key_is_error_not_crash(self):
        result = GeminiProvider(api_key="").generate("p")
        assert result["status"] == "error"
        assert "GEMINI_API_KEY" in result["error"]

    def test_embed_normalizes_and_batches(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_MODEL", "gemini-embedding-test")
        provider = gemini()
        texts = [f"odstavec {i}" for i in range(ai_service.EMBED_BATCH_SIZE + 20)]
        vectors = provider.embed(texts, task_type=ai_service.TASK_FACT_VERIFICATION)

        assert len(vectors) == len(texts)
        assert all(len(v) == 1536 for v in vectors)
        assert math.isclose(math.sqrt(sum(v * v for v in vectors[0])), 1.0, rel_tol=1e-9)
        calls = provider.client.models.embed_calls
        assert [len(c["contents"]) for c in calls] == [ai_service.EMBED_BATCH_SIZE, 20]
        assert calls[0]["model"] == "gemini-embedding-test"
        assert calls[0]["config"].task_type == "FACT_VERIFICATION"
        assert calls[0]["config"].output_dimensionality == 1536

    def test_embed_wrong_dimension_raises(self):
        with pytest.raises(AIProviderError):
            gemini(embed_dim=768).embed(["text"])

    def test_embed_api_error_raises(self):
        with pytest.raises(AIProviderError):
            gemini(error=errors.APIError(500, {"error": {"message": "boom"}})).embed(["text"])

    def test_embed_waits_on_free_tier_429(self, monkeypatch):
        """D-021: 429 s „retry in Ns“ → počkat a zopakovat, ne spadnout."""
        provider = gemini()
        models = provider.client.models
        ok = models.embed_content
        errs = [errors.APIError(429, {"error": {"message": "Quota exceeded. Please retry in 2.5s."}})]

        def flaky(**kwargs):
            if errs:
                raise errs.pop()
            return ok(**kwargs)

        models.embed_content = flaky
        waits = []
        monkeypatch.setattr(ai_service.time, "sleep", waits.append)
        assert len(provider.embed(["text"])) == 1
        assert waits == [3.5]

    def test_transcribe_inline_audio(self, monkeypatch):
        monkeypatch.setenv("TRANSCRIBE_MODEL", "gemini-transcribe-test")
        payload = {"segments": [{"speaker": "onkolog", "start": "00:12", "text": "ECOG je nula."}]}
        provider = gemini(response=_response(json.dumps(payload, ensure_ascii=False)))
        result = provider.transcribe(b"\x00\x01", "audio/mp4")

        assert result["status"] == "success"
        assert result["data"] == payload
        call = provider.client.models.calls[0]
        assert call["model"] == "gemini-transcribe-test"
        media, prompt = call["contents"]
        assert media.inline_data.mime_type == "audio/mp4"
        assert prompt == ai_service.TRANSCRIBE_PROMPT


# ── Factory ───────────────────────────────────────────────────────────────────
class TestFactory:
    def test_default_is_nvidia_or_mock_without_key(self, monkeypatch):
        monkeypatch.delenv("AI_PROVIDER")
        assert isinstance(get_ai_provider(), MockAIProvider)              # bez NVIDIA_API_KEY
        monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
        assert get_ai_provider().provider_name == "nvidia"

    def test_gemini_without_key_falls_back_to_mock(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "gemini")
        assert isinstance(get_ai_provider(), MockAIProvider)

    def test_gemini_with_key(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        assert isinstance(get_ai_provider(), GeminiProvider)

    def test_unknown_provider(self):
        with pytest.raises(ValueError):
            get_ai_provider("openai")


# ── Živý test (opt-in, jen placený tier) ──────────────────────────────────────
LIVE_KEY = os.environ.get("GEMINI_API_KEY", "")     # autouse fixture env čistí, klíč se vezme při importu


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("AI_LIVE_TESTS") != "1" or not LIVE_KEY,
    reason="živý Gemini test: AI_LIVE_TESTS=1 + GEMINI_API_KEY (placený tier, Q9)",
)
def test_gemini_live_smoke():
    provider = GeminiProvider(api_key=LIVE_KEY)
    result = provider.generate(
        "Vrať claim s id 'c1', kind 'claim', text 'Test' a citací 'P00-test'. Nic dalšího.",
        response_schema=Claim,
    )
    assert result["status"] == "success", result.get("error")
    Claim.model_validate(result["data"])

    vectors = provider.embed(["Hemoglobin 98 g/l"], task_type=ai_service.TASK_RETRIEVAL_QUERY)
    assert len(vectors[0]) == ai_service.embedding_dim()
    assert math.isclose(math.sqrt(sum(v * v for v in vectors[0])), 1.0, rel_tol=1e-6)
