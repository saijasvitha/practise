# AgentAssigner – AI investigation service (Member 4)

FastAPI service that takes a bug the user **accepts (tick mark)**, assigns it to a Claude Sonnet debugging agent, and produces the final investigation report.

## Run
```powershell
python -m venv .venv; .\.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env   # set ANTHROPIC_API_KEY (optionally ANTHROPIC_MODEL)
.\.venv\Scripts\python -m uvicorn app:app --reload --port 8000
.\.venv\Scripts\python -m pytest -q
```
Swagger UI: http://localhost:8000/docs

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
- `agent.py` – Anthropic Sonnet agent (forced tool call returns structured analysis)
- `report.py` – final report builder/saver
- `models.py` – settings and Pydantic models
- `test_app.py` – tests with a fake LLM client (no API key needed)

Notes: investigations are stored in memory (lost on restart); reports are persisted to disk. Remediation steps are suggestions only and require engineer approval.
