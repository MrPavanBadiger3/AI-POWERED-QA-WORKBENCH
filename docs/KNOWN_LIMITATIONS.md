# Known Limitations

1. **Not executed against live services by the author of this revision.** Groq and SauceDemo were unreachable and no browser existed in the build environment. Backend logic, pipelines, validation and the pytest-subprocess/ingestion path are tested; live AI quality and live Playwright pass/fail on SauceDemo are unverified until you run them.
2. **Selectors.** Page objects use SauceDemo's stable class names/placeholders/roles. If SauceDemo changes its DOM, tests fail with a *Locator Failure* - that is what the defect classifier is for.
3. **Screenshots are not analysed by AI.** The default Groq model is text-only; screenshots are captured and linked but the defect report states `screenshot analysed: no`.
4. **AI quality.** Output is schema-validated and checked for unsupported quotes/messages/data, but a plausible-looking wrong test case can still pass validation. That is why human approval is mandatory. The "AI review" button is advisory, not proof.
5. **Script safety check is static** (AST allow-list: no os/subprocess/network/sleep/eval/open). It is a guard-rail, not a sandbox; human review before approval is the real control.
6. **Single-user local app.** No authentication; one execution at a time; executions run in a background thread of the API process (a backend restart marks running executions as interrupted).
7. **Test-case ↔ automation link is human-defined.** AI test cases are free-form; static automated tests are fixed. Coverage never counts automation unless a person (or an approved script) links them.
8. **Database migrations.** Tables are created with `create_all`; if you keep an old `qa_workbench.db` from the previous version, delete it (schema changed: new columns/tables).
9. **Timeouts.** Execution timeout kills the pytest process tree (default 600 s, `EXECUTION_TIMEOUT_SECONDS`); AI timeout 60 s.
10. **Browser UI was type-checked and built, but not driven in a real browser in the build environment.** Do one click-through before the demo.
