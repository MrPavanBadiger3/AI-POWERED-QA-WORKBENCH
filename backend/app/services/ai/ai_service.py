"""Provider-agnostic AI client. Groq is the first provider; add another by implementing `AIProvider`."""
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional, Protocol

from sqlalchemy.orm import Session

from app.core.config import AVAILABLE_GROQ_MODELS, RECOMMENDED_GROQ_MODEL, settings
from app.models.models import AppConfig

logger = logging.getLogger(__name__)


class AIError(Exception):
    """Raised for every AI failure; carries an HTTP status and a machine-readable code."""

    def __init__(self, code: str, message: str, http_status: int = 502, retryable: bool = True, raw: str = "",
                 model: Optional[str] = None):
        super().__init__(message)
        self.code, self.message, self.http_status, self.retryable, self.raw, self.model = code, message, http_status, retryable, raw, model


@dataclass
class ProviderResponse:
    text: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class AIProvider(Protocol):
    async def complete(self, system: str, user: str, model: str) -> ProviderResponse: ...


def get_selected_model(db: Session) -> str:
    config = db.get(AppConfig, "groq_model")
    model = config.value if config else settings.GROQ_MODEL
    return model if model in AVAILABLE_GROQ_MODELS else RECOMMENDED_GROQ_MODEL


class GroqProvider:
    def __init__(self):
        self._client = None
        self._key = None

    def _get_client(self):
        key = settings.GROQ_API_KEY
        if not key or key.startswith("your_"):
            raise AIError("ai_not_configured", "GROQ_API_KEY is not configured. Add it to backend/.env and restart the backend.",
                          503, retryable=False)
        if self._client is None or key != self._key:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=key, timeout=settings.AI_TIMEOUT_SECONDS, max_retries=1)
            self._key = key
        return self._client

    async def complete(self, system: str, user: str, model: str) -> ProviderResponse:
        import groq
        client = self._get_client()
        is_gpt_oss = model.startswith("openai/gpt-oss-")
        request = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": 8192 if is_gpt_oss else 4096,
        }
        if is_gpt_oss:
            request["reasoning_effort"] = "low"
        try:
            try:
                resp = await client.chat.completions.create(**request, response_format={"type": "json_object"})
            except groq.BadRequestError as e:
                message = str(e).lower()
                if "model" in message and ("not found" in message or "model_not_found" in message):
                    raise AIError("ai_model_error", "Model not found or retired by Groq. Pick another model in Settings.",
                                  502, retryable=False)
                if "response_format" not in message and "json_object" not in message:
                    raise
                resp = await client.chat.completions.create(**request)
        except groq.AuthenticationError:
            raise AIError("ai_auth_failed", "The AI provider rejected the API key (invalid or revoked).", 502, retryable=False)
        except groq.PermissionDeniedError:
            raise AIError("ai_permission_denied", "The API key is not permitted to use this model.", 502, retryable=False)
        except groq.RateLimitError:
            raise AIError("ai_rate_limited", "AI provider rate limit reached. Wait a moment and retry.", 429)
        except groq.APITimeoutError:
            raise AIError("ai_timeout", f"AI request timed out after {settings.AI_TIMEOUT_SECONDS:.0f}s.", 504)
        except groq.APIConnectionError:
            raise AIError("ai_network_error", "Could not reach the AI provider (network error).", 502)
        except groq.BadRequestError as e:
            raise AIError("ai_model_error", f"AI provider rejected the request (check model='{model}'): {e}", 502, retryable=False)
        except groq.NotFoundError:
            raise AIError("ai_model_error", "Model not found or retired by Groq. Pick another model in Settings.",
                          502, retryable=False)
        except groq.APIStatusError as e:
            raise AIError("ai_provider_error", f"AI provider error (HTTP {e.status_code}).", 502)
        text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        usage = getattr(resp, "usage", None)
        return ProviderResponse(text, model, getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None))


def parse_json_object(text: str) -> dict:
    """Parse model output into a dict or raise AIError('ai_malformed_json')."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise AIError("ai_malformed_json", f"AI returned malformed JSON ({e.msg} at position {e.pos}).", 422, raw=text)
    if not isinstance(data, dict):
        raise AIError("ai_malformed_json", "AI returned JSON that is not an object.", 422, raw=text)
    return data


class AIService:
    def __init__(self, provider: Optional[AIProvider] = None):
        self.provider: AIProvider = provider or GroqProvider()

    async def call(self, system_prompt: str, user_content: str, db: Session) -> tuple[dict, ProviderResponse]:
        model = get_selected_model(db)
        try:
            resp = await self.provider.complete(system_prompt, user_content, model)
        except AIError as e:
            e.model = model
            raise
        if not resp.text:
            error = AIError("ai_empty_response", "AI returned an empty response.", 502, raw="")
            error.model = model
            raise error
        try:
            return parse_json_object(resp.text), resp
        except AIError as e:
            e.model = model
            raise


ai_service = AIService()
