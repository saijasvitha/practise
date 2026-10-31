import { useState } from 'react';
import { Activity, AlertCircle, CheckCircle2, ListFilter, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header.jsx';
import StatCard from '../components/StatCard.jsx';
import IssueTable from '../components/IssueTable.jsx';
import IssueDetailsModal from '../components/IssueDetailsModal.jsx';
import RecommendationModal from '../components/RecommendationModal.jsx';
import useIssues from '../hooks/useIssues.js';
import { defaultRecommendation, recommendations } from '../mock/recommendations.js';
import { createMockWorkflow } from '../mock/workflows.js';

export default function IssueDashboard() {
  const { issues, loading, error, recheck } = useIssues();
  const navigate = useNavigate();
  const [selected, setSelected] = useState(null);
  const [rejected, setRejected] = useState(null);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('Open issues');

  // Keep resolved incidents out of the default view, while allowing users to select them explicitly.
  const shown = issues.filter((issue) => {
    const matchesSearch = `${issue.id} ${issue.title} ${issue.service}`.toLowerCase().includes(query.toLowerCase());
    const matchesStatus = filter === 'Open issues'
      ? issue.status !== 'Resolved'
      : issue.status === filter;
    return matchesSearch && matchesStatus;
  });

  const accept = (issue) => {
    if (window.confirm(`Start mock AI-assisted resolution for ${issue.id}? A predefined safe simulated remediation will be demonstrated. No production system will be changed.`)) {
      const run = createMockWorkflow(issue);
      sessionStorage.setItem(run.executionId, JSON.stringify(run.workflow));
      navigate('/agent/' + run.executionId);
    }
  };

  const stats = [
    ['Total issues', issues.length, ListFilter, 'blue', 'Across all services'],
    ['Critical issues', issues.filter((issue) => issue.severity === 'Critical').length, AlertCircle, 'red', 'Needs immediate attention'],
    ['In progress', issues.filter((issue) => ['Investigating', 'Queued'].includes(issue.status)).length, Activity, 'purple', 'Being investigated'],
    ['Resolved issues', issues.filter((issue) => issue.status === 'Resolved').length, CheckCircle2, 'green', 'Successfully closed'],
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
          <div className="updated-label"><i />Mock incident feed · Updated just now</div>
        </div>

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
          <div className="table-toolbar">
            <label className="search-box">
              <Search size={16} />
              <input placeholder="Search issues or services…" value={query} onChange={(event) => setQuery(event.target.value)} />
            </label>
            <label className="filter-select">
              <select value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter incidents by status">
                <option>Open issues</option>
                {['New', 'Queued', 'Investigating', 'Awaiting Developer', 'Resolved', 'Failed'].map((status) => <option key={status}>{status}</option>)}
              </select>
            </label>
          </div>
          <IssueTable issues={shown} {...{ loading, error }} onSelect={setSelected} onAccept={accept} onReject={setRejected} />
          <footer className="table-footer">
            Showing {shown.length} of {issues.length} incidents <span><i />Demo data</span>
          </footer>
        </section>

        <div className="dashboard-note">
          <span>AI recommendations are informational and require developer review.</span>
          <span>IncidentIQ · Hackathon demo</span>
        </div>
      </main>
      <IssueDetailsModal issue={selected} onClose={() => setSelected(null)} />
      <RecommendationModal
        issue={rejected}
        recommendation={recommendations[rejected?.id] || defaultRecommendation}
        onClose={() => setRejected(null)}
        onRecheck={recheck}
      />
    </div>
  );
}
