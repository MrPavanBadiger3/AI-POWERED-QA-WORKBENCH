import React from 'react';

interface Props {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export const Card: React.FC<Props> = ({ children, className = '', title, subtitle, action }) => (
  <div className={`rounded-xl border border-slate-800/80 bg-slate-900/60 backdrop-blur-sm ${className}`}>
    {(title || action) && (
      <div className="flex items-center justify-between border-b border-slate-800/80 px-5 py-4">
        <div>
          {title && <h3 className="text-sm font-semibold text-slate-100">{title}</h3>}
          {subtitle && <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p>}
        </div>
        {action}
      </div>
    )}
    <div className="p-5">{children}</div>
  </div>
);
