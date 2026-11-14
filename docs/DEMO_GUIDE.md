# 30-minute Demo Guide

## Before the demo (do once, ~15 min, with internet)
1. `.env` set; both servers running; Settings → **Test AI connection** = success.
2. Run the whole workflow once with `artifacts/requirements/sample_requirements.md` (SR-2). Approve ~6 test cases, link them to automated tests, **Run All Tests**, analyse one failure (if none fails naturally, upload a CSV whose expected outcome is deliberately wrong for one row - e.g. `standard_user,secret_sauce,failure` - and say so openly), generate documentation, **Export all artifacts**.
3. Copy screenshots/reports to `artifacts/backup_evidence/`. Clear the DB (delete `backend/qa_workbench.db`, restart) if you want a clean live run.

## Running order
| Time | Show | Key point to say |
|---|---|---|
| 0–3 | README diagram, `docs/ARCHITECTURE.md`, Swagger `/docs` | React → FastAPI → Groq / pytest+Playwright → SQLite; AI is advisory, humans approve |
| 3–7 | Requirement Analyzer: load simple example → Analyze | Explicit (with source quote) vs derived vs AI suggestion vs assumptions; edit; approve; send on |
| 7–11 | Test Case Generator | Pending by default; governance flags; edit expected result; approve; filters; CSV export; regenerate one scenario |
| 11–18 | Test Automation: run *Product → Checkout*; Data-Driven: show CSV, run, per-row expected/actual; upload a bad CSV to show validation | Same test function per row; POM; failure screenshots; AI script → draft → review → approve → run |
| 18–23 | Execution Reports: history, failure log, screenshot, pytest HTML + summary; Overview dashboard | Every number is from the DB |
| 23–26 | Defect Analysis on a failed result | Category (locator/assertion/env…), root cause labelled *Hypothesis*, screenshot *not* analysed, human approves |
| 26–28 | Documentation → RTM; AI Governance | Coverage only from saved approved links; ledger of AI artifacts, validation failures |
| 28–30 | Architecture recap, limits (`KNOWN_LIMITATIONS.md`), questions | Be explicit about what is advisory/unverified |

## If something fails live
- **No internet / SauceDemo down:** show `artifacts/backup_evidence/` and state it is **recorded, not live**.
- **Groq error:** the UI shows the exact error with Retry - that itself demonstrates error handling. Show previously saved analyses/test cases (they persist in SQLite).
- **Another execution is running (409):** wait for it to finish.

## Likely questions
- *Why not auto-approve AI output?* Governance: AI confidence is not correctness.
- *How do you stop hallucinated expected results?* Prompt rules + schema validation + flags (unsupported result, quoted text not in source, data not in source) + approval blocked while expected result is undefined.
- *How is coverage computed?* `docs/TRACEABILITY_MATRIX.md`.
