import React from 'react';

export const LoadingSpinner: React.FC<{ size?: 'sm' | 'md' | 'lg'; text?: string }> = ({ size = 'md', text }) => {
  const sizes = { sm: 'h-4 w-4', md: 'h-8 w-8', lg: 'h-12 w-12' };
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8" role="status">
      <div aria-hidden="true" className={`animate-spin rounded-full border-2 border-primary/30 border-t-primary ${sizes[size]}`} />
      {text && <p className="text-sm text-slate-400">{text}</p>}
      {!text && <span className="sr-only">Loading…</span>}
    </div>
  );
};
