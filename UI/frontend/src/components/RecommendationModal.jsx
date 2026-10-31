import { useState } from "react";
import { AlertTriangle, CheckCircle2, X } from "lucide-react";
import "../recommendation.css";

export default function RecommendationModal({
  issue,
  recommendation,
  onClose,
  onRecheck,
}) {
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState("");
  if (!issue) return null;

  async function recheck() {
    setChecking(true);
    const response = await onRecheck(issue.id);
    setResult(
      response.verified
        ? "Mock verification passed. The incident is marked resolved in this demo."
        : "Mock verification could not confirm the fix.",
    );
    setChecking(false);
  }

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <section
        className="modal-card recommendation-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="recommendation-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button
          className="icon-button modal-close"
          onClick={onClose}
          aria-label="Close"
        >
          <X />
        </button>
        <div className="eyebrow">Developer-led resolution · {issue.id}</div>
        <h2 id="recommendation-title">AI investigation notes</h2>
        <p className="modal-description">
          Mock recommendations for <b>{issue.title}</b>.
        </p>
        <div className="recommendation-highlight">
          <div>
            <small>Probable root cause</small>
            <strong>{recommendation.cause}</strong>
          </div>
          <span className="confidence">
            {Math.round(recommendation.confidence * 100)}%
            <small>confidence</small>
          </span>
        </div>
        <p className="explanation">{recommendation.explanation}</p>
        <div className="recommendation-columns">
          <div className="recommendation-detail-card">
            <h3>Suggested debugging steps</h3>
            <ol>
              {recommendation.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
          <div className="recommendation-detail-card action-callout">
            <h3>Recommended action</h3>
            <p>{recommendation.action}</p>
            <span className={"risk " + recommendation.risk.toLowerCase()}>
              <AlertTriangle size={13} /> {recommendation.risk} risk
            </span>
          </div>
        </div>
        <div className="source-note">
          Source location unavailable · No source code was supplied.
        </div>
        {result && (
          <div className="verification-result">
            <CheckCircle2 size={16} />
            {result}
          </div>
        )}
        <div className="modal-footer">
          <button className="button button-secondary" onClick={onClose}>
            Close
          </button>
          <button
            className="button button-primary"
            disabled={checking}
            onClick={recheck}
          >
            {checking ? "Checking…" : "I’ve Fixed It — Recheck"}
          </button>
        </div>
        <div className="mock-label">Demo only · local mock verification</div>
      </section>
    </div>
  );
}
