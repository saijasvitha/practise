export default function ResolutionActions({ issue, onAccept, onReject }) {
  return (
    <div className="action-buttons">
      <button className="button button-accept" onClick={() => onAccept(issue)}>
        Accept
      </button>
      <button className="button button-reject" onClick={() => onReject(issue)}>
        Reject
      </button>
    </div>
  );
}
