"""Shared settings and data models for the Incident War Room AI service."""
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings:
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    success_confidence_threshold: float = float(os.getenv("SUCCESS_CONFIDENCE_THRESHOLD", "0.6"))
    reports_dir: str = os.getenv("REPORTS_DIR", "reports")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "90"))


settings = Settings()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InvestigationStatus(str, Enum):
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"  # root cause found with enough confidence
    NEEDS_REVIEW = "NEEDS_REVIEW"  # analysis done but confidence too low
    FAILED = "FAILED"  # the agent could not complete (LLM/API error)


class SimilarIncident(BaseModel):
    """Historical incident supplied by the RAG service."""
    incident_id: str
    description: str
    resolution: Optional[str] = None
    similarity: Optional[float] = None


class AcceptRequest(BaseModel):
    """Payload sent when the user clicks the tick mark on a bug."""
    bug_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    service: Optional[str] = None
    severity: Optional[str] = None
    logs: list[str] = Field(default_factory=list)
    similar_incidents: list[SimilarIncident] = Field(default_factory=list)


class RemediationStep(BaseModel):
    action: str
    type: str = "corrective"  # corrective | preventive
    requires_approval: bool = True


class RootCause(BaseModel):
    summary: str
    explanation: str
    confidence: float = Field(ge=0, le=1)


class Analysis(BaseModel):
    """Structured result produced by the LLM agent."""
    root_cause: RootCause
    evidence: list[str] = Field(default_factory=list)
    remediation: list[RemediationStep] = Field(default_factory=list)
    stakeholder_summary: str = ""
    kb_article_title: str = ""


class Investigation(BaseModel):
    bug_id: str
    request: AcceptRequest
    status: InvestigationStatus = InvestigationStatus.QUEUED
    message: str = "Investigation queued"
    model: Optional[str] = None
    analysis: Optional[Analysis] = None
    error: Optional[str] = None
    report_markdown: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    audit: list[dict] = Field(default_factory=list)


class InvestigationSummary(BaseModel):
    """What the dashboard needs to show success/failure to the user."""
    bug_id: str
    status: InvestigationStatus
    message: str
    success: Optional[bool] = None
    root_cause: Optional[str] = None
    confidence: Optional[float] = None
