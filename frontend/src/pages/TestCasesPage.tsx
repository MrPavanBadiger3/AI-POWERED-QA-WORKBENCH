import React, { useEffect, useMemo, useState } from 'react';
import { FlaskConical, Sparkles, CheckCircle2, XCircle, Trash2, Download, Search, Pencil, RotateCcw, ShieldCheck } from 'lucide-react';
import { testCasesApi, requirementsApi, automationApi } from '../services/api';
import { Requirement, TestCase } from '../types';
import { ErrorMessage } from '../components/ErrorMessage';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { Btn, Field, IssueList, Modal, Pill, inputCls } from '../components/ui';
import { useNotify } from '../components/Notify';

const TYPES = ['Functional', 'Positive', 'Negative', 'Boundary', 'Edge'];

export const TestCasesPage: React.FC<{ initialRequirementId?: string }> = ({ initialRequirementId }) => {
  const notify = useNotify();
  const [cases, setCases] = useState<TestCase[]>([]);
  const [reqs, setReqs] = useState<Requirement[]>([]);
  const [reqId, setReqId] = useState(initialRequirementId ?? '');
  const [picked, setPicked] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<{ msg: string; retry?: () => void } | null>(null);
  const [q, setQ] = useState(''); const [prio, setPrio] = useState('ALL'); const [type, setType] = useState('ALL'); const [status, setStatus] = useState('ALL');
  const [edit, setEdit] = useState<TestCase | null>(null);
  const [form, setForm] = useState({ module: '', test_scenario: '', preconditions: '', steps: '', test_data: '', expected_result: '', priority: 'Medium', test_type: 'Functional', automation_ref: '' });
  const [catalog, setCatalog] = useState<string[]>([]);
  const [view, setView] = useState<TestCase | null>(null);
  const [reviewMsg, setReviewMsg] = useState<string | null>(null);

  const load = async () => {
    try {
      const [t, r] = await Promise.all([testCasesApi.list(), requirementsApi.list()]);
      setCases(t.data); setReqs(r.data);
      setReqId((cur) => cur || initialRequirementId || r.data.find((x: Requirement) => x.status === 'approved')?.id || '');
    } catch (e) { setError({ msg: (e as Error).message, retry: load }); }
  };
  useEffect(() => { load(); }, []);

  const req = reqs.find((r) => r.id === reqId);
  const reqCode = (id?: string) => reqs.find((r) => r.id === id)?.req_id ?? '—';
  useEffect(() => setPicked([]), [reqId]);

  const act = async (label: string, fn: () => Promise<void>) => {
    setBusy(label); setError(null);
    try { await fn(); } catch (e) { setError({ msg: (e as Error).message, retry: () => act(label, fn) }); } finally { setBusy(null); }
  };
  const generate = (scenarioIds?: string[]) => act('gen', async () => {
    const { data } = await testCasesApi.generate(reqId, scenarioIds, !!scenarioIds);
    notify('success', `${data.generated} test case(s) generated as PENDING review${data.replaced_unapproved ? `; ${data.replaced_unapproved} unapproved replaced` : ''}.`);
    await load();
  });
  const decide = (tc: TestCase, kind: 'approve' | 'reject' | 'changes') => act(tc.id, async () => {
    await (kind === 'approve' ? testCasesApi.approve(tc.id) : kind === 'reject' ? testCasesApi.reject(tc.id) : testCasesApi.requestChanges(tc.id));
    notify('success', `${tc.tc_id} → ${kind === 'changes' ? 'needs modification' : kind + 'd'}`); await load();
  });
  const remove = (tc: TestCase) => { if (confirm(`Delete ${tc.tc_id}? Its ID will never be reused.`)) act(tc.id, async () => { await testCasesApi.delete(tc.id); notify('success', `${tc.tc_id} deleted`); await load(); }); };

  const openEdit = (tc: TestCase) => {
    setEdit(tc);
    setForm({ module: tc.module ?? '', test_scenario: tc.test_scenario ?? '', preconditions: tc.preconditions ?? '', steps: (tc.test_steps ?? []).join('\n'),
      test_data: JSON.stringify(tc.test_data ?? {}, null, 2), expected_result: tc.expected_result ?? '', priority: tc.priority, test_type: tc.test_type, automation_ref: tc.automation_ref ?? '' });
    automationApi.catalog().then((r) => setCatalog(r.data.functions)).catch(() => setCatalog([]));
  };
  const saveEdit = () => edit && act('save', async () => {
    let data: Record<string, unknown>;
    try { data = JSON.parse(form.test_data || '{}'); } catch { throw new Error('Test data must be valid JSON.'); }
    await testCasesApi.update(edit.id, { module: form.module, test_scenario: form.test_scenario, preconditions: form.preconditions,
      test_steps: form.steps.split('\n').map((s) => s.trim()).filter(Boolean), test_data: data, expected_result: form.expected_result,
      priority: form.priority, test_type: form.test_type, automation_ref: form.automation_ref || null });
    notify('success', `${edit.tc_id} saved${edit.status === 'approved' ? ' - returned to review (edits require re-approval)' : ''}.`);
    setEdit(null); await load();
  });
  const aiReview = (tc: TestCase) => act('rev' + tc.id, async () => {
    const { data } = await testCasesApi.aiReview(tc.id);
    setReviewMsg(`${tc.tc_id}: AI reviewer verdict "${data.verdict}" with ${data.issues.length} advisory issue(s). ${data.note}`); await load();
  });

  const filtered = useMemo(() => cases.filter((t) =>
    (`${t.tc_id} ${t.test_scenario} ${t.module}`.toLowerCase().includes(q.toLowerCase())) &&
    (prio === 'ALL' || t.priority === prio) && (type === 'ALL' || t.test_type === type) && (status === 'ALL' || t.status === status)), [cases, q, prio, type, status]);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      {error && <ErrorMessage message={error.msg} onRetry={error.retry} />}
      {reviewMsg && <div className="rounded-lg border border-sky-500/30 bg-sky-500/10 p-3 text-xs text-sky-200">{reviewMsg} <button className="ml-2 underline" onClick={() => setReviewMsg(null)}>dismiss</button></div>}

      <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs font-medium text-slate-300" htmlFor="req-select">Requirement:</label>
          <select id="req-select" value={reqId} onChange={(e) => setReqId(e.target.value)} className={`${inputCls} max-w-md flex-1`}>
            <option value="">— select —</option>
            {reqs.map((r) => <option key={r.id} value={r.id}>{r.req_id} — {r.title} ({r.status})</option>)}
          </select>
          <Btn variant="primary" busy={busy === 'gen'} disabled={!req || req.status !== 'approved'} onClick={() => generate()}><Sparkles size={13} />{busy === 'gen' ? 'Generating…' : 'Generate test cases'}</Btn>
        </div>
        {req && req.status !== 'approved' && <p className="text-xs text-amber-300">Test cases are generated only from an <b>approved</b> analysis. Approve {req.req_id} in the Requirement Analyzer first.</p>}
        {req?.status === 'approved' && req.analysis && (
          <details className="text-xs text-slate-300">
            <summary className="cursor-pointer text-slate-400">Regenerate selected scenarios only ({picked.length} selected)</summary>
            <div className="mt-2 grid gap-1 md:grid-cols-2">
              {req.analysis.scenarios.map((s) => (
                <label key={s.id} className="flex items-start gap-2 rounded border border-slate-800 p-2">
                  <input type="checkbox" checked={picked.includes(s.id)} onChange={(e) => setPicked(e.target.checked ? [...picked, s.id] : picked.filter((x) => x !== s.id))} />
                  <span><span className="font-mono text-slate-400">{s.id}</span> {s.title} <span className="text-slate-500">({s.category})</span></span>
                </label>
              ))}
            </div>
            <div className="mt-2 flex items-center gap-3"><Btn disabled={picked.length === 0} busy={busy === 'gen'} onClick={() => generate(picked)}><RotateCcw size={12} />Regenerate selected</Btn>
              <span className="text-[11px] text-slate-500">Replaces only unapproved cases for those scenarios. Approved cases are never touched.</span></div>
          </details>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-3">
        <div className="relative min-w-52 flex-1"><Search size={13} className="absolute left-3 top-2.5 text-slate-500" /><input aria-label="Search test cases" className={`${inputCls} pl-8`} placeholder="Search ID, scenario, module" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <select aria-label="Priority filter" className={`${inputCls} w-auto`} value={prio} onChange={(e) => setPrio(e.target.value)}><option value="ALL">All priorities</option>{['High', 'Medium', 'Low'].map((p) => <option key={p}>{p}</option>)}</select>
        <select aria-label="Type filter" className={`${inputCls} w-auto`} value={type} onChange={(e) => setType(e.target.value)}><option value="ALL">All types</option>{TYPES.map((p) => <option key={p}>{p}</option>)}</select>
        <select aria-label="Review status filter" className={`${inputCls} w-auto`} value={status} onChange={(e) => setStatus(e.target.value)}><option value="ALL">All review statuses</option>{['pending', 'approved', 'rejected', 'needs_modification'].map((p) => <option key={p}>{p}</option>)}</select>
        <a className="inline-flex items-center gap-1 rounded-lg border border-slate-700/60 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700" href={testCasesApi.exportUrl('csv', false)}><Download size={12} />CSV</a>
        <a className="inline-flex items-center gap-1 rounded-lg border border-slate-700/60 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700" href={testCasesApi.exportUrl('json', false)}><Download size={12} />JSON</a>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
        {filtered.length === 0 ? (
          <EmptyState icon={<FlaskConical size={24} />} title={cases.length ? 'No test cases match the filters' : 'No test cases yet'} description="Approve a requirement analysis, then generate test cases. Every generated case starts as Pending Review." />
        ) : (
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400"><tr>
              {['ID', 'Req', 'Module / Scenario', 'Type', 'Priority', 'Review status', 'Actions'].map((h) => <th key={h} className="px-3 py-3">{h}</th>)}</tr></thead>
            <tbody>
              {filtered.map((t) => (
                <tr key={t.id} className="border-b border-slate-800/60 align-top hover:bg-slate-800/30">
                  <td className="px-3 py-3 font-mono font-semibold text-indigo-400">{t.tc_id}</td>
                  <td className="px-3 py-3 font-mono text-slate-400">{reqCode(t.requirement_id)}{t.scenario_ref && <div className="text-[10px]">{t.scenario_ref}</div>}</td>
                  <td className="max-w-md px-3 py-3"><div className="text-[11px] text-slate-500">{t.module}</div><button className="cursor-pointer text-left text-slate-100 hover:underline" onClick={() => setView(t)}>{t.test_scenario}</button>
                    {(t.validation_flags?.length ?? 0) > 0 && <div className="mt-1"><Pill tone="amber">{t.validation_flags!.length} governance flag(s)</Pill></div>}</td>
                  <td className="px-3 py-3 text-slate-300">{t.test_type}</td>
                  <td className="px-3 py-3"><StatusBadge status={t.priority} /></td>
                  <td className="px-3 py-3"><StatusBadge status={t.status} /></td>
                  <td className="px-3 py-3"><div className="flex flex-wrap gap-1.5">
                    <Btn onClick={() => openEdit(t)} aria-label={`Edit ${t.tc_id}`}><Pencil size={11} />Edit</Btn>
                    <Btn variant="success" disabled={t.status === 'approved'} busy={busy === t.id} onClick={() => decide(t, 'approve')}><CheckCircle2 size={11} />Approve</Btn>
                    <Btn disabled={t.status === 'rejected'} onClick={() => decide(t, 'reject')}><XCircle size={11} />Reject</Btn>
                    <Btn variant="danger" onClick={() => remove(t)} aria-label={`Delete ${t.tc_id}`}><Trash2 size={11} /></Btn>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {view && (
        <Modal title={`${view.tc_id} — ${view.test_scenario}`} onClose={() => setView(null)}>
          <div className="space-y-3 text-xs text-slate-300">
            <div className="flex flex-wrap gap-2"><StatusBadge status={view.status} /><Pill>{view.test_type}</Pill><Pill>{view.priority}</Pill>{view.scenario_ref && <Pill tone="blue">{view.scenario_ref}</Pill>}
              {view.expected_basis && <Pill tone={view.expected_basis === 'insufficient_information' ? 'amber' : 'green'}>expected result basis: {view.expected_basis.replace(/_/g, ' ')}</Pill>}</div>
            <p><b className="text-slate-400">Preconditions:</b> {view.preconditions || '—'}</p>
            <div><b className="text-slate-400">Steps:</b><ol className="mt-1 list-inside list-decimal space-y-0.5">{(view.test_steps ?? []).map((s, i) => <li key={i}>{s}</li>)}</ol></div>
            <div><b className="text-slate-400">Test data:</b><pre className="mt-1 rounded bg-slate-950 p-2 text-[11px]">{JSON.stringify(view.test_data, null, 2)}</pre></div>
            <p><b className="text-slate-400">Expected result:</b> {view.expected_result}</p>
            <p><b className="text-slate-400">Automation link:</b> {view.automation_ref || 'not linked'}</p>
            <IssueList issues={view.validation_flags} />
            <div className="flex gap-2 pt-2">
              <Btn onClick={() => { decide(view, 'changes'); setView(null); }}>Needs modification</Btn>
              <Btn busy={busy === 'rev' + view.id} onClick={() => aiReview(view)}><ShieldCheck size={12} />AI review vs requirement</Btn>
            </div>
          </div>
        </Modal>
      )}

      {edit && (
        <Modal title={`Edit ${edit.tc_id}`} onClose={() => setEdit(null)} wide>
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Module"><input className={inputCls} value={form.module} onChange={(e) => setForm({ ...form, module: e.target.value })} /></Field>
            <Field label="Test scenario"><input className={inputCls} value={form.test_scenario} onChange={(e) => setForm({ ...form, test_scenario: e.target.value })} /></Field>
            <Field label="Preconditions"><textarea rows={2} className={inputCls} value={form.preconditions} onChange={(e) => setForm({ ...form, preconditions: e.target.value })} /></Field>
            <Field label="Expected result" hint={form.expected_result.startsWith('Insufficient') ? 'Undefined: a human must define it before approval.' : undefined}><textarea rows={2} className={inputCls} value={form.expected_result} onChange={(e) => setForm({ ...form, expected_result: e.target.value })} /></Field>
            <Field label="Steps (one per line)"><textarea rows={6} className={inputCls} value={form.steps} onChange={(e) => setForm({ ...form, steps: e.target.value })} /></Field>
            <Field label="Test data (JSON)"><textarea rows={6} className={`${inputCls} font-mono`} value={form.test_data} onChange={(e) => setForm({ ...form, test_data: e.target.value })} /></Field>
            <Field label="Priority"><select className={inputCls} value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>{['High', 'Medium', 'Low'].map((p) => <option key={p}>{p}</option>)}</select></Field>
            <Field label="Test type"><select className={inputCls} value={form.test_type} onChange={(e) => setForm({ ...form, test_type: e.target.value })}>{TYPES.map((p) => <option key={p}>{p}</option>)}</select></Field>
            <Field label="Linked automated test (for traceability)" hint="Choose the pytest function that automates this test case. Used by the RTM to report its execution status.">
              <select className={inputCls} value={form.automation_ref} onChange={(e) => setForm({ ...form, automation_ref: e.target.value })}>
                <option value="">— not automated —</option>{catalog.map((c) => <option key={c}>{c}</option>)}</select></Field>
          </div>
          <div className="mt-4 flex gap-2"><Btn variant="primary" busy={busy === 'save'} onClick={saveEdit}>Save</Btn><Btn onClick={() => setEdit(null)}>Cancel</Btn></div>
        </Modal>
      )}
    </div>
  );
};
