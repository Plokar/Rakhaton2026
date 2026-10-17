"""
AI služba MDT Copilot: abstrakce providerů (ARCHITEKTURA §5.7, D-008).

Providery:
- ``GeminiProvider``: Google AI Studio (Gemini API, **jen placený tier**) přes SDK ``google-genai``.
- ``MockAIProvider``: deterministický a bez sítě. Výchozí pro vývoj, testy a CI (``AI_PROVIDER=mock``).

Rozhraní je u obou providerů stejné:

- ``generate(prompt, system_prompt=..., response_schema=PydanticModel) -> dict``
  vrátí ``{"status": "success", "response": text, "data": dict | None, "provider", "model",
  "tokens_in", "tokens_out", "tokens_used", "latency_ms", "prompt_hash", "is_mock"}``,
  nebo ``{"status": "error", "error": ...}``. S ``response_schema`` je ``data`` vždy
  zvalidované pydantic schématem; nevalidní výstup modelu je ``error``, nikdy ne ``success``.
- ``embed(texts, task_type=...) -> list[list[float]]``: ``EMBEDDING_DIM`` čísel na text, L2 normalizované.
- ``transcribe(audio, mime_type) -> dict``: jako ``generate``, ``data`` podle schématu ``Transcript``.

Model ID jsou jen v env (``AI_MODEL``, ``AI_MODEL_STRONG``, ``EMBEDDING_MODEL``, ``EMBEDDING_DIM``,
``TRANSCRIBE_MODEL``). Výchozí hodnoty níže odpovídají ARCHITEKTURA §9.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import os
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Sequence

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# ── Konfigurace (env, výchozí hodnoty podle ARCHITEKTURA §9) ─────────────────
DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_VERIFIER_MODEL = "gpt-6-astra"
DEFAULT_OPENAI_BASE_URL = "https://apim-rakathon-q7146n.azure-api.net/openai/v1"
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_EMBEDDING_DIM = 1536
DEFAULT_TEMPERATURE = 0.2          # ARCHITEKTURA §5.1: teplota 0–0.2
DEFAULT_TIMEOUT_S = 90
RETRY_ATTEMPTS = 3                 # včetně prvního pokusu; SDK opakuje 408, 429 a 5xx
EMBED_BATCH_SIZE = 100
RATE_RETRIES = 3                                        # 429 free tieru: čekat podle „retry in Ns“
RETRY_IN = re.compile(r"retry in (\d+(?:\.\d+)?)s", re.IGNORECASE)


def _rate_retry(call):
    """Free tier (D-021) má limity za minutu; 429 nese „retry in Ns“ → počkat (max 65 s) a zkusit znovu."""
    from google.genai import errors

    for attempt in range(RATE_RETRIES + 1):
        try:
            return call()
        except errors.APIError as exc:
            delay = RETRY_IN.search(str(exc)) if exc.code == 429 else None
            if delay is None or attempt == RATE_RETRIES:
                raise
            wait = min(float(delay.group(1)) + 1, 65)
            logger.warning("Gemini 429, čekám %.0f s (pokus %d)", wait, attempt + 1)
            time.sleep(wait)
INLINE_AUDIO_MAX_BYTES = 20 * 1024 * 1024   # větší audio jde přes Files API

# task_type pro embeddingy (ARCHITEKTURA §4.5)
TASK_RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"   # chunky do IRIS
TASK_RETRIEVAL_QUERY = "RETRIEVAL_QUERY"         # dotazy
TASK_FACT_VERIFICATION = "FACT_VERIFICATION"     # ověření tvrzení (grounding)


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


def ai_model() -> str:
    return _env("AI_MODEL", DEFAULT_MODEL)


def verifier_model() -> str:
    return _env("VERIFIER_MODEL", DEFAULT_VERIFIER_MODEL)


def ai_model_strong() -> str:
    return _env("AI_MODEL_STRONG", ai_model())


def embedding_model() -> str:
    return _env("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def embedding_dim() -> int:
    return int(_env("EMBEDDING_DIM", str(DEFAULT_EMBEDDING_DIM)))


def transcribe_model() -> str:
    return _env("TRANSCRIBE_MODEL", ai_model())


class AIProviderError(RuntimeError):
    """Chyba providera u volání, která nevrací dict se ``status`` (``embed``)."""


# ── Schéma přepisu (BON-3, ARCHITEKTURA §5.6) ─────────────────────────────────
class TranscriptSegment(BaseModel):
    speaker: str = Field(description="Role mluvčího, např. předseda, onkolog, chirurg, radiolog, patolog")
    start: str = Field(description="Čas začátku úseku ve formátu MM:SS")
    text: str = Field(description="Doslovný přepis úseku")


class Transcript(BaseModel):
    segments: list[TranscriptSegment]


TRANSCRIBE_PROMPT = (
    "Přepiš nahrávku diskuse multidisciplinární onkologické komise doslova a v původním jazyce. "
    "Rozliš mluvčí podle role (předseda, onkolog, chirurg, radiolog, patolog, radiační onkolog, "
    "pacient). U každého úseku uveď čas začátku ve formátu MM:SS. Nic nedomýšlej, "
    "nesrozumitelný úsek označ [nesrozumitelné]."
)


# ── JSON Schema pro Gemini ────────────────────────────────────────────────────
# Gemini `response_json_schema` podporuje jen podmnožinu JSON Schema. Pydantic navíc
# generuje `const`, `default`, `pattern`, `minLength`… a `$ref` se sourozenci, což Gemini
# odmítá. Posíláme proto očištěné schéma a omezení hlídá až validace pydantic.
_GEMINI_SCHEMA_KEYS = {
    "$id", "$defs", "$ref", "$anchor", "type", "format", "title", "description", "enum",
    "items", "prefixItems", "minItems", "maxItems", "minimum", "maximum", "anyOf", "oneOf",
    "properties", "additionalProperties", "required",
}


def gemini_json_schema(schema: type[BaseModel]) -> dict[str, Any]:
    """Pydantic model → JSON Schema v podmnožině, kterou přijme Gemini."""
    return _clean_schema(schema.model_json_schema())


def _clean_schema(node: Any) -> Any:
    if isinstance(node, list):
        return [_clean_schema(n) for n in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return {k: v for k, v in node.items() if k.startswith("$")}
    if "allOf" in node and len(node["allOf"]) == 1:
        merged = {k: v for k, v in node.items() if k != "allOf"}
        merged.update(node["allOf"][0])
        return _clean_schema(merged)

    out: dict[str, Any] = {}
    const = node.get("const")
    if "const" in node and "enum" not in node and isinstance(const, (str, int, float)) and not isinstance(const, bool):
        out["enum"] = [const]
    for key, value in node.items():
        if key not in _GEMINI_SCHEMA_KEYS:
            continue
        if key in ("properties", "$defs"):
            out[key] = {name: _clean_schema(sub) for name, sub in value.items()}
        elif key in ("items", "prefixItems", "additionalProperties", "anyOf", "oneOf"):
            out[key] = _clean_schema(value)
        else:
            out[key] = value
    if out.get("properties"):
        out["propertyOrdering"] = list(out["properties"])
    return out


# ── Pomocné funkce ────────────────────────────────────────────────────────────
def prompt_hash(prompt: str, system_prompt: str = "") -> str:
    """Hash promptu pro audit (`LlmCallLog`, NFR-4); prompt samotný se neloguje."""
    return hashlib.sha256(f"{system_prompt}\n\n{prompt}".encode("utf-8")).hexdigest()


def l2_normalize(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        raise AIProviderError("Nulový vektor nelze normalizovat")
    return [v / norm for v in vector]


def _check_texts(texts: Sequence[str]) -> list[str]:
    if isinstance(texts, str):
        raise TypeError("embed() bere seznam textů, ne jeden string")
    texts = list(texts)
    if any(not t or not t.strip() for t in texts):
        raise ValueError("Prázdný text nelze embedovat")
    return texts


def _validate(schema: type[BaseModel], payload: Any) -> dict[str, Any]:
    return schema.model_validate(payload).model_dump(mode="json")


def _short(exc: Exception, limit: int = 500) -> str:
    text = str(exc)
    return text if len(text) <= limit else text[:limit] + "…"


# ── Providery ─────────────────────────────────────────────────────────────────
class BaseAIProvider(ABC):
    """Společné rozhraní providerů. Viz docstring modulu."""

    is_mock = False

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_schema: type[BaseModel] | None = None,
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    def embed(
        self,
        texts: Sequence[str],
        task_type: str = TASK_RETRIEVAL_DOCUMENT,
        model: str | None = None,
        dim: int | None = None,
    ) -> list[list[float]]:
        ...

    @abstractmethod
    def transcribe(
        self,
        audio: bytes,
        mime_type: str,
        prompt: str = TRANSCRIBE_PROMPT,
        model: str | None = None,
        response_schema: type[BaseModel] = Transcript,
    ) -> dict[str, Any]:
        ...

    def _success(self, *, text: str, data: Any, model: str, tokens_in: int, tokens_out: int,
                 tokens_total: int | None, started: float, p_hash: str) -> dict[str, Any]:
        return {
            "status": "success",
            "response": text,
            "data": data,
            "provider": self.provider_name,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_used": tokens_total if tokens_total is not None else tokens_in + tokens_out,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "prompt_hash": p_hash,
            "is_mock": self.is_mock,
        }

    def _error(self, error: str, *, model: str, started: float, p_hash: str) -> dict[str, Any]:
        return {
            "status": "error",
            "error": error,
            "provider": self.provider_name,
            "model": model,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "prompt_hash": p_hash,
            "is_mock": self.is_mock,
        }


class MockAIProvider(BaseAIProvider):
    """
    Deterministický provider bez sítě (testy, CI, vývoj bez klíče).

    - ``generate`` se schématem vrátí minimální instanci, která projde validací schématu,
      nebo odpověď zaregistrovanou v ``responses`` (klíč = název třídy schématu, hodnota =
      data nebo ``callable(prompt) -> data``).
    - ``embed`` vrací hashované bag-of-words vektory: stejný text = stejný vektor,
      podobné texty mají vyšší kosinovou podobnost než nesouvisející.
    """

    is_mock = True

    def __init__(self, responses: dict[str, Any] | None = None):
        self.responses = dict(responses or {})

    @property
    def provider_name(self) -> str:
        return "mock"

    def generate(self, prompt, system_prompt="", model=None, temperature=None, max_tokens=None,
                 response_schema=None):
        started = time.monotonic()
        model_name = model or "mock"
        p_hash = prompt_hash(prompt, system_prompt)
        data = None
        if response_schema is None:
            text = f"Simulovaná odpověď (AI_PROVIDER=mock). Dotaz: {prompt[:120]}"
        else:
            try:
                data = _validate(response_schema, self._payload(response_schema, prompt))
            except ValidationError as exc:
                return self._error(f"Mock odpověď neodpovídá schématu {response_schema.__name__}: {_short(exc)}",
                                   model=model_name, started=started, p_hash=p_hash)
            text = json.dumps(data, ensure_ascii=False)
        tokens_in = len(f"{system_prompt} {prompt}".split())
        tokens_out = len(text.split())
        return self._success(text=text, data=data, model=model_name, tokens_in=tokens_in,
                             tokens_out=tokens_out, tokens_total=None, started=started, p_hash=p_hash)

    def embed(self, texts, task_type=TASK_RETRIEVAL_DOCUMENT, model=None, dim=None):
        texts = _check_texts(texts)
        return [hashed_embedding(t, dim or embedding_dim()) for t in texts]

    def transcribe(self, audio, mime_type, prompt=TRANSCRIBE_PROMPT, model=None, response_schema=Transcript):
        started = time.monotonic()
        model_name = model or "mock"
        p_hash = hashlib.sha256(audio).hexdigest()
        try:
            data = _validate(response_schema, self._payload(response_schema, prompt))
        except ValidationError as exc:
            return self._error(f"Mock přepis neodpovídá schématu: {_short(exc)}",
                               model=model_name, started=started, p_hash=p_hash)
        text = json.dumps(data, ensure_ascii=False)
        return self._success(text=text, data=data, model=model_name, tokens_in=0,
                             tokens_out=len(text.split()), tokens_total=None, started=started, p_hash=p_hash)

    def _payload(self, schema: type[BaseModel], prompt: str) -> Any:
        if schema.__name__ in self.responses:
            payload = self.responses[schema.__name__]
            return payload(prompt) if callable(payload) else payload
        if schema is Transcript:
            return {"segments": [
                {"speaker": "předseda", "start": "00:00", "text": "Simulovaný přepis (AI_PROVIDER=mock)."},
            ]}
        return mock_instance(schema)


def _strip_fence(text: str) -> str:
    """Remove a single surrounding Markdown code fence, preserving the JSON inside."""
    return re.sub(r"\A```(?:json)?\s*\n?(.*?)\n?```\Z", r"\1", text.strip(),
                  flags=re.IGNORECASE | re.DOTALL).strip()


class OpenAICompatProvider(BaseAIProvider):
    """Generate-only provider for the hackathon OpenAI v1 gateway (api-key auth)."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, *, opener=None):
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (base_url or _env("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)).rstrip("/")
        self._opener = opener or urllib.request.urlopen

    @property
    def provider_name(self) -> str:
        return "openai"

    def generate(self, prompt, system_prompt="", model=None, temperature=None, max_tokens=None,
                 response_schema=None):
        started = time.monotonic()
        model_name = model or verifier_model()
        p_hash = prompt_hash(prompt, system_prompt)

        def error(message):
            return self._error(message, model=model_name, started=started, p_hash=p_hash)

        if not self.api_key:
            return error("OPENAI_API_KEY není nastaven")
        # This alias is specific to the team's gateway; other endpoints receive the model verbatim.
        deployment = ("gpt-6-astra-global" if model_name == DEFAULT_VERIFIER_MODEL
                      and self.base_url == DEFAULT_OPENAI_BASE_URL else model_name)
        messages = ([{"role": "system", "content": system_prompt}] if system_prompt else [])
        messages.append({"role": "user", "content": prompt})
        body = {"model": deployment, "messages": messages,
                "temperature": DEFAULT_TEMPERATURE if temperature is None else temperature}
        if max_tokens is not None:
            body["max_completion_tokens"] = max_tokens
        if response_schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": {
                "name": response_schema.__name__, "strict": False, "schema": response_schema.model_json_schema(),
            }}
        for attempt in range(RETRY_ATTEMPTS):
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions", data=json.dumps(body).encode("utf-8"), method="POST",
                    headers={"api-key": self.api_key, "Content-Type": "application/json", "Accept": "application/json"},
                )
                with self._opener(req, timeout=float(_env("AI_TIMEOUT_S", str(DEFAULT_TIMEOUT_S)))) as resp:
                    payload = json.loads(resp.read())
                choice = payload["choices"][0]
                if choice.get("finish_reason") == "length":
                    return error("Výstup modelu byl uříznut (length)")
                if choice.get("finish_reason") not in (None, "stop") or choice["message"].get("refusal"):
                    return error("Model odpověď nedokončil nebo odmítl")
                raw = choice["message"].get("content")
                if not isinstance(raw, str) or not raw.strip():
                    return error("Model nevrátil text")
                text = _strip_fence(raw)
                data = _validate(response_schema, json.loads(text)) if response_schema else None
                usage = payload.get("usage") or {}
                return self._success(text=text, data=data, model=model_name,
                                     tokens_in=usage.get("prompt_tokens") or 0,
                                     tokens_out=usage.get("completion_tokens") or 0,
                                     tokens_total=usage.get("total_tokens"), started=started, p_hash=p_hash)
            except urllib.error.HTTPError as exc:
                code = exc.code
                exc.close()
                if attempt == RETRY_ATTEMPTS - 1:
                    return error(f"OpenAI gateway HTTP {code}")
                if code == 400 and "temperature" in body:
                    body.pop("temperature")
                elif code == 400 and body.get("response_format", {}).get("type") == "json_schema":
                    schema = body["response_format"]["json_schema"]["schema"]
                    body["response_format"] = {"type": "json_object"}
                    messages.append({"role": "system", "content": "Vrať pouze JSON podle schématu: " + json.dumps(schema)})
                elif code in (408, 429) or 500 <= code <= 599:
                    time.sleep(2 ** attempt)
                else:
                    return error(f"OpenAI gateway HTTP {code}")
            except Exception as exc:
                # Never put the HTTP body, credentials or patient prompt into an error/log.
                return error(f"OpenAI gateway: {type(exc).__name__}")
        return error("OpenAI gateway: vyčerpány pokusy")

    def embed(self, texts, task_type=TASK_RETRIEVAL_DOCUMENT, model=None, dim=None):
        raise AIProviderError("OpenAICompatProvider nepodporuje embed")

    def transcribe(self, audio, mime_type, prompt=TRANSCRIBE_PROMPT, model=None, response_schema=Transcript):
        return self._error("OpenAICompatProvider nepodporuje transcribe", model=model or verifier_model(),
                           started=time.monotonic(), p_hash=hashlib.sha256(audio).hexdigest())


