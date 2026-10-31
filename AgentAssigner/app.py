"""FastAPI service: accepts a bug when the user clicks the tick mark and hands it to the LLM agent."""
import logging
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse

import store
from agent import AgentError, create_agent, default_guidance
from callback import notify_callback
from logs import fetch_logs
from models import (
    AcceptRequest,
    Investigation,
    InvestigationStatus,
    InvestigationSummary,
    settings,
    utcnow,
)
from report import build_report, save_report

logger = logging.getLogger(__name__)

ACTIVE = {InvestigationStatus.QUEUED, InvestigationStatus.IN_PROGRESS}


def log_event(inv: Investigation, event: str) -> None:
    inv.audit.append({"at": utcnow().isoformat(), "event": event})


def summarize(inv: Investigation) -> InvestigationSummary:
    success = None
    if inv.status not in ACTIVE:
        success = inv.status == InvestigationStatus.SUCCESS
    return InvestigationSummary(
        bug_id=inv.bug_id,
        status=inv.status,
        message=inv.message,
        success=success,
        root_cause=inv.analysis.root_cause.summary if inv.analysis else None,
        confidence=inv.analysis.root_cause.confidence if inv.analysis else None,
    )


async def run_investigation(app: FastAPI, inv: Investigation) -> None:
    agent = app.state.agent
    inv.status = InvestigationStatus.IN_PROGRESS
    inv.message = "Agent is debugging the issue"
    inv.started_at = utcnow()
    inv.model = agent.model
    log_event(inv, "Investigation started by LLM agent")
    try:
        try:
            inv.investigation_prompt = await agent.recommend_prompt(inv.request)
            log_event(inv, "Agent recommended an investigation prompt for this issue")
        except AgentError as exc:
            inv.investigation_prompt = default_guidance(inv.request)
            log_event(inv, f"Prompt recommendation failed ({exc}); using default prompt")

        logs = await fetch_logs(inv.request)
        inv.log_source, inv.log_line_count = logs.source, len(logs.lines)
        log_event(inv, f"Collected {len(logs.lines)} log lines from: {logs.source}")
        for note in logs.notes:
            log_event(inv, f"Log note: {note}")

        inv.analysis = await agent.investigate(inv.request, logs.lines, inv.investigation_prompt)
        confidence = inv.analysis.root_cause.confidence
        log_event(inv, f"Root cause identified: {inv.analysis.root_cause.summary} ({confidence:.0%})")
        if confidence >= settings.success_confidence_threshold:
            inv.status = InvestigationStatus.SUCCESS
            inv.message = "Issue debugged successfully"
        else:
            inv.status = InvestigationStatus.NEEDS_REVIEW
            inv.message = "Analysis completed with low confidence; engineer review needed"
    except AgentError as exc:
        inv.status = InvestigationStatus.FAILED
        inv.error = str(exc)
        inv.message = "Agent could not complete the investigation"
        log_event(inv, f"Investigation failed: {exc}")
    except Exception as exc:
        logger.exception("Unexpected error investigating %s", inv.bug_id)
        inv.status = InvestigationStatus.FAILED
        inv.error = f"Unexpected error: {exc}"
        inv.message = "Agent could not complete the investigation"
        log_event(inv, f"Unexpected failure: {exc}")
    finally:
        inv.completed_at = utcnow()
        log_event(inv, f"Investigation finished with status {inv.status.value}")
        inv.report_markdown = build_report(inv)
        try:
            save_report(inv)
        except OSError:
            logger.exception("Could not save report for %s", inv.bug_id)
        store.save(inv)
        outcome = await notify_callback(summarize(inv))
        if settings.callback_url:
            log_event(inv, f"Backend notification: {outcome}")
            store.save(inv)


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Service-to-service auth: enforced only when SERVICE_API_KEY is configured."""
    expected = settings.service_api_key
    if expected and not secrets.compare_digest(x_api_key or "", expected):
        raise HTTPException(401, "Missing or invalid X-API-Key")


def create_app(agent=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.agent = agent or create_agent()
        app.state.investigations = store.load_all()
        yield

    app = FastAPI(title="Incident War Room - AI Agent Service", version="1.0.0", lifespan=lifespan)
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")]
    app.add_middleware(
        CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"]
    )
    secured = [Depends(require_api_key)]

    def get_inv(bug_id: str) -> Investigation:
        inv = app.state.investigations.get(bug_id)
        if inv is None:
            raise HTTPException(404, f"No investigation found for bug '{bug_id}'")
        return inv

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse("/docs")

    @app.get("/health")
    async def health():
        """Liveness probe: the process is up."""
        return {"status": "ok", "provider": settings.llm_provider, "model": app.state.agent.model}

    @app.get("/ready")
    async def ready(response: Response):
        """Readiness probe: the service can actually run investigations."""
        key_set = bool(
            settings.anthropic_api_key if settings.llm_provider == "anthropic" else settings.gemini_api_key
        )
        checks = {
            "llm_api_key": key_set,
            "log_source_configured": bool(settings.log_api_url or settings.log_file_path),
            "callback_configured": bool(settings.callback_url),
        }
        if not key_set:
            response.status_code = 503
        return {"ready": key_set, "checks": checks}

    @app.post(
        "/api/investigations", response_model=InvestigationSummary, status_code=202, dependencies=secured
    )
    async def accept_bug(req: AcceptRequest, background: BackgroundTasks, response: Response):
        """Tick mark clicked: assign the bug to the LLM agent."""
        existing = app.state.investigations.get(req.bug_id)
        if existing and existing.status in ACTIVE:
            response.status_code = 200
            return summarize(existing)
        inv = Investigation(bug_id=req.bug_id, request=req)
        log_event(inv, "Bug accepted by user and assigned to LLM agent")
        app.state.investigations[req.bug_id] = inv
        store.save(inv)
        background.add_task(run_investigation, app, inv)
        return summarize(inv)

    @app.get("/api/investigations/{bug_id}", response_model=InvestigationSummary, dependencies=secured)
    async def get_status(bug_id: str):
        """Polled by the dashboard to display success / failure."""
        return summarize(get_inv(bug_id))

    @app.get("/api/investigations/{bug_id}/details", response_model=Investigation, dependencies=secured)
    async def get_details(bug_id: str):
        return get_inv(bug_id)

    @app.get(
        "/api/investigations/{bug_id}/report", response_class=PlainTextResponse, dependencies=secured
    )
    async def get_report(bug_id: str):
        inv = get_inv(bug_id)
        if inv.status in ACTIVE or inv.report_markdown is None:
            raise HTTPException(409, "Report not ready yet")
        return PlainTextResponse(inv.report_markdown, media_type="text/markdown")

    return app


app = create_app()
