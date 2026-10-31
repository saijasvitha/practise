import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import SeverityBadge from './SeverityBadge.jsx';

function DetailValue({ value }) {
  return <span>{value || 'Unavailable'}</span>;
}

export default function IssueDetailsModal({ issue, onClose, onLoadDetails, mockMode }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!issue) {
      setDetails(null);
      return undefined;
    }

    let stillOpen = true;
    setDetails(null);
    setLoading(true);
    setError('');
    onLoadDetails(issue)
      .then((result) => { if (stillOpen) setDetails(result); })
      .catch((requestError) => { if (stillOpen) setError(requestError.message || 'Could not load incident details.'); })
      .finally(() => { if (stillOpen) setLoading(false); });

    return () => { stillOpen = false; };
  }, [issue, onLoadDetails]);

  if (!issue) return null;
  const record = details || issue;

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="incident-details-title" onMouseDown={(event) => event.stopPropagation()}>
        <button className="icon-button modal-close" onClick={onClose} aria-label="Close details"><X /></button>
        <div className="eyebrow">Incident details · {record.id}</div>
        <h2 id="incident-details-title">{record.title || 'Title unavailable'}</h2>

        {loading && <div className="modal-state">Loading incident details…</div>}
        {error && <div className="modal-state error-state">{error}</div>}
        {!loading && !error && (
          <>
            <p className="modal-description">{record.description || 'Description unavailable.'}</p>
            <div className="details-grid">
              <div className="detail-item"><small>Service</small><DetailValue value={record.service} /></div>
              <div className="detail-item"><small>Severity</small><span><SeverityBadge value={record.severity || 'Unavailable'} /></span></div>
              <div className="detail-item"><small>Environment</small><DetailValue value={record.environment} /></div>
              <div className="detail-item"><small>Status</small><DetailValue value={record.status} /></div>
              <div className="detail-item"><small>Reported</small><DetailValue value={record.timestamp} /></div>
              <div className="detail-item"><small>Record ID</small><DetailValue value={record.backendId || record.id} /></div>
            </div>
            <div className="metadata-section">
              <h3>Additional metadata</h3>
              {record.metadata?.length
                ? <dl>{record.metadata.map(({ key, value }) => <div className="metadata-row" key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>
                : <p>No additional metadata was returned.</p>}
            </div>
            <div className="mock-label">{mockMode ? 'Demo details · local sample data' : 'Incident details returned by Spring Boot'}</div>
          </>
        )}

        <button className="button button-secondary modal-done" onClick={onClose}>Close details</button>
      </section>
    </div>
  );
}
