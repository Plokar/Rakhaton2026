"""T-331: gateway and second-model review, exclusively with fake HTTP / MockAIProvider."""
import io
import json
import threading
from copy import deepcopy
from urllib.error import HTTPError

import pytest

from apps.copilot.schemas import Brief, BriefVerifier
from services import ai_service
from services.ai import brief as brief_module
from services.ai.context_builder import context_from_resources
from services.ai.grounding import source_text
from services.ai.verifier import VerifierOutput, cross_check
from services.ai_service import AIProviderError, MockAIProvider, OpenAICompatProvider, get_verifier_provider
from services.tests.dataset import load_patient, load_studies


@pytest.fixture(autouse=True)
def verifier_env(monkeypatch):
    for name in ("VERIFIER_PROVIDER", "VERIFIER_MODEL", "OPENAI_API_KEY", "OPENAI_BASE_URL",
                 "AI_REAL_PATIENT_DATA", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(ai_service.time, "sleep", lambda _: None)


def completion(data=None, *, finish="stop", content=None):
    return {"choices": [{"message": {"content": content if content is not None else json.dumps(data or {"verdicts": []})},
                         "finish_reason": finish}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}}


class FakeHTTP:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request, json.loads(request.data), timeout))
        response = next(self.responses)
        if isinstance(response, int):
            raise HTTPError(request.full_url, response, "test error", {}, io.BytesIO(b"private response"))
        return io.BytesIO(json.dumps(response).encode())


def test_openai_success_schema_auth_model_usage_and_fence():
    http = FakeHTTP(completion(content='```json\n{"verdicts": []}\n```'))
    result = OpenAICompatProvider(api_key="<placeholder>", opener=http).generate("test", response_schema=VerifierOutput)
    req, body, timeout = http.calls[0]
    assert req.full_url == ai_service.DEFAULT_OPENAI_BASE_URL + "/chat/completions"
    assert req.get_method() == "POST" and req.get_header("Api-key") == "<placeholder>"
    assert req.get_header("Authorization") is None
    assert body["model"] == "gpt-6-astra-global" and timeout == 90
    assert body["response_format"]["json_schema"]["strict"] is False
    assert result["status"] == "success" and result["data"] == {"verdicts": []}
    assert result["model"] == "gpt-6-astra" and result["tokens_used"] == 18
    assert result["tokens_in"] == 11 and result["tokens_out"] == 7


def test_openai_400_temperature():
    http = FakeHTTP(400, completion())
    result = OpenAICompatProvider(api_key="<placeholder>", opener=http).generate("test", response_schema=VerifierOutput)
    assert result["status"] == "success" and len(http.calls) == 2
    assert "temperature" in http.calls[0][1] and "temperature" not in http.calls[1][1]
    assert http.calls[1][1]["response_format"]["type"] == "json_schema"


def test_openai_400_json_schema_falls_back_to_json_object():
    http = FakeHTTP(400, 400, completion())
    result = OpenAICompatProvider(api_key="<placeholder>", opener=http).generate("test", response_schema=VerifierOutput)
    assert result["status"] == "success" and len(http.calls) == 3
    body = http.calls[2][1]
    assert body["response_format"] == {"type": "json_object"}
    assert "VerifierOutput" in body["messages"][-1]["content"] and "temperature" not in body


@pytest.mark.parametrize("code", [408, 429, 500, 503])
def test_openai_transient_then_success(code):
    http = FakeHTTP(code, completion())
    assert OpenAICompatProvider(api_key="<placeholder>", opener=http).generate("test")["status"] == "success"
    assert len(http.calls) == 2


@pytest.mark.parametrize("codes", [(429, 429, 429), (400, 400, 400), (401,), (403,)])
def test_openai_retries_are_bounded_and_error_is_redacted(codes):
    http = FakeHTTP(*codes)
    result = OpenAICompatProvider(api_key="<placeholder>", opener=http).generate("test", response_schema=VerifierOutput)
    assert result["status"] == "error" and len(http.calls) == len(codes)
    assert "private response" not in result["error"] and "<placeholder>" not in result["error"]


@pytest.mark.parametrize("response", [completion(finish="length"), completion(content="not JSON"),
                                    completion(data={"verdicts": [{"claim_id": "a", "verdict": "invented"}]}),
                                    {"choices": []}])
def test_openai_invalid_or_truncated_output_is_error(response):
    http = FakeHTTP(response)
    assert OpenAICompatProvider(api_key="<placeholder>", opener=http).generate(
        "test", response_schema=VerifierOutput)["status"] == "error"
    assert len(http.calls) == 1


def test_openai_custom_deployment_and_unsupported_operations(monkeypatch):
    monkeypatch.setenv("VERIFIER_MODEL", "gpt-6-luna")
    http = FakeHTTP(completion())
    provider = OpenAICompatProvider(api_key="<placeholder>", opener=http)
    provider.generate("test", max_tokens=123)
    assert http.calls[0][1]["model"] == "gpt-6-luna"
    assert http.calls[0][1]["max_completion_tokens"] == 123
    with pytest.raises(AIProviderError):
        provider.embed(["test"])
    assert provider.transcribe(b"test", "audio/wav")["status"] == "error"
    with pytest.raises(ValueError):
        ai_service.get_ai_provider("openai")


