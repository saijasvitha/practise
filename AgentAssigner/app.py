"""FastAPI service: accepts a bug when the user clicks the tick mark and hands it to the LLM agent."""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse

from agent import AgentError, DebugAgent
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
    agent: DebugAgent = app.state.agent
    inv.status = InvestigationStatus.IN_PROGRESS
    inv.message = "Agent is debugging the issue"
    inv.started_at = utcnow()
    inv.model = agent.model
    log_event(inv, "Investigation started by LLM agent")
    try:
        inv.analysis = await agent.investigate(inv.request)
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


def create_app(agent: DebugAgent | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.agent = agent or DebugAgent()
        app.state.investigations = {}
        yield

    app = FastAPI(title="Incident War Room - AI Agent Service", version="1.0.0", lifespan=lifespan)
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")]
    app.add_middleware(
        CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"]
    )

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
        return {"status": "ok", "model": app.state.agent.model}

    @app.post("/api/investigations", response_model=InvestigationSummary, status_code=202)
    async def accept_bug(req: AcceptRequest, background: BackgroundTasks, response: Response):
        """Tick mark clicked: assign the bug to the LLM agent."""
        existing = app.state.investigations.get(req.bug_id)
        if existing and existing.status in ACTIVE:
            response.status_code = 200
            return summarize(existing)
        inv = Investigation(bug_id=req.bug_id, request=req)
        log_event(inv, "Bug accepted by user and assigned to LLM agent")
        app.state.investigations[req.bug_id] = inv
        background.add_task(run_investigation, app, inv)
        return summarize(inv)

    @app.get("/api/investigations/{bug_id}", response_model=InvestigationSummary)
    async def get_status(bug_id: str):
        """Polled by the dashboard to display success / failure."""
        return summarize(get_inv(bug_id))

    @app.get("/api/investigations/{bug_id}/details", response_model=Investigation)
    async def get_details(bug_id: str):
        return get_inv(bug_id)

    @app.get("/api/investigations/{bug_id}/report", response_class=PlainTextResponse)
    async def get_report(bug_id: str):
        inv = get_inv(bug_id)
        if inv.status in ACTIVE or inv.report_markdown is None:
            raise HTTPException(409, "Report not ready yet")
        return PlainTextResponse(inv.report_markdown, media_type="text/markdown")

    return app


app = create_app()
