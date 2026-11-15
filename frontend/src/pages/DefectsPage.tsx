import React, { useEffect, useState } from 'react';
import { Bug, CheckCircle2, XCircle, Sparkles, Save } from 'lucide-react';
import { defectsApi, executionsApi } from '../services/api';
import { DefectReport, Execution, TestResult } from '../types';
import { ErrorMessage } from '../components/ErrorMessage';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { ResultsTable } from '../components/ResultsTable';
import { Btn, Field, Pill, inputCls } from '../components/ui';
import { useNotify } from '../components/Notify';

const CATEGORIES = ['Application Behavior Failure', 'Assertion Failure', 'Locator Failure', 'Network Failure', 'Environment/Configuration Failure', 'Automation Framework Failure', 'Test Data Issue', 'Insufficient Evidence'];
const SEV = ['Critical', 'High', 'Medium', 'Low', 'Needs Human Assessment'];
const PRI = ['High', 'Medium', 'Low', 'Needs Human Assessment'];

export const DefectsPage: React.FC<{ seedResultId?: string }> = ({ seedResultId }) => {
  const notify = useNotify();
  const [execs, setExecs] = useState<Execution[]>([]);
  const [execId, setExecId] = useState('');
  const [results, setResults] = useState<TestResult[]>([]);
  const [defects, setDefects] = useState<DefectReport[]>([]);
  const [sel, setSel] = useState<DefectReport | null>(null);
  const [form, setForm] = useState<Partial<DefectReport>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<{ msg: string; retry?: () => void } | null>(null);
  const [pending, setPending] = useState<string | undefined>(seedResultId);

  const loadDefects = async (keep?: string) => {
    try { const { data } = await defectsApi.list(); setDefects(data); const s = data.find((d: DefectReport) => d.id === (keep ?? sel?.id)) ?? null; setSel(s); setForm(s ?? {}); }
    catch (e) { setError({ msg: (e as Error).message, retry: () => loadDefects() }); }
  };
  useEffect(() => {
    loadDefects();
    executionsApi.list().then((r) => { setExecs(r.data); const first = r.data.find((x: Execution) => x.failed > 0); if (first) setExecId(first.id); }).catch((e) => setError({ msg: e.message }));
    // eslint-disable-next-line
  }, []);
  useEffect(() => { if (execId) executionsApi.results(execId).then((r) => setResults(r.data)).catch((e) => setError({ msg: e.message })); else setResults([]); }, [execId]);

  const analyze = async (resultId: string) => {
    setBusy('analyze'); setError(null);
    try { const { data } = await defectsApi.analyze(resultId); notify('success', `${data.defect_id} drafted from stored evidence. Review before approving.`); setPending(undefined); await loadDefects(data.id); }
    catch (e) { setError({ msg: (e as Error).message, retry: () => analyze(resultId) }); } finally { setBusy(null); }
  };
  const save = async () => { if (!sel) return; setBusy('save'); try { await defectsApi.update(sel.id, form as Record<string, unknown>); notify('success', 'Saved. Approved reports return to review after edits.'); await loadDefects(sel.id); } catch (e) { setError({ msg: (e as Error).message }); } finally { setBusy(null); } };
  const decide = async (kind: 'approve' | 'reject') => { if (!sel) return; try { await (kind === 'approve' ? defectsApi.approve(sel.id) : defectsApi.reject(sel.id)); notify('success', `${sel.defect_id} ${kind}d`); await loadDefects(sel.id); } catch (e) { setError({ msg: (e as Error).message }); } };
  const set = (k: keyof DefectReport, v: string) => setForm({ ...form, [k]: v });

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {error && <ErrorMessage message={error.msg} onRetry={error.retry} />}
      {pending && (
        <div className="flex items-center justify-between rounded-lg border border-indigo-500/30 bg-indigo-500/10 p-3 text-xs text-indigo-200">
          <span>A failed result was sent here from an execution. Analyse its stored evidence with AI?</span>
          <div className="flex gap-2"><Btn variant="primary" busy={busy === 'analyze'} onClick={() => analyze(pending)}><Sparkles size={12} />Analyze this failure</Btn><Btn onClick={() => setPending(undefined)}>Dismiss</Btn></div>
        </div>
      )}

      <section className="rounded-xl border border-slate-800 bg-slate-900/60">
        <div className="flex flex-wrap items-center gap-3 border-b border-slate-800 p-4">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-100"><Bug size={15} className="text-indigo-400" />Failed results</h2>
          <select name="execution_id" aria-label="Execution" className={`${inputCls} w-auto`} value={execId} onChange={(e) => setExecId(e.target.value)}>
            <option value="">— choose execution —</option>{execs.map((x) => <option key={x.id} value={x.id}>{x.execution_id} · {x.suite_name} · {x.failed} failed</option>)}</select>
          <span className="text-[11px] text-slate-500">Evidence is read from stored results; the screenshot is attached as a file reference only (the text model cannot see images).</span>
        </div>
        {busy === 'analyze' && <p className="p-3 text-xs text-sky-300">Analysing failure evidence with AI…</p>}
        <ResultsTable results={results.filter((r) => r.status === 'failed')} onAnalyze={analyze} />
      </section>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 lg:col-span-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Defect reports ({defects.length})</h3>
          {defects.length === 0 ? <EmptyState icon={<Bug size={22} />} title="No defect reports" description="Pick a failed test above and analyse it." /> : (
            <div className="space-y-1.5">{defects.map((d) => (
              <button key={d.id} onClick={() => { setSel(d); setForm(d); }} className={`w-full cursor-pointer rounded-lg border p-2.5 text-left text-xs ${sel?.id === d.id ? 'border-indigo-500/50 bg-indigo-600/10' : 'border-slate-800 bg-slate-800/40 hover:bg-slate-800/80'}`}>
                <div className="flex items-center justify-between"><span className="font-mono font-semibold text-indigo-400">{d.defect_id}</span><StatusBadge status={d.status} /></div>
                <div className="mt-1 truncate text-slate-300">{d.title}</div><div className="mt-0.5 text-[10px] text-slate-500">{d.execution_id}{d.test_case_id ? ` · ${d.test_case_id}` : ''}</div></button>))}</div>)}
        </div>

        <div className="lg:col-span-8">
          {!sel ? <div className="rounded-xl border border-slate-800 bg-slate-900/60"><EmptyState icon={<Bug size={24} />} title="Select a defect report" description="Reports are AI drafts until a human approves them." /></div> : (
            <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-5 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div className="flex flex-wrap items-center gap-2"><span className="font-mono text-sm font-bold text-indigo-400">{sel.defect_id}</span><StatusBadge status={sel.status} />
                  <Pill tone={sel.application_defect_status === 'suspected' ? 'red' : 'slate'}>application defect: {sel.application_defect_status}</Pill><Pill tone="amber">AI draft</Pill></div>
                <div className="flex gap-2"><Btn onClick={save} busy={busy === 'save'}><Save size={12} />Save edits</Btn><Btn variant="success" onClick={() => decide('approve')} disabled={sel.status === 'approved'}><CheckCircle2 size={12} />Approve</Btn><Btn variant="danger" onClick={() => decide('reject')}><XCircle size={12} />Reject</Btn></div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Field label="Defect title"><input name="defect_title" autoComplete="off" className={inputCls} value={form.title ?? ''} onChange={(e) => set('title', e.target.value)} /></Field>
                <Field label="Failure category (human can override)"><select name="failure_category" className={inputCls} value={form.failure_category ?? ''} onChange={(e) => set('failure_category', e.target.value)}>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select></Field>
                <Field label="Severity"><select name="severity" className={inputCls} value={form.severity ?? ''} onChange={(e) => set('severity', e.target.value)}>{SEV.map((c) => <option key={c}>{c}</option>)}</select></Field>
                <Field label="Priority"><select name="priority" className={inputCls} value={form.priority ?? ''} onChange={(e) => set('priority', e.target.value)}>{PRI.map((c) => <option key={c}>{c}</option>)}</select></Field>
              </div>
              <Field label="Severity justification"><textarea name="severity_justification" autoComplete="off" rows={2} className={inputCls} value={form.severity_justification ?? ''} onChange={(e) => set('severity_justification', e.target.value)} /></Field>
              <Field label="Description"><textarea name="defect_description" autoComplete="off" rows={3} className={inputCls} value={form.description ?? ''} onChange={(e) => set('description', e.target.value)} /></Field>
              <Field label="Steps to reproduce"><textarea name="steps_to_reproduce" autoComplete="off" rows={4} className={inputCls} value={form.steps_to_reproduce ?? ''} onChange={(e) => set('steps_to_reproduce', e.target.value)} /></Field>
              <div className="grid gap-3 md:grid-cols-2">
                <Field label="Expected result"><textarea name="expected_result" autoComplete="off" rows={3} className={inputCls} value={form.expected_result ?? ''} onChange={(e) => set('expected_result', e.target.value)} /></Field>
                <Field label="Actual result"><textarea name="actual_result" autoComplete="off" rows={3} className={inputCls} value={form.actual_result ?? ''} onChange={(e) => set('actual_result', e.target.value)} /></Field>
              </div>
              <Field label="Possible root cause — UNVERIFIED HYPOTHESIS"><textarea name="possible_root_cause" autoComplete="off" rows={2} className={`${inputCls} border-amber-500/40`} value={form.possible_root_cause ?? ''} onChange={(e) => set('possible_root_cause', e.target.value)} /></Field>
              {([['Observed facts (from logs/error)', sel.observed_facts], ['Recommended investigation', sel.recommended_investigation], ['Suggested regression scenarios', sel.suggested_regression]] as [string, string[] | undefined][]).map(([t, items]) => (
                <div key={t}><h4 className="mb-1 font-semibold text-slate-300">{t}</h4><ul className="list-inside list-disc space-y-0.5 text-slate-400">{(items ?? []).map((i, k) => <li key={k}>{i}</li>)}{!items?.length && <li className="list-none text-slate-500">none</li>}</ul></div>))}
              <div className="rounded-lg border border-hairline bg-cream-light p-3 text-[11px] text-slate-400">
                <b className="text-slate-300">Evidence trail:</b> execution {sel.execution_id}; screenshot analysed by AI: <b>{sel.screenshot_analyzed ? 'yes' : 'no'}</b>.
                <details className="mt-1"><summary className="cursor-pointer">Exact evidence sent to the AI</summary><pre className="code-panel mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-code-surface p-3 font-mono text-code-text">{JSON.stringify(sel.evidence, null, 2)}</pre></details>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
