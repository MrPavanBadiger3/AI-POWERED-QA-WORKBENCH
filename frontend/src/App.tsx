import { useState } from 'react';
import { AppLayout } from './layouts/AppLayout';
import { OverviewPage } from './pages/OverviewPage';
import { RequirementsPage } from './pages/RequirementsPage';
import { TestCasesPage } from './pages/TestCasesPage';
import { AutomationPage } from './pages/AutomationPage';
import { DataDrivenPage } from './pages/DataDrivenPage';
import { DefectsPage } from './pages/DefectsPage';
import { ReportsPage } from './pages/ReportsPage';
import { DocumentationPage } from './pages/DocumentationPage';
import { GovernancePage } from './pages/GovernancePage';
import { SettingsPage } from './pages/SettingsPage';

export function App() {
  const [page, setPage] = useState('overview');
  const [reqForTestCases, setReqForTestCases] = useState<string | undefined>();
  const [defectSeed, setDefectSeed] = useState<string | undefined>();

  const render = () => {
    switch (page) {
      case 'requirements':
        return <RequirementsPage onSendToTestCases={(id) => { setReqForTestCases(id); setPage('testcases'); }} />;
      case 'testcases': return <TestCasesPage initialRequirementId={reqForTestCases} />;
      case 'automation': return <AutomationPage onAnalyzeDefect={(id) => { setDefectSeed(id); setPage('defects'); }} />;
      case 'data-driven': return <DataDrivenPage onAnalyzeDefect={(id) => { setDefectSeed(id); setPage('defects'); }} />;
      case 'defects': return <DefectsPage seedResultId={defectSeed} />;
      case 'reports': return <ReportsPage />;
      case 'documentation': return <DocumentationPage />;
      case 'governance': return <GovernancePage />;
      case 'settings': return <SettingsPage />;
      default: return <OverviewPage onNavigate={setPage} />;
    }
  };
  return <AppLayout currentPage={page} onNavigate={setPage}>{render()}</AppLayout>;
}
export default App;
