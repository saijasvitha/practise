import { X } from "lucide-react";
import SeverityBadge from "./SeverityBadge.jsx";
export default function IssueDetailsModal({ issue, onClose }) {
  if (!issue) return null;
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <section
        className="modal-card"
        role="dialog"
        aria-modal="true"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <button className="icon-button modal-close" onClick={onClose}>
          <X />
        </button>
        <div className="eyebrow">Incident details · {issue.id}</div>
        <h2>{issue.title}</h2>
        <p className="modal-description">{issue.description}</p>
        <div className="details-grid">
          {[
            ["Service", issue.service],
            ["Severity", <SeverityBadge value={issue.severity} />],
            ["Environment", issue.environment],
            ["Status", issue.status],
            ["Reported", issue.timestamp],
            ["Source", "Source location unavailable"],
          ].map(([k, v]) => (
            <div className="detail-item" key={k}>
              <small>{k}</small>
              <span>{v}</span>
            </div>
          ))}
        </div>
        <button
          className="button button-secondary modal-done"
          onClick={onClose}
        >
          Close details
        </button>
      </section>
    </div>
  );
}
