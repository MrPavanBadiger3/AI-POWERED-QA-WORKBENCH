import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Execution, TestCase, TestResult
from app.services.testcases.linking import test_cases_for_nodeid


def heuristic_category(text: str) -> str:
    """Cheap, deterministic hint passed to the AI as an UNVERIFIED hint."""
    t = text or ""
    if re.search(r"net::ERR|ERR_NAME_NOT_RESOLVED|ERR_INTERNET|ERR_CONNECTION|getaddrinfo|ECONNREFUSED", t):
        return "Network Failure"
    if re.search(r"Executable doesn't exist|playwright install|BrowserType\.launch|ModuleNotFoundError|ImportError|fixture '.*' not found", t):
        return "Environment/Configuration Failure"
    if re.search(r"waiting for (locator|selector)|strict mode violation|Locator\.|element is not (visible|enabled)", t, re.I) and "TimeoutError" in t or "strict mode violation" in t:
        return "Locator Failure"
    if "AssertionError" in t or re.search(r"^E\s+assert", t, re.M):
        return "Assertion Failure"
    return "Insufficient Evidence"


def build_evidence(db: Session, result: TestResult) -> tuple[dict, Optional[TestCase]]:
    ex: Execution = result.execution
    cases = db.query(TestCase).filter(TestCase.automation_ref.isnot(None)).all()
    linked = test_cases_for_nodeid(cases, result.test_name)
    tc = linked[0] if linked else None
    evidence = {
        "execution_id": ex.execution_id if ex else None,
        "suite": ex.suite_name if ex else None,
        "failed_test": result.test_name,
        "test_case_id": tc.tc_id if tc else None,
        "expected_result": tc.expected_result if tc else None,
        "test_steps": tc.test_steps if tc else None,
        "error_message": (result.error_message or "")[:4000],
        "logs": (result.logs or "")[:3000],
        "data_driven_evidence": result.meta,
        "screenshot_file": result.screenshot_path,
        "screenshot_analyzed": False,
        "screenshot_note": "Screenshot was captured but NOT analysed: the configured text model has no image input.",
        "heuristic_category_hint_unverified": heuristic_category((result.error_message or "") + (result.logs or "")),
    }
    return evidence, tc


def evidence_prompt(e: dict) -> str:
    return "\n".join([
        f"Execution ID: {e['execution_id']}", f"Failed test (pytest node id): {e['failed_test']}",
        f"Linked test case ID: {e['test_case_id'] or 'none linked'}",
        f"Approved expected result: {e['expected_result'] or 'Insufficient information to determine.'}",
        f"Test steps from linked test case: {e['test_steps'] or 'none linked'}",
        f"Data-driven evidence (input/expected/actual): {e['data_driven_evidence'] or 'n/a'}",
        f"Heuristic category hint (unverified, may be wrong): {e['heuristic_category_hint_unverified']}",
        "--- ERROR / EXCEPTION ---", e["error_message"] or "(none)",
        "--- EXECUTION LOG EXCERPT ---", e["logs"] or "(none)",
        f"Screenshot: {'captured (not visible to you)' if e['screenshot_file'] else 'none captured'}",
    ])
