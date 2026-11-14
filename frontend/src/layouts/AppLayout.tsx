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
    <div className="flex h-screen overflow-hidden bg-[#0a0a0f] text-[#f0f0f8]">
      <a href="#main" className="skip-link">Skip to main content</a>
      <Sidebar
        currentPage={currentPage}
        onNavigate={onNavigate}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header currentPage={currentPage} />
        <main id="main" tabIndex={-1} className="flex-1 overflow-y-auto p-6 bg-[#0c0c14]">
          {children}
        </main>
      </div>
    </div>
  );
};
