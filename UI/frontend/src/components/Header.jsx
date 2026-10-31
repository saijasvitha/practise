import { Activity, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
export default function Header({ agentStatus = "Idle", backLink = false }) {
  return (
    <header className="topbar">
      <Link to="/issues" className="brand">
        <span className="brand-mark">
          <ShieldCheck size={20} />
        </span>
        <span>
          <strong>IncidentIQ</strong>
          <small>AI-Powered Incident Management</small>
        </span>
      </Link>
      <div className="topbar-right">
        {backLink && (
          <Link className="back-link" to="/issues">
            ← Back to dashboard
          </Link>
        )}
        <span className="agent-pill">
          <i className={agentStatus === "Working" ? "working" : ""} />
          <Activity size={15} />
          {agentStatus === "Working" ? "Agent working" : "Agent idle"}
        </span>
        <span className="avatar">JD</span>
      </div>
    </header>
  );
}
