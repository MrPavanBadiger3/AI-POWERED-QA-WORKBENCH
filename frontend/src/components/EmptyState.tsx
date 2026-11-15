import React from 'react';

interface Props {
  icon: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<Props> = ({ icon, title, description, action }) => (
  <div className="flex flex-col items-center justify-center py-16 text-center">
  <div aria-hidden="true" className="mb-4 rounded-lg border border-beige-deep bg-cream p-4 text-primary-deep">{icon}</div>
    <h3 className="mb-1 text-base font-semibold text-slate-200">{title}</h3>
    <p className="mb-6 max-w-sm text-sm text-slate-400">{description}</p>
    {action}
  </div>
);
