from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.models.models import Execution
from app.api.executions import find, get_results, to_response
from app.services.reporting.service import summary_report_html

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
def list_reports(db: Session = Depends(get_db)):
    return [to_response(e).model_dump(mode="json") for e in db.query(Execution).order_by(Execution.created_at.desc()).all()]


@router.get("/{ident}")
def report_detail(ident: str, db: Session = Depends(get_db)):
    ex = find(db, ident)
    return {"execution": to_response(ex), "results": get_results(ex.id, db)}


@router.post("/{ident}/generate")
def generate_summary(ident: str, db: Session = Depends(get_db)):
    ex = find(db, ident)
    if ex.status in ("pending", "running"):
        raise HTTPException(409, "Execution has not finished yet.")
    path = settings.REPORTS_DIR / f"{ex.execution_id}_summary.html"
    path.write_text(summary_report_html(db, ex), encoding="utf-8")
    ex.summary_report_path = str(path)
    db.commit()
    return {"generated": path.name, "url": f"/api/reports/{ex.execution_id}/html?variant=summary"}


@router.get("/{ident}/html")
def report_html(ident: str, variant: str = Query("pytest", pattern="^(pytest|summary)$"), db: Session = Depends(get_db)):
    ex = find(db, ident)
    if variant == "summary":
        if ex.status in ("pending", "running"):
            raise HTTPException(409, "Execution has not finished yet.")
        html = summary_report_html(db, ex)
        (settings.REPORTS_DIR / f"{ex.execution_id}_summary.html").write_text(html, encoding="utf-8")
        return HTMLResponse(html)
    if not ex.report_path or not Path(ex.report_path).exists():
        raise HTTPException(404, "The pytest HTML report is not available for this execution (it may still be running or pytest did not start).")
    return FileResponse(ex.report_path, media_type="text/html")
