import SeverityBadge from './SeverityBadge.jsx';
import ResolutionActions from './ResolutionActions.jsx';

function cell(value) { return value || '—'; }

export default function IssueRow({ issue, onSelect, onAccept, onReject, pendingAction, mockMode }) {
  return (
    <tr className="issue-row" onClick={() => onSelect(issue)}>
      <td className="issue-id">{cell(issue.id)}</td>
      <td><button className="title-link" onClick={(event) => { event.stopPropagation(); onSelect(issue); }}>{cell(issue.title)}</button></td>
      <td className="description-cell">{cell(issue.description)}</td>
      <td>{cell(issue.service)}</td>
      <td><SeverityBadge value={issue.severity || 'Unavailable'} /></td>
      <td>{cell(issue.environment)}</td>
      <td>{cell(issue.timestamp)}</td>
      <td><span className={'status-badge ' + (issue.status || 'unknown').toLowerCase().replaceAll(' ', '-')}>{cell(issue.status)}</span></td>
      <td onClick={(event) => event.stopPropagation()}>
        <ResolutionActions {...{ issue, onAccept, onReject, pendingAction, mockMode }} />
      </td>
    </tr>
  );
}
