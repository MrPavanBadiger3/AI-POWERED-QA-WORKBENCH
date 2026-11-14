export interface Issue { severity: 'warning' | 'error'; code: string; message: string; item?: string; source?: string }

export interface ExplicitRequirement { id: string; statement: string; source_quote: string }
export interface Scenario {
  id: string; title: string; category: 'positive' | 'negative' | 'boundary' | 'edge';
  classification: 'derived' | 'ai_suggestion'; basis: string; related_requirements: string[];
}
export interface RequirementAnalysis {
  summary: string;
  explicit_requirements: ExplicitRequirement[];
  scenarios: Scenario[];
  potentially_missed_scenarios: { title: string; rationale: string }[];
  missing_information: string[];
  ambiguities: string[];
  assumptions: string[];
  validation_status: 'valid' | 'partial' | 'invalid';
  validation_notes: string;
}
export interface Requirement {
  id: string; req_id: string; title: string; description: string;
  user_story?: string | null; acceptance_criteria?: string | null;
  source_snapshot?: Record<string, string> | null;
  analysis?: RequirementAnalysis | null; analysis_validation?: Issue[] | null;
  status: 'pending' | 'analyzed' | 'approved' | 'needs_modification';
  approved_at?: string | null; created_at: string;
}

export interface TestCase {
  id: string; tc_id: string; requirement_id?: string; scenario_ref?: string | null;
  module?: string; test_scenario?: string; preconditions?: string; test_steps?: string[];
  test_data?: Record<string, unknown>; expected_result?: string; expected_basis?: string | null;
  priority: 'High' | 'Medium' | 'Low'; test_type: 'Functional' | 'Positive' | 'Negative' | 'Boundary' | 'Edge';
  status: 'pending' | 'approved' | 'rejected' | 'needs_modification';
  review_note?: string | null; validation_flags?: Issue[] | null; automation_ref?: string | null;
  ai_generated: boolean; created_at: string;
}

export interface Script {
  id: string; script_id: string; test_case_id?: string; tc_id?: string; code: string;
  explanation?: string; notes?: string; validation_issues?: Issue[]; status: 'draft' | 'approved' | 'rejected';
  file_path?: string | null; created_at: string;
}

export interface Execution {
  id: string; execution_id: string; suite_name?: string; dataset?: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'timeout';
  overall_status: 'pending' | 'running' | 'passed' | 'failed' | 'error' | 'no_tests';
  total_tests: number; passed: number; failed: number; skipped: number;
  start_time?: string; end_time?: string; duration?: number; error_message?: string | null;
  report_available: boolean; summary_report_available: boolean; created_at: string;
}
export interface TestResult {
  id: string; test_name: string; status: 'passed' | 'failed' | 'skipped'; duration?: number;
  error_message?: string | null; screenshot_url?: string | null; meta?: Record<string, string | number> | null;
  linked_test_cases: string[];
}

export interface DefectReport {
  id: string; defect_id: string; title?: string; description?: string; steps_to_reproduce?: string;
  expected_result?: string; actual_result?: string; severity?: string; priority?: string;
  severity_justification?: string; failure_category?: string; application_defect_status?: string;
  possible_root_cause?: string; observed_facts?: string[]; recommended_investigation?: string[];
  suggested_regression?: string[]; evidence?: Record<string, unknown>; screenshot_analyzed: boolean;
  test_case_id?: string; execution_id?: string; test_result_id?: string;
  status: 'pending' | 'approved' | 'rejected' | 'needs_modification'; ai_generated: boolean; created_at: string;
}

export interface ExecRow { id: string; db_id: string; suite: string; status: string; overall_status: string; passed: number; failed: number; skipped: number; total: number; created_at: string }
export interface DashboardStats {
  total_requirements: number; approved_requirements: number; total_test_cases: number; approved_test_cases: number;
  total_executions: number; total_executed_tests: number; passed: number; failed: number; skipped: number;
  pass_rate: number; total_defects: number; latest_execution: ExecRow | null; recent_executions: ExecRow[];
  recent_defects: { id: string; defect_id: string; title: string; severity: string; status: string; failure_category: string }[];
}

export interface GovernanceSummary {
  total_ai_artifacts: number; approved: number; pending: number; rejected: number; needs_modification: number;
  validation_failures: number; with_warnings: number; by_type: Record<string, number>;
}
export interface GovArtifact {
  id: string; artifact_type: string; label?: string; model?: string; validation_status: string; validation_issues: Issue[];
  review_status: string; source_refs?: Record<string, string>; created_at: string; rejected_output_excerpt?: string | null;
}

export interface TraceRow {
  requirement_id: string; requirement_description: string; title: string; status: string;
  test_cases: { tc_id: string; scenario: string; status: string; automation_ref?: string; latest_execution_status: string; latest_execution_id?: string }[];
  total_test_cases: number; approved_test_cases: number;
  coverage_status: 'covered' | 'draft_only' | 'not_covered'; latest_execution_status: string;
}
export interface TraceabilityMatrix {
  matrix: TraceRow[];
  summary: { total_requirements: number; covered: number; draft_only: number; not_covered: number; coverage_percentage: number; definition: string };
}
