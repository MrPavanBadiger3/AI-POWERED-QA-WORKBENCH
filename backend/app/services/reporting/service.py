import csv
import html
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (AIArtifact, DefectReport, Execution, GeneratedDocument, Requirement, TestCase, TestResult)
from app.services.testcases.linking import latest_status


# ---------------- dashboard ----------------
def dashboard(db: Session) -> dict:
    count = lambda col: db.query(func.count(col)).scalar() or 0  # noqa: E731
    passed = db.query(func.count(TestResult.id)).filter(TestResult.status == "passed").scalar() or 0
    failed = db.query(func.count(TestResult.id)).filter(TestResult.status == "failed").scalar() or 0
    skipped = db.query(func.count(TestResult.id)).filter(TestResult.status == "skipped").scalar() or 0
    executed = passed + failed + skipped
    recent = db.query(Execution).order_by(Execution.created_at.desc()).limit(10).all()
    latest = recent[0] if recent else None
    from app.services.execution.runner import overall_status
    ex_row = lambda e: {"id": e.execution_id, "db_id": e.id, "suite": e.suite_name, "status": e.status,  # noqa: E731
                        "overall_status": overall_status(e), "passed": e.passed, "failed": e.failed, "skipped": e.skipped,
                        "total": e.total_tests, "created_at": e.created_at.replace(tzinfo=timezone.utc).isoformat()}
    defects = db.query(DefectReport).order_by(DefectReport.created_at.desc()).limit(5).all()
    return {
        "total_requirements": count(Requirement.id), "approved_requirements": db.query(func.count(Requirement.id)).filter(Requirement.status == "approved").scalar() or 0,
        "total_test_cases": count(TestCase.id), "approved_test_cases": db.query(func.count(TestCase.id)).filter(TestCase.status == "approved").scalar() or 0,
        "total_executions": count(Execution.id), "total_executed_tests": executed,
        "passed": passed, "failed": failed, "skipped": skipped,
        "pass_rate": round(passed / executed * 100, 1) if executed else 0,
        "total_defects": count(DefectReport.id),
        "latest_execution": ex_row(latest) if latest else None,
        "recent_executions": [ex_row(e) for e in recent],
        "recent_defects": [{"id": d.id, "defect_id": d.defect_id, "title": d.title, "severity": d.severity, "status": d.status,
                            "failure_category": d.failure_category} for d in defects],
    }


# ---------------- traceability ----------------
def traceability(db: Session) -> dict:
    rows = []
    for req in db.query(Requirement).order_by(Requirement.created_at).all():
        tcs = db.query(TestCase).filter(TestCase.requirement_id == req.id).order_by(TestCase.tc_id).all()
        approved = [t for t in tcs if t.status == "approved"]
        coverage = "covered" if approved else ("draft_only" if tcs else "not_covered")
        tc_rows, exec_states = [], []
        for t in tcs:
            ls = latest_status(db, t.automation_ref)
            tc_rows.append({"tc_id": t.tc_id, "scenario": t.test_scenario, "status": t.status, "automation_ref": t.automation_ref,
                            "latest_execution_status": ls["status"], "latest_execution_id": ls["execution_id"]})
            if t.status == "approved":
                exec_states.append(ls["status"])
        if not approved:
            latest = "n/a"
        elif "failed" in exec_states:
            latest = "failed"
        elif exec_states and all(s == "passed" for s in exec_states):
            latest = "passed"
        elif "passed" in exec_states:
            latest = "partially_executed"
        else:
            latest = "not_executed"
        rows.append({"requirement_id": req.req_id, "requirement_description": req.description, "title": req.title,
                     "status": req.status, "test_cases": tc_rows, "total_test_cases": len(tcs), "approved_test_cases": len(approved),
                     "coverage_status": coverage, "latest_execution_status": latest})
    covered = sum(1 for r in rows if r["coverage_status"] == "covered")
    return {"matrix": rows, "summary": {
        "total_requirements": len(rows), "covered": covered,
        "draft_only": sum(1 for r in rows if r["coverage_status"] == "draft_only"),
        "not_covered": sum(1 for r in rows if r["coverage_status"] == "not_covered"),
        "coverage_percentage": round(covered / len(rows) * 100, 1) if rows else 0,
        "definition": "covered = at least one APPROVED test case is linked to the requirement."}}


def rtm_csv(db: Session) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Requirement ID", "Requirement Description", "Linked Test Case IDs", "Test Coverage Status", "Latest Execution Status"])
    for r in traceability(db)["matrix"]:
        w.writerow([r["requirement_id"], r["requirement_description"], "; ".join(t["tc_id"] for t in r["test_cases"]),
                    r["coverage_status"], r["latest_execution_status"]])
    return buf.getvalue()


