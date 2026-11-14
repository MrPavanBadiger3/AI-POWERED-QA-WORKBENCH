import React, { useEffect, useState } from 'react';
import { Shield } from 'lucide-react';
import { docApi } from '../services/api';
import { GovArtifact, GovernanceSummary } from '../types';
import { ErrorMessage } from '../components/ErrorMessage';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { IssueList } from '../components/ui';

const POLICIES = [
  ['Structured output validation', 'Every AI response is parsed as JSON and validated against a Pydantic schema. Malformed or schema-invalid output is rejected and logged below as a validation failure.'],
  ['Human approval', 'Requirements, test cases, scripts and defects start as pending. Nothing executes or is documented as approved until a human approves it. Editing approved content sends it back to review.'],
  ['Assumptions ≠ requirements', 'Analyses separate explicit requirements (with a verifiable source quote), derived scenarios, AI suggestions and unsupported assumptions.'],
  ['Unsupported content flags', 'Expected results with no basis, quoted messages not present in the source, and test data not found in the requirement are flagged on the test case.'],
  ['Traceability', 'Each artifact records its source references (requirement, scenario, execution, test). The RTM is computed only from saved links.'],
  ['Secrets', 'The Groq key lives only in backend/.env; no API returns it and the browser never sees it.'],
];

export const GovernancePage: React.FC = () => {
  const [sum, setSum] = useState<GovernanceSummary | null>(null);
  const [rows, setRows] = useState<GovArtifact[]>([]);
  const [error, setError] = useState<{ msg: string; retry?: () => void } | null>(null);
  const load = async () => { try { const [s, a] = await Promise.all([docApi.governance(), docApi.governanceArtifacts()]); setSum(s.data); setRows(a.data); setError(null); } catch (e) { setError({ msg: (e as Error).message, retry: load }); } };
  useEffect(() => { load(); }, []);

  const cards: [string, number | undefined, string][] = [
    ['AI artifacts', sum?.total_ai_artifacts, 'text-slate-100'], ['Approved', sum?.approved, 'text-emerald-400'], ['Pending review', sum?.pending, 'text-yellow-400'],
    ['Rejected', sum?.rejected, 'text-rose-400'], ['Needs modification', sum?.needs_modification, 'text-orange-400'], ['Validation failures', sum?.validation_failures, 'text-rose-400'], ['With warnings', sum?.with_warnings, 'text-yellow-400']];
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {error && <ErrorMessage message={error.msg} onRetry={error.retry} />}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
        {cards.map(([l, v, c]) => <div key={l} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4"><div className="text-[11px] text-slate-400">{l}</div><div className={`mt-1 text-2xl font-semibold ${c}`}>{v ?? 0}</div></div>)}
      </div>
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-100"><Shield size={15} className="text-indigo-400" />Controls in force</h2>
        <div className="grid gap-3 md:grid-cols-2">{POLICIES.map(([t, d]) => <div key={t} className="rounded-lg border border-slate-800 bg-slate-800/30 p-3"><div className="text-xs font-semibold text-slate-200">{t}</div><p className="mt-1 text-[11px] text-slate-400">{d}</p></div>)}</div>
      </section>
      <section className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
        <div className="border-b border-slate-800 p-4 text-sm font-semibold text-slate-100">AI artifact ledger</div>
        {rows.length === 0 ? <EmptyState icon={<Shield size={24} />} title="No AI artifacts yet" description="Every AI call result is recorded here with its validation outcome and review status." /> : (
          <table className="w-full text-left text-xs"><thead className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400"><tr>{['Artifact', 'Type', 'Model', 'Validation', 'Review', 'Sources', 'Created', 'Issues'].map((h) => <th key={h} className="px-3 py-3">{h}</th>)}</tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id} className="border-b border-slate-800/60 align-top">
                <td className="px-3 py-2 font-mono text-indigo-400">{r.label ?? '— (rejected output)'}</td><td className="px-3 py-2 text-slate-300">{r.artifact_type}</td><td className="px-3 py-2 text-slate-400">{r.model ?? '—'}</td>
                <td className="px-3 py-2"><StatusBadge status={r.validation_status === 'passed' ? 'approved' : r.validation_status === 'warnings' ? 'warnings' : 'rejected'} /> <span className="text-slate-500">{r.validation_status}</span></td>
                <td className="px-3 py-2"><StatusBadge status={r.review_status} /></td>
                <td className="px-3 py-2 text-[11px] text-slate-400">{Object.entries(r.source_refs ?? {}).map(([k, v]) => `${k}: ${v}`).join(', ') || '—'}</td>
                <td className="px-3 py-2 text-slate-500">{new Date(r.created_at).toLocaleString()}</td>
                <td className="max-w-xs px-3 py-2"><IssueList issues={r.validation_issues} />{r.rejected_output_excerpt && <pre className="mt-1 max-h-20 overflow-auto text-[10px] text-slate-500">{r.rejected_output_excerpt}</pre>}</td></tr>))}</tbody></table>)}
      </section>
    </div>
  );
};
