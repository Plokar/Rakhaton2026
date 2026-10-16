"""
AI Service – Provider Abstraction Layer for Hackathons
Supports: Google Gemini, OpenAI, Anthropic Claude, Ollama, and a Smart Mock Provider.
Zero-config: works out of the box with MockProvider even if no API keys are provided.
"""
import os
import json
import logging
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    """Abstraktní bázová třída pro AI providery"""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class MockAIProvider(BaseAIProvider):
    """
    Zero-config Mock Provider pro okamžitý start na hackathonu bez API klíčů.
    Vrací inteligentní kontextové odpovědi pro prezentace a testování.
    """
    @property
    def provider_name(self) -> str:
        return "mock"

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> Dict[str, Any]:
        prompt_lower = prompt.lower()

        if "code" in prompt_lower or "funkc" in prompt_lower or "react" in prompt_lower or "python" in prompt_lower:
            content = (
                "```typescript\n"
                "// Vygenerováno pro váš hackathon projekt\n"
                "export async function processDataStream<T>(items: T[]): Promise<T[]> {\n"
                "  console.log(`Zpracovávám ${items.length} položek v reálném čase...`);\n"
                "  return items.map((item) => ({\n"
                "    ...item,\n"
                "    processed: true,\n"
                "    timestamp: new Date().toISOString(),\n"
                "  }));\n"
                "}\n"
                "```\n\n"
                "Tato implementace zajišťuje efektivní a škálovatelné zpracování dat."
            )
        elif "summar" in prompt_lower or "shrň" in prompt_lower:
            content = (
                "### Klíčové body a shrnutí projektu:\n\n"
                "1. **Rychlost vývoje:** Šablona zkracuje čas od nápadu k funkčnímu prototypu pod 10 minut.\n"
                "2. **Architektura:** Plná integrace Next.js 16 + Django REST + WebSockets.\n"
                "3. **Škálovatelnost:** Připraveno pro okamžitou demonstraci i nasazení do produkce."
            )
        else:
            content = (
                f"**[Hackathon AI Studio – Režim simulace]**\n\n"
                f"Úspěšně jsem zpracoval váš dotaz: *\"{prompt[:80]}{'...' if len(prompt) > 80 else ''}\"*\n\n"
                f"Systém je připraven. Pro zapnutí živého LLM stačí nastavit proměnnou prostředí `GEMINI_API_KEY` nebo `OPENAI_API_KEY` v `.env`."
            )

        return {
            "response": content,
            "provider": "mock",
            "model": model or "hackathon-mock-v1",
            "tokens_used": len(prompt.split()) + len(content.split()),
            "status": "success",
            "is_mock": True,
        }


class GeminiProvider(BaseAIProvider):
    """Google Gemini REST Provider (bez nutnosti instalace těžkého SDK)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    @property
    def provider_name(self) -> str:
        return "gemini"

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> Dict[str, Any]:
        if not self.api_key:
            logger.warning("GEMINI_API_KEY není nastaven, přecházím na MockProvider")
            return MockAIProvider().generate(prompt, system_prompt, model, temperature, max_tokens)

        model_name = model or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System instructions: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        body = json.dumps({
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join([p.get("text", "") for p in parts])
                    return {
                        "response": text,
                        "provider": "gemini",
                        "model": model_name,
                        "tokens_used": data.get("usageMetadata", {}).get("totalTokenCount", 0),
                        "status": "success",
                        "is_mock": False,
                    }
                return {"error": "No response from Gemini API", "status": "error"}
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode('utf-8')
            logger.error(f"Gemini API error: {err_msg}")
            return {"error": f"Gemini HTTP {e.code}: {err_msg}", "status": "error"}
        except Exception as e:
            logger.error(f"Gemini request failed: {e}")
            return {"error": str(e), "status": "error"}


class OpenAIProvider(BaseAIProvider):
    """OpenAI REST Provider"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    @property
    def provider_name(self) -> str:
        return "openai"

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return MockAIProvider().generate(prompt, system_prompt, model, temperature, max_tokens)

        model_name = model or "gpt-4o-mini"
        url = "https://api.openai.com/v1/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body = json.dumps({
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"]
                return {
                    "response": text,
                    "provider": "openai",
                    "model": model_name,
                    "tokens_used": data.get("usage", {}).get("total_tokens", 0),
                    "status": "success",
                    "is_mock": False,
                }
        except Exception as e:
            return {"error": str(e), "status": "error"}


class OllamaProvider(BaseAIProvider):
    """Lokální Ollama Provider pro offline hackathony"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def provider_name(self) -> str:
        return "ollama"

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> Dict[str, Any]:
        model_name = model or "llama3.2"
        url = f"{self.base_url}/api/generate"

        body = json.dumps({
            "model": model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": temperature}
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "response": data.get("response", ""),
                    "provider": "ollama",
                    "model": model_name,
                    "tokens_used": data.get("eval_count", 0),
                    "status": "success",
                    "is_mock": False,
                }
        except Exception as e:
            logger.warning(f"Ollama nedostupná ({e}), padám na MockProvider")
            return MockAIProvider().generate(prompt, system_prompt, model, temperature, max_tokens)


def get_ai_provider(provider_name: Optional[str] = None) -> BaseAIProvider:
    """Factory pro získání požadovaného AI providera"""
    chosen = (provider_name or os.environ.get("AI_PROVIDER", "mock")).lower()

    if chosen == "gemini":
        return GeminiProvider()
    elif chosen in ("openai", "gpt"):
        return OpenAIProvider()
    elif chosen == "ollama":
        return OllamaProvider()
    elif chosen == "mock":
        return MockAIProvider()

    # Default fallback
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiProvider()
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIProvider()

    return MockAIProvider()
