from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, Course
from app.schemas.tracking import AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    status: Literal["open", "resolved", "dismissed"] | None = None,
    course_id: int | None = None,
    since: datetime | None = None,
    db: Session = Depends(get_db),
):
    """Alerts, newest change first. ``since`` keeps only alerts opened or changed at or after that sim time.

    Read-only for now: the inbox with Approve / Reject arrives in Phase 6.
    """
    stmt = select(Alert, Course.code, Course.name).join(Course, Course.id == Alert.course_id)
    if status:
        stmt = stmt.where(Alert.status == status)
    if course_id is not None:
        stmt = stmt.where(Alert.course_id == course_id)
    if since is not None:
        stmt = stmt.where(Alert.updated_at >= since)
    rows = db.execute(stmt.order_by(Alert.updated_at.desc(), Alert.id.desc()))
    return [
        {
            "id": a.id, "course_id": a.course_id, "course_code": code, "course_name": name, "created_at": a.created_at,
            "updated_at": a.updated_at, "risk_level": a.risk_level, "shortfall_type": a.shortfall_type,
            "projected_completions": a.projected_completions, "target_completions": a.target_completions,
            "message": a.message, "status": a.status, "details": a.details or {},
        }
        for a, code, name in rows
    ]
