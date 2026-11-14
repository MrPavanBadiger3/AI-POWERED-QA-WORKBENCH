from app.services.ai.ai_service import AIError, GroqProvider, ai_service
from tests.conftest import REQ_TEXT, analysis


def test_health_and_config_do_not_leak_key(client):
    assert client.get("/api/health").json()["status"] == "healthy"
    cfg = client.get("/api/config/status").json()
    assert cfg["groq_api_configured"] is False
    assert "key" not in " ".join(cfg.keys()).replace("groq_api_configured", "")


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
