from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.ids import next_code
from app.database.database import get_db
from app.models.models import DefectReport, TestResult
from app.schemas.schemas import DefectAnalyzeRequest, DefectResponse, DefectUpdate, ReviewNote
from app.services.ai.pipeline import log_artifact, run_ai, sync_review
from app.services.ai.schemas_ai import DefectOut, FAILURE_CATEGORIES
from app.services.defects.service import build_evidence, evidence_prompt

router = APIRouter(prefix="/api/defects", tags=["defects"])


def _get(db: Session, did: str) -> DefectReport:
    d = db.get(DefectReport, did)
    if not d:
        raise HTTPException(404, "Defect report not found")
    return d


@router.post("/analyze")
async def analyze_defect(body: DefectAnalyzeRequest, db: Session = Depends(get_db)):
    """Evidence is read from the STORED execution result - the client cannot supply or alter it."""
    result = db.get(TestResult, body.test_result_id)
    if not result:
        raise HTTPException(404, "Test result not found")
    if result.status != "failed":
        raise HTTPException(409, "Only FAILED test results can be analysed.")
    evidence, tc = build_evidence(db, result)
    out, resp = await run_ai(db, "defect_analysis", evidence_prompt(evidence), DefectOut, "defect_report",
                             {"execution": evidence["execution_id"], "test": result.test_name})
    steps = out.steps_to_reproduce if isinstance(out.steps_to_reproduce, str) else "\n".join(f"{i+1}. {s}" for i, s in enumerate(out.steps_to_reproduce))
    cause = out.possible_root_cause if out.possible_root_cause.lower().startswith("hypothesis") else f"Hypothesis: {out.possible_root_cause}"
    d = DefectReport(defect_id=next_code(db, DefectReport.defect_id, "DEF"), title=out.defect_title, description=out.description,
                     steps_to_reproduce=steps, expected_result=out.expected_result, actual_result=out.actual_result, severity=out.severity,
                     priority=out.priority, severity_justification=out.severity_justification, failure_category=out.failure_category,
                     application_defect_status=out.application_defect_status, possible_root_cause=cause, observed_facts=out.observed_facts,
                     recommended_investigation=out.recommended_investigation, suggested_regression=out.suggested_regression_scenarios,
                     evidence=evidence, screenshot_analyzed=False, test_case_id=tc.tc_id if tc else None,
                     execution_id=evidence["execution_id"], test_result_id=result.id, status="pending", ai_generated=True)
    db.add(d)
    db.flush()
    log_artifact(db, "defect_report", "defect_analysis", resp, d.id, d.defect_id, [], {"execution": evidence["execution_id"], "test": result.test_name})
    db.commit()
    db.refresh(d)
    return DefectResponse.model_validate(d)


@router.get("")
def list_defects(db: Session = Depends(get_db)):
    return [DefectResponse.model_validate(d) for d in db.query(DefectReport).order_by(DefectReport.created_at.desc()).all()]


@router.get("/{did}")
def get_defect(did: str, db: Session = Depends(get_db)):
    return DefectResponse.model_validate(_get(db, did))


@router.put("/{did}")
def update_defect(did: str, body: DefectUpdate, db: Session = Depends(get_db)):
    d = _get(db, did)
    changes = body.model_dump(exclude_unset=True)
    if "failure_category" in changes and changes["failure_category"] not in FAILURE_CATEGORIES:
        raise HTTPException(400, f"failure_category must be one of {FAILURE_CATEGORIES}")
    for k, v in changes.items():
        setattr(d, k, v)
    if d.status == "approved":
        d.status = "needs_modification"
        sync_review(db, "defect_report", d.id, "needs_modification")
    db.commit()
    db.refresh(d)
    return DefectResponse.model_validate(d)


@router.post("/{did}/approve")
def approve_defect(did: str, db: Session = Depends(get_db)):
    d = _get(db, did)
    d.status = "approved"
    sync_review(db, "defect_report", d.id, "approved")
    db.commit()
    return {"status": "approved", "defect_id": d.defect_id}


@router.post("/{did}/reject")
def reject_defect(did: str, body: ReviewNote | None = None, db: Session = Depends(get_db)):
    d = _get(db, did)
    d.status = "rejected"
    sync_review(db, "defect_report", d.id, "rejected")
    db.commit()
    return {"status": "rejected", "defect_id": d.defect_id}
