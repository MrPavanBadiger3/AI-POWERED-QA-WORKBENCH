from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.models.models import Execution, TestCase, TestResult
from app.schemas.schemas import ExecutionResponse, RunRequest, TestResultResponse
from app.services.execution import runner
from app.services.testcases.linking import test_cases_for_nodeid

router = APIRouter(tags=["executions"])


def to_response(ex: Execution) -> ExecutionResponse:
    r = ExecutionResponse.model_validate(ex)
    r.report_available = bool(ex.report_path and Path(ex.report_path).exists())
    r.summary_report_available = ex.status in ("completed", "failed", "timeout")
    r.overall_status = runner.overall_status(ex)
    return r


def find(db: Session, ident: str) -> Execution:
    ex = db.get(Execution, ident) or db.query(Execution).filter(Execution.execution_id == ident).first()
    if not ex:
        raise HTTPException(404, "Execution not found")
    return ex


@router.post("/api/executions/run", status_code=202)
def run_execution(body: RunRequest, db: Session = Depends(get_db)):
    ex = runner.start_execution(db, body.suite, body.dataset)
    return {"execution_id": ex.execution_id, "db_id": ex.id, "status": "started"}


@router.get("/api/executions")
def list_executions(db: Session = Depends(get_db)):
    return [to_response(e) for e in db.query(Execution).order_by(Execution.created_at.desc()).all()]


@router.get("/api/executions/suites")
def suites():
    return {"suites": {k: [Path(p).name for p in v] for k, v in runner.suite_targets().items()}, "datasets": runner.list_datasets()}


@router.get("/api/executions/{ident}")
def get_execution(ident: str, db: Session = Depends(get_db)):
    return to_response(find(db, ident))


@router.get("/api/executions/{ident}/results")
def get_results(ident: str, db: Session = Depends(get_db)):
    ex = find(db, ident)
    cases = db.query(TestCase).filter(TestCase.automation_ref.isnot(None)).all()
    out = []
    for r in db.query(TestResult).filter(TestResult.execution_id == ex.id).order_by(TestResult.created_at, TestResult.test_name).all():
        item = TestResultResponse.model_validate(r)
        item.screenshot_url = f"/api/evidence/screenshots/{r.screenshot_path}" if r.screenshot_path else None
        item.linked_test_cases = [t.tc_id for t in test_cases_for_nodeid(cases, r.test_name)]
        out.append(item)
    return out


@router.get("/api/executions/{ident}/logs")
def get_logs(ident: str, db: Session = Depends(get_db)):
    ex = find(db, ident)
    return {"status": ex.status, "error_message": ex.error_message, "logs": runner.read_log(ex) or "No log output yet."}


@router.get("/api/evidence/screenshots/{filename}")
def screenshot(filename: str):
    safe = settings.SCREENSHOTS_DIR / Path(filename).name   # basename only: no path traversal
    if safe.suffix.lower() != ".png" or not safe.is_file():
        raise HTTPException(404, "Screenshot not found")
    return FileResponse(safe, media_type="image/png")
