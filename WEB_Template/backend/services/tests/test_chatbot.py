"""Chatbot u zasedání (T-338): odpověď s citacemi přes grounding, chybějící údaje, NEJISTOTA AI, odpověď bez LLM,
výběr provideru (Azure OpenAI gateway, D-021)."""
import json

import pytest

from services.ai import chatbot
from services.ai.context_builder import context_from_resources
from services.ai_service import MockAIProvider, OpenAICompatProvider
from services.tests.dataset import load_patient, load_studies

# Odpověď, jak by ji napsal LLM: dvě tvrzení sedí na zdroj, jedno má jiné číslo, jedno neexistující citaci
P03_ANSWER = {
    "claims": [
        {"text": "Poslední CEA je 13,9 µg/l.", "citations": ["P03-lab06-cea", "P03-lab06-cea"]},
        {"text": "ECOG podle lékaře je 0.", "citations": ["P03-ecog03"]},
        {"text": "CEA je 14,9 µg/l.", "citations": ["P03-lab06-cea"]},
        {"text": "Pacient je po resekci jater.", "citations": ["P03-neexistuje"]},
        {"text": "   ", "citations": ["P03-ecog03"]},
    ],
    "missing": [{"text": "Výsledek PET/CT", "expected_source": "zobrazovací vyšetření"},
                {"text": "Histologie z jater", "expected_source": " "}],
    "uncertain": [{"text": "ECOG podle lékaře 0, podle pacienta 1.", "citations": ["P03-ecog03", "P03-vymysl"]}],
}


@pytest.fixture(autouse=True)
def indexed_grounding_vectors(grounding_vectors):
    """Grounding ověřuje odpověď proti stejným in-memory vektorům jako IRIS."""


def p03_context():
    return context_from_resources("P03", load_patient("P03"), studies=load_studies())


class CaptureProvider(MockAIProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calls = []

    def generate(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs.get("system_prompt", "")))
        return super().generate(prompt, **kwargs)


class FailingProvider(MockAIProvider):
    is_mock = False

    def generate(self, prompt, **kwargs):
        return self._error("kvóta", model="gemini", started=0, p_hash="x")


def test_answer_claims_go_through_grounding():
    logged = []
    result = chatbot.answer_from_context("Jaké je poslední CEA a ECOG?", p03_context(), [],
                                         MockAIProvider(responses={"ChatbotOutput": P03_ANSWER}),
                                         lambda purpose, r: logged.append(purpose))
    assert [(c["id"], c["kind"], c["verification"], c["citations"]) for c in result["claims"]] == [
        ("bot-01", "claim", "verified", ["P03-lab06-cea"]),       # duplicitní citace jen jednou
        ("bot-02", "claim", "verified", ["P03-ecog03"]),
        ("bot-03", "claim", "unverified", ["P03-lab06-cea"]),     # 14,9 ve zdroji není
        ("bot-04", "claim", "unverified", ["P03-neexistuje"]),    # citace mimo povolená ID
        ("bot-miss-01", "missing", "verified", []),
        ("bot-miss-02", "missing", "verified", []),
    ]
    assert result["claims"][4]["expected_source"] == "zobrazovací vyšetření"
    assert "expected_source" not in result["claims"][5]
    assert all(not k.startswith("_") for c in result["claims"] for k in c)      # důvody groundingu mimo kontrakt
    # NEJISTOTA AI: citace jen z povolených ID
    assert result["uncertain"] == [{"text": "ECOG podle lékaře 0, podle pacienta 1.", "citations": ["P03-ecog03"]}]
    assert (result["text"], result["model"], logged) == ("", "mock", ["chatbot"])


def test_prompt_has_context_history_and_pseudonymized_question():
    provider = CaptureProvider(responses={"ChatbotOutput": P03_ANSWER})
    history = [{"role": "user", "text": "Jaký je ECOG?"},
               {"role": "ai", "text": "", "claims": [
                   {"kind": "claim", "text": "ECOG podle lékaře je 0.", "citations": ["P03-ecog03"]},
                   {"kind": "missing", "text": "ECOG z posledního měsíce", "citations": []}]}]
    resources = load_patient("P03")
    chatbot.answer_from_context("Co Pacient P03 (fiktivní), RČ 680312/1234, uvádí v dotazníku?",
                                context_from_resources("P03", resources), history, provider,
                                lambda *_: None, chatbot.pseudonymizer_for(resources))
    prompt, system = provider.calls[0]
    assert "[P03-lab06-cea]" in prompt and prompt.index("## Předchozí část rozhovoru") < prompt.index("## Otázka lékaře")
    assert "Lékař: Jaký je ECOG?" in prompt
    assert "AI: ECOG podle lékaře je 0. [P03-ecog03] Chybí: ECOG z posledního měsíce" in prompt
    question = prompt.split("## Otázka lékaře\n", 1)[1]
    assert question == "Co P03, RČ [RČ], uvádí v dotazníku?\n"
    assert "doporučujeme" in system and "NEJISTOTA AI" in system