class GeminiProvider(BaseAIProvider):
    """Google Gemini API (Google AI Studio) přes SDK ``google-genai``."""

    def __init__(self, api_key: str | None = None, client: Any = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._client = client
        self._client_lock = threading.Lock()

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def client(self):
        # Volání podkladu běží paralelně: bez zámku vznikne víc klientů a přepsaný se při GC zavře
        # („client has been closed“) uprostřed požadavku jiného vlákna.
        with self._client_lock:
            return self._make_client()

    def _make_client(self):
        if self._client is None:
            if not self.api_key:
                raise AIProviderError("GEMINI_API_KEY není nastaven")
            from google import genai
            from google.genai import types

            timeout_ms = int(float(_env("AI_TIMEOUT_S", str(DEFAULT_TIMEOUT_S))) * 1000)
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    timeout=timeout_ms,
                    retry_options=types.HttpRetryOptions(attempts=RETRY_ATTEMPTS),
                ),
            )
        return self._client

    def generate(self, prompt, system_prompt="", model=None, temperature=None, max_tokens=None,
                 response_schema=None):
        from google.genai import types

        config: dict[str, Any] = {
            "temperature": DEFAULT_TEMPERATURE if temperature is None else temperature,
        }
        if system_prompt:
            config["system_instruction"] = system_prompt
        if max_tokens:
            config["max_output_tokens"] = max_tokens
        thinking_level = os.environ.get("AI_THINKING_LEVEL")
        if thinking_level:
            config["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)
        return self._call(
            model=model or ai_model(),
            contents=prompt,
            config=config,
            response_schema=response_schema,
            p_hash=prompt_hash(prompt, system_prompt),
        )

    def embed(self, texts, task_type=TASK_RETRIEVAL_DOCUMENT, model=None, dim=None):
        from google.genai import errors, types

        texts = _check_texts(texts)
        model_name = model or embedding_model()
        dim = dim or embedding_dim()
        config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=dim)
        vectors: list[list[float]] = []
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i:i + EMBED_BATCH_SIZE]
            try:
                resp = _rate_retry(lambda: self.client.models.embed_content(model=model_name, contents=batch,
                                                                            config=config))
            except errors.APIError as exc:
                raise AIProviderError(f"Gemini embed HTTP {exc.code}: {_short(exc)}") from exc
            embeddings = resp.embeddings or []
            if len(embeddings) != len(batch):
                raise AIProviderError(f"Gemini vrátil {len(embeddings)} embeddingů pro {len(batch)} textů")
            for emb in embeddings:
                values = emb.values or []
                if len(values) != dim:
                    raise AIProviderError(f"Embedding má {len(values)} dimenzí, čekáno {dim}")
                # pod 3072 dimenzí Google vyžaduje L2 normalizaci (ARCHITEKTURA §4.5)
                vectors.append(l2_normalize(values))
        return vectors

    def transcribe(self, audio, mime_type, prompt=TRANSCRIBE_PROMPT, model=None, response_schema=Transcript):
        from google.genai import errors, types

        started = time.monotonic()
        model_name = model or transcribe_model()
        p_hash = hashlib.sha256(audio).hexdigest()
        if len(audio) <= INLINE_AUDIO_MAX_BYTES:
            media: Any = types.Part.from_bytes(data=audio, mime_type=mime_type)
        else:
            try:
                media = self.client.files.upload(
                    file=io.BytesIO(audio), config=types.UploadFileConfig(mime_type=mime_type))
            except (errors.APIError, AIProviderError) as exc:
                return self._error(f"Gemini Files API: {_short(exc)}", model=model_name, started=started, p_hash=p_hash)
        return self._call(
            model=model_name,
            contents=[media, prompt],
            config={"temperature": 0.0},
            response_schema=response_schema,
            p_hash=p_hash,
        )

    def _call(self, *, model: str, contents: Any, config: dict[str, Any],
              response_schema: type[BaseModel] | None, p_hash: str) -> dict[str, Any]:
        from google.genai import errors, types

        started = time.monotonic()
        if response_schema is not None:
            config = {
                **config,
                "response_mime_type": "application/json",
                "response_json_schema": gemini_json_schema(response_schema),
            }
        try:
            resp = _rate_retry(lambda: self.client.models.generate_content(
                model=model, contents=contents, config=types.GenerateContentConfig(**config)))
        except errors.APIError as exc:
            logger.error("Gemini API error %s (model %s)", exc.code, model)
            return self._error(f"Gemini HTTP {exc.code}: {_short(exc)}", model=model, started=started, p_hash=p_hash)
        except AIProviderError as exc:
            return self._error(str(exc), model=model, started=started, p_hash=p_hash)
        except Exception as exc:  # síť, timeout…
            logger.error("Gemini request failed (model %s): %s", model, type(exc).__name__)
            return self._error(f"Gemini request failed: {_short(exc)}", model=model, started=started, p_hash=p_hash)

        candidate = resp.candidates[0] if resp.candidates else None
        finish = getattr(candidate, "finish_reason", None)
        finish_name = getattr(finish, "name", None) or (str(finish) if finish else None)
        text = resp.text
        if finish_name == "MAX_TOKENS":
            return self._error("Výstup modelu byl uříznut (MAX_TOKENS)", model=model, started=started, p_hash=p_hash)
        if not text:
            reason = finish_name or getattr(getattr(resp, "prompt_feedback", None), "block_reason", None)
            return self._error(f"Gemini nevrátil text (důvod: {reason})", model=model, started=started, p_hash=p_hash)

        data = None
        if response_schema is not None:
            try:
                data = _validate(response_schema, json.loads(text))
            except (json.JSONDecodeError, ValidationError) as exc:
                return self._error(f"Výstup neodpovídá schématu {response_schema.__name__}: {_short(exc)}",
                                   model=model, started=started, p_hash=p_hash)

        usage = resp.usage_metadata
        tokens_in = (usage.prompt_token_count or 0) if usage else 0
        tokens_out = ((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)) if usage else 0
        return self._success(text=text, data=data, model=resp.model_version or model, tokens_in=tokens_in,
                             tokens_out=tokens_out, tokens_total=usage.total_token_count if usage else None,
                             started=started, p_hash=p_hash)


