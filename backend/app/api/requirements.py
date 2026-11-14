from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.ids import next_code
from app.database.database import get_db
from app.models.models import Requirement, now_utc
from app.schemas.schemas import RequirementCreate, RequirementResponse, RequirementUpdate
from app.services.ai.pipeline import log_artifact, run_ai, sync_review
from app.services.ai.schemas_ai import RequirementAnalysisOut, check_analysis
from app.services.requirements.service import source_text

router = APIRouter(prefix="/api/requirements", tags=["requirements"])


def _get(db: Session, req_id: str) -> Requirement:
    req = db.get(Requirement, req_id)
    if not req:
        raise HTTPException(404, "Requirement not found")
    return req


async def _analyze_into(db: Session, req: Requirement):
    text = source_text(req)
    out, resp = await run_ai(db, "requirement_analysis", text, RequirementAnalysisOut, "requirement_analysis", {"requirement": req.req_id})
    issues = check_analysis(out, text)
    req.analysis, req.analysis_validation, req.status = out.model_dump(), issues, "analyzed"
    db.add(req)
    db.flush()
    # a re-analysis supersedes earlier pending ledger entries for this requirement
    sync_review(db, "requirement_analysis", req.id, "rejected")
    log_artifact(db, "requirement_analysis", "requirement_analysis", resp, req.id, req.req_id, issues, {"requirement": req.req_id})


@router.post("/analyze")
async def analyze_requirement(body: RequirementCreate, db: Session = Depends(get_db)):
    snapshot = body.model_dump()
    req = Requirement(req_id="PENDING", title=body.title.strip(), description=body.description.strip(),
                      user_story=(body.user_story or "").strip() or None,
                      acceptance_criteria=(body.acceptance_criteria or "").strip() or None, source_snapshot=snapshot)
    # AI first: if it fails nothing is stored and no ID is consumed.
    text = source_text(req)
    out, resp = await run_ai(db, "requirement_analysis", text, RequirementAnalysisOut, "requirement_analysis")
    req.req_id = next_code(db, Requirement.req_id, "REQ")
    issues = check_analysis(out, text)
    req.analysis, req.analysis_validation, req.status = out.model_dump(), issues, "analyzed"
    db.add(req)
    db.flush()
    log_artifact(db, "requirement_analysis", "requirement_analysis", resp, req.id, req.req_id, issues, {"requirement": req.req_id})
    db.commit()
    db.refresh(req)
    return {"requirement": RequirementResponse.model_validate(req), "analysis": req.analysis, "validation_issues": issues}


@router.get("")
def list_requirements(db: Session = Depends(get_db)):
    return [RequirementResponse.model_validate(r) for r in db.query(Requirement).order_by(Requirement.created_at.desc()).all()]


@router.get("/{req_id}")
def get_requirement(req_id: str, db: Session = Depends(get_db)):
    return RequirementResponse.model_validate(_get(db, req_id))


@router.put("/{req_id}")
def update_requirement(req_id: str, body: RequirementUpdate, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "No fields to update")
    for k, v in changes.items():
        setattr(req, k, (v.strip() if isinstance(v, str) else v) or None)
    if req.status in ("analyzed", "approved"):
        # Text changed => the stored analysis no longer matches it. Never keep an approval silently.
        req.status = "needs_modification"
    db.commit()
    db.refresh(req)
    return RequirementResponse.model_validate(req)


@router.post("/{req_id}/regenerate")
async def regenerate_analysis(req_id: str, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    if req.status == "approved":
        raise HTTPException(409, "This requirement is approved. Edit it first (which returns it to review) before regenerating.")
    await _analyze_into(db, req)
    db.commit()
    db.refresh(req)
    return {"requirement": RequirementResponse.model_validate(req), "analysis": req.analysis, "validation_issues": req.analysis_validation}


@router.post("/{req_id}/approve")
def approve_requirement(req_id: str, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    if req.status != "analyzed" or not req.analysis:
        raise HTTPException(409, f"Only an analysed requirement can be approved (current status: {req.status}). Regenerate the analysis first.")
    req.status, req.approved_at = "approved", now_utc()
    sync_review(db, "requirement_analysis", req.id, "approved")
    db.commit()
    return {"status": "approved", "req_id": req.req_id}


@router.delete("/{req_id}")
def delete_requirement(req_id: str, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    if req.test_cases:
        raise HTTPException(409, "Delete or move this requirement's test cases first.")
    db.delete(req)
    db.commit()
    return {"deleted": req.req_id}
