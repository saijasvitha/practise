import { Inbox } from 'lucide-react';
import IssueRow from './IssueRow.jsx';

export default function IssueTable({ issues, loading, error, emptyMessage, onSelect, onAccept, onReject, pendingAction, mockMode }) {
  if (loading && !issues.length) return <div className="table-state">Loading incidents…</div>;
  if (!issues.length) {
    return error
      ? <div className="table-state error-state">{error}</div>
      : <div className="table-state"><Inbox /><strong>{emptyMessage || 'No incidents available.'}</strong></div>;
  }

  return (
    <div className="table-scroll">
      {error && <div className="table-request-error" role="alert">{error} Previously loaded incidents are still shown.</div>}
      {loading && <div className="inline-loading">Refreshing incident list…</div>}
      <table>
        <thead><tr>{['Incident / event ID', 'Issue title', 'Description', 'Service', 'Severity', 'Environment', 'Timestamp', 'Status', 'Actions'].map((heading) => <th key={heading}>{heading}</th>)}</tr></thead>
        <tbody>
          {issues.map((issue, index) => (
            <IssueRow key={issue.backendId || issue.id || index} {...{ issue, onSelect, onAccept, onReject, pendingAction, mockMode }} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
