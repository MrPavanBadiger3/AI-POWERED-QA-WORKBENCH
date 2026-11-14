import React, { useEffect, useState } from 'react';
import { Play, Sparkles, CheckCircle2, XCircle, Save, FileCode } from 'lucide-react';
import { automationApi, executionsApi, testCasesApi, reportsApi } from '../services/api';
import { Script, TestCase } from '../types';
import { useExecution } from '../hooks/useExecution';
import { ErrorMessage } from '../components/ErrorMessage';
import { StatusBadge } from '../components/StatusBadge';
import { ResultsTable } from '../components/ResultsTable';
import { Btn, IssueList, Pill, inputCls } from '../components/ui';
import { useNotify } from '../components/Notify';

const SUITES: [string, string, string][] = [
  ['all', 'Run All Tests', 'Login, e2e, data-driven (+ approved scripts)'],
  ['login', 'Login suite', '5 fixed login scenarios'],
  ['e2e', 'Product → Checkout', 'Selection, cart, checkout, confirmation'],
  ['approved_scripts', 'Approved AI scripts', 'Only scripts a human approved'],
];

export const AutomationPage: React.FC<{ onAnalyzeDefect: (resultId: string) => void }> = ({ onAnalyzeDefect }) => {
  const notify = useNotify();
  const ex = useExecution((e) => notify(e.overall_status === 'passed' ? 'success' : 'error', `${e.execution_id}: ${e.overall_status.toUpperCase()} (${e.passed} passed, ${e.failed} failed)`));
  const [error, setError] = useState<{ msg: string; retry?: () => void } | null>(null);
  const [starting, setStarting] = useState<string | null>(null);
  const [cases, setCases] = useState<TestCase[]>([]);
  const [scripts, setScripts] = useState<Script[]>([]);
  const [tcId, setTcId] = useState('');
  const [genBusy, setGenBusy] = useState(false);
  const [openScript, setOpenScript] = useState<Script | null>(null);
  const [code, setCode] = useState('');
  const [showLogs, setShowLogs] = useState(false);

  const loadAll = async () => {
    try {
      const [c, s] = await Promise.all([testCasesApi.list(), automationApi.scripts()]);
      setCases(c.data.filter((t: TestCase) => t.status === 'approved')); setScripts(s.data);
    } catch (e) { setError({ msg: (e as Error).message, retry: loadAll }); }
  };
  useEffect(() => { loadAll(); executionsApi.list().then((r) => r.data[0] && ex.track(r.data[0].id)).catch(() => {}); /* eslint-disable-next-line */ }, []);

  const run = async (suite: string) => {
    setStarting(suite); setError(null);
    try { const { data } = await executionsApi.run(suite); ex.track(data.db_id); notify('info', `Execution ${data.execution_id} started.`); }
    catch (e) { setError({ msg: (e as Error).message, retry: () => run(suite) }); } finally { setStarting(null); }
  };
  const generate = async () => {
    setGenBusy(true); setError(null);
    try {
      const { data } = await automationApi.generateScript(tcId);
      notify('success', data.message); await loadAll(); setOpenScript(data.script); setCode(data.script.code);
    } catch (e) { setError({ msg: (e as Error).message, retry: generate }); } finally { setGenBusy(false); }
  };
  const scriptAct = async (fn: () => Promise<unknown>, ok: string) => {
    try { await fn(); notify('success', ok); await loadAll(); setOpenScript(null); } catch (e) { setError({ msg: (e as Error).message }); }
  };
  const saveCode = async () => {
    if (!openScript) return;
    try { const { data } = await automationApi.editScript(openScript.id, code); setOpenScript(data); notify('info', 'Saved as draft; re-validated. Approval is required again.'); await loadAll(); }
    catch (e) { setError({ msg: (e as Error).message }); }
  };

  const e = ex.execution;
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {error && <ErrorMessage message={error.msg} onRetry={error.retry} />}

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-100"><Play size={15} className="text-indigo-400" />Run Playwright / pytest suites against SauceDemo</h2>
        <div className="grid gap-3 md:grid-cols-4">
          {SUITES.map(([id, label, desc]) => (
            <button key={id} disabled={ex.running || !!starting} onClick={() => run(id)}
              className="cursor-pointer rounded-lg border border-slate-700/60 bg-slate-800/50 p-3 text-left hover:border-indigo-500/50 disabled:cursor-not-allowed disabled:opacity-50">
              <div className="text-xs font-semibold text-slate-100">{starting === id ? 'Starting…' : label}</div><div className="mt-1 text-[11px] text-slate-400">{desc}</div>
            </button>
          ))}
        </div>
        <p className="mt-2 text-[11px] text-slate-500">Only whitelisted suites can run, one execution at a time. Results below come from the real pytest process.</p>
      </section>

      {e && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 p-4">
            <div className="flex items-center gap-3"><span className="font-mono text-sm font-semibold text-indigo-400">{e.execution_id}</span><StatusBadge status={ex.running ? e.status : e.overall_status} />
              <span className="text-xs text-slate-400">suite: {e.suite_name}{e.dataset ? ` · ${e.dataset}` : ''}</span>
              {ex.running && <span className="flex items-center gap-1.5 text-xs text-sky-300"><span className="h-3 w-3 animate-spin rounded-full border-2 border-sky-300/30 border-t-sky-300" />running…</span>}</div>
            <div className="flex items-center gap-4 text-xs text-slate-300">
              <span>Total {e.total_tests}</span><span className="text-emerald-400">Passed {e.passed}</span><span className="text-rose-400">Failed {e.failed}</span><span className="text-yellow-400">Skipped {e.skipped}</span>
              <span className="text-slate-500">{e.duration ? `${e.duration.toFixed(1)}s` : ''}</span></div>
          </div>
          {e.error_message && <div className="m-4"><ErrorMessage message={e.error_message} /></div>}
          <ResultsTable results={ex.results} onAnalyze={onAnalyzeDefect} />
          <div className="flex flex-wrap gap-2 border-t border-slate-800 p-3">
            <Btn onClick={() => setShowLogs(!showLogs)}>{showLogs ? 'Hide' : 'View'} execution log</Btn>
            {e.report_available && <a className="inline-flex items-center rounded-lg border border-slate-700/60 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700" target="_blank" rel="noreferrer" href={reportsApi.pytestUrl(e.execution_id)}>Open pytest HTML report</a>}
            {!ex.running && <a className="inline-flex items-center rounded-lg border border-slate-700/60 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700" target="_blank" rel="noreferrer" href={reportsApi.summaryUrl(e.execution_id)}>Generate HTML summary</a>}
          </div>
          {showLogs && <pre className="max-h-80 overflow-auto border-t border-slate-800 bg-slate-950 p-3 text-[11px] text-slate-400">{ex.logs}</pre>}
        </section>
      )}

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="mb-1 flex items-center gap-2 text-sm font-semibold text-slate-100"><Sparkles size={15} className="text-indigo-400" />AI-assisted script generation</h2>
        <p className="mb-3 text-xs text-slate-400">AI proposes a Playwright script for an <b>approved</b> test case. It is saved as a <b>draft and is never executed</b> until you review and approve it; the runner only executes the approved, saved file.</p>
        <div className="flex flex-wrap gap-2">
          <select aria-label="Approved test case" className={`${inputCls} max-w-lg flex-1`} value={tcId} onChange={(x) => setTcId(x.target.value)}>
            <option value="">— choose an approved test case —</option>{cases.map((c) => <option key={c.id} value={c.id}>{c.tc_id} — {c.test_scenario}</option>)}</select>
          <Btn variant="primary" disabled={!tcId} busy={genBusy} onClick={generate}><Sparkles size={12} />Generate script</Btn>
        </div>
        {cases.length === 0 && <p className="mt-2 text-[11px] text-amber-300">No approved test cases yet: approve some in the Test Case Generator.</p>}

        {scripts.length > 0 && (
          <table className="mt-4 w-full text-left text-xs">
            <thead className="border-b border-slate-800 text-[11px] uppercase text-slate-400"><tr><th className="px-3 py-2">Script</th><th className="px-3 py-2">Test case</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Validation</th><th className="px-3 py-2" /></tr></thead>
            <tbody>{scripts.map((s) => (
              <tr key={s.id} className="border-b border-slate-800/60"><td className="px-3 py-2 font-mono text-indigo-400">{s.script_id}</td><td className="px-3 py-2 font-mono text-slate-300">{s.tc_id}</td>
                <td className="px-3 py-2"><StatusBadge status={s.status} /></td>
                <td className="px-3 py-2">{(s.validation_issues ?? []).some((i) => i.severity === 'error') ? <Pill tone="red">blocked</Pill> : <Pill tone="green">passes static checks</Pill>}</td>
                <td className="px-3 py-2"><Btn onClick={() => { setOpenScript(s); setCode(s.code); }}><FileCode size={11} />Review</Btn></td></tr>))}</tbody>
          </table>
        )}

        {openScript && (
          <div className="mt-4 space-y-3 rounded-lg border border-slate-700 bg-slate-950/60 p-4">
            <div className="flex items-center justify-between"><h3 className="text-xs font-semibold text-slate-100">{openScript.script_id} <StatusBadge status={openScript.status} /></h3><button className="cursor-pointer text-xs text-slate-400" onClick={() => setOpenScript(null)}>Close ✕</button></div>
            {openScript.explanation && <p className="text-xs text-slate-300"><b className="text-slate-400">AI explanation:</b> {openScript.explanation}</p>}
            {openScript.notes && <p className="text-xs text-slate-400"><b>Notes:</b> {openScript.notes}</p>}
            <IssueList issues={openScript.validation_issues} />
            <textarea aria-label="Script source" className={`${inputCls} font-mono`} rows={14} value={code} onChange={(x) => setCode(x.target.value)} spellCheck={false} />
            <div className="flex flex-wrap gap-2">
              <Btn onClick={saveCode} disabled={code === openScript.code}><Save size={12} />Save edits (re-validate)</Btn>
              <Btn variant="success" disabled={openScript.status === 'approved' || code !== openScript.code} onClick={() => scriptAct(() => automationApi.approveScript(openScript.id), 'Script approved and written to automation/generated. Run it with the “Approved AI scripts” suite.')}><CheckCircle2 size={12} />Approve for execution</Btn>
              <Btn variant="danger" onClick={() => scriptAct(() => automationApi.rejectScript(openScript.id), 'Script rejected.')}><XCircle size={12} />Reject</Btn>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
