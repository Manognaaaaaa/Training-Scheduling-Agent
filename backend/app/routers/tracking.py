from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.tracking import CourseDetail, CourseRow, RecomputeResult, SeriesPoint, TrackingSummary
from app.services import tracking_views as views
from app.services.audit import log_event
from app.services.tracking_jobs import weekly_close

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/summary", response_model=TrackingSummary)
def get_summary(db: Session = Depends(get_db)):
    """Headline numbers for the dashboard tiles."""
    return views.summary(db)


@router.get("/courses", response_model=list[CourseRow])
def list_courses(db: Session = Depends(get_db)):
    """One forecast row per course, riskiest first. Uses a fixed number of queries."""
    return views.course_rows(db)[2]


@router.get("/series", response_model=dict[int, list[SeriesPoint]])
def all_series(db: Session = Depends(get_db)):
    """Chart series (actual, target pace, forecast cone) for every course, keyed by course id."""
    return views.all_series(db)


@router.get("/courses/{course_id}", response_model=CourseDetail)
def get_course(course_id: int, db: Session = Depends(get_db)):
    """Everything the course detail page draws: forecast, chart series, snapshots, who is behind, events, sessions."""
    return views.course_detail(db, course_id)


@router.post("/recompute", response_model=RecomputeResult)
def recompute(db: Session = Depends(get_db)):
    """Run the weekly close now (snapshot + alert sync), e.g. after manual edits to sessions or bookings."""
    result = weekly_close(db)
    c = result.changes
    log_event(db, result.as_of, "user", "tracking_recomputed", "tracking", None, {
        "snapshots": result.snapshots, "alerts_opened": len(c.opened), "alerts_escalated": len(c.escalated),
        "alerts_deescalated": len(c.deescalated), "alerts_resolved": len(c.resolved),
    })
    db.commit()
    return RecomputeResult(
        as_of=result.as_of, snapshots=result.snapshots, alerts_opened=len(c.opened), alerts_escalated=len(c.escalated),
        alerts_deescalated=len(c.deescalated), alerts_resolved=len(c.resolved),
    )