def claim(cid="c1", **kwargs):
    return {"id": cid, "kind": "claim", "verification": "verified", "text": "ECOG 0 podle lékaře",
            "citations": ["P03-ecog03"], **kwargs}


@pytest.fixture
def context():
    return context_from_resources("P03", load_patient("P03"))


@pytest.mark.parametrize("verdict", ["unsupported", "uncertain"])
def test_cross_check_rejects_or_marks_uncertainty(context, verdict):
    claims = [claim(_grounding=["previous"])]
    logged = []
    provider = MockAIProvider(responses={"VerifierOutput": {"verdicts": [
        {"claim_id": "c1", "verdict": verdict, "issue": "Rozpor se zdrojem P03-ecog03"}]}})
    result = cross_check(claims, context, provider, lambda *args: logged.append(args))
    BriefVerifier.model_validate(result)
    assert result["status"] == "ok" and result["checked"] == result["rejected"] == 1
    assert result["unchecked"] == 0 and result["issues"][0]["verdict"] == verdict
    assert claims[0]["verification"] == "unverified" and claims[0]["_grounding"][0] == "previous"
    assert claims[0]["text"] == claim()["text"]
    assert logged[0][0] == "brief.verifier" and logged[0][1]["model"] == "gpt-6-astra"
    if verdict == "uncertain":
        assert "NEJISTOTA AI" in result["issues"][0]["issue"]


def test_cross_check_missing_verdict_keeps_original_and_reports_partial(context):
    claims = [claim(), claim("c2")]
    provider = MockAIProvider(responses={"VerifierOutput": {"verdicts": [{"claim_id": "c1", "verdict": "supported"}]}})
    result = cross_check(claims, context, provider, lambda *_: None)
    assert result["status"] == "partial" and result["checked"] == result["unchecked"] == 1
    assert result["issues"] == [{"claim_id": "c2", "verdict": "unchecked", "issue": "Chybí jednoznačný verdikt druhé AI"}]
    assert claims == [claim(), claim("c2")]


@pytest.mark.parametrize("raises", [False, True])
def test_cross_check_failed_call_preserves_claim_and_audits(context, raises):
    def failure(_):
        raise TimeoutError("private details")
    provider = MockAIProvider(responses={"VerifierOutput": failure if raises else {"verdicts": "invalid"}})
    claims, logged = [claim()], []
    result = cross_check(claims, context, provider, lambda *args: logged.append(args))
    assert result["status"] == "error" and result["unchecked"] == 1 and result["checked"] == 0
    assert claims == [claim()] and len(logged) == 1 and logged[0][1]["status"] == "error"
    assert "private details" not in json.dumps(result)


def test_cross_check_filters_batches_parallel_and_sends_complete_sources(context):
    claims = [claim(f"c{i}", citations=["P03-img03", "P03-ecog03"]) for i in range(41)]
    excluded = [claim("missing", kind="missing"), claim("old", verification="unverified"), claim("recist", _computed=True)]
    barrier, prompts = threading.Barrier(3, timeout=5), []
    def supported(prompt):
        data = json.loads(prompt)
        prompts.append(data)
        barrier.wait()
        return {"verdicts": [{"claim_id": c["claim_id"], "verdict": "supported"} for c in data["claims"]]}
    result = cross_check(claims + excluded, context, MockAIProvider(responses={"VerifierOutput": supported}), lambda *_: None)
    assert result["status"] == "ok" and result["checked"] == 41 and result["rejected"] == 0
    assert sorted(len(p["claims"]) for p in prompts) == [1, 20, 20]
    assert all(p["sources"]["P03-img03"] == source_text(context, "P03-img03") for p in prompts)
    assert excluded == [claim("missing", kind="missing"), claim("old", verification="unverified"), claim("recist", _computed=True)]


def test_cross_check_duplicate_and_foreign_verdicts_are_not_applied(context):
    provider = MockAIProvider(responses={"VerifierOutput": {"verdicts": [
        {"claim_id": "c1", "verdict": "supported"}, {"claim_id": "c1", "verdict": "unsupported"},
        {"claim_id": "foreign", "verdict": "unsupported"}]}})
    claims = [claim()]
    result = cross_check(claims, context, provider, lambda *_: None)
    assert result["checked"] == 0 and result["unchecked"] == 1 and claims == [claim()]


def test_cross_check_off(context):
    assert cross_check([claim()], context, None, lambda *_: pytest.fail("no call")) == {
        "status": "off", "model": "gpt-6-astra", "checked": 0, "rejected": 0, "unchecked": 1, "issues": []}


