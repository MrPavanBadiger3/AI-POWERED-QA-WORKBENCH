import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.models.models import Execution
from app.api.executions import find, get_results, to_response
from app.services.reporting.service import REPORT_THEME_PATH, summary_report_html

router = APIRouter(prefix="/api/reports", tags=["reports"])
REPORT_THEME_MARKER = "qa-workbench-mistral-theme"


def _styled_pytest_report(content: str) -> str:
    if REPORT_THEME_MARKER in content:
        return content
    head = re.search(r"</head\s*>", content, re.IGNORECASE)
    if head is None:
        raise HTTPException(500, "The pytest HTML report is missing its head section.")
    style = REPORT_THEME_PATH.read_text(encoding="utf-8")
    return f"{content[:head.start()]}<style>{style}</style>{content[head.start():]}"


def _html_response(content: str, download: bool, filename: str) -> HTMLResponse:
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'} if download else None
    return HTMLResponse(content, headers=headers)


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
def report_html(ident: str, variant: str = Query("pytest", pattern="^(pytest|summary)$"),
                download: bool = Query(False), db: Session = Depends(get_db)):
    ex = find(db, ident)
    if variant == "summary":
        if ex.status in ("pending", "running"):
            raise HTTPException(409, "Execution has not finished yet.")
        html = summary_report_html(db, ex)
        path = settings.REPORTS_DIR / f"{ex.execution_id}_summary.html"
        path.write_text(html, encoding="utf-8")
        safe_id = re.sub(r"[^A-Za-z0-9._-]", "_", ex.execution_id)
        filename = f"{safe_id}_summary.html"
        return _html_response(html, download, filename)
    if not ex.report_path or not Path(ex.report_path).exists():
        raise HTTPException(404, "The pytest HTML report is not available for this execution (it may still be running or pytest did not start).")
    report_path = Path(ex.report_path)
    html = _styled_pytest_report(report_path.read_text(encoding="utf-8"))
    safe_id = re.sub(r"[^A-Za-z0-9._-]", "_", ex.execution_id)
    filename = f"{safe_id}.html"
    return _html_response(html, download, filename)
