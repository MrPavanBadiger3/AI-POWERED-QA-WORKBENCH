import React from 'react';

interface Props {
  status: string;
  size?: 'sm' | 'md';
}

const STATUS_COLORS: Record<string, string> = {
  needs_modification: 'bg-orange-500/15 text-orange-400 border border-orange-500/30',
  draft_only: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  error: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
  timeout: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
  not_executed: 'bg-slate-500/15 text-slate-300 border border-slate-500/30',
  not_automated: 'bg-slate-500/15 text-slate-300 border border-slate-500/30',
  partially_executed: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  warnings: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  no_tests: 'bg-slate-500/15 text-slate-300 border border-slate-500/30',
  pending: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  analyzed: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
  approved: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
  rejected: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
  passed: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
  failed: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
  skipped: 'bg-slate-500/15 text-slate-400 border border-slate-500/30',
  running: 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 animate-pulse',
  completed: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
  covered: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
  not_covered: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
  Critical: 'bg-rose-600/20 text-rose-300 border border-rose-500/40',
  High: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
  Medium: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  Low: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
  valid: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
  partial: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  invalid: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
};

export const StatusBadge: React.FC<Props> = ({ status, size = 'sm' }) => {
  const colorClass = STATUS_COLORS[status] || 'bg-slate-500/15 text-slate-400 border border-slate-500/30';
  const sizeClass = size === 'sm' ? 'text-xs px-2.5 py-0.5' : 'text-sm px-3.5 py-1';
  return (
    <span className={`inline-flex items-center font-medium rounded-full ${colorClass} ${sizeClass}`}>
      {status ? status.replace(/_/g, ' ') : 'unknown'}
    </span>
  );
};
