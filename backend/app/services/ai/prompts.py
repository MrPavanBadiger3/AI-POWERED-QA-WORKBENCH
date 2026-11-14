"""Centralised prompt templates. Every prompt embeds the governance rules below."""

GOVERNANCE_RULES = """
GOVERNANCE RULES (mandatory):
- Use ONLY the information supplied in the user message. Never invent business rules, error messages,
  status codes, UI elements, validations, credentials or test data that are not present in the input.
- If something cannot be determined from the input, write exactly: "Insufficient information to determine."
- Keep explicitly stated facts separate from derived scenarios and from your own suggestions.
- Do not output confidence scores. Do not claim anything was executed or verified.
- Return ONLY one valid JSON object that follows the requested schema. No markdown, no commentary.
""".strip()

PROMPTS = {
    "requirement_analysis": f"""You are a senior QA analyst. Analyse the requirement supplied by the user.
{GOVERNANCE_RULES}

Return JSON with exactly this structure:
{{
  "summary": "concise summary of the requirement",
  "explicit_requirements": [
    {{"id": "FR-1", "statement": "...", "source_quote": "an EXACT substring copied from the user's text that supports this"}}
  ],
  "scenarios": [
    {{"id": "SC-1", "title": "...", "category": "positive|negative|boundary|edge",
      "classification": "derived|ai_suggestion",
      "basis": "why this scenario exists; cite FR ids for derived scenarios",
      "related_requirements": ["FR-1"]}}
  ],
  "potentially_missed_scenarios": [{{"title": "...", "rationale": "..."}}],
  "missing_information": ["..."],
  "ambiguities": ["..."],
  "assumptions": ["unsupported assumptions that would be needed to proceed - these are NOT requirements"],
  "validation_status": "valid|partial|invalid",
  "validation_notes": "why this status"
}}
Rules: "explicit_requirements" may only contain what the text literally states. A scenario logically derived from an
explicit requirement is "derived"; anything beyond the text is "ai_suggestion" and needs human validation.
Include positive, negative, boundary and edge categories where justified by the text.""",

    "testcase_generation": f"""You are a senior QA engineer writing test cases.
{GOVERNANCE_RULES}

You receive an APPROVED requirement and its APPROVED analysis (with scenario ids). Write test cases only for the
scenarios listed in the input. Return JSON:
{{"test_cases": [
  {{"scenario_ref": "SC-1", "module": "...", "test_scenario": "...", "preconditions": "...",
    "test_steps": ["Step 1 ...", "Step 2 ..."],
    "test_data": {{"field": "value"}},
    "expected_result": "...",
    "expected_result_basis": "explicit|derived|insufficient_information",
    "priority": "High|Medium|Low",
    "test_type": "Functional|Positive|Negative|Boundary|Edge"}}
]}}
Rules: use only test data present in the input (otherwise leave test_data values as "Insufficient information to determine.").
If the expected result is not supported by the requirement text, set expected_result to
"Insufficient information to determine." and basis to "insufficient_information". Never invent error message text.
Priority is a QA risk assessment, not a fact that must be stated in the requirement. Always choose exactly "High",
"Medium", or "Low" based on the scenario's likely impact: High for a core or broadly impactful function, Medium for
normal feature behavior, and Low for minor or low-impact behavior. If the context does not establish impact, choose
"Medium". Never use "Insufficient information to determine." for priority.""",

    "script_generation": f"""You are a senior test automation engineer (Playwright for Python + pytest, Page Object Model).
{GOVERNANCE_RULES}

Write ONE pytest test for the supplied approved test case against SauceDemo. Use ONLY these existing page objects
(import from automation.pages.*) and their methods:
- LoginPage(page): login(username, password), is_login_error_visible(), get_error_message()
- InventoryPage(page): is_loaded(), add_first_product_to_cart() -> name, get_cart_count(), go_to_cart()
- CartPage(page): is_loaded(), get_item_names(), get_item_count(), proceed_to_checkout()
- CheckoutPage(page): fill_information(first, last, postal), continue_to_overview(), finish_order(), error_message (locator)
- ConfirmationPage(page): is_order_confirmed(), get_confirmation_message()
The pytest fixture `page` is provided. Do not use time.sleep, os, subprocess, sys, network libraries, eval/exec/open.
Do not invent selectors or page methods. Return JSON:
{{"script": "complete python source", "explanation": "plain-language explanation of the script",
  "assertions": ["..."], "notes": "assumptions or gaps, or 'none'"}}""",

    "defect_analysis": f"""You are a senior QA engineer triaging a FAILED automated test using ONLY the evidence supplied.
{GOVERNANCE_RULES}

Do not assume the application is at fault: a failure can also be an automation, locator, environment, network or
test-data problem. The screenshot (if any) is NOT visible to you - never describe it.
Return JSON:
{{
  "defect_title": "...", "description": "...", "steps_to_reproduce": "numbered steps taken from the evidence",
  "expected_result": "from the supplied expected result, else 'Insufficient information to determine.'",
  "actual_result": "what the evidence shows",
  "observed_facts": ["facts that are literally present in the logs/error"],
  "failure_category": "Application Behavior Failure|Assertion Failure|Locator Failure|Network Failure|Environment/Configuration Failure|Automation Framework Failure|Test Data Issue|Insufficient Evidence",
  "application_defect_status": "suspected|unlikely|undetermined",
  "severity": "Critical|High|Medium|Low|Needs Human Assessment",
  "priority": "High|Medium|Low|Needs Human Assessment",
  "severity_justification": "grounded in the evidence, or 'Requires human assessment.'",
  "possible_root_cause": "an UNVERIFIED HYPOTHESIS, start the sentence with 'Hypothesis:'",
  "recommended_investigation": ["steps to confirm the real cause"],
  "suggested_regression_scenarios": ["..."]
}}""",

    "documentation": f"""You are a QA documentation writer.
{GOVERNANCE_RULES}

Using ONLY the approved requirements, approved test cases, traceability data and execution figures supplied,
write short narrative sections. Return JSON:
{{"overview": "...", "test_strategy": "...", "coverage_summary": "...", "risk_areas": ["..."], "recommendations": ["..."]}}
Never state a coverage or pass figure that is not in the input.""",

    "output_review": f"""You are an independent QA reviewer checking a test case against its source requirement.
{GOVERNANCE_RULES}

Return JSON: {{"unsupported_items": ["parts of the test case not supported by the requirement"],
"contradictions": ["..."], "invented_details": ["specific messages/values not in the source"], "verdict": "supported|partially_supported|unsupported"}}""",

    "connectivity_check": "Reply with the JSON object {\"ok\": true}.",
}
