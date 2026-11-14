from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.ids import next_code
from app.database.database import get_db
from app.models.models import GeneratedDocument
from app.schemas.schemas import DocGenerateRequest
from app.services.ai.pipeline import log_artifact, run_ai
from app.services.ai.schemas_ai import DocNarrativeOut
from app.services.reporting import service as rs

router = APIRouter(tags=["documentation"])


@router.get("/api/traceability")
def get_traceability(db: Session = Depends(get_db)):
    return rs.traceability(db)


@router.get("/api/traceability/export")
def export_traceability(db: Session = Depends(get_db)):
    return Response(rs.rtm_csv(db), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=traceability_matrix.csv"})


@router.post("/api/documentation/generate")
async def generate_documentation(body: DocGenerateRequest | None = None, db: Session = Depends(get_db)):
    body = body or DocGenerateRequest()
    data = rs.documentation_inputs(db)
    if not data["requirements"]:
        raise HTTPException(409, "No approved requirements exist. Documentation is generated from approved artifacts only.")
    narrative, resp = None, None
    if body.include_ai_narrative:
        out, resp = await run_ai(db, "documentation", rs.narrative_prompt(data), DocNarrativeOut, "documentation")
        narrative = out.model_dump()
    doc = GeneratedDocument(doc_id=next_code(db, GeneratedDocument.doc_id, "DOC"), title="Test Documentation - SauceDemo",
                            markdown=rs.documentation_markdown(data, narrative), ai_narrative=narrative)
    db.add(doc)
    db.flush()
    if resp:
        log_artifact(db, "documentation", "documentation", resp, doc.id, doc.doc_id, [], {"requirements": [r.req_id for r in data["requirements"]]})
    db.commit()
    return {"id": doc.id, "doc_id": doc.doc_id, "markdown": doc.markdown, "ai_narrative": narrative,
            "counts": {"requirements": len(data["requirements"]), "test_cases": len(data["test_cases"])}}


@router.get("/api/documentation")
def list_documents(db: Session = Depends(get_db)):
    return [{"id": d.id, "doc_id": d.doc_id, "title": d.title, "created_at": d.created_at.isoformat() + "Z", "has_ai_narrative": bool(d.ai_narrative)}
            for d in db.query(GeneratedDocument).order_by(GeneratedDocument.created_at.desc()).all()]


@router.get("/api/documentation/{doc_id}/download")
def download_document(doc_id: str, db: Session = Depends(get_db)):
    d = db.get(GeneratedDocument, doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    return Response(d.markdown, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename={d.doc_id}.md"})


@router.post("/api/artifacts/export")
def export_artifacts(db: Session = Depends(get_db)):
    """Write approved requirements, analyses, test cases, defects, reports and the RTM into /artifacts."""
    return rs.export_artifacts(db)
