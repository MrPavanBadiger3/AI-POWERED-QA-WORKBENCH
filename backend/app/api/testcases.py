import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.ids import next_code
from app.database.database import get_db
from app.models.models import AutomationScript, Requirement, TestCase, now_utc
from app.schemas.schemas import GenerateTestCases, ReviewNote, TestCaseResponse, TestCaseUpdate
from app.services.ai.pipeline import log_artifact, run_ai, sync_review
from app.services.ai.schemas_ai import INSUFFICIENT, ReviewOut, TestCaseBatchOut, check_test_case
from app.services.requirements.service import source_text

router = APIRouter(prefix="/api/testcases", tags=["testcases"])


def _get(db: Session, tc_id: str) -> TestCase:
    tc = db.get(TestCase, tc_id)
    if not tc:
        raise HTTPException(404, "Test case not found")
    return tc


@router.post("/generate")
async def generate_test_cases(body: GenerateTestCases, db: Session = Depends(get_db)):
    req = db.get(Requirement, body.requirement_id)
    if not req:
        raise HTTPException(404, "Requirement not found")
    if req.status != "approved" or not req.analysis:
        raise HTTPException(409, "Test cases are generated only from an APPROVED requirement analysis. Approve it in the Requirement Analyzer first.")
    all_scenarios = req.analysis.get("scenarios", [])
    known = {s["id"] for s in all_scenarios}
    chosen = all_scenarios
    if body.scenario_ids:
        unknown = set(body.scenario_ids) - known
        if unknown:
            raise HTTPException(400, f"Unknown scenario ids: {sorted(unknown)}")
        chosen = [s for s in all_scenarios if s["id"] in body.scenario_ids]
    if not chosen:
        raise HTTPException(409, "The approved analysis contains no scenarios to generate test cases from.")

    text = source_text(req)
    prompt = (f"APPROVED REQUIREMENT {req.req_id}\n{text}\n\nAPPROVED EXPLICIT REQUIREMENTS:\n{json.dumps(req.analysis.get('explicit_requirements', []), indent=1)}"
              f"\n\nSCENARIOS TO COVER (write test cases for these only):\n{json.dumps(chosen, indent=1)}")
    out, resp = await run_ai(db, "testcase_generation", prompt, TestCaseBatchOut, "test_case", {"requirement": req.req_id})

    removed = 0
    if body.replace_unapproved:  # only after a successful generation; approved cases are never touched
        q = db.query(TestCase).filter(TestCase.requirement_id == req.id, TestCase.status != "approved")
        if body.scenario_ids:
            q = q.filter(TestCase.scenario_ref.in_(body.scenario_ids))
        for old in q.all():
            if not db.query(AutomationScript).filter(AutomationScript.test_case_id == old.id).count():
                db.delete(old)
                removed += 1
        db.flush()

    created = []
    for item in out.test_cases:
        flags = check_test_case(item, text, known)
        tc = TestCase(tc_id=next_code(db, TestCase.tc_id, "TC"), requirement_id=req.id, scenario_ref=item.scenario_ref, module=item.module,
                      test_scenario=item.test_scenario, preconditions=item.preconditions, test_steps=item.test_steps, test_data=item.test_data,
                      expected_result=item.expected_result, expected_basis=item.expected_result_basis, priority=item.priority,
                      test_type=item.test_type, status="pending", validation_flags=flags, ai_generated=True)
        db.add(tc)
        db.flush()
        log_artifact(db, "test_case", "testcase_generation", resp, tc.id, tc.tc_id, flags, {"requirement": req.req_id, "scenario": item.scenario_ref})
        created.append(tc)
    db.commit()
    return {"generated": len(created), "replaced_unapproved": removed, "test_cases": [TestCaseResponse.model_validate(t) for t in created]}


