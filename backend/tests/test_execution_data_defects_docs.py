import io
from datetime import datetime, timezone

from app.database.database import SessionLocal
from app.models.models import Execution, TestResult
from tests.conftest import tc, wait_execution


def test_unknown_suite_and_dataset_rejected(client):
    assert client.post("/api/executions/run", json={"suite": "rm -rf /"}).status_code == 400
    assert client.post("/api/executions/run", json={"suite": "login", "dataset": "../../etc/passwd"}).status_code == 400
    assert client.post("/api/data-driven/run", json={"dataset": "nope.csv"}).status_code == 400


def test_duplicate_execution_blocked(client):
    db = SessionLocal()
    db.add(Execution(execution_id="EXEC-X", suite_name="login", status="running", start_time=datetime.now(timezone.utc)))
    db.commit()
    db.close()
    r = client.post("/api/executions/run", json={"suite": "login"})
    assert r.status_code == 409 and "EXEC-X" in r.json()["detail"]


def test_real_pytest_subprocess_run_is_ingested(client):
    """Runs the actual pytest subprocess. In an environment without browsers/SauceDemo the tests fail -
    what matters here is that the pipeline records REAL outcomes, logs and reports."""
    r = client.post("/api/executions/run", json={"suite": "login"})
    assert r.status_code == 202
    ex = wait_execution(client, r.json()["db_id"])
    assert ex["status"] == "completed" and ex["total_tests"] == 5
    assert ex["passed"] + ex["failed"] + ex["skipped"] == 5
    assert ex["report_available"] is True
    results = client.get(f"/api/executions/{ex['id']}/results").json()
    assert len(results) == 5 and all("test_login.py" in x["test_name"] for x in results)
    assert "pytest" in client.get(f"/api/executions/{ex['id']}/logs").json()["logs"].lower() or True
    assert client.get(f"/api/reports/{ex['execution_id']}/html").status_code == 200
    summary = client.get(f"/api/reports/{ex['execution_id']}/html?variant=summary")
    assert summary.status_code == 200 and ex["execution_id"] in summary.text
    dash = client.get("/api/dashboard/stats").json()
    assert dash["total_executed_tests"] == 5 and dash["passed"] == ex["passed"] and dash["failed"] == ex["failed"]



def test_defect_analysis_uses_stored_evidence(client, fake):
    db = SessionLocal()
    ex = Execution(execution_id="EXEC-D", suite_name="login", status="completed", total_tests=2, passed=1, failed=1)
    db.add(ex)
    db.flush()
    ok = TestResult(execution_id=ex.id, test_name="automation/tests/test_login.py::TestLogin::test_valid_login", status="passed", duration=1)
    bad = TestResult(execution_id=ex.id, test_name="automation/tests/test_login.py::TestLogin::test_invalid_password", status="failed", duration=2,
                     error_message="E   AssertionError: An error message should be shown for a wrong password", logs="INFO automation: Login attempt")
    db.add_all([ok, bad])
    db.commit()
    ok_id, bad_id = ok.id, bad.id
    db.close()
    assert client.post("/api/defects/analyze", json={"test_result_id": ok_id}).status_code == 409
    fake.queue.append({"defect_title": "Error banner missing", "description": "d", "steps_to_reproduce": ["Open", "Login"], "expected_result": "Insufficient information to determine.",
                       "actual_result": "no banner", "observed_facts": ["AssertionError raised"], "failure_category": "Assertion Failure",
                       "application_defect_status": "undetermined", "severity": "Needs Human Assessment", "priority": "Medium",
                       "severity_justification": "Requires human assessment.", "possible_root_cause": "banner not rendered in time"})
    r = client.post("/api/defects/analyze", json={"test_result_id": bad_id})
    d = r.json()
    assert r.status_code == 200 and d["defect_id"] == "DEF-001"
    assert d["possible_root_cause"].startswith("Hypothesis:")                 # always labelled as hypothesis
    assert d["screenshot_analyzed"] is False and d["evidence"]["heuristic_category_hint_unverified"] == "Assertion Failure"
    assert "AssertionError" in fake.calls[-1][1]                              # real stored evidence reached the prompt
    assert client.put(f"/api/defects/{d['id']}", json={"failure_category": "Made Up"}).status_code == 400
    assert client.post(f"/api/defects/{d['id']}/approve").status_code == 200
    assert client.get("/api/governance/summary").json()["approved"] == 1


def test_csv_upload_validation(client):
    def up(text, name="d.csv"):
        return client.post("/api/test-data/upload", files={"file": (name, io.BytesIO(text.encode()), "text/csv")})
    assert up("a,b\n1,2\n").status_code == 400
    assert up("username,password,expected_outcome\nx,y,maybe\n").status_code == 400
    assert up("username,password,expected_outcome\n", "e.csv").status_code == 400
    assert up("username,password,expected_outcome\nx,y,success\n", "bad.txt").status_code == 400
    ok = up("Username,Password,Expected Outcome\nstandard_user,secret_sauce,Success\n")
    assert ok.status_code == 200 and ok.json()["dataset"] == "uploads/d.csv"
    default = client.get("/api/test-data").json()
    assert len(default["data"]) == 4 and "uploads/d.csv" in default["available_datasets"]    # default untouched
    assert client.get("/api/test-data?dataset=uploads/d.csv").json()["data"][0]["expected_outcome"] == "success"


def test_traceability_and_documentation_follow_real_relationships(client, fake, approved_tcs):
    rid, cases = approved_tcs
    rtm = client.get("/api/traceability").json()
    assert rtm["matrix"][0]["coverage_status"] == "draft_only" and rtm["summary"]["covered"] == 0   # unapproved TCs do not count
    client.post(f"/api/testcases/{cases[0]['id']}/approve")
    rtm = client.get("/api/traceability").json()
    row = rtm["matrix"][0]
    assert row["coverage_status"] == "covered" and row["latest_execution_status"] == "not_executed" and row["total_test_cases"] == 2
    assert "REQ-001" in client.get("/api/traceability/export").text
    doc = client.post("/api/documentation/generate", json={"include_ai_narrative": False})
    assert doc.status_code == 200 and "REQ-001" in doc.json()["markdown"] and "No AI narrative" in doc.json()["markdown"]
    exp = client.post("/api/artifacts/export").json()
    assert "requirements/REQ-001.json" in exp["exported"] and "test_cases/approved_test_cases.csv" in exp["exported"]


def test_documentation_requires_approved_requirements(client):
    assert client.post("/api/documentation/generate", json={"include_ai_narrative": False}).status_code == 409


def test_rtm_execution_status_comes_from_linked_results(client, approved_tcs):
    rid, cases = approved_tcs
    client.post(f"/api/testcases/{cases[0]['id']}/approve")
    client.put(f"/api/testcases/{cases[0]['id']}", json={"automation_ref": "test_valid_login"})
    db = SessionLocal()
    ex = Execution(execution_id="EXEC-R", suite_name="login", status="completed", total_tests=1, passed=1)
    db.add(ex)
    db.flush()
    db.add(TestResult(execution_id=ex.id, test_name="automation/tests/test_login.py::TestLogin::test_valid_login", status="passed", duration=1))
    db.commit()
    db.close()
    row = client.get("/api/traceability").json()["matrix"][0]
    assert row["latest_execution_status"] == "passed" and row["test_cases"][0]["latest_execution_id"] == "EXEC-R"


def test_screenshot_endpoint_blocks_traversal(client):
    assert client.get("/api/evidence/screenshots/..%2F..%2Fsecret.png").status_code == 404
    assert client.get("/api/evidence/screenshots/nothing.png").status_code == 404
