from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Page
from app.schemas.trainers import TrainerCreate, TrainerOut, TrainerUpdate
from app.services import trainers as svc
from app.services.pagination import PageParams, page_params

router = APIRouter(prefix="/trainers", tags=["trainers"])


@router.get("", response_model=Page[TrainerOut])
def list_trainers(
    q: str | None = Query(None, description="trainer name"),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    items, total = svc.list_trainers(db, params, q=q)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("", response_model=TrainerOut, status_code=201)
def create_trainer(body: TrainerCreate, db: Session = Depends(get_db)):
    return svc.create_trainer(db, body)


@router.get("/{trainer_id}", response_model=TrainerOut)
def get_trainer(trainer_id: int, db: Session = Depends(get_db)):
    return svc.get_trainer(db, trainer_id)


@router.patch("/{trainer_id}", response_model=TrainerOut)
def update_trainer(trainer_id: int, body: TrainerUpdate, db: Session = Depends(get_db)):
    """Lowering the weekly limit is allowed; ``warnings`` names future weeks that are now over it."""
    return svc.update_trainer(db, trainer_id, body)


@router.delete("/{trainer_id}", status_code=204)
def delete_trainer(trainer_id: int, db: Session = Depends(get_db)):
    svc.delete_trainer(db, trainer_id)
    return Response(status_code=204)
