import { Inbox } from "lucide-react";
import IssueRow from "./IssueRow.jsx";
export default function IssueTable({
  issues,
  loading,
  error,
  onSelect,
  onAccept,
  onReject,
}) {
  if (loading) return <div className="table-state">Loading incidents…</div>;
  if (error) return <div className="table-state">{error}</div>;
  if (!issues.length)
    return (
      <div className="table-state">
        <Inbox />
        <strong>No incidents found</strong>
      </div>
    );
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {[
              "Issue ID",
              "Issue title",
              "Description",
              "Service",
              "Severity",
              "Environment",
              "Timestamp",
              "Status",
              "Actions",
            ].map((x) => (
              <th key={x}>{x}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {issues.map((issue) => (
            <IssueRow
              key={issue.id}
              {...{ issue, onSelect, onAccept, onReject }}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
