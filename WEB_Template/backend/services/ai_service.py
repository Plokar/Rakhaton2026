"""
AI služba MDT Copilot: abstrakce providerů (ARCHITEKTURA §5.7, D-008).

Providery (výběr v ``.env``):
- ``GeminiProvider``: Google AI Studio (Gemini API) přes SDK ``google-genai``: LLM, embeddingy, audio i PDF.
- ``NvidiaProvider``: NVIDIA API (OpenAI-kompatibilní, ``integrate.api.nvidia.com``): LLM se strukturovaným
  výstupem (``response_format: json_schema``) a embeddingy (``nemotron-3-embed-1b`` @ 2048).
- ``GroqProvider``: jen přepis audia (Whisper ``whisper-large-v3``); mluvčí doplní LLM (``scribe.label_speakers``).
- ``MockAIProvider``: deterministický a bez sítě. Výchozí pro vývoj, testy a CI (``AI_PROVIDER=mock``);
  ``mock`` vypne i embeddingy a přepis, takže testy nikdy nevolají skutečné API.

Kdo co dělá: ``AI_PROVIDER`` (LLM), ``EMBEDDING_PROVIDER`` (vektory v IRIS, výchozí = ``AI_PROVIDER``),
``TRANSCRIBE_PROVIDER`` (audio, výchozí Groq, když je ``GROQ_API_KEY``). Viz ``embedding_provider()``
a ``transcription_provider()``.

Rozhraní je u všech providerů stejné:

- ``generate(prompt, system_prompt=..., response_schema=PydanticModel) -> dict``
  vrátí ``{"status": "success", "response": text, "data": dict | None, "provider", "model",
  "tokens_in", "tokens_out", "tokens_used", "latency_ms", "prompt_hash", "is_mock"}``,
  nebo ``{"status": "error", "error": ...}``. S ``response_schema`` je ``data`` vždy
  zvalidované pydantic schématem; nevalidní výstup modelu je ``error``, nikdy ne ``success``.
- ``embed(texts, task_type=...) -> list[list[float]]``: ``EMBEDDING_DIM`` čísel na text, L2 normalizované.
- ``transcribe(audio, mime_type) -> dict``: jako ``generate``, ``data`` podle schématu ``Transcript``.

Model ID jsou jen v env (Gemini: ``AI_MODEL``, ``AI_MODEL_STRONG``, ``EMBEDDING_MODEL``, ``EMBEDDING_DIM``,
``TRANSCRIBE_MODEL``; NVIDIA: ``NVIDIA_MODEL``, ``NVIDIA_MODEL_STRONG``, ``NVIDIA_EMBEDDING_MODEL``,
``NVIDIA_EMBEDDING_DIM``; Groq: ``GROQ_TRANSCRIBE_MODEL``). Výchozí hodnoty níže odpovídají ARCHITEKTURA §9.
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
from abc import ABC, abstractmethod
from typing import Any, Sequence

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# ── Konfigurace (env, výchozí hodnoty podle ARCHITEKTURA §9) ─────────────────
DEFAULT_MODEL = "gemini-3.8-flash"
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


DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NVIDIA_MODEL = "nvidia/nemotron-3-super-120b-a12b"
DEFAULT_NVIDIA_EMBEDDING_MODEL = "nvidia/nemotron-3-embed-1b"
DEFAULT_NVIDIA_EMBEDDING_DIM = 2048          # nemotron-3-embed-1b umí jen 2048
DEFAULT_NVIDIA_MAX_TOKENS = 16384            # reasoning model: přemýšlení se počítá do max_tokens
NVIDIA_EMBED_BATCH_SIZE = 50
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_TRANSCRIBE_MODEL = "whisper-large-v3"
# Whisper `prompt` = slovník domény (max ~224 tokenů), zlepší pravopis léků a zkratek
WHISPER_VOCABULARY = ("Onkologická komise MDT. FOLFOX, FOLFIRI, bevacizumab, oxaliplatina, pembrolizumab, durvalumab, "
                      "trastuzumab, KRAS G12D, BRAF, HER2, MMR, MSI, PD-L1, RECIST, ECOG, FLR, CT, MR, PET-CT, TNM.")
AUDIO_EXTENSIONS = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/m4a": "m4a",
                    "audio/mpeg": "mp3", "audio/wav": "wav", "audio/x-wav": "wav", "audio/flac": "flac", "video/webm": "webm"}


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


def ai_provider_name() -> str:
    return (os.environ.get("AI_PROVIDER") or "mock").lower()


def embedding_provider_name() -> str:
    """Kdo počítá vektory v IRIS. ``AI_PROVIDER=mock`` = vše offline (testy, CI)."""
    llm = ai_provider_name()
    return "mock" if llm == "mock" else (os.environ.get("EMBEDDING_PROVIDER") or llm).lower()


def gemini_model() -> str:
    return _env("AI_MODEL", DEFAULT_MODEL)


def ai_model() -> str:
    """Model LLM zvoleného ``AI_PROVIDER`` (přepnutí provideru v .env přepne i model)."""
    return _env("NVIDIA_MODEL", DEFAULT_NVIDIA_MODEL) if ai_provider_name() == "nvidia" else gemini_model()


def ai_model_strong() -> str:
    return _env("NVIDIA_MODEL_STRONG" if ai_provider_name() == "nvidia" else "AI_MODEL_STRONG", ai_model())


def embedding_model() -> str:
    if embedding_provider_name() == "nvidia":
        return _env("NVIDIA_EMBEDDING_MODEL", DEFAULT_NVIDIA_EMBEDDING_MODEL)
    return _env("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def embedding_dim() -> int:
    """Dimenze vektorů v IRIS (sloupec `VECTOR(DOUBLE, n)`); jiná dimenze = tabulky se založí znovu (vector_store)."""
    if embedding_provider_name() == "nvidia":
        return int(_env("NVIDIA_EMBEDDING_DIM", str(DEFAULT_NVIDIA_EMBEDDING_DIM)))
    return int(_env("EMBEDDING_DIM", str(DEFAULT_EMBEDDING_DIM)))


def transcribe_model() -> str:
    return _env("TRANSCRIBE_MODEL", gemini_model())


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
            model=model or gemini_model(),
            contents=prompt,
            config=config,
            response_schema=response_schema,
            p_hash=prompt_hash(prompt, system_prompt),
        )

    def embed(self, texts, task_type=TASK_RETRIEVAL_DOCUMENT, model=None, dim=None):
        from google.genai import errors, types

        texts = _check_texts(texts)
        model_name = model or _env("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
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


# ── OpenAI-kompatibilní HTTP API (NVIDIA, Groq) ───────────────────────────────
_HTTP_CLIENT = None
_HTTP_LOCK = threading.Lock()


def _http():
    """Jeden sdílený `httpx.Client` (thread-safe, podklad volá LLM paralelně, spojení se recyklují)."""
    global _HTTP_CLIENT
    with _HTTP_LOCK:
        if _HTTP_CLIENT is None:
            import httpx

            _HTTP_CLIENT = httpx.Client(timeout=float(_env("AI_TIMEOUT_S", str(DEFAULT_TIMEOUT_S))))
        return _HTTP_CLIENT


def _post(url: str, api_key: str, **kwargs) -> dict[str, Any]:
    """POST s opakováním 429 / 5xx / výpadku sítě (`Retry-After`, max 65 s); jinak `AIProviderError` s HTTP kódem."""
    import httpx

    for attempt in range(RATE_RETRIES + 1):
        last = attempt == RATE_RETRIES
        try:
            resp = _http().post(url, headers={"Authorization": f"Bearer {api_key}"}, **kwargs)
        except httpx.HTTPError as exc:
            if last:
                raise AIProviderError(f"{type(exc).__name__}: {_short(exc)}") from exc
            time.sleep(2 ** attempt)
            continue
        if (resp.status_code == 429 or resp.status_code >= 500) and not last:
            try:
                wait = float(resp.headers.get("retry-after", ""))
            except ValueError:
                wait = 2 ** (attempt + 1)
            logger.warning("%s HTTP %s, čekám %.0f s (pokus %d)", url, resp.status_code, min(wait, 65), attempt + 1)
            time.sleep(min(wait, 65))
            continue
        if resp.status_code >= 400:
            raise AIProviderError(f"HTTP {resp.status_code}: {_short(resp.text)}")
        return resp.json()
    raise AIProviderError("nedosažitelné")      # pragma: no cover


def _json_text(text: str) -> Any:
    """JSON z odpovědi modelu; snese obal ```json … ```."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return json.loads(text)


