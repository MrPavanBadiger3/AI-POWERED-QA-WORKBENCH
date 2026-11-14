import React, { useEffect, useState } from 'react';
import { FileText, Sparkles, CheckCircle2, RotateCcw, ArrowRight, Pencil, ShieldAlert } from 'lucide-react';
import { requirementsApi } from '../services/api';
import { Requirement, Scenario } from '../types';
import { ErrorMessage } from '../components/ErrorMessage';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { Btn, Field, IssueList, Pill, inputCls } from '../components/ui';
import { useNotify } from '../components/Notify';

const SIMPLE = {
  title: 'User login',
  description: 'As a user, I should be able to log in to the application using valid credentials.',
  user_story: '', acceptance_criteria: '',
};
const DETAILED = {
  title: 'SauceDemo user authentication',
  description: 'Users must be able to log in to SauceDemo using valid credentials and reach the inventory page. Invalid credentials and empty submissions must be rejected.',
  user_story: 'As a SauceDemo customer, I want to log in with my username and password so that I can access the product catalogue.',
  acceptance_criteria: '1. Given standard_user / secret_sauce, the user is taken to the inventory page.\n2. Given invalid credentials, an error message is displayed and the user stays on the login page.\n3. Given empty username or password, an error message is displayed.',
};

const catTone = { positive: 'green', negative: 'red', boundary: 'blue', edge: 'amber' } as const;

