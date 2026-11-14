from fastapi import Request
from fastapi.responses import JSONResponse

from app.services.ai.ai_service import AIError


async def ai_error_handler(request: Request, exc: AIError):
    return JSONResponse(status_code=exc.http_status,
                        content={"detail": exc.message, "code": exc.code, "retryable": exc.retryable})
