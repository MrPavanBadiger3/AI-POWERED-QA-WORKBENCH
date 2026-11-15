import React, { useEffect, useState } from 'react';
import { Activity, Wifi, WifiOff } from 'lucide-react';
import { systemApi } from '../services/api';

const PAGE_TITLES: Record<string, string> = {
  overview: 'Executive Dashboard & Metrics',
  requirements: 'AI Requirement Analyzer',
  testcases: 'AI Test Case Generator',
  automation: 'Automated Test Execution (Playwright)',
  'data-driven': 'Data-Driven Testing (SauceDemo)',
  defects: 'AI Defect Analysis & Root Cause',
  reports: 'Execution Reports & Evidence',
  documentation: 'Test Documentation & Traceability Matrix (RTM)',
  governance: 'AI Governance & Validation Controls',
  settings: 'System Configuration & Environment',
};

export const Header: React.FC<{ currentPage: string }> = ({ currentPage }) => {
  const [apiStatus, setApiStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');

  useEffect(() => {
    const check = async () => {
      try {
        await systemApi.health();
        setApiStatus('connected');
      } catch {
        setApiStatus('disconnected');
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="flex min-h-[4.5rem] shrink-0 items-center justify-between gap-3 border-b border-hairline bg-white px-4 sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <h1 className="truncate font-display text-xl leading-tight text-ink sm:text-2xl">{PAGE_TITLES[currentPage] || currentPage}</h1>
        <span className="hidden rounded-md border border-beige-deep bg-cream px-2 py-1 text-[11px] font-medium text-slate-400 sm:inline-flex">AUT: SauceDemo</span>
      </div>
      <div className="flex shrink-0 items-center gap-4">
        <div className="flex items-center gap-2 rounded-md border border-hairline bg-slate-50 px-2.5 py-1.5 sm:px-3" role="status" aria-live="polite">
          {apiStatus === 'connected' ? (
            <>
              <Wifi size={13} aria-hidden="true" className="text-emerald-400" />
              <span className="hidden text-xs font-medium text-emerald-400 sm:inline">Backend Online</span>
            </>
          ) : apiStatus === 'disconnected' ? (
            <>
              <WifiOff size={13} aria-hidden="true" className="text-rose-400" />
              <span className="hidden text-xs font-medium text-rose-400 sm:inline">Backend Offline</span>
            </>
          ) : (
            <>
              <Activity size={13} aria-hidden="true" className="animate-pulse text-amber-400" />
              <span className="hidden text-xs font-medium text-amber-400 sm:inline">Checking…</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
