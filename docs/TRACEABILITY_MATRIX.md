# Requirement Traceability Matrix (RTM)

The RTM is **computed live** by `GET /api/traceability` (UI: *Test Documentation*; CSV: `GET /api/traceability/export`).
A static table is deliberately not kept here: a hand-written matrix can drift from reality or claim coverage that
does not exist (an earlier version of this file did exactly that and was removed).

## How each column is derived
| Column | Source |
|---|---|
| Requirement ID / Description | `requirements` table (REQ-001…) |
| Linked Test Case IDs | `test_cases.requirement_id` (saved relationship created at generation time) |
| Test Coverage Status | `covered` = ≥1 **approved** test case; `draft_only` = cases exist but none approved; `not_covered` = none |
| Latest Execution Status | For each approved case linked to an automated test (`automation_ref`), the newest execution containing a matching test: `passed` / `failed` / `not_executed` / `not_automated`; rolled up per requirement |

## Linking a test case to automation
In *Test Case Generator → Edit*, choose the pytest function that automates the case (list comes from pytest collection).
Approving an AI-generated script auto-links its test function if the case has no link yet. Unlinked cases show
`not_automated`, never a guessed status.

## Example (illustrative format only - not real data)
| Requirement | Linked TCs | Coverage | Latest execution |
|---|---|---|---|
| REQ-001 | TC-001, TC-002 | covered | passed |
| REQ-002 | TC-003 (pending) | draft_only | n/a |
| REQ-003 | - | not_covered | n/a |
