from app.models.models import Requirement


def source_text(req: Requirement) -> str:
    """The exact text the AI sees; also used to verify source quotes."""
    parts = [f"Title: {req.title}", f"Description: {req.description}"]
    parts.append(f"User story: {req.user_story}" if req.user_story else "User story: (not provided)")
    parts.append(f"Acceptance criteria: {req.acceptance_criteria}" if req.acceptance_criteria else "Acceptance criteria: (not provided)")
    return "\n".join(parts)
