import React, { useEffect, useRef, useState } from 'react';
import { Database, Upload, Play } from 'lucide-react';
import { dataApi } from '../services/api';
import { useExecution } from '../hooks/useExecution';
import { ErrorMessage } from '../components/ErrorMessage';
import { StatusBadge } from '../components/StatusBadge';
import { ResultsTable } from '../components/ResultsTable';
import { Btn, inputCls } from '../components/ui';
import { useNotify } from '../components/Notify';

export const DataDrivenPage: React.FC<{ onAnalyzeDefect: (id: string) => void }> = ({ onAnalyzeDefect }) => {
  const notify = useNotify();
  const ex = useExecution((e) => notify(e.failed === 0 && e.status === 'completed' ? 'success' : 'error', `${e.execution_id}: ${e.passed} passed, ${e.failed} failed`));
  const [datasets, setDatasets] = useState<string[]>([]);
  const [dataset, setDataset] = useState('login_data.csv');
  const [rows, setRows] = useState<Record<string, string>[]>([]);
  const [error, setError] = useState<{ msg: string; retry?: () => void } | null>(null);
  const [busy, setBusy] = useState(false);
  const file = useRef<HTMLInputElement>(null);

  const load = async (name = dataset) => {
    try { const { data } = await dataApi.getTestData(name); setDatasets(data.available_datasets); setRows(data.data); setDataset(name); setError(null); }
    catch (e) { setError({ msg: (e as Error).message, retry: () => load(name) }); }
  };
  useEffect(() => { load('login_data.csv'); /* eslint-disable-next-line */ }, []);

  const upload = async (f?: File) => {
    if (!f) return;
    try { const { data } = await dataApi.upload(f); notify('success', `${data.rows} rows validated and saved as ${data.dataset}`); await load(data.dataset); }
    catch (e) { setError({ msg: (e as Error).message }); } finally { if (file.current) file.current.value = ''; }
  };
  const run = async () => {
    setBusy(true); setError(null);
    try { const { data } = await dataApi.run(dataset); ex.track(data.db_id); notify('info', `Data-driven execution ${data.execution_id} started`); }
    catch (e) { setError({ msg: (e as Error).message, retry: run }); } finally { setBusy(false); }
  };

  const e = ex.execution;
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {error && <ErrorMessage message={error.msg} onRetry={error.retry} />}
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="mb-1 flex items-center gap-2 text-sm font-semibold text-slate-100"><Database size={15} className="text-indigo-400" />Login dataset</h2>
        <p className="mb-3 text-xs text-slate-400">One parameterised pytest function runs once per row. Data lives in CSV, not in code. Required columns: <code className="text-slate-300">username, password, expected_outcome</code> (success|failure). Blank cells mean empty input.</p>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <select aria-label="Dataset" className={`${inputCls} w-auto`} value={dataset} onChange={(x) => load(x.target.value)}>{datasets.map((d) => <option key={d}>{d}</option>)}</select>
          <input ref={file} name="dataset_file" type="file" accept=".csv" className="hidden" onChange={(x) => upload(x.target.files?.[0])} aria-label="Upload CSV dataset" />
          <Btn onClick={() => file.current?.click()}><Upload size={12} />Upload CSV</Btn>
          <Btn variant="primary" busy={busy || ex.running} onClick={run}><Play size={12} />Run data-driven tests</Btn>
        </div>
        <table className="w-full text-left text-xs"><thead className="border-b border-slate-800 text-[11px] uppercase text-slate-400"><tr><th className="px-3 py-2">#</th><th className="px-3 py-2">Username</th><th className="px-3 py-2">Password</th><th className="px-3 py-2">Expected outcome</th></tr></thead>
          <tbody>{rows.map((r, i) => <tr key={i} className="border-b border-slate-800/60 text-slate-300"><td className="px-3 py-2">{i + 1}</td><td className="px-3 py-2">{r.username || <i className="text-slate-500">(empty)</i>}</td>
            <td className="px-3 py-2">{r.password ? '••••••••' : <i className="text-slate-500">(empty)</i>}</td><td className="px-3 py-2">{r.expected_outcome}</td></tr>)}</tbody></table>
      </section>

      {e && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 p-4">
            <div className="flex items-center gap-3"><span className="font-mono text-sm font-semibold text-indigo-400">{e.execution_id}</span><StatusBadge status={ex.running ? e.status : e.overall_status} /><span className="text-xs text-slate-400">{e.dataset}</span></div>
            <div className="flex gap-4 text-xs"><span className="text-emerald-400">Passed {e.passed}</span><span className="text-rose-400">Failed {e.failed}</span><span className="text-slate-400">Total {e.total_tests}</span></div>
          </div>
          {e.error_message && <div className="m-4"><ErrorMessage message={e.error_message} /></div>}
          <ResultsTable results={ex.results} showData onAnalyze={onAnalyzeDefect} />
        </section>
      )}
    </div>
  );
};
