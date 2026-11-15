import React, { useEffect, useState } from 'react';
import { BookOpen, Download, Sparkles, FolderDown } from 'lucide-react';
import { docApi } from '../services/api';
import { TraceabilityMatrix } from '../types';
import { ErrorMessage } from '../components/ErrorMessage';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { Btn } from '../components/ui';
import { useNotify } from '../components/Notify';

interface Doc { id: string; doc_id: string; title: string; created_at: string; has_ai_narrative: boolean }

export const DocumentationPage: React.FC = () => {
  const notify = useNotify();
  const [rtm, setRtm] = useState<TraceabilityMatrix | null>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [markdown, setMarkdown] = useState('');
  const [useAi, setUseAi] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<{ msg: string; retry?: () => void } | null>(null);

  const load = async () => {
    try { const [t, d] = await Promise.all([docApi.traceability(), docApi.list()]); setRtm(t.data); setDocs(d.data); } catch (e) { setError({ msg: (e as Error).message, retry: load }); }
  };
  useEffect(() => { load(); }, []);

  const generate = async () => {
    setBusy('gen'); setError(null);
    try { const { data } = await docApi.generate(useAi); setMarkdown(data.markdown); notify('success', `${data.doc_id} generated from ${data.counts.requirements} approved requirement(s) and ${data.counts.test_cases} approved test case(s).`); await load(); }
    catch (e) { setError({ msg: (e as Error).message, retry: generate }); } finally { setBusy(null); }
  };
  const exportAll = async () => {
    setBusy('exp');
    try { const { data } = await docApi.exportArtifacts(); notify('success', `${data.exported.length} artifact file(s) written to ${data.location}`); } catch (e) { setError({ msg: (e as Error).message }); } finally { setBusy(null); }
  };

  const s = rtm?.summary;
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {error && <ErrorMessage message={error.msg} onRetry={error.retry} />}

      <section className="rounded-xl border border-slate-800 bg-slate-900/60">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 p-4">
          <div><h2 className="flex items-center gap-2 text-sm font-semibold text-slate-100"><BookOpen size={15} className="text-indigo-400" />Requirement Traceability Matrix</h2>
            <p className="mt-0.5 text-[11px] text-slate-500">{s?.definition} Coverage and execution status are computed from saved relationships only.</p></div>
          <a className="inline-flex items-center gap-1 rounded-lg border border-slate-700/60 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700" href={docApi.rtmUrl()}><Download size={12} />Export RTM (CSV)</a>
        </div>
        {s && <div className="grid grid-cols-2 gap-3 border-b border-slate-800 p-4 md:grid-cols-4 text-xs">
          {[['Requirements', s.total_requirements], ['Covered (approved TCs)', s.covered], ['Draft-only', s.draft_only], ['No test cases', s.not_covered]].map(([l, v]) => <div key={l as string} className="rounded-lg bg-slate-800/50 p-3"><div className="text-slate-400">{l}</div><div className="text-xl font-semibold text-slate-100">{v}</div></div>)}</div>}
        {!rtm || rtm.matrix.length === 0 ? <EmptyState icon={<BookOpen size={24} />} title="No requirements yet" description="Analyse a requirement to start the matrix." /> : (
          <div className="overflow-x-auto"><table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400"><tr>{['Requirement', 'Description', 'Linked test cases', 'Coverage', 'Latest execution'].map((h) => <th key={h} className="px-3 py-3">{h}</th>)}</tr></thead>
            <tbody>{rtm.matrix.map((r) => (
              <tr key={r.requirement_id} className="border-b border-slate-800/60 align-top">
                <td className="px-3 py-3 font-mono text-indigo-400">{r.requirement_id}</td><td className="max-w-sm px-3 py-3 text-slate-300">{r.requirement_description}</td>
                <td className="px-3 py-3">{r.test_cases.length === 0 ? <span className="text-rose-300">none — no coverage</span> : r.test_cases.map((t) => (
                  <div key={t.tc_id} className="mb-1 flex items-center gap-2"><span className="font-mono text-slate-200">{t.tc_id}</span><StatusBadge status={t.status} /><StatusBadge status={t.latest_execution_status} /></div>))}</td>
                <td className="px-3 py-3"><StatusBadge status={r.coverage_status} /></td><td className="px-3 py-3"><StatusBadge status={r.latest_execution_status} /></td></tr>))}</tbody></table></div>)}
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="mb-1 text-sm font-semibold text-slate-100">Generate test documentation</h2>
        <p className="mb-3 text-xs text-slate-400">Built from <b>approved</b> requirements and test cases plus stored execution figures. The optional AI narrative may only use those facts.</p>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex min-h-9 items-center gap-2 text-xs text-slate-300"><input name="include_ai_narrative" type="checkbox" checked={useAi} onChange={(e) => setUseAi(e.target.checked)} />Include AI narrative</label>
          <Btn variant="primary" busy={busy === 'gen'} onClick={generate}><Sparkles size={12} />Generate documentation</Btn>
          <Btn busy={busy === 'exp'} onClick={exportAll}><FolderDown size={12} />Export all artifacts to /artifacts</Btn>
        </div>
        {markdown && <pre className="code-panel mt-4 max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-lg bg-code-surface p-4 font-mono text-[11px] text-code-text">{markdown}</pre>}
        {docs.length > 0 && <div className="mt-4"><h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Generated documents</h3>
          <ul className="space-y-1 text-xs">{docs.map((d) => <li key={d.id} className="flex items-center gap-3 text-slate-300"><span className="font-mono text-indigo-400">{d.doc_id}</span><span>{new Date(d.created_at).toLocaleString()}</span><span className="text-slate-500">{d.has_ai_narrative ? 'with AI narrative' : 'no AI narrative'}</span><a className="text-indigo-400 underline" href={docApi.downloadUrl(d.id)}>Download .md</a></li>)}</ul></div>}
      </section>
    </div>
  );
};
