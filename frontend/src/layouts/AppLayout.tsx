import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface Props {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
}

export const AppLayout: React.FC<Props> = ({ children, currentPage, onNavigate }) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  return (
    <div className="flex h-dvh overflow-hidden bg-slate-50 text-ink">
      <a href="#main" className="skip-link">Skip to main content</a>
      <Sidebar
        currentPage={currentPage}
        onNavigate={onNavigate}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header currentPage={currentPage} />
        <main id="main" tabIndex={-1} className="flex-1 overflow-x-hidden overflow-y-auto bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto min-h-[calc(100%-5rem)] max-w-[1440px]">
            {children}
          </div>
          <footer className="mx-auto mt-12 max-w-[1440px] pb-2">
            <div className="sunset-stripe h-2 rounded-full" aria-hidden="true" />
            <div className="flex flex-wrap items-center justify-between gap-2 py-4 text-xs text-slate-500">
              <span>AI-powered QA Workbench</span>
              <span>Human-reviewed. Evidence-backed.</span>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
};
