# AgentAssigner – AI investigation service (Member 4)

FastAPI service that takes a bug the user **accepts (tick mark)**, assigns it to an LLM debugging agent, and produces the final investigation report. The LLM is **Google Gemini (free tier)** by default, with Claude Sonnet available as an option.

## Run
```powershell
python -m venv .venv; .\.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env   # set GEMINI_API_KEY (free key: https://aistudio.google.com/apikey)
.\.venv\Scripts\python -m uvicorn app:app --reload --port 8000
.\.venv\Scripts\python -m pytest -q
```
Swagger UI: http://localhost:8000/docs. `GET /health` shows the active provider and model.

To use Claude instead, set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` in `.env`.

## How an investigation runs
1. **Prompt recommendation:** the LLM writes a focused investigation prompt from the bug (shown in `details` and the report). If this step fails, a default prompt is used.
2. **Log collection (`logs.py`):** logs come from the REST endpoint `LOG_API_URL`; if it is unavailable or empty, from `LOG_FILE_PATH` (a file, or a folder whose newest `.log`/`.txt` is used, filtered to the bug id/service when possible). Logs sent in the POST body are added on top. The last `LOG_MAX_LINES` lines are used.
3. **Analysis:** the LLM gets the issue, the recommended prompt and the logs, and returns the root cause, evidence quoting log lines, and a recommended fix.

The log endpoint may return a JSON list, a JSON object wrapping a list (`logs`, `data`, `items`, ...) or plain text. `{service}` and `{bug_id}` in `LOG_API_URL` are replaced per bug.

## Running as a microservice
This service is self-contained: it owns its own state, talks to others only over HTTP, and is configured entirely through environment variables.

```powershell
copy .env.example .env      # fill in GEMINI_API_KEY etc.
docker compose up --build   # http://localhost:8000, data persisted in Docker volumes
```

| Concern | How |
|---|---|
| Probes | `GET /health` (liveness) and `GET /ready` (readiness: 503 until the LLM key is configured) |
| Auth between services | Set `SERVICE_API_KEY`; callers then send header `X-API-Key: <key>` on every `/api` call |
| Results pushed to the backend | Set `CALLBACK_URL` (e.g. the Spring Boot incident backend). When an investigation ends, the service POSTs `{bug_id, status, success, message, root_cause, confidence}` there (3 attempts; sends `X-API-Key: CALLBACK_API_KEY` if set). Failures never break the investigation. |
| Logs from the log simulator | `LOG_API_URL` (REST) with `LOG_FILE_PATH` as fallback |
| Browser callers | `CORS_ORIGINS` |
| State | Investigations are saved as JSON in `DATA_DIR` and reloaded on start; any run interrupted by a restart is marked `FAILED` so it can be re-run |
| Contract for other teams | `GET /openapi.json` (also browsable at `/docs`) |

Typical wiring: dashboard -> incident backend -> `POST /api/investigations` on this service -> backend receives the callback (or polls `GET /api/investigations/{bug_id}`) and shows success/failure.

## API
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/investigations` | Tick mark clicked. Body: `bug_id`, `description` (required); optional `service`, `severity`, `logs[]`, `similar_incidents[]` (from the RAG service). Returns 202 immediately. |
| GET | `/api/investigations/{bug_id}` | Poll for result: `status`, `success`, `message`, `root_cause`, `confidence`. |
| GET | `/api/investigations/{bug_id}/details` | Full analysis, evidence, remediation and audit trail. |
| GET | `/api/investigations/{bug_id}/report` | Final investigation report (Markdown). Also saved to `reports/<bug_id>.md`. |

Status values: `QUEUED`, `IN_PROGRESS`, `SUCCESS` (show "success" to the user), `NEEDS_REVIEW` (confidence below `SUCCESS_CONFIDENCE_THRESHOLD`), `FAILED` (LLM/API error).

## Files
- `app.py` – FastAPI routes and background investigation flow
- `agent.py` – `GeminiAgent` (REST, free tier) and `DebugAgent` (Claude Sonnet); `create_agent()` picks one via `LLM_PROVIDER`
- `callback.py` – notifies the backend when an investigation finishes
- `store.py` – persists investigations to disk
- `Dockerfile`, `docker-compose.yml` – container packaging
- `logs.py` – fetches logs from the log REST API, falling back to a local file
- `report.py` – final report builder/saver
- `models.py` – settings and Pydantic models
- `test_app.py` – tests with a fake LLM client (no API key needed)

Notes: investigations are stored in memory (lost on restart); reports are persisted to disk. Remediation steps are suggestions only and require engineer approval.
