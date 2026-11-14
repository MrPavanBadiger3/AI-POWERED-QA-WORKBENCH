# AI Prompts and Governance

All prompts live in **one file**: `backend/app/services/ai/prompts.py` (`PROMPTS` dict). Each begins with shared
`GOVERNANCE_RULES`: use only supplied information; never invent business rules/messages/data; write exactly
"Insufficient information to determine." when unsure; keep explicit facts, derived scenarios and suggestions separate;
no confidence scores; return one JSON object only. Model: `GROQ_MODEL` (default `openai/gpt-oss-120b`),
temperature 0.2, JSON mode (`response_format=json_object`).

| Key | Used by | Output schema (Pydantic, `schemas_ai.py`) | Extra enforcement |
|---|---|---|---|
| `requirement_analysis` | Requirement Analyzer | `RequirementAnalysisOut` - summary, explicit_requirements(+source_quote), scenarios(category, classification derived/ai_suggestion), potentially_missed, missing_information, ambiguities, assumptions, validation_status | each `source_quote` must appear in the input text; derived scenarios must cite an explicit requirement |
| `testcase_generation` | Test Case Generator | `TestCaseBatchOut` (all mandatory fields + `expected_result_basis`) | enum validation; flags: unsupported expected result, quoted message not in source, test data not in source, unknown scenario ref; approval blocked while expected result undefined |
| `script_generation` | Automation | `ScriptOut` | AST allow-list; draft only; never auto-run |
| `defect_analysis` | Defect Analysis | `DefectOut` - category (6 failure types + test data + insufficient evidence), `application_defect_status`, severity/priority incl. "Needs Human Assessment" | root cause forced to "Hypothesis:"; screenshot never claimed as analysed |
| `documentation` | Documentation | `DocNarrativeOut` | input limited to approved artifacts and stored figures |
| `output_review` | Test case "AI review" | `ReviewOut` | advisory only; written to flags, never changes status |
| `connectivity_check` | Settings → Test AI | `{ok:true}` | one real call |

Test-case priority is a QA risk assessment and must always be `High`, `Medium`, or `Low`; when impact is unclear,
the generation prompt directs the model to choose `Medium`. The insufficient-information value is not valid for priority.

## Failure handling
Missing key → 503 `ai_not_configured`; bad key → 502 `ai_auth_failed`; rate limit → 429; timeout → 504; network → 502;
bad model → 502 `ai_model_error`; non-JSON → 422 `ai_malformed_json`; schema violation → 422 `ai_schema_invalid`
(raw output kept in the governance ledger, nothing else stored). No fallback text is ever fabricated.

## Prompt-change checklist
Edit `prompts.py` → keep the JSON keys in sync with `schemas_ai.py` → run `python -m pytest tests` → re-run one real analysis.
