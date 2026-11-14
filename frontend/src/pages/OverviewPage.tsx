import React, { useEffect, useState } from 'react';
import { FileText, FlaskConical, Play, CheckCircle2, XCircle, MinusCircle, Bug } from 'lucide-react';
import { systemApi } from '../services/api';
import { DashboardStats } from '../types';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';

export const OverviewPage: React.FC<{ onNavigate: (p: string) => void }> = ({ onNavigate }) => {
  const [d, setD] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<{ msg: string; retry?: () => void } | null>(null);
  const load = async () => { try { setD((await systemApi.dashboard()).data); setError(null); } catch (e) { setError({ msg: (e as Error).message, retry: load }); } };
  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t); }, []);

  if (!d && !error) return <LoadingSpinner />;
  if (!d) return <ErrorMessage message={error!.msg} onRetry={error!.retry} />;
  const tiles = [
    { l: 'Requirements', v: d.total_requirements, s: `${d.approved_requirements} approved`, i: <FileText size={16} />, to: 'requirements' },
    { l: 'Test cases', v: d.total_test_cases, s: `${d.approved_test_cases} approved`, i: <FlaskConical size={16} />, to: 'testcases' },
    { l: 'Tests executed', v: d.total_executed_tests, s: `${d.total_executions} execution(s)`, i: <Play size={16} />, to: 'reports' },
    { l: 'Passed', v: d.passed, s: '', i: <CheckCircle2 size={16} className="text-emerald-400" />, to: 'reports' },
    { l: 'Failed', v: d.failed, s: '', i: <XCircle size={16} className="text-rose-400" />, to: 'reports' },
    { l: 'Skipped', v: d.skipped, s: '', i: <MinusCircle size={16} className="text-yellow-400" />, to: 'reports' },
  ];
  const tot = d.total_executed_tests || 1;
  const seg = (n: number) => `${(n / tot) * 100}%`;
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {error && <ErrorMessage message={error.msg} onRetry={error.retry} />}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        {tiles.map((t) => (
          <button key={t.l} onClick={() => onNavigate(t.to)} className="cursor-pointer rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-left hover:border-indigo-500/40">
            <div className="flex items-center justify-between text-slate-400"><span className="text-[11px]">{t.l}</span>{t.i}</div><div className="mt-2 text-2xl font-semibold text-slate-100">{t.v}</div><div className="text-[11px] text-slate-500">{t.s}&nbsp;</div></button>))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-100">Pass rate (all recorded tests)</h2>
          {d.total_executed_tests === 0 ? <p className="py-6 text-center text-xs text-slate-500">No tests executed yet.</p> : (<>
            <div className="text-3xl font-semibold text-slate-100">{d.pass_rate}%</div>
            <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-slate-800" role="img" aria-label={`${d.passed} passed, ${d.failed} failed, ${d.skipped} skipped`}>
              <div className="bg-emerald-500" style={{ width: seg(d.passed) }} /><div className="bg-rose-500" style={{ width: seg(d.failed) }} /><div className="bg-yellow-500" style={{ width: seg(d.skipped) }} /></div>
            <div className="mt-2 flex gap-4 text-[11px] text-slate-400"><span>● {d.passed} passed</span><span>● {d.failed} failed</span><span>● {d.skipped} skipped</span></div></>)}
          <div className="mt-5 border-t border-slate-800 pt-3 text-xs text-slate-400">Latest execution: {d.latest_execution ? <span className="ml-1 inline-flex items-center gap-2"><span className="font-mono text-indigo-400">{d.latest_execution.id}</span><StatusBadge status={d.latest_execution.overall_status} /></span> : 'none'}</div>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 lg:col-span-2">
          <div className="border-b border-slate-800 p-4 text-sm font-semibold text-slate-100">Recent executions</div>
          {d.recent_executions.length === 0 ? <EmptyState icon={<Play size={22} />} title="No executions yet" description="Run a suite from Test Automation." /> : (
            <table className="w-full text-left text-xs"><thead className="border-b border-slate-800 text-[11px] uppercase text-slate-400"><tr><th className="px-4 py-2">ID</th><th className="px-4 py-2">Suite</th><th className="px-4 py-2">Result</th><th className="px-4 py-2">P / F / S</th></tr></thead>
              <tbody>{d.recent_executions.map((e) => <tr key={e.id} className="border-b border-slate-800/60"><td className="px-4 py-2 font-mono text-indigo-400">{e.id}</td><td className="px-4 py-2 text-slate-300">{e.suite}</td><td className="px-4 py-2"><StatusBadge status={e.overall_status} /></td><td className="px-4 py-2 text-slate-400">{e.passed} / {e.failed} / {e.skipped}</td></tr>)}</tbody></table>)}
        </section>
      </div>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60">
        <div className="flex items-center gap-2 border-b border-slate-800 p-4 text-sm font-semibold text-slate-100"><Bug size={15} className="text-indigo-400" />Recent defect reports</div>
        {d.recent_defects.length === 0 ? <p className="p-6 text-center text-xs text-slate-500">No defect reports yet.</p> : (
          <ul className="divide-y divide-slate-800/60">{d.recent_defects.map((x) => <li key={x.id} className="flex items-center gap-3 px-4 py-2.5 text-xs"><span className="font-mono text-indigo-400">{x.defect_id}</span><span className="flex-1 truncate text-slate-300">{x.title}</span><span className="text-slate-500">{x.failure_category}</span><StatusBadge status={x.status} /></li>)}</ul>)}
      </section>
    </div>
  );
};
