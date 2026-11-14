import React, { useEffect, useState } from 'react';
import { BarChart3, ExternalLink } from 'lucide-react';
import { executionsApi, reportsApi } from '../services/api';
import { Execution, TestResult } from '../types';
import { ErrorMessage } from '../components/ErrorMessage';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ResultsTable } from '../components/ResultsTable';
import { ago } from '../components/ui';

const linkCls = 'inline-flex items-center gap-1 rounded-lg border border-slate-700/60 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700';

export const ReportsPage: React.FC = () => {
  const [execs, setExecs] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ msg: string; retry?: () => void } | null>(null);
  const [sel, setSel] = useState<Execution | null>(null);
  const [results, setResults] = useState<TestResult[]>([]);
  const [logs, setLogs] = useState('');

  const load = async () => {
    setLoading(true);
    try { const { data } = await executionsApi.list(); setExecs(data); setError(null); } catch (e) { setError({ msg: (e as Error).message, retry: load }); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const open = async (e: Execution) => {
    setSel(e); setResults([]); setLogs('');
    try { const [r, l] = await Promise.all([executionsApi.results(e.id), executionsApi.logs(e.id)]); setResults(r.data); setLogs(l.data.logs); } catch (x) { setError({ msg: (x as Error).message }); }
  };

  if (loading) return <LoadingSpinner />;
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {error && <ErrorMessage message={error.msg} onRetry={error.retry} />}
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
        {execs.length === 0 ? <EmptyState icon={<BarChart3 size={24} />} title="No executions yet" description="Run a suite from Test Automation or Data-Driven Testing. Every row here comes from a real run." /> : (
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400"><tr>{['Execution', 'Suite', 'Started', 'Ended', 'Total', 'Passed', 'Failed', 'Skipped', 'Duration', 'Status', 'Reports'].map((h) => <th key={h} className="px-3 py-3">{h}</th>)}</tr></thead>
            <tbody>{execs.map((e) => (
              <tr key={e.id} className={`cursor-pointer border-b border-slate-800/60 hover:bg-slate-800/30 ${sel?.id === e.id ? 'bg-indigo-600/10' : ''}`} onClick={() => open(e)}>
                <td className="px-3 py-3 font-mono text-indigo-400">{e.execution_id}</td><td className="px-3 py-3 text-slate-300">{e.suite_name}</td>
                <td className="px-3 py-3 text-slate-400">{ago(e.start_time)}</td><td className="px-3 py-3 text-slate-400">{ago(e.end_time)}</td>
                <td className="px-3 py-3">{e.total_tests}</td><td className="px-3 py-3 text-emerald-400">{e.passed}</td><td className="px-3 py-3 text-rose-400">{e.failed}</td><td className="px-3 py-3 text-yellow-400">{e.skipped}</td>
                <td className="px-3 py-3 text-slate-400">{e.duration ? `${e.duration.toFixed(1)}s` : '—'}</td><td className="px-3 py-3"><StatusBadge status={e.overall_status} /></td>
                <td className="px-3 py-3" onClick={(x) => x.stopPropagation()}><div className="flex gap-1.5">
                  {e.report_available && <a className={linkCls} target="_blank" rel="noreferrer" href={reportsApi.pytestUrl(e.execution_id)}><ExternalLink size={11} />pytest</a>}
                  {e.summary_report_available && <a className={linkCls} target="_blank" rel="noreferrer" href={reportsApi.summaryUrl(e.execution_id)}><ExternalLink size={11} />summary</a>}</div></td>
              </tr>))}</tbody>
          </table>
        )}
      </div>
      {sel && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="border-b border-slate-800 p-4 text-sm font-semibold text-slate-100">Execution details — <span className="font-mono text-indigo-400">{sel.execution_id}</span></div>
          {sel.error_message && <div className="m-4"><ErrorMessage message={sel.error_message} /></div>}
          <ResultsTable results={results} showData={sel.suite_name === 'data_driven'} />
          <details className="border-t border-slate-800 p-3"><summary className="cursor-pointer text-xs text-slate-400">Execution log</summary><pre className="mt-2 max-h-80 overflow-auto bg-slate-950 p-3 text-[11px] text-slate-400">{logs}</pre></details>
        </div>
      )}
    </div>
  );
};
