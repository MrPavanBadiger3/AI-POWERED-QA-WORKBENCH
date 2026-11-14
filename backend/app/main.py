import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (automation, data_driven, defects, documentation, executions, governance, health, reporting, requirements, testcases)
from app.core.config import settings
from app.core.errors import ai_error_handler
from app.database.database import close_db, init_db
from app.services.ai.ai_service import AIError
from app.services.execution.runner import recover_stale_executions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    recover_stale_executions()
    yield
    close_db()


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan,
              description="AI-Powered QA Workbench API - AI-assisted testing of SauceDemo. Swagger UI at /docs.")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.add_exception_handler(AIError, ai_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    msg = "; ".join(f"{'.'.join(str(p) for p in e['loc'] if p != 'body')}: {e['msg']}" for e in exc.errors()[:5])
    return JSONResponse(status_code=422, content={"detail": f"Invalid input - {msg}", "code": "validation_error", "retryable": False})


@app.exception_handler(Exception)
async def general_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s", request.url, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error. See backend log.", "code": "internal_error", "retryable": True})


for module in (requirements, testcases, automation, executions, data_driven, defects, reporting, documentation, governance, health):
    app.include_router(module.router)