# ── Mock: generování dat podle schématu a hashované embeddingy ────────────────
def mock_instance(schema: type[BaseModel]) -> Any:
    """Minimální data, která projdou validací schématu (jen povinná pole)."""
    root = schema.model_json_schema()
    return _mock_value(root, root.get("$defs", {}), 0)


def _mock_value(node: dict[str, Any], defs: dict[str, Any], depth: int) -> Any:
    if depth > 32:
        return None
    if "$ref" in node:
        return _mock_value(defs[node["$ref"].rsplit("/", 1)[-1]], defs, depth + 1)
    if "const" in node:
        return node["const"]
    if node.get("enum"):
        return node["enum"][0]
    for key in ("anyOf", "oneOf"):
        if key in node:
            options = [o for o in node[key] if o.get("type") != "null"] or node[key]
            return _mock_value(options[0], defs, depth + 1)
    if "allOf" in node:
        merged: dict[str, Any] = {}
        for part in node["allOf"]:
            merged.update(part)
        return _mock_value(merged, defs, depth + 1)

    kind = node.get("type")
    if kind == "object" or "properties" in node:
        required = set(node.get("required", []))
        return {name: _mock_value(sub, defs, depth + 1)
                for name, sub in node.get("properties", {}).items() if name in required}
    if kind == "array":
        return [_mock_value(node.get("items", {}), defs, depth + 1) for _ in range(node.get("minItems", 0))]
    if kind == "string":
        fmt = node.get("format")
        if fmt == "date":
            return "2026-01-01"
        if fmt == "date-time":
            return "2026-01-01T00:00:00Z"
        value = "mock".ljust(node.get("minLength", 0), "x")
        return value[:node["maxLength"]] if "maxLength" in node else value
    if kind in ("integer", "number"):
        value: float = 0
        if "minimum" in node:
            value = max(value, node["minimum"])
        if "exclusiveMinimum" in node:
            value = max(value, node["exclusiveMinimum"] + 1)
        if "maximum" in node:
            value = min(value, node["maximum"])
        return int(value) if kind == "integer" else float(value)
    if kind == "boolean":
        return False
    return None


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def hashed_embedding(text: str, dim: int) -> list[float]:
    """Deterministický L2-normalizovaný vektor (hashovaná slova + znakové trigramy)."""
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    vector = [0.0] * dim
    for word in _TOKEN_RE.findall(plain):
        features = [(word, 1.0)]
        padded = f"#{word}#"
        features += [(padded[i:i + 3], 0.5) for i in range(len(padded) - 2)]
        for feature, weight in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign * weight
    if not any(vector):
        vector[0] = 1.0
    return l2_normalize(vector)


