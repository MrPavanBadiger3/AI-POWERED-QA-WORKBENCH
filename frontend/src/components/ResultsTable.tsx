import React, { useState } from 'react';
import { Bug, Image as ImageIcon } from 'lucide-react';
import { TestResult } from '../types';
import { StatusBadge } from './StatusBadge';
import { Btn } from './ui';

export const ResultsTable: React.FC<{ results: TestResult[]; onAnalyze?: (resultId: string) => void; showData?: boolean }> = ({ results, onAnalyze, showData }) => {
  const [open, setOpen] = useState<string | null>(null);
  if (results.length === 0) return <p className="p-6 text-center text-xs text-slate-500">No test results recorded.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400">
          <tr><th className="px-3 py-2">Test</th>{showData && <><th className="px-3 py-2">Username</th><th className="px-3 py-2">Expected</th><th className="px-3 py-2">Actual</th></>}
            <th className="px-3 py-2">Result</th><th className="px-3 py-2">Duration</th><th className="px-3 py-2">Linked TC</th><th className="px-3 py-2">Evidence</th></tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <React.Fragment key={r.id}>
              <tr className="border-b border-slate-800/60 align-top hover:bg-slate-800/30">
                <td className="max-w-xs break-all px-3 py-2 font-mono text-[11px] text-slate-200">{r.test_name.replace('automation/tests/', '')}</td>
                {showData && <>
                  <td className="px-3 py-2 text-slate-300">{String(r.meta?.username ?? '—')}</td>
                  <td className="px-3 py-2 text-slate-300">{String(r.meta?.expected_outcome ?? '—')}</td>
                  <td className="px-3 py-2 text-slate-300">{String(r.meta?.actual_outcome ?? '—')}</td></>}
                <td className="px-3 py-2"><StatusBadge status={r.status} /></td>
                <td className="px-3 py-2 text-slate-400">{(r.duration ?? 0).toFixed(2)}s</td>
                <td className="px-3 py-2 font-mono text-slate-400">{r.linked_test_cases.join(', ') || '—'}</td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1.5">
                    {r.status === 'failed' && <Btn onClick={() => setOpen(open === r.id ? null : r.id)}>Failure log</Btn>}
                    {r.screenshot_url && <a href={r.screenshot_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-lg border border-slate-700/60 bg-slate-800 px-2 py-1.5 text-[11px] text-slate-200 hover:bg-slate-700"><ImageIcon size={11} />Screenshot</a>}
                    {r.status === 'failed' && onAnalyze && <Btn variant="primary" onClick={() => onAnalyze(r.id)}><Bug size={11} />Analyze defect</Btn>}
                  </div>
                </td>
              </tr>
              {open === r.id && (
                <tr><td colSpan={showData ? 8 : 5} className="bg-cream-light px-3 py-3">
                  <pre className="code-panel max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-code-surface p-3 font-mono text-[11px] text-code-text">{r.error_message || 'No exception text was captured.'}</pre>
                  {r.screenshot_url && <img src={r.screenshot_url} alt={`Failure screenshot for ${r.test_name}`} width={1280} height={720} loading="lazy" className="mt-3 max-h-80 max-w-full rounded border border-slate-700 object-contain object-left" />}
                </td></tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
};
