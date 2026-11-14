from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import AIArtifact
from app.services.reporting.service import governance

router = APIRouter(prefix="/api/governance", tags=["governance"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return governance(db)


@router.get("/artifacts")
def artifacts(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.query(AIArtifact).order_by(AIArtifact.created_at.desc()).limit(min(limit, 500)).all()
    return [{"id": a.id, "artifact_type": a.artifact_type, "label": a.reference_label, "model": a.model_used, "prompt_key": a.prompt_key,
             "validation_status": a.validation_status, "validation_issues": a.validation_issues or [], "review_status": a.review_status,
             "source_refs": a.source_refs, "prompt_tokens": a.prompt_tokens, "completion_tokens": a.completion_tokens,
             "created_at": a.created_at.isoformat() + "Z", "reviewed_at": a.reviewed_at.isoformat() + "Z" if a.reviewed_at else None,
             "rejected_output_excerpt": (a.raw_output or "")[:400] or None} for a in rows]
