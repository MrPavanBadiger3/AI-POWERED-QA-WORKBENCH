# Progress Tracker

Levels: **Not Started · In Progress · Implemented · Tested · Verified · Blocked**.
*Tested* = automated checks passed in the build environment. *Verified* = demonstrated end-to-end with the real
external services. No row is "Verified" for live Groq/SauceDemo because those could not be reached while building.

## Evidence collected (this revision)
- `python -m pytest tests` → **24 passed** (API, governance, validation, execution subprocess, RTM, upload, defect pipeline).
- `pytest automation/tests --collect-only` → 13 tests (5 login, 4 e2e, 4 data-driven rows from CSV).
- Real pytest subprocess run through the execution manager: results/report/log ingested (in an environment without a browser the tests error - the pipeline recorded that honestly).
- `tsc -b` clean; `vite build` OK (fresh `npm ci`).
- Live `uvicorn`: `/api/health`, `/docs`, missing-key → HTTP 503 `ai_not_configured`, zero-state dashboard.

## Feature status
| Area | Status | Notes |
|---|---|---|
| Prereq audit + project skills | Verified | Skills actually installed (`skills-lock.json`, `DESIGN.md`) |
| Backend foundation, config, DB, IDs | Tested | Monotonic ID counter (IDs never reused) |
| AI service (Groq), prompts, validation pipeline | Tested (test double) | Live Groq call: **Not verified** - use Settings → Test AI |
| Requirement analyzer + approval | Tested | explicit/derived/suggestion/assumption separation, source-quote check |
| Test case generator + review workflow | Tested | gated on approved analysis; edit/approve/reject/delete/export/regenerate-scenarios |
| AI script generation → review → approve → run | Tested | static safety check; only approved saved file executes |
| Playwright POM + pytest suites | Implemented | Collected OK; **live SauceDemo run not verified** |
| Failure screenshots / evidence metadata | Implemented | needs a browser to exercise |
| Data-driven login (CSV, upload validation) | Tested (API/collection) | live per-row results: not verified |
| Execution manager, reports (pytest-html + summary) | Tested | duplicate-run block, timeout, restart recovery |
| AI defect analysis | Tested (test double) | evidence read from DB; hypothesis labelled; screenshot not analysed |
| Dashboard (real data) | Tested | all-time totals from DB |
| RTM + documentation + artifact export | Tested | coverage computed from saved links |
| AI governance ledger/dashboard | Tested | approvals sync from review actions |
| Frontend (10 pages) | Implemented (type-check + build) | not click-tested in a real browser |

## Remaining before submission (needs your machine)
1. Add `GROQ_API_KEY`; Settings → Test AI connection.
2. Run the full workflow once (see `DEMO_GUIDE.md`), including *Run All Tests* and one AI defect analysis.
3. Export artifacts; copy screenshots into `artifacts/backup_evidence/`.
4. Click through every page once; fix anything environment-specific; update this tracker to Verified with dates.

## Known issues
See `KNOWN_LIMITATIONS.md`. Fixed in this revision: non-unique IDs after deletes, no AI error handling, governance always "pending", dashboard counting only last 10 runs, naive timestamps, racy `is_visible()` assertions, stale static RTM, uploads overwriting the default dataset, client-supplied defect evidence, no screenshot capture.
