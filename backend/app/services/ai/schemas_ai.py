"""Pydantic models describing what the AI is allowed to return, plus deterministic governance checks."""
import re
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

INSUFFICIENT = "Insufficient information to determine."


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


# ---- Requirement analysis -------------------------------------------------
class ExplicitRequirement(_Base):
    id: str
    statement: str
    source_quote: str = ""


class Scenario(_Base):
    id: str
    title: str
    category: Literal["positive", "negative", "boundary", "edge"]
    classification: Literal["derived", "ai_suggestion"]
    basis: str = ""
    related_requirements: List[str] = Field(default_factory=list)

    @field_validator("category", "classification", mode="before")
    @classmethod
    def _lower(cls, v):
        return v.strip().lower().replace(" ", "_") if isinstance(v, str) else v


class MissedScenario(_Base):
    title: str
    rationale: str = ""


class RequirementAnalysisOut(_Base):
    summary: str
    explicit_requirements: List[ExplicitRequirement]
    scenarios: List[Scenario]
    potentially_missed_scenarios: List[MissedScenario] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    validation_status: Literal["valid", "partial", "invalid"]
    validation_notes: str = ""

    @field_validator("validation_status", mode="before")
    @classmethod
    def _lower(cls, v):
        return v.strip().lower() if isinstance(v, str) else v


def check_analysis(a: RequirementAnalysisOut, source_text: str) -> list[dict]:
    """Governance warnings (do not mutate the AI output)."""
    issues: list[dict] = []
    src = _norm(source_text)
    ids = {r.id for r in a.explicit_requirements}
    for r in a.explicit_requirements:
        if not r.source_quote or _norm(r.source_quote) not in src:
            issues.append({"severity": "warning", "code": "unsupported_explicit_requirement", "item": r.id,
                           "message": f"{r.id} is presented as explicit but its source quote was not found in the input text."})
    seen = set()
    for s in a.scenarios:
        if s.id in seen:
            issues.append({"severity": "error", "code": "duplicate_scenario_id", "item": s.id, "message": f"Duplicate scenario id {s.id}."})
        seen.add(s.id)
        if s.classification == "derived" and not (set(s.related_requirements) & ids):
            issues.append({"severity": "warning", "code": "derived_without_basis", "item": s.id,
                           "message": f"{s.id} is marked 'derived' but references no explicit requirement."})
    return issues


# ---- Test cases -----------------------------------------------------------
def _normalize_enum(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    lowered = cleaned.lower().replace("-", " ").replace("_", " ")

    if field_name == "expected_result_basis":
        if lowered in {"insufficient information", "insufficient", "insufficient_information"}:
            return "insufficient_information"
        return lowered.replace(" ", "_")

    if field_name == "priority":
        mapping = {
            "high": "High",
            "medium": "Medium",
            "low": "Low",
        }
        return mapping.get(lowered, cleaned)

    if field_name == "test_type":
        mapping = {
            "functional": "Functional",
            "positive": "Positive",
            "negative": "Negative",
            "boundary": "Boundary",
            "edge": "Edge",
        }
        return mapping.get(lowered, cleaned)

    return cleaned


class TestCaseOut(_Base):
    __test__ = False
    scenario_ref: Optional[str] = None
    module: str = "General"
    test_scenario: str
    preconditions: str = ""
    test_steps: List[str]
    test_data: dict[str, Any] = Field(default_factory=dict)
    expected_result: str
    expected_result_basis: Literal["explicit", "derived", "insufficient_information"] = "insufficient_information"
    priority: Literal["High", "Medium", "Low"]
    test_type: Literal["Functional", "Positive", "Negative", "Boundary", "Edge"]

    @field_validator("priority", "test_type", "expected_result_basis", mode="before")
    @classmethod
    def _case(cls, v, info):
        return _normalize_enum(v, field_name=info.field_name)

    @field_validator("test_steps")
    @classmethod
    def _steps(cls, v):
        if not v or not all(isinstance(x, str) and x.strip() for x in v):
            raise ValueError("test_steps must be a non-empty list of non-empty strings")
        return v


class TestCaseBatchOut(_Base):
    __test__ = False
    test_cases: List[TestCaseOut]

    @field_validator("test_cases")
    @classmethod
    def _non_empty(cls, v):
        if not v:
            raise ValueError("no test cases returned")
        return v


_QUOTED = re.compile(r"[\"“'‘]([^\"”'’]{6,})[\"”'’]")


def check_test_case(tc: TestCaseOut, source_text: str, valid_scenarios: set[str]) -> list[dict]:
    issues: list[dict] = []
    src = _norm(source_text)
    if tc.scenario_ref and valid_scenarios and tc.scenario_ref not in valid_scenarios:
        issues.append({"severity": "warning", "code": "unknown_scenario_ref", "message": f"scenario_ref '{tc.scenario_ref}' is not in the approved analysis."})
    if not tc.scenario_ref:
        issues.append({"severity": "warning", "code": "missing_scenario_ref", "message": "No scenario_ref: traceability to an analysed scenario is missing."})
    if tc.expected_result.strip() == INSUFFICIENT or tc.expected_result_basis == "insufficient_information":
        issues.append({"severity": "warning", "code": "unsupported_expected_result", "message": "Expected result is not supported by the requirement text; a human must define it."})
    for quoted in _QUOTED.findall(tc.expected_result):
        if _norm(quoted) not in src:
            issues.append({"severity": "warning", "code": "possibly_invented_message", "message": f"Expected result quotes text not found in the requirement: \"{quoted}\"."})
    for k, v in tc.test_data.items():
        if isinstance(v, str) and v.strip() and v != INSUFFICIENT and _norm(v) not in src:
            issues.append({"severity": "warning", "code": "test_data_not_in_source", "message": f"Test data '{k}={v}' does not appear in the requirement text."})
    return issues


# ---- Script generation ----------------------------------------------------
class ScriptOut(_Base):
    script: str
    explanation: str = ""
    assertions: List[str] = Field(default_factory=list)
    notes: str = ""


# ---- Defect analysis ------------------------------------------------------
FAILURE_CATEGORIES = ["Application Behavior Failure", "Assertion Failure", "Locator Failure", "Network Failure",
                      "Environment/Configuration Failure", "Automation Framework Failure", "Test Data Issue", "Insufficient Evidence"]


class DefectOut(_Base):
    defect_title: str
    description: str
    steps_to_reproduce: str | List[str] = ""
    expected_result: str = INSUFFICIENT
    actual_result: str = ""
    observed_facts: List[str] = Field(default_factory=list)
    failure_category: Literal[tuple(FAILURE_CATEGORIES)]  # type: ignore[valid-type]
    application_defect_status: Literal["suspected", "unlikely", "undetermined"]
    severity: Literal["Critical", "High", "Medium", "Low", "Needs Human Assessment"]
    priority: Literal["High", "Medium", "Low", "Needs Human Assessment"]
    severity_justification: str = ""
    possible_root_cause: str
    recommended_investigation: List[str] = Field(default_factory=list)
    suggested_regression_scenarios: List[str] = Field(default_factory=list)

    @field_validator("application_defect_status", mode="before")
    @classmethod
    def _lower(cls, v):
        return v.strip().lower() if isinstance(v, str) else v


# ---- Documentation / review ----------------------------------------------
class DocNarrativeOut(_Base):
    overview: str
    test_strategy: str = ""
    coverage_summary: str = ""
    risk_areas: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ReviewOut(_Base):
    unsupported_items: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    invented_details: List[str] = Field(default_factory=list)
    verdict: Literal["supported", "partially_supported", "unsupported"]
