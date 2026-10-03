from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Page
from app.schemas.courses import CourseCreate, CourseOut, CourseUpdate
from app.services import courses as svc
from app.services.pagination import PageParams, page_params

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=Page[CourseOut])
def list_courses(
    q: str | None = Query(None, description="course code or name"),
    is_mandatory: bool | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    items, total = svc.list_courses(db, params, q=q, is_mandatory=is_mandatory)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("", response_model=CourseOut, status_code=201)
def create_course(body: CourseCreate, db: Session = Depends(get_db)):
    return svc.create_course(db, body)


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: int, db: Session = Depends(get_db)):
    return svc.get_course(db, course_id)


@router.patch("/{course_id}", response_model=CourseOut)
def update_course(course_id: int, body: CourseUpdate, db: Session = Depends(get_db)):
    return svc.update_course(db, course_id, body)


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: int, db: Session = Depends(get_db)):
    svc.delete_course(db, course_id)
    return Response(status_code=204)
