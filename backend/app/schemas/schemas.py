from datetime import datetime, timezone
from typing import Annotated, Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator


def _utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UTC = Annotated[datetime, PlainSerializer(_utc, return_type=str, when_used="json")]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Requirements ----
class RequirementCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=8000)
    user_story: Optional[str] = Field(default=None, max_length=4000)
    acceptance_criteria: Optional[str] = Field(default=None, max_length=8000)


class RequirementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=8000)
    user_story: Optional[str] = Field(default=None, max_length=4000)
    acceptance_criteria: Optional[str] = Field(default=None, max_length=8000)


class RequirementResponse(ORM):
    id: str
    req_id: str
    title: str
    description: str
    user_story: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    source_snapshot: Optional[dict] = None
    analysis: Optional[dict] = None
    analysis_validation: Optional[List[dict]] = None
    status: str
    approved_at: Optional[UTC] = None
    created_at: UTC
    updated_at: Optional[UTC] = None


# ---- Test cases ----
class GenerateTestCases(BaseModel):
    requirement_id: str
    scenario_ids: Optional[List[str]] = None       # regenerate only these scenarios
    replace_unapproved: bool = False               # drop pending/rejected cases of those scenarios first


class TestCaseUpdate(BaseModel):
    __test__ = False
    module: Optional[str] = None
    test_scenario: Optional[str] = None
    preconditions: Optional[str] = None
    test_steps: Optional[List[str]] = None
    test_data: Optional[dict] = None
    expected_result: Optional[str] = None
    priority: Optional[str] = None
    test_type: Optional[str] = None
    review_note: Optional[str] = None
    automation_ref: Optional[str] = None

    @field_validator("priority")
    @classmethod
    def _p(cls, v):
        if v is not None and v not in ("High", "Medium", "Low"):
            raise ValueError("priority must be High, Medium or Low")
        return v

    @field_validator("test_type")
    @classmethod
    def _t(cls, v):
        if v is not None and v not in ("Functional", "Positive", "Negative", "Boundary", "Edge"):
            raise ValueError("test_type must be Functional, Positive, Negative, Boundary or Edge")
        return v


class ReviewNote(BaseModel):
    note: Optional[str] = None


class TestCaseResponse(ORM):
    __test__ = False
    id: str
    tc_id: str
    requirement_id: Optional[str] = None
    scenario_ref: Optional[str] = None
    module: Optional[str] = None
    test_scenario: Optional[str] = None
    preconditions: Optional[str] = None
    test_steps: Optional[List[str]] = None
    test_data: Optional[dict] = None
    expected_result: Optional[str] = None
    expected_basis: Optional[str] = None
    priority: str
    test_type: str
    status: str
    review_note: Optional[str] = None
    validation_flags: Optional[List[dict]] = None
    automation_ref: Optional[str] = None
    ai_generated: bool
    created_at: UTC
    updated_at: Optional[UTC] = None


# ---- Automation scripts ----
class ScriptGenerateRequest(BaseModel):
    test_case_id: str


class ScriptUpdate(BaseModel):
    code: str = Field(min_length=10, max_length=40000)


class ScriptResponse(ORM):
    id: str
    script_id: str
    test_case_id: Optional[str] = None
    code: str
    explanation: Optional[str] = None
    notes: Optional[str] = None
    validation_issues: Optional[List[dict]] = None
    status: str
    file_path: Optional[str] = None
    model_used: Optional[str] = None
    created_at: UTC
    approved_at: Optional[UTC] = None


# ---- Executions ----
class RunRequest(BaseModel):
    suite: str = "all"
    dataset: Optional[str] = None


class ExecutionResponse(ORM):
    id: str
    execution_id: str
    suite_name: Optional[str] = None
    dataset: Optional[str] = None
    status: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    start_time: Optional[UTC] = None
    end_time: Optional[UTC] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    created_at: UTC
    report_available: bool = False
    summary_report_available: bool = False
    overall_status: str = "pending"


class TestResultResponse(ORM):
    __test__ = False
    id: str
    execution_id: Optional[str] = None
    test_name: str
    status: str
    duration: Optional[float] = None
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    screenshot_url: Optional[str] = None
    meta: Optional[dict] = None
    linked_test_cases: List[str] = Field(default_factory=list)


# ---- Defects ----
class DefectAnalyzeRequest(BaseModel):
    test_result_id: str


class DefectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    severity_justification: Optional[str] = None
    possible_root_cause: Optional[str] = None
    failure_category: Optional[str] = None


class DefectResponse(ORM):
    id: str
    defect_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    severity_justification: Optional[str] = None
    failure_category: Optional[str] = None
    application_defect_status: Optional[str] = None
    possible_root_cause: Optional[str] = None
    observed_facts: Optional[List[str]] = None
    recommended_investigation: Optional[List[str]] = None
    suggested_regression: Optional[List[str]] = None
    evidence: Optional[dict] = None
    screenshot_analyzed: bool = False
    test_case_id: Optional[str] = None
    execution_id: Optional[str] = None
    test_result_id: Optional[str] = None
    status: str
    ai_generated: bool
    created_at: UTC
    updated_at: Optional[UTC] = None


class DocGenerateRequest(BaseModel):
    include_ai_narrative: bool = True
