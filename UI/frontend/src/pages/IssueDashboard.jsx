import { useRef, useState } from 'react';
import { Activity, AlertCircle, CheckCircle2, ListFilter } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header.jsx';
import StatCard from '../components/StatCard.jsx';
import IssueTable from '../components/IssueTable.jsx';
import IssueFilters from '../components/IssueFilters.jsx';
import IssueDetailsModal from '../components/IssueDetailsModal.jsx';
import RecommendationModal from '../components/RecommendationModal.jsx';
import useIssues from '../hooks/useIssues.js';
import { filterIssues } from '../utils/issueFilters.js';
import { defaultRecommendation, recommendations } from '../mock/recommendations.js';
import { createMockWorkflow } from '../mock/workflows.js';
import '../dashboard-enhancements.css';

const initialFilters = { search: '', status: '', severity: '', service: '', environment: '' };

export default function IssueDashboard() {
  const { issues, loading, error, refresh, getDetails, approve, reject, recheck, mockMode } = useIssues();
  const navigate = useNavigate();
  const [selected, setSelected] = useState(null);
  const [rejected, setRejected] = useState(null);
  const [filters, setFilters] = useState(initialFilters);
  const [pendingAction, setPendingAction] = useState(null);
  const [notice, setNotice] = useState(null);
  const actionInFlight = useRef(false);
  const shown = filterIssues(issues, filters);

  async function performBackendAction(action, issue) {
    if (actionInFlight.current) return;
    actionInFlight.current = true;
    setPendingAction({ action, id: issue.backendId });
    setNotice(null);
    try {
      const result = action === 'approve' ? await approve(issue) : await reject(issue);
      const actionName = action === 'approve' ? 'Approve' : 'Reject';
      setNotice({
        kind: 'success',
        text: result.refreshed
          ? `${actionName} request completed successfully. The incident list was refreshed.`
          : `${actionName} request completed, but the list could not refresh. Use Refresh to try again.`,
      });
    } catch (actionError) {
      setNotice({ kind: 'error', text: actionError.message || 'The request could not be completed.' });
    } finally {
      actionInFlight.current = false;
      setPendingAction(null);
    }
  }

  function handleAccept(issue) {
    const message = mockMode
      ? `Start a mock AI-assisted resolution for ${issue.id}? This demonstrates a predefined safe simulated remediation; no production system will change.`
      : `Send an approval request for ${issue.id}? The backend response does not currently confirm that this starts an agent workflow.`;
    if (!window.confirm(message)) return;

    if (mockMode) {
      const run = createMockWorkflow(issue);
      sessionStorage.setItem(run.executionId, JSON.stringify(run.workflow));
      navigate('/agent/' + run.executionId);
      return;
    }
    performBackendAction('approve', issue);
  }

  function handleReject(issue) {
    const message = mockMode
      ? `Continue with developer-led resolution for ${issue.id} and view mock recommendations?`
      : `Send a rejection request for ${issue.id}? This will call the confirmed Spring Boot endpoint.`;
    if (!window.confirm(message)) return;

    if (mockMode) {
      setRejected(issue);
      return;
    }
    performBackendAction('reject', issue);
  }

  const stats = [
    ['Total issues', issues.length, ListFilter, 'blue', 'Across all services'],
    ['Critical issues', issues.filter((issue) => issue.severity.toLowerCase() === 'critical').length, AlertCircle, 'red', 'Needs immediate attention'],
    ['In progress', issues.filter((issue) => ['investigating', 'queued'].includes(issue.status.toLowerCase())).length, Activity, 'purple', 'Being investigated'],
    ['Resolved issues', issues.filter((issue) => issue.status.toLowerCase() === 'resolved').length, CheckCircle2, 'green', 'Successfully closed'],
  ];

  return (
    <div className="app-shell">
      <Header />
      <main className="dashboard-main">
        <div className="page-heading">
          <div>
            <div className="eyebrow">Operations / Overview</div>
            <h1>Issue dashboard</h1>
            <p>Monitor incoming incidents and choose how your team resolves them.</p>
          </div>
          <div className="updated-label"><i />{mockMode ? 'Mock mode · local demo data' : 'Spring Boot · manual refresh'}</div>
        </div>

        {notice && <div className={'dashboard-alert ' + notice.kind} role={notice.kind === 'error' ? 'alert' : 'status'}>{notice.text}</div>}

        <section className="stats-grid">
          {stats.map(([label, value, icon, tone, detail]) => (
            <StatCard key={label} {...{ label, value, icon, tone, detail }} />
          ))}
        </section>

        <section className="issues-panel">
          <div className="panel-heading">
            <div><h2>Incoming incidents</h2><p>Review incidents and select a resolution path.</p></div>
            <span className="count-pill">{shown.length} incidents</span>
          </div>
          <IssueFilters issues={issues} filters={filters} onChange={setFilters} onRefresh={refresh} refreshing={loading} />
          <IssueTable
            issues={shown}
            loading={loading}
            error={error}
            emptyMessage={issues.length ? 'No incidents match these filters.' : 'No incidents are available.'}
            onSelect={setSelected}
            onAccept={handleAccept}
            onReject={handleReject}
            pendingAction={pendingAction}
            mockMode={mockMode}
          />
          <footer className="table-footer">
            Showing {shown.length} of {issues.length} incidents
            <span><i />{mockMode ? 'Mock data' : 'Spring Boot API'}</span>
          </footer>
        </section>

        <div className="dashboard-note">
          <span>AI recommendations are informational and require developer review.</span>
          <span>IncidentIQ · Hackathon demo</span>
        </div>
      </main>
      <IssueDetailsModal issue={selected} onClose={() => setSelected(null)} onLoadDetails={getDetails} mockMode={mockMode} />
      <RecommendationModal
        issue={rejected}
        recommendation={recommendations[rejected?.id] || defaultRecommendation}
        onClose={() => setRejected(null)}
        onRecheck={recheck}
      />
    </div>
  );
}
