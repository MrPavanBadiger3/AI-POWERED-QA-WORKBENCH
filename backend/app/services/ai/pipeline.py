"""run_ai(): call provider -> parse JSON -> validate with Pydantic -> log to governance ledger."""
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.models.models import AIArtifact, now_utc
from app.services.ai.ai_service import AIError, ai_service
from app.services.ai.prompts import PROMPTS

T = TypeVar("T", bound=BaseModel)


def record_failure(db: Session, artifact_type: str, prompt_key: str, code: str, message: str, raw: str, refs: dict | None):
    db.add(AIArtifact(artifact_type=artifact_type, prompt_key=prompt_key, validation_status="failed",
                      validation_issues=[{"severity": "error", "code": code, "message": message}],
                      review_status="rejected", reviewed_at=now_utc(), source_refs=refs or {}, raw_output=(raw or "")[:8000]))
    db.commit()


async def run_ai(db: Session, prompt_key: str, user_content: str, schema: Type[T], artifact_type: str,
                 refs: dict | None = None):
    """Returns (validated_model, ProviderResponse). Raises AIError on any failure.

    Provider/network/auth failures are NOT stored as artifacts (nothing was generated); malformed or
    schema-invalid outputs ARE stored as 'failed' so governance can show validation failures.
    """
    try:
        data, resp = await ai_service.call(PROMPTS[prompt_key], user_content)
    except AIError as e:
        if e.code in ("ai_malformed_json", "ai_empty_response"):
            record_failure(db, artifact_type, prompt_key, e.code, e.message, e.raw, refs)
        raise
    try:
        return schema.model_validate(data), resp
    except ValidationError as e:
        problems = "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()[:6])
        record_failure(db, artifact_type, prompt_key, "ai_schema_invalid", problems, str(data), refs)
        raise AIError("ai_schema_invalid", f"AI output failed schema validation and was rejected: {problems}", 422, retryable=True, raw=str(data))


def log_artifact(db: Session, artifact_type: str, prompt_key: str, resp, reference_id: str, label: str,
                 issues: list[dict], refs: dict | None = None) -> AIArtifact:
    status = "passed" if not issues else ("failed" if any(i["severity"] == "error" for i in issues) else "warnings")
    art = AIArtifact(artifact_type=artifact_type, prompt_key=prompt_key, reference_id=reference_id, reference_label=label,
                     model_used=resp.model, prompt_tokens=resp.prompt_tokens, completion_tokens=resp.completion_tokens,
                     validation_status=status, validation_issues=issues, review_status="pending", source_refs=refs or {})
    db.add(art)
    return art


def sync_review(db: Session, artifact_type: str, reference_id: str, review_status: str):
    """Keep the governance ledger in step with human decisions."""
    for art in db.query(AIArtifact).filter(AIArtifact.artifact_type == artifact_type, AIArtifact.reference_id == reference_id).all():
        art.review_status = review_status
        art.reviewed_at = now_utc()
