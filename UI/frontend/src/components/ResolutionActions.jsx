export default function ResolutionActions({ issue, onAccept, onReject, pendingAction, mockMode }) {
  const busy = pendingAction?.id === issue.backendId;
  const unavailable = !mockMode && !issue.backendId;

  return (
    <div className="action-buttons">
      <button className="button button-accept" onClick={() => onAccept(issue)} disabled={busy || Boolean(pendingAction) || unavailable} title={unavailable ? 'The backend incident ID is unavailable.' : undefined}>
        {busy && pendingAction.action === 'approve' ? 'Approving…' : 'Approve'}
      </button>
      <button className="button button-reject" onClick={() => onReject(issue)} disabled={busy || Boolean(pendingAction) || unavailable} title={unavailable ? 'The backend incident ID is unavailable.' : undefined}>
        {busy && pendingAction.action === 'reject' ? 'Rejecting…' : 'Reject'}
      </button>
    </div>
  );
}