class NvidiaProvider(BaseAIProvider):
    """NVIDIA API (``integrate.api.nvidia.com``, OpenAI-kompatibilní): chat se strukturovaným výstupem a embeddingy."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY", "")
        self.base_url = _env("NVIDIA_BASE_URL", DEFAULT_NVIDIA_BASE_URL).rstrip("/")

    @property
    def provider_name(self) -> str:
        return "nvidia"

    def generate(self, prompt, system_prompt="", model=None, temperature=None, max_tokens=None,
                 response_schema=None):
        started = time.monotonic()
        model = model or ai_model()
        p_hash = prompt_hash(prompt, system_prompt)
        body: dict[str, Any] = {
            "model": model,
            "messages": [*([{"role": "system", "content": system_prompt}] if system_prompt else []),
                         {"role": "user", "content": prompt}],
            "temperature": DEFAULT_TEMPERATURE if temperature is None else temperature,
            "max_tokens": max_tokens or int(_env("NVIDIA_MAX_TOKENS", str(DEFAULT_NVIDIA_MAX_TOKENS))),
        }
        if _env("NVIDIA_THINKING", "0").lower() not in ("1", "true", "on"):
            # bez přemýšlení ~3× rychleji se stejným výstupem (NFR-1 < 20 s); přesnost hlídá grounding validátor
            body["chat_template_kwargs"] = {"enable_thinking": False}
        if response_schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": {
                "name": response_schema.__name__, "schema": response_schema.model_json_schema()}}
        try:
            resp = _post(f"{self.base_url}/chat/completions", self.api_key, json=body)
        except AIProviderError as exc:
            logger.error("NVIDIA API error (model %s): %s", model, exc)
            return self._error(f"NVIDIA {exc}", model=model, started=started, p_hash=p_hash)

        choice = (resp.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content") or ""
        if choice.get("finish_reason") == "length":
            return self._error("Výstup modelu byl uříznut (max_tokens)", model=model, started=started, p_hash=p_hash)
        if not text.strip():
            return self._error(f"NVIDIA nevrátil text (důvod: {choice.get('finish_reason')})", model=model,
                               started=started, p_hash=p_hash)
        data = None
        if response_schema is not None:
            try:
                data = _validate(response_schema, _json_text(text))
            except (json.JSONDecodeError, ValidationError) as exc:
                return self._error(f"Výstup neodpovídá schématu {response_schema.__name__}: {_short(exc)}",
                                   model=model, started=started, p_hash=p_hash)
        usage = resp.get("usage") or {}
        return self._success(text=text, data=data, model=resp.get("model") or model,
                             tokens_in=usage.get("prompt_tokens") or 0, tokens_out=usage.get("completion_tokens") or 0,
                             tokens_total=usage.get("total_tokens"), started=started, p_hash=p_hash)

    def embed(self, texts, task_type=TASK_RETRIEVAL_DOCUMENT, model=None, dim=None):
        texts = _check_texts(texts)
        model_name = model or _env("NVIDIA_EMBEDDING_MODEL", DEFAULT_NVIDIA_EMBEDDING_MODEL)
        dim = dim or embedding_dim()
        # asymetrické vyhledávání: index = passage, dotaz i ověřované tvrzení = query
        input_type = "passage" if task_type == TASK_RETRIEVAL_DOCUMENT else "query"
        vectors: list[list[float]] = []
        for i in range(0, len(texts), NVIDIA_EMBED_BATCH_SIZE):
            batch = texts[i:i + NVIDIA_EMBED_BATCH_SIZE]
            resp = _post(f"{self.base_url}/embeddings", self.api_key, json={
                "model": model_name, "input": batch, "input_type": input_type, "encoding_format": "float",
                "truncate": "END"})
            data = sorted(resp.get("data") or [], key=lambda d: d.get("index", 0))
            if len(data) != len(batch):
                raise AIProviderError(f"NVIDIA vrátil {len(data)} embeddingů pro {len(batch)} textů")
            for item in data:
                if len(item["embedding"]) != dim:
                    raise AIProviderError(f"Embedding má {len(item['embedding'])} dimenzí, čekáno {dim} (NVIDIA_EMBEDDING_DIM)")
                vectors.append(l2_normalize(item["embedding"]))
        return vectors

    def transcribe(self, audio, mime_type, prompt=TRANSCRIBE_PROMPT, model=None, response_schema=Transcript):
        return self._error("NVIDIA LLM audio nepřepisuje: nastav GROQ_API_KEY (TRANSCRIBE_PROVIDER=groq)",
                           model=model or ai_model(), started=time.monotonic(), p_hash=hashlib.sha256(audio).hexdigest())


class GroqProvider(BaseAIProvider):
    """Groq: jen přepis audia Whisperem (``verbose_json`` s časy úseků). Mluvčí Whisper nerozlišuje: ``speaker`` je
    prázdný a role doplní LLM v zapisovateli (``scribe.label_speakers``)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.base_url = _env("GROQ_BASE_URL", DEFAULT_GROQ_BASE_URL).rstrip("/")

    @property
    def provider_name(self) -> str:
        return "groq"

    def generate(self, prompt, system_prompt="", model=None, temperature=None, max_tokens=None,
                 response_schema=None):
        return self._error("Groq je jen pro přepis audia (TRANSCRIBE_PROVIDER), LLM nastav v AI_PROVIDER",
                           model=model or "groq", started=time.monotonic(), p_hash=prompt_hash(prompt, system_prompt))

    def embed(self, texts, task_type=TASK_RETRIEVAL_DOCUMENT, model=None, dim=None):
        raise AIProviderError("Groq embeddingy nemá, nastav EMBEDDING_PROVIDER")

    def transcribe(self, audio, mime_type, prompt=TRANSCRIBE_PROMPT, model=None, response_schema=Transcript):
        started = time.monotonic()
        model_name = model or _env("GROQ_TRANSCRIBE_MODEL", DEFAULT_GROQ_TRANSCRIBE_MODEL)
        p_hash = hashlib.sha256(audio).hexdigest()
        if response_schema is not Transcript:
            return self._error("Groq přepisuje jen audio (PDF čte pypdf)", model=model_name, started=started, p_hash=p_hash)
        mime = mime_type.split(";")[0].strip().lower()
        try:
            resp = _post(f"{self.base_url}/audio/transcriptions", self.api_key,
                         files={"file": (f"audio.{AUDIO_EXTENSIONS.get(mime, 'webm')}", audio, mime)},
                         data={"model": model_name, "temperature": "0", "response_format": "verbose_json",
                               "language": _env("TRANSCRIBE_LANGUAGE", "cs"), "prompt": WHISPER_VOCABULARY})
        except AIProviderError as exc:
            logger.error("Groq API error (model %s): %s", model_name, exc)
            return self._error(f"Groq {exc}", model=model_name, started=started, p_hash=p_hash)
        # úsek s vysokou pravděpodobností ticha = typická halucinace Whisperu („Titulky vytvořil…“)
        segments = [{"speaker": "", "start": f"{int(s['start']) // 60:02d}:{int(s['start']) % 60:02d}",
                     "text": s["text"].strip()}
                    for s in resp.get("segments") or [] if s.get("text", "").strip() and s.get("no_speech_prob", 0) < 0.8]
        data = _validate(Transcript, {"segments": segments})
        return self._success(text=resp.get("text", ""), data=data, model=model_name, tokens_in=0, tokens_out=0,
                             tokens_total=0, started=started, p_hash=p_hash)


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
PROVIDERS: dict[str, tuple[str, type[BaseAIProvider]]] = {
    "gemini": ("GEMINI_API_KEY", GeminiProvider),
    "nvidia": ("NVIDIA_API_KEY", NvidiaProvider),
    "groq": ("GROQ_API_KEY", GroqProvider),
}
SUPPORTED_PROVIDERS = ("mock", *PROVIDERS)


