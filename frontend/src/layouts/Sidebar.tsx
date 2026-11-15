import React from 'react';
import {
  LayoutDashboard, FileText, FlaskConical, Play, Database,
  Bug, BarChart3, BookOpen, Shield, Settings, ChevronLeft,
  ChevronRight, Zap
} from 'lucide-react';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={16} /> },
  { id: 'requirements', label: 'Requirement Analyzer', icon: <FileText size={16} /> },
  { id: 'testcases', label: 'Test Case Generator', icon: <FlaskConical size={16} /> },
  { id: 'automation', label: 'Test Automation', icon: <Play size={16} /> },
  { id: 'data-driven', label: 'Data-Driven Testing', icon: <Database size={16} /> },
  { id: 'defects', label: 'Defect Analysis', icon: <Bug size={16} /> },
  { id: 'reports', label: 'Execution Reports', icon: <BarChart3 size={16} /> },
  { id: 'documentation', label: 'Test Documentation', icon: <BookOpen size={16} /> },
  { id: 'governance', label: 'AI Governance', icon: <Shield size={16} /> },
  { id: 'settings', label: 'Settings', icon: <Settings size={16} /> },
];

interface Props {
  currentPage: string;
  onNavigate: (page: string) => void;
  collapsed: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<Props> = ({ currentPage, onNavigate, collapsed, onToggle }) => (
  <aside
    className={`flex shrink-0 flex-col border-r border-hairline bg-cream-light ${
      collapsed ? 'w-14' : 'w-14 md:w-60'
    }`}
  >
    <div className="flex h-[4.5rem] shrink-0 items-center gap-3 border-b border-beige-deep px-3 md:px-4">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary text-white shadow-sm">
        <Zap size={17} aria-hidden="true" />
      </div>
      {!collapsed && (
        <div className="hidden min-w-0 overflow-hidden md:block">
          <div className="truncate text-xs font-semibold tracking-[0.12em] text-ink">QA WORKBENCH</div>
          <div className="mt-0.5 text-[10px] font-medium tracking-[0.16em] text-primary-deep">AI-POWERED</div>
        </div>
      )}
    </div>

    <nav aria-label="Main navigation" className="flex-1 space-y-1 overflow-y-auto px-1.5 py-3 md:px-2">
      {NAV_ITEMS.map((item) => {
        const isActive = currentPage === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            aria-label={item.label}
            aria-current={isActive ? 'page' : undefined}
            className={`flex min-h-10 w-full cursor-pointer items-center justify-center gap-3 rounded-md border px-2 py-2 text-left md:justify-start md:px-3 ${
              isActive
                ? 'border-primary/20 bg-cream text-primary-deep font-medium shadow-sm'
                : 'border-transparent text-slate-400 hover:bg-white hover:text-ink'
            }`}
            title={collapsed ? item.label : undefined}
          >
            <span aria-hidden="true" className={`shrink-0 ${isActive ? 'text-primary' : 'text-slate-500'}`}>
              {item.icon}
            </span>
            {!collapsed && <span className="hidden truncate text-xs md:inline">{item.label}</span>}
          </button>
        );
      })}
    </nav>

    <div className="shrink-0 border-t border-beige-deep p-2">
      <button
        onClick={onToggle}
        className="flex min-h-10 w-full cursor-pointer items-center justify-center rounded-md text-slate-500 hover:bg-white hover:text-ink"
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        aria-expanded={!collapsed}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={16} aria-hidden="true" /> : <ChevronLeft size={16} aria-hidden="true" />}
      </button>
    </div>
  </aside>
);
