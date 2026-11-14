"""Safe execution manager.

* Only whitelisted suites can run - no user-supplied commands or paths ever reach the shell.
* One execution at a time (HTTP 409 otherwise).
* pytest runs in a child process; output streams to a log file; JSON results are ingested afterwards.
* Works on Windows/macOS/Linux (thread + Popen, no asyncio subprocess).
"""
import json
import logging
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, settings
from app.core.ids import new_execution_code
from app.database.database import SessionLocal
from app.models.models import Execution, TestResult

logger = logging.getLogger(__name__)
_start_lock = threading.Lock()
TESTS = BACKEND_DIR / "automation" / "tests"


def suite_targets() -> dict[str, list[Path]]:
    generated = list(settings.GENERATED_DIR.glob("test_*.py"))
    return {
        "all": [TESTS] + ([settings.GENERATED_DIR] if generated else []),
        "login": [TESTS / "test_login.py"],
        "e2e": [TESTS / "test_e2e.py"],
        "data_driven": [TESTS / "test_data_driven.py"],
        "approved_scripts": [settings.GENERATED_DIR] if generated else [],
    }


def list_datasets() -> list[str]:
    names = [p.name for p in settings.TEST_DATA_DIR.glob("*.csv")]
    names += [f"uploads/{p.name}" for p in (settings.TEST_DATA_DIR / "uploads").glob("*.csv")]
    return sorted(names)


def recover_stale_executions():
    """On startup: executions left pending/running by a crashed server can never finish."""
    db = SessionLocal()
    try:
        for ex in db.query(Execution).filter(Execution.status.in_(["pending", "running"])).all():
            ex.status, ex.error_message = "failed", "Interrupted: the backend restarted while this execution was running."
            ex.end_time = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def start_execution(db: Session, suite: str, dataset: Optional[str] = None) -> Execution:
    targets = suite_targets()
    if suite not in targets:
        raise HTTPException(400, f"Unknown suite '{suite}'. Valid suites: {sorted(targets)}")
    if not targets[suite]:
        raise HTTPException(409, "No approved automation scripts exist yet. Approve a generated script first.")
    if dataset is not None and dataset not in list_datasets():
        raise HTTPException(400, f"Unknown dataset '{dataset}'. Available: {list_datasets()}")
    with _start_lock:
        active = db.query(Execution).filter(Execution.status.in_(["pending", "running"])).first()
        if active:
            raise HTTPException(409, f"Execution {active.execution_id} is still {active.status}. Wait for it to finish.")
        uses_dataset = suite in ("all", "data_driven")
        ex = Execution(execution_id=new_execution_code(), suite_name=suite,
                       dataset=(dataset or "login_data.csv") if uses_dataset else None, status="pending")
        db.add(ex)
        db.commit()
        db.refresh(ex)
    threading.Thread(target=_run, args=(ex.id, suite), daemon=True, name=f"exec-{ex.execution_id}").start()
    return ex


def _kill_tree(proc: subprocess.Popen):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:  # pragma: no cover
        proc.kill()


