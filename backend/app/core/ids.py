"""Stable, collision-free human IDs (REQ-001, TC-001 ...).

A persistent counter per prefix guarantees an ID is NEVER re-issued, even if the newest record is deleted
(important for traceability: TC-003 must always mean the same thing).
"""
import re
import time

from sqlalchemy.orm import Session

from app.models.models import IDCounter


def next_code(db: Session, column, prefix: str, width: int = 3) -> str:
    db.flush()
    counter = db.get(IDCounter, prefix)
    if counter is None:  # first use (or upgrade of an older DB): start after the highest existing number
        pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
        highest = max((int(m.group(1)) for (v,) in db.query(column).all() if (m := pattern.match(v or ""))), default=0)
        counter = IDCounter(prefix=prefix, value=highest)
        db.add(counter)
    counter.value += 1
    db.flush()
    return f"{prefix}-{counter.value:0{width}d}"


def new_execution_code() -> str:
    return f"EXEC-{time.strftime('%Y%m%d-%H%M%S')}"