def get_ai_provider(provider_name: str | None = None) -> BaseAIProvider:
    """
    Provider podle ``provider_name`` nebo env ``AI_PROVIDER`` (výchozí ``mock``).

    Provider bez klíče (``GEMINI_API_KEY``, ``NVIDIA_API_KEY``, ``GROQ_API_KEY``) spadne na mock s varováním;
    výsledek má pak ``provider == "mock"`` a ``is_mock == True``, takže záměna je vidět.
    Skutečná data pacientů jen s placeným tierem a DPA (ARCHITEKTURA §5.7, D-021); hackathon = syntetická data.
    """
    chosen = (provider_name or ai_provider_name()).lower()
    if chosen == "mock":
        return MockAIProvider()
    if chosen not in PROVIDERS:
        raise ValueError(f"Neznámý AI provider {chosen!r}, podporované: {', '.join(SUPPORTED_PROVIDERS)}")
    key_env, cls = PROVIDERS[chosen]
    if not os.environ.get(key_env):
        logger.warning("Provider %s bez %s: používám MockAIProvider", chosen, key_env)
        return MockAIProvider()
    return cls()


def embedding_provider(provider: BaseAIProvider | None = None) -> BaseAIProvider:
    """Provider pro vektory v IRIS (RAG, grounding): ``EMBEDDING_PROVIDER``, jinak stejný jako LLM.

    Index musí mít vektory jednoho modelu a dimenze, proto nezávisí na tom, kdo zrovna generuje text.
    Mock provider (testy) zůstává mockem, nic se neposílá ven.
    """
    provider = provider or get_ai_provider()
    name = embedding_provider_name()
    return provider if provider.is_mock or provider.provider_name == name else get_ai_provider(name)


def transcription_provider(provider: BaseAIProvider | None = None) -> BaseAIProvider:
    """Přepis audia: ``TRANSCRIBE_PROVIDER``, jinak Groq Whisper (je-li ``GROQ_API_KEY``), jinak LLM provider."""
    provider = provider or get_ai_provider()
    if provider.is_mock:
        return provider
    name = os.environ.get("TRANSCRIBE_PROVIDER") or ("groq" if os.environ.get("GROQ_API_KEY") else provider.provider_name)
    return provider if provider.provider_name == name.lower() else get_ai_provider(name)