def test_without_llm_answer_shows_nearest_sources_verbatim():
    result = chatbot.answer_from_context("Jaká je hodnota CEA?", p03_context(), [], MockAIProvider(), lambda *_: None)
    assert result["text"].startswith("Jazykový model není zapnutý (AI_PROVIDER=mock).")
    assert result["model"] is None and result["uncertain"] == []
    assert 1 <= len(result["claims"]) <= chatbot.NEAREST
    # citaci přiřadil kód k doslovnému textu zdroje: vždy ověřené
    assert all(len(c["citations"]) == 1 and c["verification"] == "verified" for c in result["claims"])
    assert all("CEA" in c["text"] for c in result["claims"])
    assert result["claims"][0] == {"id": "bot-src-01", "kind": "claim", "text": "2026-10-05: CEA: 13,9 µg/l (ref 0–5) H",
                                   "citations": ["P03-lab06-cea"], "verification": "verified"}    # nejnovější první
    # „hodnota“ ≠ „hodnoceno“, pomocná slova („jaký“, „poslední“) nic nenajdou
    assert chatbot._stems("Jaká je poslední hodnota hemoglobinu?") == {"hodnot", "hemoglobin"}


def test_llm_error_and_nothing_found():
    result = chatbot.answer_from_context("xyzzy qwerty", p03_context(), [], FailingProvider(), lambda *_: None)
    assert result == {"text": "AI se teď nepodařilo odpovědět. K dotazu se v dokumentaci nic nenašlo.",
                      "claims": [], "uncertain": [], "model": None}


def test_answer_loads_patient_from_iris(fake_fhir_dataset):
    result = chatbot.answer("Jaké je poslední CEA?", "P03", provider=MockAIProvider(responses={"ChatbotOutput": P03_ANSWER}),
                            log_call=lambda *_: None)
    assert result["claims"][0]["verification"] == "verified"


def test_general_question_uses_guidelines_and_trials(fake_fhir_dataset):
    context, _, resources = chatbot.load_context(None)
    assert resources == [] and context.evidence == []
    assert {"KRC", "PLI", "OBC"} <= set(context.guideline_sets)
    assert {"KRC-2.4", "RKT-03/V3"} <= context.allowed_ids
    assert context.render().startswith("# Doporučené postupy a klinické studie (bez konkrétního pacienta)")
    result = chatbot.answer("Kdy je nutný restaging před resekcí jater?", None, provider=MockAIProvider(),
                            log_call=lambda *_: None)
    assert result["claims"] and all(c["citations"][0].startswith(("KRC-", "PLI-", "OBC-", "PRS-", "RKT-"))
                                    for c in result["claims"])


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


def test_azure_gateway_answers_with_citations():
    sent = []

    def opener(req, timeout):
        sent.append((req.full_url, dict(req.header_items()), json.loads(req.data)))
        content = "```json\n" + json.dumps(P03_ANSWER, ensure_ascii=False) + "\n```"     # gateway občas obalí JSON
        return FakeResponse({"choices": [{"finish_reason": "stop", "message": {"content": content}}],
                             "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})

    provider = OpenAICompatProvider(api_key="test-key", opener=opener)
    result = chatbot.answer_from_context("Jaké je poslední CEA?", p03_context(), [], provider, lambda *_: None,
                                         model="gpt-6-astra")
    assert result["model"] == "gpt-6-astra"
    assert [c["verification"] for c in result["claims"]][:2] == ["verified", "verified"]
    url, headers, body = sent[0]
    assert url == "https://apim-rakathon-q7146n.azure-api.net/openai/v1/chat/completions"
    assert headers["Api-key"] == "test-key"
    assert body["model"] == "gpt-6-astra-global"                         # alias deploymentu gateway týmu
    assert body["response_format"]["json_schema"]["name"] == "ChatbotOutput"
    assert body["messages"][0]["role"] == "system" and "## Otázka lékaře" in body["messages"][1]["content"]


def test_chatbot_provider_choice(monkeypatch):
    for name in ("CHATBOT_PROVIDER", "CHATBOT_MODEL", "OPENAI_API_KEY", "VERIFIER_MODEL", "AI_REAL_PATIENT_DATA"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AI_PROVIDER", "mock")
    synthetic = load_patient("P03")
    provider, model = chatbot.chatbot_provider(synthetic)
    assert provider.is_mock and model is None                            # bez klíče hlavní AI_PROVIDER

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider, model = chatbot.chatbot_provider(synthetic)
    assert isinstance(provider, OpenAICompatProvider) and model == "gpt-6-1-sol-dz-eu"   # EU Data Zone
    assert isinstance(chatbot.chatbot_provider(None)[0], OpenAICompatProvider)        # obecný dotaz
    monkeypatch.setenv("CHATBOT_MODEL", "gpt-6-astra")
    assert chatbot.chatbot_provider(synthetic)[1] == "gpt-6-astra"

    # D-021: skutečný pacient (bez tagu fiktivni-data) do gateway nejde
    real = [{**r, "meta": {}} if r["resourceType"] == "Patient" else r for r in synthetic]
    provider, model = chatbot.chatbot_provider(real)
    assert provider.is_mock and model is None

    monkeypatch.setenv("CHATBOT_PROVIDER", "mock")
    assert chatbot.chatbot_provider(synthetic)[0].is_mock
    monkeypatch.setenv("CHATBOT_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY")
    assert chatbot.chatbot_provider(synthetic)[0].is_mock               # bez klíče zpět na AI_PROVIDER
    monkeypatch.setenv("CHATBOT_PROVIDER", "azure")
    with pytest.raises(ValueError):
        chatbot.chatbot_provider(synthetic)


def test_iris_down_returns_note(monkeypatch):
    def down(_):
        raise ConnectionError("IRIS neběží")
    monkeypatch.setattr(chatbot, "load_resources", down)
    assert chatbot.answer("CEA?", "P03", log_call=lambda *_: None) == {
        "text": "Podklady se nepodařilo načíst z IRIS, AI teď neodpoví.", "claims": [], "uncertain": [], "model": None}