def _run(execution_pk: str, suite: str):
    db = SessionLocal()
    try:
        ex = db.get(Execution, execution_pk)
        code = ex.execution_id
        log_path = settings.REPORTS_DIR / f"{code}.log"
        json_path = settings.REPORTS_DIR / f"{code}.json"
        html_path = settings.REPORTS_DIR / f"{code}.html"
        ex.status, ex.start_time, ex.log_path = "running", datetime.now(timezone.utc), str(log_path)
        db.commit()

        cmd = [sys.executable, "-m", "pytest", *[str(t) for t in suite_targets()[suite]],
               "--json-report", f"--json-report-file={json_path}", f"--html={html_path}", "--self-contained-html",
               "-p", "no:cacheprovider", "--rootdir", str(BACKEND_DIR)]
        env = {**os.environ, "PYTHONPATH": str(BACKEND_DIR), "PYTHONIOENCODING": "utf-8",
               "QA_EXECUTION_ID": code, "QA_BASE_URL": settings.SAUCEDEMO_URL,
               "QA_HEADLESS": "1" if settings.HEADLESS else "0", "QA_SCREENSHOT_DIR": str(settings.SCREENSHOTS_DIR)}
        if ex.dataset:
            env["QA_LOGIN_DATASET"] = str(settings.TEST_DATA_DIR / ex.dataset)

        returncode, err = None, None
        kwargs = {"start_new_session": True} if os.name != "nt" else {}
        try:
            with open(log_path, "w", encoding="utf-8", errors="replace") as log:
                log.write(f"[{code}] suite={suite} dataset={ex.dataset}\n")
                log.flush()
                proc = subprocess.Popen(cmd, cwd=BACKEND_DIR, stdout=log, stderr=subprocess.STDOUT, env=env, **kwargs)
                try:
                    returncode = proc.wait(timeout=settings.EXECUTION_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    _kill_tree(proc)
                    err = f"Timed out after {settings.EXECUTION_TIMEOUT_SECONDS}s; process killed."
        except Exception as e:
            err = f"Could not start pytest: {e}"
        _finish(db, ex, json_path, html_path, returncode, err)
    except Exception as e:  # never leave an execution stuck in 'running'
        logger.exception("execution failed")
        db.rollback()
        ex = db.get(Execution, execution_pk)
        if ex:
            ex.status, ex.error_message, ex.end_time = "failed", f"Internal error while finishing execution: {e}", datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def _stage_text(stage: dict) -> str:
    parts = [stage[k] for k in ("stdout", "stderr") if stage.get(k)]
    for rec in stage.get("log", []) or []:
        parts.append(f"{rec.get('levelname', '')} {rec.get('name', '')}: {rec.get('msg', '')}")
    return "\n".join(parts)


def ingest_report(db: Session, ex: Execution, json_path: Path) -> tuple[int, int, int]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    p = f = s = 0
    for t in data.get("tests", []):
        outcome = t.get("outcome")
        status = "passed" if outcome in ("passed", "xpassed") else ("skipped" if outcome in ("skipped", "xfailed") else "failed")
        stages = [t.get(k) or {} for k in ("setup", "call", "teardown")]
        error = None
        if status == "failed":
            for st in stages:
                if st.get("outcome") in ("failed", "error") and st.get("longrepr"):
                    error = str(st["longrepr"])[:8000]
                    break
        meta = t.get("metadata") or {}
        db.add(TestResult(
            execution_id=ex.id, test_name=t.get("nodeid", ""), status=status,
            duration=round(sum(st.get("duration", 0) or 0 for st in stages), 3), error_message=error,
            screenshot_path=meta.get("screenshot"),
            logs="\n".join(filter(None, (_stage_text(st) for st in stages)))[:20000],
            meta={k: v for k, v in meta.items() if k != "screenshot"} or None))
        p, f, s = p + (status == "passed"), f + (status == "failed"), s + (status == "skipped")
    return p, f, s


def _finish(db: Session, ex: Execution, json_path: Path, html_path: Path, returncode, err):
    ex.end_time = datetime.now(timezone.utc)
    if ex.start_time:
        ex.duration = (ex.end_time - ex.start_time.replace(tzinfo=timezone.utc)).total_seconds()
    ex.report_path = str(html_path) if html_path.exists() else None
    if err:
        ex.status = "timeout" if err.startswith("Timed out") else "failed"
        ex.error_message = err
    elif json_path.exists():
        try:
            ex.passed, ex.failed, ex.skipped = ingest_report(db, ex, json_path)
            ex.total_tests = ex.passed + ex.failed + ex.skipped
            ex.status = "completed" if returncode in (0, 1) else "failed"
            if returncode not in (0, 1):
                ex.error_message = f"pytest exited with code {returncode} (2=interrupted, 3=internal error, 4=usage error, 5=no tests collected)."
        except Exception as e:
            ex.status, ex.error_message = "failed", f"Could not read pytest JSON report: {e}"
    else:
        ex.status, ex.error_message = "failed", f"pytest produced no JSON report (exit code {returncode}). See the execution log."
    db.commit()


def read_log(ex: Execution, tail_chars: int = 60000) -> str:
    if not ex.log_path or not Path(ex.log_path).exists():
        return ""
    return Path(ex.log_path).read_text(encoding="utf-8", errors="replace")[-tail_chars:]


def overall_status(ex: Execution) -> str:
    if ex.status in ("pending", "running"):
        return ex.status
    if ex.status in ("failed", "timeout"):
        return "error"
    if ex.total_tests == 0:
        return "no_tests"
    return "passed" if ex.failed == 0 else "failed"


def collect_catalog() -> list[str]:
    """List node ids of available automated tests (fixed command, no user input)."""
    targets = [str(t) for t in suite_targets()["all"]]
    out = subprocess.run([sys.executable, "-m", "pytest", *targets, "--collect-only", "-q", "-o", "addopts=", "-p", "no:cacheprovider", "--rootdir", str(BACKEND_DIR)],
                         cwd=BACKEND_DIR, capture_output=True, text=True, timeout=120,
                         env={**os.environ, "PYTHONPATH": str(BACKEND_DIR)})
    nodes = [ln.strip() for ln in out.stdout.splitlines() if "::" in ln]
    return [re.sub(r"^.*?automation[\\/]", "automation/", n).replace("\\", "/") for n in nodes]
