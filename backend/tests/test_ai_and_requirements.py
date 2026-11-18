import asyncio
from types import SimpleNamespace

import groq
import httpx

from app.services.ai.ai_service import AIError, GroqProvider, ai_service
from tests.conftest import REQ_TEXT, analysis


def test_gpt_oss_retries_without_rejected_json_response_format():
    calls = []

    class Completions:
        async def create(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise groq.BadRequestError(
                    "response_format json_object is unsupported",
                    response=httpx.Response(400, request=httpx.Request("POST", "https://api.groq.com")),
                    body={"error": "unsupported response_format"},
                )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))],
                usage=None,
            )

    provider = GroqProvider()
    provider._get_client = lambda: SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    response = asyncio.run(provider.complete("system", "user", "openai/gpt-oss-120b"))

    assert response.text == '{"ok":true}'
    assert calls[0]["reasoning_effort"] == "low" and calls[0]["max_tokens"] == 8192
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in calls[1]


def test_groq_model_not_found_has_settings_guidance():
    class Completions:
        async def create(self, **kwargs):
            raise groq.NotFoundError(
                "model not found",
                response=httpx.Response(404, request=httpx.Request("POST", "https://api.groq.com")),
                body={"error": "model not found"},
            )

    provider = GroqProvider()
    provider._get_client = lambda: SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    try:
        asyncio.run(provider.complete("system", "user", "openai/gpt-oss-20b"))
    except AIError as e:
        assert e.message == "Model not found or retired by Groq. Pick another model in Settings."
    else:
        raise AssertionError("Expected Groq model-not-found error")


def test_health_and_config_do_not_leak_key(client):
    assert client.get("/api/health").json()["status"] == "healthy"
    cfg = client.get("/api/config/status").json()
    assert cfg["groq_api_configured"] is False
    assert cfg["available_models"] == ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]
    assert cfg["groq_model"] == "openai/gpt-oss-120b"
    assert "key" not in " ".join(cfg.keys()).replace("groq_api_configured", "")


def test_model_selection_is_validated_persisted_and_used_in_ledger(client, fake):
    assert client.put("/api/config/model", json={"model": "unknown/model"}).status_code == 400
    selected = "qwen/qwen3.6-27b"
    assert client.put("/api/config/model", json={"model": selected}).json()["groq_model"] == selected
    fake.queue.append(analysis())
    assert client.post("/api/requirements/analyze", json=REQ_TEXT).status_code == 200
    assert client.get("/api/config/status").json()["groq_model"] == selected
    assert client.get("/api/governance/artifacts").json()[0]["model"] == selected


def test_missing_api_key_is_a_clear_503_not_a_fake_answer(client):
    old = ai_service.provider
    ai_service.provider = GroqProvider()
    try:
        r = client.post("/api/requirements/analyze", json=REQ_TEXT)
    finally:
        ai_service.provider = old
    assert r.status_code == 503 and r.json()["code"] == "ai_not_configured"
    assert client.get("/api/requirements").json() == []


def test_analyze_stores_requirement_and_governance_flags_bad_quote(client, fake):
    fake.queue.append(analysis(quote="this text is not in the requirement"))
    r = client.post("/api/requirements/analyze", json=REQ_TEXT)
    body = r.json()
    assert r.status_code == 200 and body["requirement"]["req_id"] == "REQ-001" and body["requirement"]["status"] == "analyzed"
    assert any(i["code"] == "unsupported_explicit_requirement" for i in body["validation_issues"])
    assert body["requirement"]["source_snapshot"]["description"] == REQ_TEXT["description"]
    g = client.get("/api/governance/summary").json()
    assert g["total_ai_artifacts"] == 1 and g["pending"] == 1 and g["with_warnings"] == 1


def test_malformed_json_rejected_and_logged(client, fake):
    fake.queue.append("this is not json {")
    r = client.post("/api/requirements/analyze", json=REQ_TEXT)
    assert r.status_code == 422 and r.json()["code"] == "ai_malformed_json"
    assert client.get("/api/requirements").json() == []
    assert client.get("/api/governance/summary").json()["validation_failures"] == 1


def test_schema_invalid_rejected(client, fake):
    fake.queue.append({"summary": "x"})  # missing required fields
    r = client.post("/api/requirements/analyze", json=REQ_TEXT)
    assert r.status_code == 422 and r.json()["code"] == "ai_schema_invalid"
    assert client.get("/api/governance/summary").json()["validation_failures"] == 1


def test_lowercase_priority_and_type_are_normalized(client, fake, approved_req):
    fake.queue.append({
        "test_cases": [{
            "scenario_ref": "SC-1",
            "module": "Login",
            "test_scenario": "Valid login",
            "preconditions": "User is on the login page",
            "test_steps": ["Open the site", "Enter standard_user and secret_sauce", "Click Login"],
            "test_data": {"username": "standard_user", "password": "secret_sauce"},
            "expected_result": "The inventory page is shown",
            "expected_result_basis": "explicit",
            "priority": "low",
            "test_type": "positive",
        }]
    })
    r = client.post("/api/testcases/generate", json={"requirement_id": approved_req})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["test_cases"][0]["priority"] == "Low"
    assert body["test_cases"][0]["test_type"] == "Positive"


def test_provider_errors_surface_with_status(client, fake):
    fake.queue.append(AIError("ai_rate_limited", "slow down", 429))
    r = client.post("/api/requirements/analyze", json=REQ_TEXT)
    assert r.status_code == 429 and r.json()["retryable"] is True


def test_approval_workflow_and_edit_resets_approval(client, fake):
    fake.queue.append(analysis())
    rid = client.post("/api/requirements/analyze", json=REQ_TEXT).json()["requirement"]["id"]
    assert client.post(f"/api/requirements/{rid}/approve").json()["status"] == "approved"
    assert client.get("/api/governance/summary").json()["approved"] == 1
    edited = client.put(f"/api/requirements/{rid}", json={"description": "Users must log in with valid credentials only. Updated."}).json()
    assert edited["status"] == "needs_modification"
    assert client.post(f"/api/requirements/{rid}/approve").status_code == 409      # stale analysis cannot be approved
    fake.queue.append(analysis())
    regen = client.post(f"/api/requirements/{rid}/regenerate")
    assert regen.status_code == 200 and regen.json()["requirement"]["status"] == "analyzed"
    assert client.post(f"/api/requirements/{rid}/approve").status_code == 200
