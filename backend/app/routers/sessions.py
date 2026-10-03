from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Page
from app.schemas.sessions import (
    EligibleDriver, EnrollmentCreate, EnrollmentOut, SessionCreate, SessionOut, SessionUpdate,
)
from app.services import enrollments as enroll_svc
from app.services import sessions as svc
from app.services.pagination import PageParams, page_params

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=Page[SessionOut])
def list_sessions(
    course_id: int | None = None,
    trainer_id: int | None = None,
    status: str | None = None,
    source: str | None = None,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    items, total = svc.list_sessions(
        db, params, course_id=course_id, trainer_id=trainer_id, status=status, source=source,
        start_from=start_from, start_to=start_to,
    )
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreate, db: Session = Depends(get_db)):
    return svc.create_session(db, body)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    return svc.get_session_out(db, session_id)


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(session_id: int, body: SessionUpdate, db: Session = Depends(get_db)):
    return svc.update_session(db, session_id, body)


@router.post("/{session_id}/cancel", response_model=SessionOut)
def cancel_session(session_id: int, db: Session = Depends(get_db)):
    """No hard delete: the session becomes 'cancelled' and its booked drivers are released."""
    return svc.cancel_session(db, session_id)


@router.get("/{session_id}/enrollments", response_model=list[EnrollmentOut])
def list_enrollments(session_id: int, db: Session = Depends(get_db)):
    return enroll_svc.list_enrollments(db, session_id)


@router.post("/{session_id}/enrollments", response_model=EnrollmentOut, status_code=201)
def add_enrollment(session_id: int, body: EnrollmentCreate, db: Session = Depends(get_db)):
    return enroll_svc.add_enrollment(db, session_id, body.driver_id)


@router.delete("/{session_id}/enrollments/{enrollment_id}", response_model=EnrollmentOut)
def cancel_enrollment(session_id: int, enrollment_id: int, db: Session = Depends(get_db)):
    return enroll_svc.cancel_enrollment(db, session_id, enrollment_id)


@router.get("/{session_id}/eligible-drivers", response_model=list[EligibleDriver])
def eligible_drivers(session_id: int, q: str | None = Query(None), db: Session = Depends(get_db)):
    """Active drivers who would pass every enrollment check (max 50)."""
    return enroll_svc.eligible_drivers(db, session_id, q)
