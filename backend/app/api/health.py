from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.services.ai.ai_service import ai_service, parse_json_object
from app.services.ai.prompts import PROMPTS
from app.services.reporting.service import dashboard

router = APIRouter(tags=["system"])


@router.get("/api/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        ok = True
    except Exception:
        ok = False
    return {"status": "healthy" if ok else "degraded", "database": "connected" if ok else "error", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@router.get("/api/config/status")
def config_status():
    key = settings.GROQ_API_KEY
    return {"groq_api_configured": bool(key) and not key.startswith("your_"), "groq_model": settings.GROQ_MODEL, "ai_timeout_seconds": settings.AI_TIMEOUT_SECONDS,
            "saucedemo_url": settings.SAUCEDEMO_URL, "headless": settings.HEADLESS, "execution_timeout_seconds": settings.EXECUTION_TIMEOUT_SECONDS}


@router.post("/api/config/test-ai")
async def test_ai():
    """Makes one tiny REAL call to the AI provider to prove the key/model work."""
    data, resp = await ai_service.call(PROMPTS["connectivity_check"], "ping")
    return {"ok": True, "model": resp.model, "response": data}


@router.get("/api/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    return dashboard(db)
