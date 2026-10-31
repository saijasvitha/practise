"""Persists investigations as JSON files so state survives restarts and container redeploys."""
import logging
from pathlib import Path

from models import Investigation, InvestigationStatus, settings, utcnow

logger = logging.getLogger(__name__)


# Builds the JSON file path for a bug ID, replacing unsafe characters.
def _path(bug_id: str) -> Path:
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in bug_id)
    return Path(settings.data_dir) / f"{safe_id}.json"


# Saves an investigation to disk atomically (temp file, then rename); logs instead of raising on I/O errors.
def save(inv: Investigation) -> None:
    try:
        path = _path(inv.bug_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(inv.model_dump_json(), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        logger.exception("Could not persist investigation %s", inv.bug_id)


# Loads all saved investigations at startup and marks any that were mid-run as FAILED (interrupted by restart).
def load_all() -> dict[str, Investigation]:
    result: dict[str, Investigation] = {}
    folder = Path(settings.data_dir)
    if not folder.is_dir():
        return result
    for file in folder.glob("*.json"):
        try:
            inv = Investigation.model_validate_json(file.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Skipping unreadable investigation file %s", file)
            continue
        if inv.status in (InvestigationStatus.QUEUED, InvestigationStatus.IN_PROGRESS):
            inv.status = InvestigationStatus.FAILED
            inv.error = "Service restarted while the investigation was running"
            inv.message = "Investigation interrupted by a service restart; please re-run"
            inv.audit.append({"at": utcnow().isoformat(), "event": "Interrupted by service restart"})
            save(inv)
        result[inv.bug_id] = inv
    return result
