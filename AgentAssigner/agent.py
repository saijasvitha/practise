"""LLM debugging agent: sends a bug to Claude Sonnet and returns a structured analysis."""
import logging
from typing import Optional

from anthropic import AsyncAnthropic

from models import AcceptRequest, Analysis, settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are the debugging agent of an Incident War Room. Given a bug id, its description, "
    "optional logs and similar historical incidents, identify the most probable root cause, "
    "give an honest confidence score between 0 and 1, cite the evidence you relied on, and "
    "recommend corrective and preventive actions. Never claim certainty you do not have; if "
    "the input is insufficient, say so and lower the confidence. Remediation actions are only "
    "suggestions and always require engineer approval."
)

ANALYSIS_TOOL = {
    "name": "submit_analysis",
    "description": "Submit the final incident analysis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "root_cause": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "One-line probable root cause."},
                    "explanation": {"type": "string", "description": "Why this is the likely cause."},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["summary", "explanation", "confidence"],
            },
            "evidence": {"type": "array", "items": {"type": "string"}},
            "remediation": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "type": {"type": "string", "enum": ["corrective", "preventive"]},
                    },
                    "required": ["action", "type"],
                },
            },
            "stakeholder_summary": {
                "type": "string",
                "description": "Short non-technical status update for stakeholders.",
            },
            "kb_article_title": {"type": "string"},
        },
        "required": ["root_cause", "evidence", "remediation", "stakeholder_summary"],
    },
}


class AgentError(Exception):
    pass


def build_user_prompt(req: AcceptRequest) -> str:
    parts = [f"Bug ID: {req.bug_id}", f"Description: {req.description}"]
    if req.service:
        parts.append(f"Service: {req.service}")
    if req.severity:
        parts.append(f"Severity: {req.severity}")
    if req.logs:
        parts.append("Logs:\n" + "\n".join(req.logs[-200:]))
    if req.similar_incidents:
        lines = []
        for s in req.similar_incidents:
            line = f"- [{s.incident_id}] {s.description}"
            if s.resolution:
                line += f" | resolution: {s.resolution}"
            lines.append(line)
        parts.append("Similar historical incidents:\n" + "\n".join(lines))
    return "\n\n".join(parts)


class DebugAgent:
    def __init__(self, client: Optional[AsyncAnthropic] = None, model: Optional[str] = None):
        self.model = model or settings.anthropic_model
        self._client = client

    @property
    def client(self) -> AsyncAnthropic:
        if self._client is None:
            if not settings.anthropic_api_key:
                raise AgentError("ANTHROPIC_API_KEY is not configured")
            self._client = AsyncAnthropic(
                api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_seconds
            )
        return self._client

    async def investigate(self, req: AcceptRequest) -> Analysis:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=[ANALYSIS_TOOL],
                tool_choice={"type": "tool", "name": ANALYSIS_TOOL["name"]},
                messages=[{"role": "user", "content": build_user_prompt(req)}],
            )
        except AgentError:
            raise
        except Exception as exc:
            logger.exception("LLM call failed for bug %s", req.bug_id)
            raise AgentError(f"LLM call failed: {exc}") from exc

        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == ANALYSIS_TOOL["name"]:
                try:
                    return Analysis.model_validate(block.input)
                except Exception as exc:
                    raise AgentError(f"LLM returned an invalid analysis: {exc}") from exc
        raise AgentError("LLM did not return an analysis")
