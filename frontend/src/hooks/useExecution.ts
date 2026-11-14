import { useCallback, useEffect, useRef, useState } from 'react';
import { executionsApi } from '../services/api';
import { Execution, TestResult } from '../types';

/** Polls an execution every 2s until it is no longer pending/running. */
export function useExecution(onFinished?: (e: Execution) => void) {
  const [id, setId] = useState<string | null>(null);
  const [execution, setExecution] = useState<Execution | null>(null);
  const [results, setResults] = useState<TestResult[]>([]);
  const [logs, setLogs] = useState('');
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const cb = useRef(onFinished);
  cb.current = onFinished;

  const stop = () => { if (timer.current) { clearInterval(timer.current); timer.current = null; } };

  const refresh = useCallback(async (execId: string) => {
    try {
      const { data } = await executionsApi.get(execId);
      setExecution(data);
      const [r, l] = await Promise.all([executionsApi.results(execId), executionsApi.logs(execId)]);
      setResults(r.data); setLogs(l.data.logs);
      if (data.status !== 'pending' && data.status !== 'running') { stop(); cb.current?.(data); }
    } catch (e) { setError((e as Error).message); stop(); }
  }, []);

  useEffect(() => {
    stop();
    if (!id) return;
    refresh(id);
    timer.current = setInterval(() => refresh(id), 2000);
    return stop;
  }, [id, refresh]);

  const running = execution?.status === 'pending' || execution?.status === 'running';
  return { id, track: (x: string) => { setError(null); setId(x); }, execution, results, logs, error, running };
}
