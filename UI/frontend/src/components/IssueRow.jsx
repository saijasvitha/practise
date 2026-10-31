import SeverityBadge from "./SeverityBadge.jsx";
import ResolutionActions from "./ResolutionActions.jsx";
export default function IssueRow({ issue, onSelect, onAccept, onReject }) {
  return (
    <tr className="issue-row" onClick={() => onSelect(issue)}>
      <td className="issue-id">{issue.id}</td>
      <td>
        <button
          className="title-link"
          onClick={(e) => {
            e.stopPropagation();
            onSelect(issue);
          }}
        >
          {issue.title}
        </button>
      </td>
      <td className="description-cell">{issue.description}</td>
      <td>{issue.service}</td>
      <td>
        <SeverityBadge value={issue.severity} />
      </td>
      <td>{issue.environment}</td>
      <td>{issue.timestamp}</td>
      <td>
        <span
          className={
            "status-badge " + issue.status.toLowerCase().replaceAll(" ", "-")
          }
        >
          {issue.status}
        </span>
      </td>
      <td onClick={(e) => e.stopPropagation()}>
        <ResolutionActions
          issue={issue}
          onAccept={onAccept}
          onReject={onReject}
        />
      </td>
    </tr>
  );
}
