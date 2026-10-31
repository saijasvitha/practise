"""Builds the final investigation report from an Investigation."""
from pathlib import Path

from models import Investigation, settings


def build_report(inv: Investigation) -> str:
    a = inv.analysis
    lines = [
        f"# Investigation Report - {inv.bug_id}",
        "",
        f"- **Status:** {inv.status.value}",
        f"- **Outcome:** {inv.message}",
        f"- **Model:** {inv.model or 'n/a'}",
        f"- **Service:** {inv.request.service or 'n/a'}",
        f"- **Severity:** {inv.request.severity or 'n/a'}",
        f"- **Started:** {inv.started_at.isoformat() if inv.started_at else 'n/a'}",
        f"- **Completed:** {inv.completed_at.isoformat() if inv.completed_at else 'n/a'}",
        "",
        "## Incident",
        inv.request.description,
        "",
    ]
    if a is None:
        lines += ["## Error", inv.error or "Investigation did not produce an analysis.", ""]
    else:
        lines += [
            "## Probable Root Cause",
            f"**{a.root_cause.summary}** (confidence: {a.root_cause.confidence:.0%})",
            "",
            a.root_cause.explanation,
            "",
            "## Evidence",
            *([f"- {e}" for e in a.evidence] or ["- None provided"]),
            "",
            "## Recommended Remediation (requires engineer approval)",
            *([f"- [{r.type}] {r.action}" for r in a.remediation] or ["- None provided"]),
            "",
            "## Stakeholder Summary",
            a.stakeholder_summary or "n/a",
            "",
        ]
        if a.kb_article_title:
            lines += ["## Suggested Knowledge-Base Article", a.kb_article_title, ""]
    if inv.request.similar_incidents:
        lines += ["## Similar Historical Incidents"]
        lines += [f"- {s.incident_id}: {s.description}" for s in inv.request.similar_incidents]
        lines.append("")
    lines += ["## Audit Trail"] + [f"- {e['at']} - {e['event']}" for e in inv.audit]
    return "\n".join(lines) + "\n"


def save_report(inv: Investigation) -> Path:
    out_dir = Path(settings.reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in inv.bug_id)
    path = out_dir / f"{safe_id}.md"
    path.write_text(inv.report_markdown or "", encoding="utf-8")
    return path
