import axios from 'axios';

const api = axios.create({ baseURL: '/api', headers: { 'Content-Type': 'application/json' }, timeout: 120000 });

api.interceptors.response.use(
  (r) => r,
  (error) => {
    const d = error.response?.data;
    const message = (typeof d?.detail === 'string' && d.detail) || error.message || 'An error occurred';
    const e = new Error(message) as Error & { code?: string; retryable?: boolean };
    e.code = d?.code;
    e.retryable = d?.retryable;
    return Promise.reject(e);
  },
);

export const requirementsApi = {
  analyze: (data: { title: string; description: string; user_story?: string; acceptance_criteria?: string }) => api.post('/requirements/analyze', data),
  list: () => api.get('/requirements'),
  update: (id: string, data: Record<string, string>) => api.put(`/requirements/${id}`, data),
  approve: (id: string) => api.post(`/requirements/${id}/approve`),
  regenerate: (id: string) => api.post(`/requirements/${id}/regenerate`),
};

export const testCasesApi = {
  generate: (requirementId: string, scenarioIds?: string[], replaceUnapproved = false) =>
    api.post('/testcases/generate', { requirement_id: requirementId, scenario_ids: scenarioIds, replace_unapproved: replaceUnapproved }),
  list: () => api.get('/testcases'),
  update: (id: string, data: Record<string, unknown>) => api.put(`/testcases/${id}`, data),
  approve: (id: string) => api.post(`/testcases/${id}/approve`),
  reject: (id: string) => api.post(`/testcases/${id}/reject`),
  requestChanges: (id: string) => api.post(`/testcases/${id}/request-changes`),
  aiReview: (id: string) => api.post(`/testcases/${id}/ai-review`),
  delete: (id: string) => api.delete(`/testcases/${id}`),
  exportUrl: (format: 'csv' | 'json', approvedOnly: boolean) => `/api/testcases/export?format=${format}&approved_only=${approvedOnly}`,
};

export const automationApi = {
  catalog: () => api.get('/automation/catalog'),
  generateScript: (testCaseId: string) => api.post('/automation/generate-script', { test_case_id: testCaseId }),
  scripts: () => api.get('/automation/scripts'),
  editScript: (id: string, code: string) => api.put(`/automation/scripts/${id}`, { code }),
  approveScript: (id: string) => api.post(`/automation/scripts/${id}/approve`),
  rejectScript: (id: string) => api.post(`/automation/scripts/${id}/reject`),
};

export const executionsApi = {
  run: (suite: string, dataset?: string) => api.post('/executions/run', { suite, dataset }),
  suites: () => api.get('/executions/suites'),
  list: () => api.get('/executions'),
  get: (id: string) => api.get(`/executions/${id}`),
  results: (id: string) => api.get(`/executions/${id}/results`),
  logs: (id: string) => api.get(`/executions/${id}/logs`),
};

export const defectsApi = {
  analyze: (testResultId: string) => api.post('/defects/analyze', { test_result_id: testResultId }),
  list: () => api.get('/defects'),
  update: (id: string, data: Record<string, unknown>) => api.put(`/defects/${id}`, data),
  approve: (id: string) => api.post(`/defects/${id}/approve`),
  reject: (id: string) => api.post(`/defects/${id}/reject`),
};

export const reportsApi = {
  generate: (executionId: string) => api.post(`/reports/${executionId}/generate`),
  pytestUrl: (executionId: string) => `/api/reports/${executionId}/html?variant=pytest`,
  summaryUrl: (executionId: string) => `/api/reports/${executionId}/html?variant=summary`,
};

export const dataApi = {
  getTestData: (dataset?: string) => api.get('/test-data', { params: dataset ? { dataset } : {} }),
  upload: (file: File) => { const f = new FormData(); f.append('file', file); return api.post('/test-data/upload', f, { headers: { 'Content-Type': 'multipart/form-data' } }); },
  run: (dataset: string) => api.post('/data-driven/run', { dataset }),
};

export const docApi = {
  traceability: () => api.get('/traceability'),
  rtmUrl: () => '/api/traceability/export',
  generate: (includeAi: boolean) => api.post('/documentation/generate', { include_ai_narrative: includeAi }),
  list: () => api.get('/documentation'),
  downloadUrl: (id: string) => `/api/documentation/${id}/download`,
  exportArtifacts: () => api.post('/artifacts/export'),
  governance: () => api.get('/governance/summary'),
  governanceArtifacts: () => api.get('/governance/artifacts'),
};

export const systemApi = {
  health: () => api.get('/health'),
  config: () => api.get('/config/status'),
  testAi: () => api.post('/config/test-ai'),
  dashboard: () => api.get('/dashboard/stats'),
};
