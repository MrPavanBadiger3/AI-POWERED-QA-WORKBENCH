"""API tests. The AI provider is replaced by a scripted test double (tests only - never used by the app)."""
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="qaw_test_"))
os.environ.update({
    "DATABASE_URL": f"sqlite:///{(_TMP / 'test.db').as_posix()}", "REPORTS_DIR": str(_TMP / "reports"), "SCREENSHOTS_DIR": str(_TMP / "shots"),
    "GENERATED_DIR": str(_TMP / "generated"), "ARTIFACTS_DIR": str(_TMP / "artifacts"), "GROQ_API_KEY": "",
    "EXECUTION_TIMEOUT_SECONDS": "120", "TEST_DATA_DIR": str(_TMP / "test_data"),
})
shutil.copytree(Path(__file__).resolve().parents[1] / "automation" / "test_data", _TMP / "test_data")
(Path(os.environ["GENERATED_DIR"])).mkdir(parents=True, exist_ok=True)

from fastapi.testclient import TestClient  # noqa: E402

from app.database.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.ai.ai_service import AIError, ProviderResponse, ai_service, GroqProvider  # noqa: E402

REQ_TEXT = {"title": "Login feature", "description": "Users must be able to log in with valid credentials and reach the inventory page.",
            "user_story": "As a customer I want to log in so that I can shop.",
            "acceptance_criteria": "Given standard_user and secret_sauce the inventory page is shown."}


class ScriptedProvider:
    """Returns queued responses (dict -> JSON text, str -> raw text, Exception -> raised)."""
    def __init__(self):
        self.queue, self.calls = [], []

    async def complete(self, system, user, model):
        self.calls.append((system, user))
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return ProviderResponse(item if isinstance(item, str) else json.dumps(item), model, 10, 20)


def analysis(quote="log in with valid credentials", **over):
    base = {"summary": "Login", "explicit_requirements": [{"id": "FR-1", "statement": "Valid users can log in", "source_quote": quote}],
            "scenarios": [{"id": "SC-1", "title": "Valid login", "category": "positive", "classification": "derived", "basis": "FR-1", "related_requirements": ["FR-1"]},
                          {"id": "SC-2", "title": "Wrong password", "category": "negative", "classification": "ai_suggestion", "basis": "suggested", "related_requirements": []}],
            "potentially_missed_scenarios": [], "missing_information": ["Lockout rules"], "ambiguities": [], "assumptions": [],
            "validation_status": "partial", "validation_notes": "ok"}
    return base | over


def tc(ref="SC-1", expected="The inventory page is shown", basis="explicit", **over):
    return {"scenario_ref": ref, "module": "Login", "test_scenario": f"Scenario {ref}", "preconditions": "none",
            "test_steps": ["Open site", "Enter credentials", "Click Login"], "test_data": {"username": "standard_user"},
            "expected_result": expected, "expected_result_basis": basis, "priority": "High", "test_type": "Positive"} | over


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    gen = Path(os.environ["GENERATED_DIR"])
    for f in gen.glob("*.py"):
        f.unlink()
    yield


@pytest.fixture
def fake():
    p = ScriptedProvider()
    old = ai_service.provider
    ai_service.provider = p
    yield p
    ai_service.provider = old


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def approved_req(client, fake):
    fake.queue.append(analysis())
    r = client.post("/api/requirements/analyze", json=REQ_TEXT)
    assert r.status_code == 200, r.text
    rid = r.json()["requirement"]["id"]
    assert client.post(f"/api/requirements/{rid}/approve").status_code == 200
    return rid


@pytest.fixture
def approved_tcs(client, fake, approved_req):
    fake.queue.append({"test_cases": [tc("SC-1"), tc("SC-2", expected="Insufficient information to determine.", basis="insufficient_information", test_type="Negative")]})
    r = client.post("/api/testcases/generate", json={"requirement_id": approved_req})
    assert r.status_code == 200, r.text
    return approved_req, r.json()["test_cases"]


def wait_execution(client, ident, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        ex = client.get(f"/api/executions/{ident}").json()
        if ex["status"] not in ("pending", "running"):
            return ex
        time.sleep(0.5)
    raise AssertionError("execution did not finish")
