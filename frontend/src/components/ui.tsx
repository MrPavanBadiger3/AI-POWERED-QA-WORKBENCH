import React from 'react';

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'danger' | 'success'; busy?: boolean };
export const Btn: React.FC<BtnProps> = ({ variant = 'ghost', busy, children, className = '', disabled, ...rest }) => {
  const styles = {
    primary: 'bg-indigo-600 hover:bg-indigo-500 text-white',
    success: 'bg-emerald-600 hover:bg-emerald-500 text-white',
    danger: 'bg-rose-600/80 hover:bg-rose-500 text-white',
    ghost: 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/60',
  }[variant];
  return (
    <button {...rest} disabled={disabled || busy}
      className={`inline-flex cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}>
      {busy && <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white" />}
      {children}
    </button>
  );
};

export const inputCls = 'w-full rounded-lg border border-slate-700/60 bg-slate-800/80 px-3 py-2 text-xs text-slate-100 focus:border-indigo-500 focus:outline-none';

export const Field: React.FC<{ label: string; children: React.ReactNode; hint?: string }> = ({ label, children, hint }) => (
  <label className="block">
    <span className="mb-1 block text-xs font-medium text-slate-300">{label}</span>
    {children}
    {hint && <span className="mt-1 block text-[11px] text-slate-500">{hint}</span>}
  </label>
);

export const Pill: React.FC<{ tone?: 'amber' | 'blue' | 'green' | 'red' | 'slate'; children: React.ReactNode }> = ({ tone = 'slate', children }) => {
  const c = { amber: 'border-amber-500/30 bg-amber-500/10 text-amber-300', blue: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
    green: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300', red: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
    slate: 'border-slate-600 bg-slate-800 text-slate-300' }[tone];
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] ${c}`}>{children}</span>;
};

export const Modal: React.FC<{ title: string; onClose: () => void; children: React.ReactNode; wide?: boolean }> = ({ title, onClose, children, wide }) => (
  <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true" aria-label={title}
    onKeyDown={(e) => e.key === 'Escape' && onClose()}>
    <div className={`max-h-[90vh] w-full overflow-y-auto overscroll-contain rounded-xl border border-slate-700 bg-slate-900 ${wide ? 'max-w-4xl' : 'max-w-2xl'}`}>
      <div className="sticky top-0 flex items-center justify-between border-b border-slate-800 bg-slate-900 px-5 py-3">
        <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
        <button onClick={onClose} className="cursor-pointer text-xs text-slate-400 hover:text-slate-200" autoFocus>Close ✕</button>
      </div>
      <div className="p-5">{children}</div>
    </div>
  </div>
);

export const IssueList: React.FC<{ issues?: { severity: string; message: string; code: string }[] | null }> = ({ issues }) =>
  !issues || issues.length === 0 ? null : (
    <ul className="space-y-1">
      {issues.map((i, k) => (
        <li key={k} className={`rounded border px-2 py-1 text-[11px] ${i.severity === 'error' ? 'border-rose-500/30 bg-rose-500/10 text-rose-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300'}`}>
          <span className="font-mono opacity-70">{i.code}</span> — {i.message}
        </li>
      ))}
    </ul>
  );

export const ago = (iso?: string | null) => (iso ? new Date(iso).toLocaleString() : '—');
