"""Collects the logs for a bug from the log REST API, falling back to a local log file."""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import httpx

from models import AcceptRequest, settings

logger = logging.getLogger(__name__)

LIST_KEYS = ("logs", "data", "items", "results", "entries", "lines", "content")
MAX_LINE_CHARS = 500


@dataclass
class LogResult:
    lines: list[str] = field(default_factory=list)
    source: str = "none"
    notes: list[str] = field(default_factory=list)  # why a source was skipped, for the audit trail


def _format_entry(entry) -> str:
    if isinstance(entry, dict):
        known = [str(entry[k]) for k in ("timestamp", "time", "level", "service", "message", "msg") if k in entry]
        text = " ".join(known) if known else json.dumps(entry, default=str)
    else:
        text = str(entry)
    return text.strip()[:MAX_LINE_CHARS]


def parse_log_payload(body: str) -> list[str]:
    """Accepts a JSON list, a JSON object wrapping a list, or plain text lines."""
    try:
        data = json.loads(body)
    except ValueError:
        return [ln.strip()[:MAX_LINE_CHARS] for ln in body.splitlines() if ln.strip()]
    if isinstance(data, dict):
        data = next((data[k] for k in LIST_KEYS if isinstance(data.get(k), list)), [data])
    if isinstance(data, str):
        return parse_log_payload_lines(data)
    if not isinstance(data, list):
        data = [data]
    return [line for line in (_format_entry(e) for e in data) if line]


def parse_log_payload_lines(text: str) -> list[str]:
    return [ln.strip()[:MAX_LINE_CHARS] for ln in text.splitlines() if ln.strip()]


def _read_log_file(req: AcceptRequest) -> list[str]:
    path = Path(settings.log_file_path)
    if path.is_dir():
        candidates = [p for p in path.iterdir() if p.suffix.lower() in (".log", ".txt")]
        if not candidates:
            raise FileNotFoundError(f"no .log/.txt files in {path}")
        path = max(candidates, key=lambda p: p.stat().st_mtime)
    lines = parse_log_payload_lines(path.read_text(encoding="utf-8", errors="replace"))
    needles = [n.lower() for n in (req.bug_id, req.service) if n]
    relevant = [ln for ln in lines if any(n in ln.lower() for n in needles)]
    return relevant or lines


async def fetch_logs(req: AcceptRequest, http: Optional[httpx.AsyncClient] = None) -> LogResult:
    """Fetches from the log REST API, falling back to a local file; request-supplied logs are added."""
    fetched = await _fetch_configured_logs(req, http)
    if req.logs:
        fetched.lines = (fetched.lines + req.logs)[-settings.log_max_lines :]
        fetched.source = "request body" if fetched.source == "none" else fetched.source + " + request body"
    return fetched


async def _fetch_configured_logs(req: AcceptRequest, http: Optional[httpx.AsyncClient]) -> LogResult:
    limit = settings.log_max_lines
    result = LogResult()

    if settings.log_api_url:
        url = settings.log_api_url.replace("{service}", quote(req.service or "")).replace(
            "{bug_id}", quote(req.bug_id)
        )
        client = http or httpx.AsyncClient(timeout=settings.log_timeout_seconds)
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            lines = parse_log_payload(resp.text)
            if lines:
                return LogResult(lines=lines[-limit:], source=f"log API ({settings.log_api_url})")
            result.notes.append("log API returned no log lines")
        except Exception as exc:
            logger.warning("Log API fetch failed for %s: %r", req.bug_id, exc)
            result.notes.append(f"log API unavailable: {exc!r}")
        finally:
            if http is None:
                await client.aclose()

    if settings.log_file_path:
        try:
            lines = _read_log_file(req)
            if lines:
                return LogResult(
                    lines=lines[-limit:], source=f"log file ({settings.log_file_path})", notes=result.notes
                )
            result.notes.append("log file is empty")
        except Exception as exc:
            logger.warning("Log file read failed for %s: %r", req.bug_id, exc)
            result.notes.append(f"log file unavailable: {exc!r}")

    if not (settings.log_api_url or settings.log_file_path):
        result.notes.append("no log source configured (set LOG_API_URL or LOG_FILE_PATH)")
    return result
