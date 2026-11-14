# Prerequisite Audit

Two environments are described separately because they differ. Nothing below is claimed without a source.

## A. Developer's machine (recorded by the previous agent session; *not re-verified in this session*)
Windows 11, Python 3.11.9, Node 22.23.2, npm 10.9.8, Git 2.45.1, Playwright 1.65.1 with Chromium, GROQ_API_KEY **not set**
(user to supply). SauceDemo reachability was reported there; treat it as unconfirmed until you run the suite.

## B. Environment used to complete the project (this session) - verified by running commands
| Item | Result |
|---|---|
| Python / Node | 3.12.3 / 22.23.4 |
| Backend deps | installed via pip (FastAPI 0.162, SQLAlchemy 2.1, Pydantic 2.14, groq 1.7, pytest 9.2, pytest-html 4.2, pytest-json-report 1.5, playwright 1.65) |
| Frontend | `npm ci`, `tsc -b`, `vite build` succeed |
| Browser (Chromium) | **not available** |
| https://www.saucedemo.com | **unreachable** from this environment |
| https://api.groq.com | **unreachable** from this environment |
| GROQ_API_KEY | not configured |

Consequence: live Groq calls and live Playwright runs against SauceDemo were **not** executed here. See `PROGRESS_TRACKER.md`.

## C. Project-scope skills (installed in this session)
| Command | Result |
|---|---|
| `npx skills add .../vercel-labs/agent-skills --skill web-design-guidelines` | Installed → `.agents/skills/web-design-guidelines` (recorded in `skills-lock.json`). Its checklist was applied to the UI (aria-labels, focus rings, skip link, reduced motion, dark color-scheme, tabular numbers). |
| `npx skills add .../lombiq/tailwind-agent-skills --skill tailwind-4-docs` | Installed → `.agents/skills/tailwind-4-docs`. Project uses Tailwind 4 (`@import "tailwindcss"` + `@tailwindcss/vite`), no v3 config. |
| `npx getdesign@latest add elevenlabs` | Installed → `DESIGN.md` (reference only; no audio feature added). |

The earlier audit listed these as "reviewed/evaluated"; they had not actually been installed until now.

## D. Blockers for you
1. Create `backend/.env` with a valid `GROQ_API_KEY` (Settings page → *Test AI connection* proves it).
2. `python -m playwright install chromium` on the demo machine.
3. Internet access to SauceDemo during the live run.
