import React, { useEffect, useState } from 'react';
import { CheckCircle2, XCircle, Plug } from 'lucide-react';
import { systemApi } from '../services/api';
import { ErrorMessage } from '../components/ErrorMessage';
import { Btn } from '../components/ui';

interface Cfg { groq_api_configured: boolean; groq_model: string; available_models: string[]; ai_timeout_seconds: number; saucedemo_url: string; headless: boolean; execution_timeout_seconds: number }

export const SettingsPage: React.FC = () => {
  const [cfg, setCfg] = useState<Cfg | null>(null);
  const [health, setHealth] = useState<{ status: string; version: string } | null>(null);
  const [error, setError] = useState<{ msg: string; retry?: () => void } | null>(null);
  const [test, setTest] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [selectedModel, setSelectedModel] = useState('');
  const [modelBusy, setModelBusy] = useState(false);
  const [modelMessage, setModelMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const load = async () => { try { const [c, h] = await Promise.all([systemApi.config(), systemApi.health()]); setCfg(c.data); setSelectedModel(c.data.groq_model); setHealth(h.data); setError(null); } catch (e) { setError({ msg: (e as Error).message, retry: load }); } };
  useEffect(() => { load(); }, []);
  const saveModel = async () => {
    setModelBusy(true); setModelMessage(null);
    try { await systemApi.updateModel(selectedModel); setModelMessage({ ok: true, text: 'Model saved.' }); }
    catch (e) { setModelMessage({ ok: false, text: (e as Error).message }); }
    finally { setModelBusy(false); }
  };
  const testAi = async () => {
    setBusy(true); setTest(null);
    try { const { data } = await systemApi.testAi(); setTest({ ok: true, text: `Real call to ${data.model} succeeded.` }); } catch (e) { setTest({ ok: false, text: (e as Error).message }); } finally { setBusy(false); }
  };

  const row = (label: string, value: React.ReactNode) => <div className="flex items-center justify-between border-b border-slate-800/60 py-2.5 text-xs"><span className="text-slate-400">{label}</span><span className="text-slate-200">{value}</span></div>;
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      {error && <ErrorMessage message={error.msg} onRetry={error.retry} />}
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="mb-2 text-sm font-semibold text-slate-100">Backend & AI configuration</h2>
        {cfg && <>
          {row('Backend', health ? `${health.status} · v${health.version}` : '—')}
          {row('Groq API key', cfg.groq_api_configured ? <span className="flex items-center gap-1 text-emerald-400"><CheckCircle2 size={13} />configured</span> : <span className="flex items-center gap-1 text-rose-400"><XCircle size={13} />missing: set GROQ_API_KEY in backend/.env and restart</span>)}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/60 py-2.5">
            <label htmlFor="ai-model" className="text-xs text-slate-400">AI model</label>
            <div className="flex flex-wrap items-center gap-2">
              <select id="ai-model" value={selectedModel} onChange={(e) => { setSelectedModel(e.target.value); setModelMessage(null); }}
                className="min-h-9 rounded-md border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200">
                {cfg.available_models.map((model) => <option key={model} value={model}>{model}{model === 'openai/gpt-oss-120b' ? ' (recommended)' : ''}</option>)}
              </select>
              <Btn variant="primary" busy={modelBusy} onClick={saveModel}>Save model</Btn>
              {modelMessage && <span role="status" className={`text-xs ${modelMessage.ok ? 'text-emerald-400' : 'text-rose-400'}`}>{modelMessage.text}</span>}
            </div>
          </div>
          {row('AI timeout', `${cfg.ai_timeout_seconds}s`)}{row('Application under test', cfg.saucedemo_url)}
          {row('Browser mode', cfg.headless ? 'headless' : 'headed')}{row('Execution timeout', `${cfg.execution_timeout_seconds}s`)}
        </>}
        <div className="mt-4 flex items-center gap-3"><Btn variant="primary" busy={busy} onClick={testAi}><Plug size={12} />Test AI connection</Btn>
          {test && <span className={`text-xs ${test.ok ? 'text-emerald-400' : 'text-rose-400'}`}>{test.text}</span>}</div>
        <p className="mt-3 text-[11px] text-slate-500">Secrets are held only by the backend. Change them in <code>backend/.env</code>; the key is never sent to this page.</p>
      </section>
    </div>
  );
};
