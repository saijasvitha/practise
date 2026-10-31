"""Shared settings and data models for the Incident War Room AI service."""
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini").lower()  # gemini | anthropic
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    # Tried in order when the primary model keeps returning 429/5xx
    gemini_fallback_models: list[str] = [
        m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash-lite,gemini-flash-lite-latest").split(",") if m.strip()
    ]
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    success_confidence_threshold: float = float(os.getenv("SUCCESS_CONFIDENCE_THRESHOLD", "0.6"))
    reports_dir: str = os.getenv("REPORTS_DIR", "reports")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "90"))
    # e.g. http://localhost:9000/logs?service={service}; {service} and {bug_id} are filled in
    log_api_url: str = os.getenv("LOG_API_URL", "")
    log_file_path: str = os.getenv("LOG_FILE_PATH", "")  # file, or a folder (newest .log/.txt is used)
    log_max_lines: int = int(os.getenv("LOG_MAX_LINES", "200"))
    log_timeout_seconds: float = float(os.getenv("LOG_TIMEOUT_SECONDS", "10"))
    # Microservice integration
    service_api_key: str = os.getenv("SERVICE_API_KEY", "")  # if set, callers must send X-API-Key
    callback_url: str = os.getenv("CALLBACK_URL", "")  # backend endpoint notified when an investigation ends
    callback_api_key: str = os.getenv("CALLBACK_API_KEY", "")
    # Central incident service (Spring Boot), e.g. http://localhost:8080 ; used for GET /api/incidents/{id}
    central_url: str = os.getenv("CENTRAL_API_URL", "").rstrip("/")
    # After an investigation: SUCCESS -> POST approve, FAILED -> POST reject on the central service
    central_push_status: bool = os.getenv("CENTRAL_PUSH_STATUS", "true").lower() in ("1", "true", "yes")
    data_dir: str = os.getenv("DATA_DIR", "data")  # investigations are persisted here


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
    # Optional when CENTRAL_API_URL is set: it is then fetched from GET /api/incidents/{bug_id}
    description: Optional[str] = Field(default=None, min_length=1)
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
    model_used: Optional[str] = None  # set by the service, not by the LLM


class Investigation(BaseModel):
    bug_id: str
    request: AcceptRequest
    status: InvestigationStatus = InvestigationStatus.QUEUED
    message: str = "Investigation queued"
    model: Optional[str] = None
    investigation_prompt: Optional[str] = None
    log_source: Optional[str] = None
    log_line_count: int = 0
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
