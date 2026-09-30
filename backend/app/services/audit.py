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