def test_factory_defaults_off_missing_key_and_explicit_off(monkeypatch):
    resources = load_patient("P03")
    assert get_verifier_provider(resources) is None
    monkeypatch.setenv("VERIFIER_PROVIDER", "openai")
    assert get_verifier_provider(resources) is None
    monkeypatch.setenv("OPENAI_API_KEY", "<placeholder>")
    assert isinstance(get_verifier_provider(resources), OpenAICompatProvider)
    monkeypatch.delenv("VERIFIER_PROVIDER")
    assert isinstance(get_verifier_provider(resources), OpenAICompatProvider)
    monkeypatch.setenv("VERIFIER_PROVIDER", "off")
    assert get_verifier_provider(resources) is None


@pytest.mark.parametrize("chosen", ["mock", "openai", "gemini"])
def test_factory_d021_and_provider_selection(monkeypatch, chosen):
    monkeypatch.setenv("VERIFIER_PROVIDER", chosen)
    monkeypatch.setenv("OPENAI_API_KEY", "<placeholder>")
    monkeypatch.setenv("GEMINI_API_KEY", "<placeholder>")
    resources = [{"resourceType": "Patient", "id": "P99"}]
    assert get_verifier_provider(resources) is None
    assert get_verifier_provider([]) is None
    monkeypatch.setenv("AI_REAL_PATIENT_DATA", "True")
    assert get_verifier_provider(resources).provider_name == chosen
    assert get_verifier_provider(load_patient("P03")).provider_name == chosen


def test_p03_mock_verifier_retains_zero_unverified(grounding_vectors):
    def supported(prompt):
        return {"verdicts": [{"claim_id": c["claim_id"], "verdict": "supported"} for c in json.loads(prompt)["claims"]]}
    brief = brief_module.build_brief("P03", load_patient("P03"), studies=load_studies(), provider=MockAIProvider(),
                                    verifier=MockAIProvider(responses={"VerifierOutput": supported}))
    Brief.model_validate(brief)
    assert brief["stats"]["claims_unverified"] == 0
    assert brief["verifier"]["checked"] > 0 and brief["verifier"]["status"] == "ok"


def test_brief_reviews_raw_sections_and_rationale_then_computes_stats(grounding_vectors, monkeypatch):
    seen = []
    def review(claims, context, provider, log_call):
        seen.extend(deepcopy(claims))
        eligible = [c for c in claims if c["kind"] == "claim" and c["verification"] == "verified" and not c.get("_computed")]
        for c in eligible:
            c["verification"] = "unverified"
            c["_grounding"] = ["rejected"]
        return {"status": "ok", "model": "mock", "checked": len(eligible), "rejected": len(eligible), "unchecked": 0, "issues": []}
    monkeypatch.setattr(brief_module, "cross_check", review)
    brief = brief_module.build_brief("P03", load_patient("P03"), studies=load_studies(), provider=MockAIProvider())
    assert any(c.get("_computed") for c in seen)  # role calculations and fallback rationale retain internals
    assert not any(c["id"].startswith("tl-") for c in seen)
    assert any("-why-" in c["id"] for c in seen)
    assert brief["stats"]["claims_unverified"] == brief["verifier"]["rejected"] > 0
    public = [c for s in brief["sections"] for c in s["items"]]
    public += [c for o in brief["decision_support"]["treatment_options"] for c in o["rationale"]]
    assert not any(k.startswith("_") for c in public for k in c)


def test_brief_verifier_rejects_llm_rationale_without_changing_traffic_lights(grounding_vectors):
    class DraftProvider(MockAIProvider):
        is_mock = False  # exercise the B2 LLM path with a deterministic local response

    resources = load_patient("P03")
    baseline = brief_module.build_brief("P03", resources, provider=MockAIProvider())
    option_id = baseline["decision_support"]["treatment_options"][0]["id"]
    provider = DraftProvider(responses={"OptionsDraft": {"options": [{
        "procedure_id": option_id, "title": "Postup k diskusi",
        "rationale": [{"text": "ECOG 0 podle lékaře", "citations": ["P03-ecog03"]}],
        "guideline_citations": [], "considerations": [],
    }]}})
    def verdicts(prompt):
        return {"verdicts": [{"claim_id": c["claim_id"],
                               "verdict": "uncertain" if c["claim_id"] == f"{option_id}-why-1" else "supported",
                               "issue": "Test nejistoty u P03-ecog03"}
                              for c in json.loads(prompt)["claims"]]}
    brief = brief_module.build_brief("P03", resources, provider=provider,
                                    verifier=MockAIProvider(responses={"VerifierOutput": verdicts}))
    Brief.model_validate(brief)
    options = brief["decision_support"]["treatment_options"]
    target = next(o for o in options if o["id"] == option_id)
    assert target["rationale"][0]["verification"] == "unverified"
    assert brief["stats"]["claims_unverified"] == brief["verifier"]["rejected"] == 1
    assert {o["id"]: o["compatibility"] for o in options} == {
        o["id"]: o["compatibility"] for o in baseline["decision_support"]["treatment_options"]}