# ── Factory ───────────────────────────────────────────────────────────────────
SUPPORTED_PROVIDERS = ("mock", "gemini")


def get_ai_provider(provider_name: str | None = None) -> BaseAIProvider:
    """
    Provider podle ``provider_name`` nebo env ``AI_PROVIDER`` (výchozí ``mock``).

    ``gemini`` bez ``GEMINI_API_KEY`` spadne na mock s varováním; výsledek má pak
    ``provider == "mock"`` a ``is_mock == True``, takže záměna je vidět.
    Data pacientů se smí posílat jen s placeným tierem (ARCHITEKTURA §5.7, Q9).
    """
    chosen = (provider_name or os.environ.get("AI_PROVIDER") or "mock").lower()
    if chosen == "mock":
        return MockAIProvider()
    if chosen == "gemini":
        if not os.environ.get("GEMINI_API_KEY"):
            logger.warning("AI_PROVIDER=gemini, ale GEMINI_API_KEY není nastaven: používám MockAIProvider")
            return MockAIProvider()
        return GeminiProvider()
    raise ValueError(f"Neznámý AI provider {chosen!r}, podporované: {', '.join(SUPPORTED_PROVIDERS)}")


# ── D-021: data skutečných pacientů jen s placeným tierem ─────────────────────
REAL_DATA_ENV = "AI_REAL_PATIENT_DATA"
FICTIONAL_TAG_CODE = "fiktivni-data"