export const RequirementsPage: React.FC<{ onSendToTestCases: (id: string) => void }> = ({ onSendToTestCases }) => {
  const notify = useNotify();
  const [list, setList] = useState<Requirement[]>([]);
  const [sel, setSel] = useState<Requirement | null>(null);
  const [form, setForm] = useState({ title: '', description: '', user_story: '', acceptance_criteria: '' });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<{ msg: string; retry?: () => void } | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(form);
  const [showSource, setShowSource] = useState(false);

  const load = async (keepId?: string) => {
    try {
      const { data } = await requirementsApi.list();
      setList(data);
      setSel((cur) => data.find((r: Requirement) => r.id === (keepId ?? cur?.id)) ?? data[0] ?? null);
    } catch (e) { setError({ msg: (e as Error).message, retry: () => load() }); }
  };
  useEffect(() => { load(); }, []);

  const run = async (label: string, fn: () => Promise<void>, retry?: () => void) => {
    setBusy(label); setError(null);
    try { await fn(); } catch (e) { setError({ msg: (e as Error).message, retry }); } finally { setBusy(null); }
  };

  const analyze = (e: React.FormEvent) => {
    e.preventDefault();
    run('analyze', async () => {
      const { data } = await requirementsApi.analyze(form);
      notify('success', `${data.requirement.req_id} analysed. Review it, then approve.`);
      setForm({ title: '', description: '', user_story: '', acceptance_criteria: '' });
      await load(data.requirement.id);
    }, () => analyze(e));
  };
  const regenerate = () => sel && run('regen', async () => { await requirementsApi.regenerate(sel.id); notify('success', 'Analysis regenerated.'); await load(sel.id); }, regenerate);
  const approve = () => sel && run('approve', async () => { await requirementsApi.approve(sel.id); notify('success', `${sel.req_id} approved.`); await load(sel.id); });
  const saveEdit = () => sel && run('edit', async () => {
    await requirementsApi.update(sel.id, draft); setEditing(false);
    notify('info', 'Requirement edited. Its analysis is now stale - regenerate and re-approve.'); await load(sel.id);
  });
  const startEdit = () => { if (!sel) return; setDraft({ title: sel.title, description: sel.description, user_story: sel.user_story ?? '', acceptance_criteria: sel.acceptance_criteria ?? '' }); setEditing(true); };

  const a = sel?.analysis;
  const byCat = (c: string) => a?.scenarios.filter((s: Scenario) => s.category === c) ?? [];
  const flagged = new Set((sel?.analysis_validation ?? []).filter((i) => i.code === 'unsupported_explicit_requirement').map((i) => i.item));

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {error && <ErrorMessage message={error.msg} onRetry={error.retry} />}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-4">
          <form onSubmit={analyze} className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-100"><FileText size={16} className="text-indigo-400" />New requirement</h2>
            <div className="flex gap-3 text-[11px]">
              <button type="button" className="cursor-pointer text-indigo-400 underline" onClick={() => setForm(SIMPLE)}>Load simple example</button>
              <button type="button" className="cursor-pointer text-indigo-400 underline" onClick={() => setForm(DETAILED)}>Load detailed example</button>
            </div>
            <Field label="Title *"><input className={inputCls} required minLength={3} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
            <Field label="Requirement / user story text *"><textarea className={inputCls} rows={4} required minLength={10} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
            <Field label="User story (optional)"><textarea className={inputCls} rows={2} value={form.user_story} onChange={(e) => setForm({ ...form, user_story: e.target.value })} /></Field>
            <Field label="Acceptance criteria (optional)"><textarea className={inputCls} rows={4} value={form.acceptance_criteria} onChange={(e) => setForm({ ...form, acceptance_criteria: e.target.value })} /></Field>
            <Btn type="submit" variant="primary" busy={busy === 'analyze'} className="w-full justify-center"><Sparkles size={13} />{busy === 'analyze' ? 'Analysing with AI…' : 'Analyze Requirement'}</Btn>
          </form>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Requirements ({list.length})</h3>
            {list.length === 0 ? <p className="py-4 text-center text-xs text-slate-500">None yet. Analyse one above.</p> : (
              <div className="max-h-72 space-y-1.5 overflow-y-auto">
                {list.map((r) => (
                  <button key={r.id} onClick={() => { setSel(r); setEditing(false); }}
                    className={`w-full cursor-pointer rounded-lg border p-2.5 text-left text-xs ${sel?.id === r.id ? 'border-indigo-500/50 bg-indigo-600/10' : 'border-slate-800 bg-slate-800/40 hover:bg-slate-800/80'}`}>
                    <div className="flex items-center justify-between"><span className="font-mono font-semibold text-indigo-400">{r.req_id}</span><StatusBadge status={r.status} /></div>
                    <div className="mt-1 truncate text-slate-300">{r.title}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-8">
          {!sel ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/60"><EmptyState icon={<FileText size={24} />} title="No requirement selected" description="Enter a requirement on the left and run the AI analysis. Nothing is analysed until you do." /></div>
          ) : (
            <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2"><span className="font-mono text-sm font-bold text-indigo-400">{sel.req_id}</span><StatusBadge status={sel.status} /></div>
                  <h2 className="mt-1 text-base font-semibold text-slate-100">{sel.title}</h2>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Btn onClick={startEdit}><Pencil size={12} />Edit Requirement</Btn>
                  <Btn onClick={regenerate} busy={busy === 'regen'} disabled={sel.status === 'approved'} title={sel.status === 'approved' ? 'Edit the requirement first' : ''}><RotateCcw size={12} />Regenerate Analysis</Btn>
                  <Btn variant="success" onClick={approve} busy={busy === 'approve'} disabled={sel.status !== 'analyzed'}><CheckCircle2 size={12} />Approve Analysis</Btn>
                  <Btn variant="primary" onClick={() => onSendToTestCases(sel.id)} disabled={sel.status !== 'approved'} title={sel.status !== 'approved' ? 'Approve the analysis first' : ''}>Send to Test Case Generator<ArrowRight size={12} /></Btn>
                </div>
              </div>

              {sel.status === 'needs_modification' && <div className="rounded-lg border border-orange-500/30 bg-orange-500/10 p-3 text-xs text-orange-300">The requirement text was edited after analysis. The stored analysis may no longer match: regenerate it, review it, then approve again.</div>}

              {editing ? (
                <div className="space-y-3 rounded-lg border border-slate-700 bg-slate-800/40 p-4">
                  <Field label="Title"><input className={inputCls} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} /></Field>
                  <Field label="Requirement text"><textarea className={inputCls} rows={4} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} /></Field>
                  <Field label="User story"><textarea className={inputCls} rows={2} value={draft.user_story} onChange={(e) => setDraft({ ...draft, user_story: e.target.value })} /></Field>
                  <Field label="Acceptance criteria"><textarea className={inputCls} rows={4} value={draft.acceptance_criteria} onChange={(e) => setDraft({ ...draft, acceptance_criteria: e.target.value })} /></Field>
                  <div className="flex gap-2"><Btn variant="primary" onClick={saveEdit} busy={busy === 'edit'}>Save changes</Btn><Btn onClick={() => setEditing(false)}>Cancel</Btn></div>
                  <p className="text-[11px] text-slate-500">Saving changes does not alter the preserved original source below.</p>
                </div>
              ) : (
                <div className="space-y-2 text-xs text-slate-300">
                  <p className="whitespace-pre-wrap">{sel.description}</p>
                  {sel.user_story && <p><b className="text-slate-400">User story:</b> {sel.user_story}</p>}
                  {sel.acceptance_criteria && <p className="whitespace-pre-wrap"><b className="text-slate-400">Acceptance criteria:</b> {sel.acceptance_criteria}</p>}
                  <button className="cursor-pointer text-[11px] text-indigo-400 underline" onClick={() => setShowSource(!showSource)}>{showSource ? 'Hide' : 'Show'} preserved original source</button>
                  {showSource && <pre className="overflow-x-auto rounded bg-slate-950 p-3 text-[11px] text-slate-400">{JSON.stringify(sel.source_snapshot, null, 2)}</pre>}
                </div>
              )}

              {a && (
                <div className="space-y-5">
                  <div className="flex items-center gap-2 text-xs"><span className="text-slate-400">AI validation status:</span><StatusBadge status={a.validation_status} /><span className="text-slate-400">{a.validation_notes}</span></div>
                  <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-300"><b className="text-slate-400">Summary: </b>{a.summary}</div>
                  {sel.analysis_validation && sel.analysis_validation.length > 0 && (
                    <div><h4 className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-amber-300"><ShieldAlert size={13} />Governance checks on this AI output</h4><IssueList issues={sel.analysis_validation} /></div>
                  )}

                  <section>
                    <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-emerald-400">Explicitly defined in the source</h4>
                    {a.explicit_requirements.length === 0 && <p className="text-xs text-slate-500">None identified.</p>}
                    <ul className="space-y-2">
                      {a.explicit_requirements.map((r) => (
                        <li key={r.id} className="rounded-lg border border-slate-800 bg-slate-800/30 p-2.5 text-xs">
                          <div className="flex items-center gap-2"><span className="font-mono text-emerald-400">{r.id}</span><span className="text-slate-200">{r.statement}</span>{flagged.has(r.id) && <Pill tone="red">source quote not found</Pill>}</div>
                          <div className="mt-1 text-[11px] italic text-slate-500">source: “{r.source_quote}”</div>
                        </li>
                      ))}
                    </ul>
                  </section>

                  {(['positive', 'negative', 'boundary', 'edge'] as const).map((c) => (
                    <section key={c}>
                      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">{c} scenarios ({byCat(c).length})</h4>
                      {byCat(c).length === 0 ? <p className="text-xs text-slate-500">None.</p> : (
                        <ul className="space-y-1.5">
                          {byCat(c).map((s) => (
                            <li key={s.id} className="flex flex-wrap items-start gap-2 rounded-lg border border-slate-800 bg-slate-800/30 p-2.5 text-xs">
                              <span className="font-mono text-slate-400">{s.id}</span><Pill tone={catTone[c]}>{c}</Pill>
                              {s.classification === 'derived' ? <Pill tone="blue">derived</Pill> : <Pill tone="amber">AI suggestion — needs human validation</Pill>}
                              <span className="min-w-0 flex-1 text-slate-200">{s.title}<span className="block text-[11px] text-slate-500">basis: {s.basis || '—'}</span></span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </section>
                  ))}

                  {([['Potentially missed scenarios (AI suggestions)', a.potentially_missed_scenarios.map((m) => `${m.title} — ${m.rationale}`)],
                     ['Missing information', a.missing_information], ['Ambiguities', a.ambiguities],
                     ['Unsupported assumptions (NOT requirements)', a.assumptions]] as [string, string[]][]).map(([t, items]) => (
                    <section key={t}>
                      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-amber-400">{t}</h4>
                      {items.length === 0 ? <p className="text-xs text-slate-500">None reported.</p> : <ul className="list-inside list-disc space-y-1 text-xs text-slate-300">{items.map((i, k) => <li key={k}>{i}</li>)}</ul>}
                    </section>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
