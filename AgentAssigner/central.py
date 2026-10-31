"""Client for the central incident service (Spring Boot, GET /api/incidents/{id})."""
import json
import logging
from typing import Optional
from urllib.parse import quote

import httpx

from models import settings

logger = logging.getLogger(__name__)

# The incident document's field names are not fixed, so several common spellings are accepted.
FIELD_ALIASES = {
    "description": ("description", "bugDescription", "bug_description", "message", "summary", "title", "errorMessage"),
    "service": ("service", "serviceName", "service_name", "source"),
    "severity": ("severity", "priority", "level"),
    "logs": ("logs", "logLines", "log_lines", "logMessages", "log", "stackTrace"),
}
MAX_LINE_CHARS = 500


# Turns a logs value (string, list, or mixed items) into a clean list of non-empty, length-capped lines.
def _logs_to_lines(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = value.splitlines()
    if not isinstance(value, list):
        value = [value]
    lines = []
    for item in value:
        text = item if isinstance(item, str) else json.dumps(item, default=str)
        if text.strip():
            lines.append(text.strip()[:MAX_LINE_CHARS])
    return lines


# Maps an incident document with varying field names to description/service/severity/logs;
# falls back to the raw JSON as the description if none is found.
def normalize_incident(doc: dict) -> dict:
    out: dict = {}
    for target, aliases in FIELD_ALIASES.items():
        value = next((doc[a] for a in aliases if doc.get(a) not in (None, "", [])), None)
        if value is None:
            continue
        out[target] = _logs_to_lines(value) if target == "logs" else str(value)
    if "description" not in out:  # unknown schema: still give the AI the raw incident
        out["description"] = json.dumps(doc, default=str)[:1000]
    return out


# Checks whether the central service is reachable, for the readiness endpoint.
async def ping_central(http: Optional[httpx.AsyncClient] = None) -> tuple[bool, str]:
    """Checks that the central service answers on GET /api/incidents. Never raises."""
    url = f"{settings.central_url}/api/incidents"
    client = http or httpx.AsyncClient(timeout=3)
    try:
        resp = await client.get(url)
        return resp.status_code < 500, f"GET {url} -> HTTP {resp.status_code}"
    except Exception as exc:
        return False, f"GET {url} failed: {exc!r}"
    finally:
        if http is None:
            await client.aclose()


# Tells the central service to approve or reject the incident, retrying once on server errors.
async def push_status(bug_id: str, action: str, http: Optional[httpx.AsyncClient] = None) -> str:
    """POSTs approve/reject for the incident on the central service. Never raises."""
    assert action in ("approve", "reject")
    url = f"{settings.central_url}/api/incidents/{quote(bug_id, safe='')}/{action}"
    # Lets the central service recognise this call came from the AI agent and not call back into it
    headers = {"X-Initiated-By": "ai-agent"}
    client = http or httpx.AsyncClient(timeout=10)
    last_error = ""
    try:
        for attempt in range(2):
            try:
                resp = await client.post(url, headers=headers)
                if resp.status_code < 300:
                    return f"central {action} succeeded (HTTP {resp.status_code})"
                last_error = f"HTTP {resp.status_code}"
                if resp.status_code < 500:
                    break  # client error: retrying will not help
            except httpx.HTTPError as exc:
                last_error = repr(exc)
    finally:
        if http is None:
            await client.aclose()
    logger.warning("Central %s failed for %s: %s", action, bug_id, last_error)
    return f"central {action} failed: {last_error}"


# Downloads the incident from the central service and returns its normalized fields plus an audit note.
async def fetch_incident(
    bug_id: str, http: Optional[httpx.AsyncClient] = None
) -> tuple[Optional[dict], str]:
    """Returns (normalized fields or None, note for the audit trail). Never raises."""
    url = f"{settings.central_url}/api/incidents/{quote(bug_id, safe='')}"
    client = http or httpx.AsyncClient(timeout=10)
    try:
        resp = await client.get(url)
        if resp.status_code == 404:
            return None, f"incident {bug_id} not found in central service"
        resp.raise_for_status()
        doc = resp.json()
        if not isinstance(doc, dict):
            return None, "central service returned an unexpected response"
        return normalize_incident(doc), f"incident details fetched from central service ({url})"
    except Exception as exc:
        logger.warning("Central fetch failed for %s: %r", bug_id, exc)
        return None, f"central service unavailable: {exc!r}"
    finally:
        if http is None:
            await client.aclose()