def real_patient_data_allowed() -> bool:
    """`AI_REAL_PATIENT_DATA=True` = placený tier / Vertex AI EU (D-021); jinak jen syntetická data."""
    return os.environ.get(REAL_DATA_ENV, "").strip().lower() in ("1", "true", "yes")


def is_synthetic_patient(resources) -> bool:
    """Pacient datasetu (a testovací pacient založený se `synthetic`) má v `Patient.meta.tag` `fiktivni-data`."""
    return any(tag.get("code") == FICTIONAL_TAG_CODE for r in resources if r.get("resourceType") == "Patient"
               for tag in (r.get("meta") or {}).get("tag", []))


def provider_for_patient(resources) -> BaseAIProvider:
    """Provider pro data konkrétního pacienta. U skutečného pacienta (bez tagu `fiktivni-data`) bez
    `AI_REAL_PATIENT_DATA=True` vrátí `MockAIProvider`: nic z jeho dat neodejde do LLM ani do embeddingů,
    aplikace jede dál deterministicky (pravidla, citace, „údaj chybí“)."""
    provider = get_ai_provider()
    if provider.is_mock or is_synthetic_patient(resources) or real_patient_data_allowed():
        return provider
    logger.warning("Pacient nemá syntetická data a %s není zapnuté: LLM se nevolá (D-021)", REAL_DATA_ENV)
    return MockAIProvider()


