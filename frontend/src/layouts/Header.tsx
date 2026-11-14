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
    <header className="flex items-center justify-between border-b border-slate-800 bg-[#11111a] px-6 h-14 shrink-0">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-slate-100">{PAGE_TITLES[currentPage] || currentPage}</h1>
        <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60">AUT: SauceDemo</span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-1">
          {apiStatus === 'connected' ? (
            <>
              <Wifi size={13} className="text-emerald-400" />
              <span className="text-xs font-medium text-emerald-400">Backend Online</span>
            </>
          ) : apiStatus === 'disconnected' ? (
            <>
              <WifiOff size={13} className="text-rose-400" />
              <span className="text-xs font-medium text-rose-400">Backend Offline</span>
            </>
          ) : (
            <>
              <Activity size={13} className="text-amber-400 animate-pulse" />
              <span className="text-xs font-medium text-amber-400">Checking...</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
