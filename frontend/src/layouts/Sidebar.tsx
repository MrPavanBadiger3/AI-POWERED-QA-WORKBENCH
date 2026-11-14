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
    className={`flex flex-col border-r border-slate-800 bg-[#11111a] transition-all duration-200 shrink-0 ${
      collapsed ? 'w-16' : 'w-56'
    }`}
  >
    {/* Logo */}
    <div className="flex items-center gap-3 border-b border-slate-800 px-4 h-14 shrink-0">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/20 border border-indigo-500/40 text-indigo-400">
        <Zap size={16} />
      </div>
      {!collapsed && (
        <div className="overflow-hidden">
          <div className="text-xs font-bold text-white tracking-wide">QA WORKBENCH</div>
          <div className="text-[10px] text-indigo-400 font-medium">AI-POWERED</div>
        </div>
      )}
    </div>

    {/* Navigation */}
    <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
      {NAV_ITEMS.map((item) => {
        const isActive = currentPage === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`flex w-full items-center gap-3 px-3 py-2 rounded-lg text-left transition-all cursor-pointer ${
              isActive
                ? 'bg-indigo-600/20 text-indigo-300 font-medium border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
            title={collapsed ? item.label : undefined}
          >
            <span className={`shrink-0 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`}>
              {item.icon}
            </span>
            {!collapsed && <span className="text-xs truncate">{item.label}</span>}
          </button>
        );
      })}
    </nav>

    {/* Toggle */}
    <div className="p-2 border-t border-slate-800 shrink-0">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-center py-2 text-slate-500 hover:text-slate-300 rounded hover:bg-slate-800/50 transition-colors cursor-pointer"
        aria-label="Toggle sidebar"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </div>
  </aside>
);
