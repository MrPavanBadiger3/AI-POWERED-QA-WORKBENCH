import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Requirement(Base):
    __tablename__ = "requirements"
    id = Column(String, primary_key=True, default=new_id)
    req_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    user_story = Column(Text)
    acceptance_criteria = Column(Text)
    source_snapshot = Column(JSON)          # original text as first submitted; never modified
    analysis = Column(JSON)                 # AI analysis (draft until approved)
    analysis_validation = Column(JSON)      # governance issues found in the analysis
    # pending | analyzed | approved | needs_modification
    status = Column(String, default="pending")
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    test_cases = relationship("TestCase", back_populates="requirement")


class TestCase(Base):
    __tablename__ = "test_cases"
    __test__ = False  # not a pytest class
    id = Column(String, primary_key=True, default=new_id)
    tc_id = Column(String, unique=True, nullable=False)
    requirement_id = Column(String, ForeignKey("requirements.id"))
    scenario_ref = Column(String)           # e.g. SC-2 from the approved analysis
    module = Column(String)
    test_scenario = Column(Text)
    preconditions = Column(Text)
    test_steps = Column(JSON)
    test_data = Column(JSON)
    expected_result = Column(Text)
    expected_basis = Column(String)         # explicit | derived | insufficient_information
    priority = Column(String, default="Medium")
    test_type = Column(String, default="Functional")
    # pending | approved | rejected | needs_modification
    status = Column(String, default="pending")
    review_note = Column(Text)
    validation_flags = Column(JSON)         # governance warnings
    automation_ref = Column(String)         # human-set link to an automated test (function name / node id)
    ai_generated = Column(Boolean, default=True)
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    requirement = relationship("Requirement", back_populates="test_cases")


class AutomationScript(Base):
    __tablename__ = "automation_scripts"
    id = Column(String, primary_key=True, default=new_id)
    script_id = Column(String, unique=True, nullable=False)
    test_case_id = Column(String, ForeignKey("test_cases.id"))
    code = Column(Text, nullable=False)
    explanation = Column(Text)
    notes = Column(Text)
    validation_issues = Column(JSON)
    status = Column(String, default="draft")   # draft | approved | rejected
    file_path = Column(String)                 # set only when approved & written to automation/generated
    model_used = Column(String)
    created_at = Column(DateTime, default=now_utc)
    approved_at = Column(DateTime)


class Execution(Base):
    __tablename__ = "executions"
    id = Column(String, primary_key=True, default=new_id)
    execution_id = Column(String, unique=True, nullable=False)
    suite_name = Column(String)
    dataset = Column(String)
    status = Column(String, default="pending")   # pending | running | completed | failed | timeout
    total_tests = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Float)
    report_path = Column(String)
    summary_report_path = Column(String)
    log_path = Column(String)
    error_message = Column(Text)
    created_at = Column(DateTime, default=now_utc)
    results = relationship("TestResult", back_populates="execution", cascade="all, delete-orphan")


class TestResult(Base):
    __tablename__ = "test_results"
    __test__ = False
    id = Column(String, primary_key=True, default=new_id)
    execution_id = Column(String, ForeignKey("executions.id"))
    test_name = Column(String)       # pytest node id
    status = Column(String)          # passed | failed | skipped
    duration = Column(Float)
    error_message = Column(Text)
    screenshot_path = Column(String) # file name inside backend/screenshots
    logs = Column(Text)
    meta = Column(JSON)              # data-driven evidence: username, expected, actual ...
    created_at = Column(DateTime, default=now_utc)
    execution = relationship("Execution", back_populates="results")


class DefectReport(Base):
    __tablename__ = "defect_reports"
    id = Column(String, primary_key=True, default=new_id)
    defect_id = Column(String, unique=True, nullable=False)
    title = Column(String)
    description = Column(Text)
    steps_to_reproduce = Column(Text)
    expected_result = Column(Text)
    actual_result = Column(Text)
    severity = Column(String)
    priority = Column(String)
    severity_justification = Column(Text)
    failure_category = Column(String)
    application_defect_status = Column(String)   # suspected | unlikely | undetermined
    possible_root_cause = Column(Text)           # always a HYPOTHESIS
    observed_facts = Column(JSON)
    recommended_investigation = Column(JSON)
    suggested_regression = Column(JSON)
    evidence = Column(JSON)                      # exactly what was sent to the AI
    screenshot_analyzed = Column(Boolean, default=False)
    test_case_id = Column(String)
    execution_id = Column(String)
    test_result_id = Column(String)
    status = Column(String, default="pending")   # pending | approved | rejected | needs_modification
    ai_generated = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"
    id = Column(String, primary_key=True, default=new_id)
    doc_id = Column(String, unique=True, nullable=False)
    title = Column(String)
    markdown = Column(Text)
    ai_narrative = Column(JSON)
    created_at = Column(DateTime, default=now_utc)


class AIArtifact(Base):
    """Governance ledger: one row per AI call result (or per item generated by it)."""
    __tablename__ = "ai_artifacts"
    id = Column(String, primary_key=True, default=new_id)
    artifact_type = Column(String)      # requirement_analysis | test_case | automation_script | defect_report | documentation | review
    reference_id = Column(String)       # primary key of the stored entity (None if output was rejected)
    reference_label = Column(String)    # human code e.g. TC-003
    prompt_key = Column(String)
    model_used = Column(String)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    validation_status = Column(String, default="passed")   # passed | warnings | failed
    validation_issues = Column(JSON)
    review_status = Column(String, default="pending")      # pending | approved | rejected | needs_modification
    source_refs = Column(JSON)          # e.g. {"requirement": "REQ-001"}
    raw_output = Column(Text)           # kept only for rejected outputs (audit)
    created_at = Column(DateTime, default=now_utc)
    reviewed_at = Column(DateTime)


class IDCounter(Base):
    """Monotonic counters so a human ID (TC-003) is never issued twice, even after deletions."""
    __tablename__ = "id_counters"
    prefix = Column(String, primary_key=True)
    value = Column(Integer, nullable=False, default=0)


class AppConfig(Base):
    __tablename__ = "app_config"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
