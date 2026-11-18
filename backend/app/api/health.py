from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import AVAILABLE_GROQ_MODELS, settings
from app.database.database import get_db
from app.models.models import AppConfig
from app.services.ai.ai_service import ai_service, get_selected_model
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
def config_status(db: Session = Depends(get_db)):
    key = settings.GROQ_API_KEY
    return {"groq_api_configured": bool(key) and not key.startswith("your_"), "groq_model": get_selected_model(db),
            "available_models": list(AVAILABLE_GROQ_MODELS), "ai_timeout_seconds": settings.AI_TIMEOUT_SECONDS,
            "saucedemo_url": settings.SAUCEDEMO_URL, "headless": settings.HEADLESS, "execution_timeout_seconds": settings.EXECUTION_TIMEOUT_SECONDS}


class ModelSelection(BaseModel):
    model: str


@router.put("/api/config/model")
def update_model(selection: ModelSelection, db: Session = Depends(get_db)):
    if selection.model not in AVAILABLE_GROQ_MODELS:
        raise HTTPException(status_code=400, detail="Model is not in the allowed list.")
    config = db.get(AppConfig, "groq_model")
    if config is None:
        db.add(AppConfig(key="groq_model", value=selection.model))
    else:
        config.value = selection.model
    db.commit()
    return {"groq_model": selection.model}


@router.post("/api/config/test-ai")
async def test_ai(db: Session = Depends(get_db)):
    """Makes one tiny REAL call to the AI provider to prove the key/model work."""
    data, resp = await ai_service.call(PROMPTS["connectivity_check"], "ping", db)
    return {"ok": True, "model": resp.model, "response": data}


@router.get("/api/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    return dashboard(db)