@router.get("")
def list_test_cases(requirement_id: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(TestCase).order_by(TestCase.tc_id)
    if requirement_id:
        q = q.filter(TestCase.requirement_id == requirement_id)
    if status:
        q = q.filter(TestCase.status == status)
    return [TestCaseResponse.model_validate(t) for t in q.all()]


@router.get("/export")
def export_test_cases(format: str = Query("csv", pattern="^(csv|json)$"), approved_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(TestCase).order_by(TestCase.tc_id)
    if approved_only:
        q = q.filter(TestCase.status == "approved")
    code = {r.id: r.req_id for r in db.query(Requirement).all()}
    rows = [{"Test Case ID": t.tc_id, "Requirement ID": code.get(t.requirement_id, ""), "Module": t.module, "Test Scenario": t.test_scenario,
             "Preconditions": t.preconditions, "Test Steps": t.test_steps or [], "Test Data": t.test_data or {}, "Expected Result": t.expected_result,
             "Priority": t.priority, "Test Type": t.test_type, "Review Status": t.status} for t in q.all()]
    if format == "json":
        return Response(json.dumps(rows, indent=2), media_type="application/json", headers={"Content-Disposition": "attachment; filename=test_cases.json"})
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = list(rows[0].keys()) if rows else ["Test Case ID"]
    w.writerow(cols)
    for r in rows:
        w.writerow([" | ".join(v) if isinstance(v, list) else (json.dumps(v) if isinstance(v, dict) else v) for v in r.values()])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=test_cases.csv"})


@router.get("/{tc_id}")
def get_test_case(tc_id: str, db: Session = Depends(get_db)):
    return TestCaseResponse.model_validate(_get(db, tc_id))


@router.put("/{tc_id}")
def update_test_case(tc_id: str, body: TestCaseUpdate, db: Session = Depends(get_db)):
    tc = _get(db, tc_id)
    changes = body.model_dump(exclude_unset=True)
    content_changed = any(k not in ("automation_ref", "review_note") for k in changes)
    for k, v in changes.items():
        setattr(tc, k, v)
    if content_changed and tc.status in ("approved", "rejected"):
        tc.status, tc.approved_at = "needs_modification", None  # edits to approved content require re-approval
        sync_review(db, "test_case", tc.id, "needs_modification")
    if "expected_result" in changes and changes["expected_result"] and changes["expected_result"].strip() != INSUFFICIENT:
        tc.expected_basis = "human_defined"
    db.commit()
    db.refresh(tc)
    return TestCaseResponse.model_validate(tc)


def _set_status(db: Session, tc: TestCase, status: str, note: str | None = None):
    tc.status = status
    tc.approved_at = now_utc() if status == "approved" else None
    if note is not None:
        tc.review_note = note
    sync_review(db, "test_case", tc.id, status)
    db.commit()


@router.post("/{tc_id}/approve")
def approve_test_case(tc_id: str, db: Session = Depends(get_db)):
    tc = _get(db, tc_id)
    if (tc.expected_result or "").strip() in ("", INSUFFICIENT):
        raise HTTPException(409, "The expected result is undefined (insufficient information). Edit the test case and define it before approving.")
    if not tc.test_steps:
        raise HTTPException(409, "A test case needs at least one step before approval.")
    _set_status(db, tc, "approved")
    return {"status": "approved", "tc_id": tc.tc_id}


@router.post("/{tc_id}/reject")
def reject_test_case(tc_id: str, body: ReviewNote | None = None, db: Session = Depends(get_db)):
    tc = _get(db, tc_id)
    _set_status(db, tc, "rejected", body.note if body else None)
    return {"status": "rejected", "tc_id": tc.tc_id}


@router.post("/{tc_id}/request-changes")
def request_changes(tc_id: str, body: ReviewNote | None = None, db: Session = Depends(get_db)):
    tc = _get(db, tc_id)
    _set_status(db, tc, "needs_modification", body.note if body else None)
    return {"status": "needs_modification", "tc_id": tc.tc_id}


@router.post("/{tc_id}/ai-review")
async def ai_review(tc_id: str, db: Session = Depends(get_db)):
    """Advisory second-opinion check of a test case against its source requirement (AI output validation prompt)."""
    tc = _get(db, tc_id)
    req = db.get(Requirement, tc.requirement_id)
    prompt = (f"SOURCE REQUIREMENT:\n{source_text(req)}\n\nTEST CASE {tc.tc_id}:\nScenario: {tc.test_scenario}\nPreconditions: {tc.preconditions}\n"
              f"Steps: {json.dumps(tc.test_steps)}\nTest data: {json.dumps(tc.test_data)}\nExpected result: {tc.expected_result}")
    out, resp = await run_ai(db, "output_review", prompt, ReviewOut, "review", {"test_case": tc.tc_id})
    new = [{"severity": "warning", "code": f"ai_review_{k}", "source": "ai_reviewer", "message": m}
           for k, items in (("unsupported", out.unsupported_items), ("contradiction", out.contradictions), ("invented", out.invented_details)) for m in items]
    tc.validation_flags = [f for f in (tc.validation_flags or []) if f.get("source") != "ai_reviewer"] + new
    art = log_artifact(db, "review", "output_review", resp, tc.id, tc.tc_id, [], {"test_case": tc.tc_id})
    art.review_status = "not_applicable"
    db.commit()
    return {"verdict": out.verdict, "issues": new, "note": "Advisory only - an AI verdict is not proof of correctness."}


@router.delete("/{tc_id}")
def delete_test_case(tc_id: str, db: Session = Depends(get_db)):
    tc = _get(db, tc_id)
    scripts = db.query(AutomationScript).filter(AutomationScript.test_case_id == tc.id).all()
    if any(s.status == "approved" for s in scripts):
        raise HTTPException(409, "This test case has an approved automation script. Reject the script first.")
    for s in scripts:
        db.delete(s)
    code = tc.tc_id
    db.delete(tc)
    db.commit()
    return {"deleted": code}