def provider_for_patient_id(patient_id: str) -> BaseAIProvider:
    """Jako `provider_for_patient`, `Patient` přečte z IRIS; když ho nenajde, bere ho jako skutečného."""
    from services.fhir import client as fhir
    try:
        resources = [fhir.read("Patient", patient_id)]
    except Exception:
        resources = []
    return provider_for_patient(resources)


def get_verifier_provider(resources) -> BaseAIProvider | None:
    """Separate verifier factory; primary AI_PROVIDER remains mock/gemini. Enforces D-021."""
    chosen = _env("VERIFIER_PROVIDER", "openai" if os.environ.get("OPENAI_API_KEY") else "off").strip().lower()
    if chosen not in ("off", "mock", "openai", "gemini"):
        raise ValueError(f"Neznámý verifier provider {chosen!r}")
    if chosen == "off" or not (is_synthetic_patient(resources) or real_patient_data_allowed()):
        return None
    if chosen == "mock":
        return MockAIProvider()
    key = "OPENAI_API_KEY" if chosen == "openai" else "GEMINI_API_KEY"
    if not os.environ.get(key):
        logger.warning("VERIFIER_PROVIDER=%s, ale %s není nastaven: kontrola vypnuta", chosen, key)
        return None
    return OpenAICompatProvider() if chosen == "openai" else GeminiProvider()
