from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_event(
    db: Session,
    timestamp: datetime,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Add one audit row (the caller commits). ``timestamp`` is simulated time, not the real clock."""
    row = AuditLog(
        timestamp=timestamp,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
    )
    db.add(row)
    return row


def _jsonable(value: Any) -> Any:
    """Dates are stored in the JSON details as ISO strings."""
    return value.isoformat() if hasattr(value, "isoformat") else value


def apply_changes(obj: Any, changes: dict[str, Any]) -> dict[str, list]:
    """Set each field on ``obj`` and return only the ones that really changed, as ``{field: [old, new]}``."""
    diff: dict[str, list] = {}
    for field, new in changes.items():
        old = getattr(obj, field)
        if old != new:
            diff[field] = [_jsonable(old), _jsonable(new)]
            setattr(obj, field, new)
    return diff
