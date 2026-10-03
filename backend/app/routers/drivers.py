from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Page
from app.schemas.drivers import (
    DriverCreate, DriverDeactivated, DriverDetail, DriverOptions, DriverOut, DriverUpdate,
    UnavailabilityCreate, UnavailabilityOut,
)
from app.services import drivers as svc
from app.services.pagination import PageParams, page_params

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.get("", response_model=Page[DriverOut])
def list_drivers(
    q: str | None = Query(None, description="name or employee code"),
    nationality: str | None = None,
    shift: str | None = None,
    depot: str | None = None,
    is_active: bool | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    items, total = svc.list_drivers(db, params, q=q, nationality=nationality, shift=shift, depot=depot, is_active=is_active)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/options", response_model=DriverOptions)
def driver_options(db: Session = Depends(get_db)):
    """Distinct values for the filter dropdowns."""
    return svc.options(db)


@router.post("", response_model=DriverOut, status_code=201)
def create_driver(body: DriverCreate, db: Session = Depends(get_db)):
    return svc.create_driver(db, body)


@router.get("/{driver_id}", response_model=DriverDetail)
def get_driver(driver_id: int, db: Session = Depends(get_db)):
    return svc.driver_detail(db, driver_id)


@router.patch("/{driver_id}", response_model=DriverOut)
def update_driver(driver_id: int, body: DriverUpdate, db: Session = Depends(get_db)):
    return svc.update_driver(db, driver_id, body)


@router.delete("/{driver_id}", response_model=DriverDeactivated)
def deactivate_driver(driver_id: int, db: Session = Depends(get_db)):
    """Soft delete: marks the driver inactive and cancels their future booked sessions."""
    driver, cancelled = svc.deactivate_driver(db, driver_id)
    return {**DriverOut.model_validate(driver).model_dump(), "cancelled_bookings": cancelled}


@router.get("/{driver_id}/unavailability", response_model=list[UnavailabilityOut])
def list_unavailability(driver_id: int, db: Session = Depends(get_db)):
    return svc.list_unavailability(db, driver_id)


@router.post("/{driver_id}/unavailability", response_model=UnavailabilityOut, status_code=201)
def add_unavailability(driver_id: int, body: UnavailabilityCreate, db: Session = Depends(get_db)):
    block, cancelled = svc.add_unavailability(db, driver_id, body)
    return {**UnavailabilityOut.model_validate(block).model_dump(), "cancelled_bookings": cancelled}


@router.delete("/{driver_id}/unavailability/{uid}", status_code=204)
def remove_unavailability(driver_id: int, uid: int, db: Session = Depends(get_db)):
    svc.remove_unavailability(db, driver_id, uid)
    return Response(status_code=204)
