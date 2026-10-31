"""Notifies the backend service (e.g. the incident backend) when an investigation finishes."""
import asyncio
import logging
from typing import Optional
from urllib.parse import quote

import httpx

from models import InvestigationSummary, settings

logger = logging.getLogger(__name__)

RETRY_DELAYS = (1, 3)  # seconds between attempts; 3 attempts in total


# Sends the investigation summary to the backend callback URL with retries; never raises.
async def notify_callback(
    summary: InvestigationSummary, http: Optional[httpx.AsyncClient] = None
) -> str:
    """POSTs the summary to CALLBACK_URL. Never raises; returns a message for the audit trail."""
    if not settings.callback_url:
        return "no callback configured"
    headers = {"X-API-Key": settings.callback_api_key} if settings.callback_api_key else {}
    client = http or httpx.AsyncClient(timeout=10)
    url = settings.callback_url.replace("{bug_id}", quote(summary.bug_id, safe=""))
    payload = summary.model_dump(mode="json")
    last_error = ""
    try:
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code < 300:
                    return f"callback delivered (HTTP {resp.status_code})"
                last_error = f"HTTP {resp.status_code}"
            except httpx.HTTPError as exc:
                last_error = repr(exc)
            if attempt < len(RETRY_DELAYS):
                await asyncio.sleep(RETRY_DELAYS[attempt])
    finally:
        if http is None:
            await client.aclose()
    logger.warning("Callback for %s failed: %s", summary.bug_id, last_error)
    return f"callback failed after retries: {last_error}"
