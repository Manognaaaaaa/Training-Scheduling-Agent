from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.sessions import CalendarResponse
from app.services import sessions as svc

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=CalendarResponse)
def calendar(
    start: datetime,
    end: datetime,
    course_id: int | None = None,
    trainer_id: int | None = None,
    include_cancelled: bool = False,
    db: Session = Depends(get_db),
):
    """Sessions starting in [start, end) (max 62 days), with fill rate and band, plus the sim clock."""
    return svc.calendar_events(
        db, start, end, course_id=course_id, trainer_id=trainer_id, include_cancelled=include_cancelled
    )
