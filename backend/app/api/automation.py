import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.ids import next_code
from app.database.database import get_db
from app.models.models import AutomationScript, TestCase, now_utc
from app.schemas.schemas import ScriptGenerateRequest, ScriptResponse, ScriptUpdate
from app.services.ai.pipeline import log_artifact, run_ai, sync_review
from app.services.ai.schemas_ai import ScriptOut
from app.services.execution.runner import collect_catalog
from app.services.testcases.script_safety import check_script, test_function_names

router = APIRouter(prefix="/api/automation", tags=["automation"])


def _get(db: Session, sid: str) -> AutomationScript:
    s = db.get(AutomationScript, sid)
    if not s:
        raise HTTPException(404, "Script not found")
    return s


@router.get("/catalog")
def catalog():
    """Automated tests that exist right now (collected by pytest). Used to link test cases to automation."""
    try:
        nodes = collect_catalog()
    except Exception as e:
        raise HTTPException(500, f"Could not collect tests: {e}")
    return {"tests": nodes, "functions": sorted({n.split("::")[-1].split("[")[0] for n in nodes})}


@router.post("/generate-script")
async def generate_script(body: ScriptGenerateRequest, db: Session = Depends(get_db)):
    tc = db.get(TestCase, body.test_case_id)
    if not tc:
        raise HTTPException(404, "Test case not found")
    if tc.status != "approved":
        raise HTTPException(409, "Scripts are generated only for APPROVED test cases.")
    prompt = (f"Test case {tc.tc_id}: {tc.test_scenario}\nModule: {tc.module} | Type: {tc.test_type} | Priority: {tc.priority}\n"
              f"Preconditions: {tc.preconditions}\nSteps: {json.dumps(tc.test_steps)}\nTest data: {json.dumps(tc.test_data)}\n"
              f"Expected result: {tc.expected_result}\nApplication under test: {settings.SAUCEDEMO_URL}")
    out, resp = await run_ai(db, "script_generation", prompt, ScriptOut, "automation_script", {"test_case": tc.tc_id})
    issues = check_script(out.script)
    sc = AutomationScript(script_id=next_code(db, AutomationScript.script_id, "SCR"), test_case_id=tc.id, code=out.script,
                          explanation=out.explanation, notes=out.notes, validation_issues=issues, status="draft", model_used=resp.model)
    db.add(sc)
    db.flush()
    log_artifact(db, "automation_script", "script_generation", resp, sc.id, sc.script_id, issues, {"test_case": tc.tc_id})
    db.commit()
    db.refresh(sc)
    return {"script": ScriptResponse.model_validate(sc), "assertions": out.assertions, "test_case": {"tc_id": tc.tc_id, "scenario": tc.test_scenario},
            "executed": False, "message": "Saved as DRAFT. It has NOT been executed. Review, then approve it to make it runnable."}


@router.get("/scripts")
def list_scripts(db: Session = Depends(get_db)):
    tcs = {t.id: t.tc_id for t in db.query(TestCase).all()}
    return [ScriptResponse.model_validate(s).model_dump(mode="json") | {"tc_id": tcs.get(s.test_case_id)}
            for s in db.query(AutomationScript).order_by(AutomationScript.script_id).all()]


@router.get("/scripts/{sid}")
def get_script(sid: str, db: Session = Depends(get_db)):
    return ScriptResponse.model_validate(_get(db, sid))


@router.put("/scripts/{sid}")
def edit_script(sid: str, body: ScriptUpdate, db: Session = Depends(get_db)):
    s = _get(db, sid)
    s.code, s.validation_issues = body.code, check_script(body.code)
    if s.status == "approved":   # edited => no longer the approved version
        _remove_file(s)
        sync_review(db, "automation_script", s.id, "needs_modification")
    s.status, s.approved_at = "draft", None
    db.commit()
    db.refresh(s)
    return ScriptResponse.model_validate(s)


def _remove_file(s: AutomationScript):
    if s.file_path:
        from pathlib import Path
        Path(s.file_path).unlink(missing_ok=True)
        s.file_path = None


@router.post("/scripts/{sid}/approve")
def approve_script(sid: str, db: Session = Depends(get_db)):
    s = _get(db, sid)
    issues = check_script(s.code)
    s.validation_issues = issues
    if any(i["severity"] == "error" for i in issues):
        db.commit()
        raise HTTPException(409, "Script failed validation: " + "; ".join(i["message"] for i in issues if i["severity"] == "error"))
    tc = db.get(TestCase, s.test_case_id)
    path = settings.GENERATED_DIR / f"test_gen_{s.script_id.lower().replace('-', '_')}.py"
    header = (f'"""{s.script_id} for {tc.tc_id if tc else "?"}. AI-generated, human-approved on '
              f'{datetime.now(timezone.utc).isoformat(timespec="seconds")}Z. Edit via the workbench so approval is re-recorded."""\n')
    path.write_text(header + s.code, encoding="utf-8")
    s.file_path, s.status, s.approved_at = str(path), "approved", now_utc()
    names = test_function_names(s.code)
    if tc and not tc.automation_ref and names:
        tc.automation_ref = names[0]    # makes the RTM able to report this test case's execution status
    sync_review(db, "automation_script", s.id, "approved")
    db.commit()
    return {"status": "approved", "file": path.name, "test_functions": names}


@router.post("/scripts/{sid}/reject")
def reject_script(sid: str, db: Session = Depends(get_db)):
    s = _get(db, sid)
    _remove_file(s)
    s.status, s.approved_at = "rejected", None
    sync_review(db, "automation_script", s.id, "rejected")
    db.commit()
    return {"status": "rejected"}
