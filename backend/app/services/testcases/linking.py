"""Link human-reviewed test cases to automated tests, and derive their latest execution status."""
import re
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.models import Execution, TestCase, TestResult


def function_name(nodeid: str) -> str:
    last = nodeid.split("::")[-1]
    return re.sub(r"\[.*\]$", "", last)


def ref_matches(ref: Optional[str], nodeid: str) -> bool:
    ref = (ref or "").strip()
    if not ref:
        return False
    if "::" in ref or ref.endswith(".py"):
        return nodeid == ref or nodeid.startswith(ref)
    return function_name(nodeid) == ref


def test_cases_for_nodeid(cases: Iterable[TestCase], nodeid: str) -> list[TestCase]:
    return [tc for tc in cases if ref_matches(tc.automation_ref, nodeid)]


def latest_status(db: Session, ref: Optional[str]) -> dict:
    """Aggregate status of the most recent execution that contained a test matching `ref`."""
    if not ref:
        return {"status": "not_automated", "execution_id": None}
    execs = db.query(Execution).filter(Execution.status.in_(["completed", "failed", "timeout"])).order_by(Execution.created_at.desc()).all()
    for ex in execs:
        matched = [r for r in ex.results if ref_matches(ref, r.test_name)]
        if matched:
            statuses = {r.status for r in matched}
            status = "failed" if "failed" in statuses else ("passed" if "passed" in statuses else "skipped")
            return {"status": status, "execution_id": ex.execution_id, "tests_matched": len(matched)}
    return {"status": "not_executed", "execution_id": None}