# ---------------- governance ----------------
def governance(db: Session) -> dict:
    q = lambda *f: db.query(func.count(AIArtifact.id)).filter(*f).scalar() or 0  # noqa: E731
    by_type = {t: n for t, n in db.query(AIArtifact.artifact_type, func.count(AIArtifact.id)).group_by(AIArtifact.artifact_type).all()}
    return {
        "total_ai_artifacts": q(),
        "approved": q(AIArtifact.review_status == "approved"),
        "pending": q(AIArtifact.review_status == "pending"),
        "rejected": q(AIArtifact.review_status == "rejected"),
        "needs_modification": q(AIArtifact.review_status == "needs_modification"),
        "validation_failures": q(AIArtifact.validation_status == "failed"),
        "with_warnings": q(AIArtifact.validation_status == "warnings"),
        "by_type": by_type,
    }


# ---------------- HTML summary report ----------------
def _img_b64(name: str | None) -> str:
    import base64
    if not name:
        return ""
    p = settings.SCREENSHOTS_DIR / Path(name).name
    return f'<img alt="failure screenshot" style="max-width:100%;border:1px solid #ccc" src="data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}">' if p.exists() else ""


def summary_report_html(db: Session, ex: Execution) -> str:
    e = html.escape
    rows = []
    for r in ex.results:
        meta = ", ".join(f"{e(str(k))}={e(str(v))}" for k, v in (r.meta or {}).items())
        detail = ""
        if r.status == "failed":
            detail = f"<pre>{e(r.error_message or 'No error text captured')}</pre>{_img_b64(r.screenshot_path)}"
        rows.append(f"<tr class='{r.status}'><td>{e(r.test_name)}</td><td>{r.status.upper()}</td><td>{(r.duration or 0):.2f}s</td><td>{meta}</td></tr>"
                    + (f"<tr><td colspan=4>{detail}</td></tr>" if detail else ""))
    from app.services.execution.runner import overall_status
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{e(ex.execution_id)} - Execution Summary</title>
<style>body{{font:14px/1.5 system-ui,sans-serif;margin:2rem;color:#111}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top}}
.passed td:nth-child(2){{color:#067d2e;font-weight:600}}.failed td:nth-child(2){{color:#b00020;font-weight:600}}pre{{white-space:pre-wrap;background:#f6f6f6;padding:8px}}</style></head><body>
<h1>Execution Summary - {e(ex.execution_id)}</h1>
<p>Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} from stored pytest results. Suite: <b>{e(ex.suite_name or '')}</b>{(' / dataset: ' + e(ex.dataset)) if ex.dataset else ''}</p>
<table><tr><th>Overall</th><th>Total</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Duration</th><th>Started</th><th>Finished</th></tr>
<tr><td>{overall_status(ex).upper()}</td><td>{ex.total_tests}</td><td>{ex.passed}</td><td>{ex.failed}</td><td>{ex.skipped}</td><td>{(ex.duration or 0):.1f}s</td><td>{e(str(ex.start_time or ''))}</td><td>{e(str(ex.end_time or ''))}</td></tr></table>
{('<p><b>Execution error:</b> ' + e(ex.error_message) + '</p>') if ex.error_message else ''}
<h2>Test results</h2><table><tr><th>Test</th><th>Result</th><th>Duration</th><th>Data / evidence</th></tr>{''.join(rows) or '<tr><td colspan=4>No test results recorded.</td></tr>'}</table>
</body></html>"""


# ---------------- documentation ----------------
def documentation_inputs(db: Session) -> dict:
    reqs = db.query(Requirement).filter(Requirement.status == "approved").order_by(Requirement.req_id).all()
    ids = [r.id for r in reqs]
    tcs = db.query(TestCase).filter(TestCase.requirement_id.in_(ids), TestCase.status == "approved").order_by(TestCase.tc_id).all() if ids else []
    return {"requirements": reqs, "test_cases": tcs, "rtm": traceability(db), "dash": dashboard(db),
            "defects": db.query(DefectReport).filter(DefectReport.status == "approved").order_by(DefectReport.defect_id).all()}


def narrative_prompt(d: dict) -> str:
    rtm = d["rtm"]["summary"]
    lines = ["APPROVED REQUIREMENTS:"] + [f"- {r.req_id}: {r.title} - {r.description}" for r in d["requirements"]]
    lines += ["APPROVED TEST CASES:"] + [f"- {t.tc_id} ({t.test_type}, {t.priority}): {t.test_scenario}" for t in d["test_cases"]]
    lines += [f"TRACEABILITY: {rtm['covered']} of {rtm['total_requirements']} requirements covered by approved test cases.",
              f"EXECUTION FIGURES: {d['dash']['total_executed_tests']} tests executed, {d['dash']['passed']} passed, {d['dash']['failed']} failed, {d['dash']['skipped']} skipped."]
    return "\n".join(lines)


def documentation_markdown(d: dict, narrative: dict | None) -> str:
    dash, rtm = d["dash"], d["rtm"]
    md = [f"# Test Documentation - SauceDemo", f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}Z from approved artifacts only._", ""]
    if narrative:
        md += ["## AI-drafted narrative (review before use)", f"**Overview.** {narrative.get('overview', '')}", "", f"**Strategy.** {narrative.get('test_strategy', '')}", "",
               f"**Coverage.** {narrative.get('coverage_summary', '')}", ""]
        if narrative.get("risk_areas"):
            md += ["**Risk areas:**"] + [f"- {x}" for x in narrative["risk_areas"]] + [""]
        if narrative.get("recommendations"):
            md += ["**Recommendations:**"] + [f"- {x}" for x in narrative["recommendations"]] + [""]
    else:
        md += ["_No AI narrative was requested for this document._", ""]
    md += ["## Approved requirements"] + [f"- **{r.req_id}** {r.title}: {r.description}" for r in d["requirements"]] + [""]
    md += ["## Approved test cases", "| ID | Requirement | Type | Priority | Scenario | Expected result |", "|---|---|---|---|---|---|"]
    code = {r.id: r.req_id for r in d["requirements"]}
    md += [f"| {t.tc_id} | {code.get(t.requirement_id, '')} | {t.test_type} | {t.priority} | {(t.test_scenario or '').replace('|', '/')} | {(t.expected_result or '').replace('|', '/')} |" for t in d["test_cases"]] + [""]
    md += ["## Requirement Traceability Matrix", "| Requirement | Linked test cases | Coverage | Latest execution |", "|---|---|---|---|"]
    md += [f"| {r['requirement_id']} | {', '.join(t['tc_id'] for t in r['test_cases']) or '-'} | {r['coverage_status']} | {r['latest_execution_status']} |" for r in rtm["matrix"]] + [""]
    md += ["## Execution summary (from stored results)",
           f"- Executions: {dash['total_executions']}; tests executed: {dash['total_executed_tests']}; passed: {dash['passed']}; failed: {dash['failed']}; skipped: {dash['skipped']}; pass rate: {dash['pass_rate']}%", ""]
    md += ["## Approved defect reports"] + ([f"- **{x.defect_id}** {x.title} (severity: {x.severity}, category: {x.failure_category})" for x in d["defects"]] or ["- none approved"])
    return "\n".join(md)


# ---------------- artifact export ----------------
def export_artifacts(db: Session) -> dict:
    root = settings.ARTIFACTS_DIR
    written = []

    def write(rel: str, text: str):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        written.append(rel)

    reqs = db.query(Requirement).filter(Requirement.status == "approved").all()
    for r in reqs:
        write(f"requirements/{r.req_id}.json", json.dumps({"req_id": r.req_id, "title": r.title, "description": r.description, "user_story": r.user_story,
                                                             "acceptance_criteria": r.acceptance_criteria, "source_snapshot": r.source_snapshot}, indent=2))
        write(f"test_scenarios/{r.req_id}_analysis.json", json.dumps({"req_id": r.req_id, "analysis": r.analysis, "governance_issues": r.analysis_validation}, indent=2))
    tcs = db.query(TestCase).filter(TestCase.status == "approved").order_by(TestCase.tc_id).all()
    code = {r.id: r.req_id for r in db.query(Requirement).all()}
    if tcs:
        write("test_cases/approved_test_cases.json", json.dumps([{"tc_id": t.tc_id, "requirement": code.get(t.requirement_id), "module": t.module, "test_scenario": t.test_scenario,
                                                                 "preconditions": t.preconditions, "test_steps": t.test_steps, "test_data": t.test_data, "expected_result": t.expected_result,
                                                                 "priority": t.priority, "test_type": t.test_type, "automation_ref": t.automation_ref} for t in tcs], indent=2))
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["tc_id", "requirement", "module", "scenario", "preconditions", "steps", "test_data", "expected", "priority", "type"])
        for t in tcs:
            w.writerow([t.tc_id, code.get(t.requirement_id), t.module, t.test_scenario, t.preconditions, " | ".join(t.test_steps or []), json.dumps(t.test_data), t.expected_result, t.priority, t.test_type])
        write("test_cases/approved_test_cases.csv", buf.getvalue())
    for d in db.query(DefectReport).filter(DefectReport.status == "approved").all():
        write(f"defect_reports/{d.defect_id}.json", json.dumps(DefectExport.dump(d), indent=2, default=str))
    for ex in db.query(Execution).filter(Execution.status == "completed").all():
        if ex.report_path and Path(ex.report_path).exists():
            write(f"execution_reports/{ex.execution_id}.html", Path(ex.report_path).read_text(encoding="utf-8"))
        write(f"execution_reports/{ex.execution_id}_summary.html", summary_report_html(db, ex))
    write("traceability_matrix.csv", rtm_csv(db))
    return {"exported": written, "location": str(root)}


class DefectExport:
    FIELDS = ["defect_id", "title", "description", "steps_to_reproduce", "expected_result", "actual_result", "severity", "priority",
              "severity_justification", "failure_category", "application_defect_status", "possible_root_cause", "observed_facts",
              "recommended_investigation", "suggested_regression", "evidence", "test_case_id", "execution_id", "status"]

    @classmethod
    def dump(cls, d):
        return {f: getattr(d, f) for f in cls.FIELDS} | {"root_cause_is_unverified_hypothesis": True}
