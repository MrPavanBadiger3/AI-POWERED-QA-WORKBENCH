from tests.conftest import tc


def test_generation_requires_approved_requirement(client, fake):
    from tests.conftest import REQ_TEXT, analysis
    fake.queue.append(analysis())
    rid = client.post("/api/requirements/analyze", json=REQ_TEXT).json()["requirement"]["id"]
    r = client.post("/api/testcases/generate", json={"requirement_id": rid})
    assert r.status_code == 409
    assert len(fake.queue) == 0 and len(fake.calls) == 1   # the AI was not even called


def test_generate_validates_ids_flags_and_review_flow(client, approved_tcs):
    rid, cases = approved_tcs
    assert [c["tc_id"] for c in cases] == ["TC-001", "TC-002"]
    assert all(c["status"] == "pending" for c in cases)                       # never auto-approved
    unsupported = cases[1]
    assert any(f["code"] == "unsupported_expected_result" for f in unsupported["validation_flags"])
    assert client.post(f"/api/testcases/{unsupported['id']}/approve").status_code == 409   # undefined expected result
    ok = client.put(f"/api/testcases/{unsupported['id']}", json={"expected_result": "An error message is displayed"})
    assert ok.json()["expected_basis"] == "human_defined"
    assert client.post(f"/api/testcases/{unsupported['id']}/approve").status_code == 200
    # editing an approved case sends it back to review
    assert client.put(f"/api/testcases/{unsupported['id']}", json={"priority": "Low"}).json()["status"] == "needs_modification"
    assert client.put(f"/api/testcases/{unsupported['id']}", json={"priority": "Urgent"}).status_code == 422


def test_ids_are_never_reused_after_delete(client, fake, approved_tcs):
    rid, cases = approved_tcs
    assert client.delete(f"/api/testcases/{cases[1]['id']}").status_code == 200
    fake.queue.append({"test_cases": [tc("SC-2")]})
    new = client.post("/api/testcases/generate", json={"requirement_id": rid, "scenario_ids": ["SC-2"]}).json()["test_cases"][0]
    assert new["tc_id"] == "TC-003"


def test_regenerate_selected_scenario_never_touches_approved(client, fake, approved_tcs):
    rid, cases = approved_tcs
    client.post(f"/api/testcases/{cases[0]['id']}/approve")
    fake.queue.append({"test_cases": [tc("SC-1"), tc("SC-1", test_type="Functional")]})
    r = client.post("/api/testcases/generate", json={"requirement_id": rid, "scenario_ids": ["SC-1"], "replace_unapproved": True}).json()
    assert r["replaced_unapproved"] == 0 and r["generated"] == 2
    assert client.get(f"/api/testcases/{cases[0]['id']}").json()["status"] == "approved"
    assert client.post("/api/testcases/generate", json={"requirement_id": rid, "scenario_ids": ["SC-99"]}).status_code == 400


def test_export_csv_and_json(client, approved_tcs):
    csv_text = client.get("/api/testcases/export?format=csv").text
    assert csv_text.splitlines()[0].startswith("Test Case ID,Requirement ID,Module") and "TC-001" in csv_text
    assert client.get("/api/testcases/export?format=json").json()[0]["Test Case ID"] == "TC-001"


SAFE = "from automation.pages.login_page import LoginPage\n\ndef test_gen(page):\n    LoginPage(page).login('standard_user','secret_sauce')\n    assert True\n"


def _approved_tc(client, approved_tcs):
    _, cases = approved_tcs
    client.post(f"/api/testcases/{cases[0]['id']}/approve")
    return cases[0]


def test_script_requires_approved_test_case(client, fake, approved_tcs):
    _, cases = approved_tcs
    assert client.post("/api/automation/generate-script", json={"test_case_id": cases[0]["id"]}).status_code == 409


def test_unsafe_script_cannot_be_approved(client, fake, approved_tcs):
    case = _approved_tc(client, approved_tcs)
    fake.queue.append({"script": "import os\nos.system('echo hi')\ndef test_x(page):\n    assert True\n", "explanation": "e"})
    r = client.post("/api/automation/generate-script", json={"test_case_id": case["id"]}).json()
    assert r["executed"] is False and r["script"]["status"] == "draft"
    assert any(i["severity"] == "error" for i in r["script"]["validation_issues"])
    assert client.post(f"/api/automation/scripts/{r['script']['id']}/approve").status_code == 409


def test_approved_script_is_written_and_linked_then_rejection_removes_it(client, fake, approved_tcs):
    from pathlib import Path
    case = _approved_tc(client, approved_tcs)
    fake.queue.append({"script": SAFE, "explanation": "e"})
    sid = client.post("/api/automation/generate-script", json={"test_case_id": case["id"]}).json()["script"]["id"]
    assert client.get("/api/executions/suites").json()["suites"]["approved_scripts"] == []
    assert client.post("/api/executions/run", json={"suite": "approved_scripts"}).status_code == 409   # nothing approved yet
    ap = client.post(f"/api/automation/scripts/{sid}/approve").json()
    assert ap["status"] == "approved" and ap["test_functions"] == ["test_gen"]
    f = Path(__import__("os").environ["GENERATED_DIR"]) / ap["file"]
    assert f.exists() and f.read_text().startswith('"""SCR-001')
    assert client.get(f"/api/testcases/{case['id']}").json()["automation_ref"] == "test_gen"
    assert client.get("/api/executions/suites").json()["suites"]["approved_scripts"] != []
    client.post(f"/api/automation/scripts/{sid}/reject")
    assert not f.exists()
