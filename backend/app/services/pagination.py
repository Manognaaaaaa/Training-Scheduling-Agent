"""Shared paging and sorting for list endpoints."""
from dataclasses import dataclass

from fastapi import Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.services.errors import Invalid


@dataclass
class PageParams:
    page: int
    page_size: int
    sort: str | None


def page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    sort: str | None = Query(None, description="field name; prefix with - for descending"),
) -> PageParams:
    """FastAPI dependency giving every list endpoint the same page / page_size / sort."""
    return PageParams(page, page_size, sort)


def paginate(db: Session, stmt: Select, params: PageParams, allowed: dict, default_sort: str, tiebreak):
    """Apply sort + paging to ``stmt``. Returns (rows, total).

    ``allowed`` maps whitelisted sort names to columns; anything else is a 422.
    ``tiebreak`` (usually the id column) keeps the order stable between pages.
    """
    sort = params.sort or default_sort
    descending = sort.startswith("-")
    name = sort.lstrip("-")
    if name not in allowed:
        raise Invalid(f"Cannot sort by '{name}'. Allowed: {', '.join(sorted(allowed))}", {"sort": "not allowed"})
    column = allowed[name]
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    ordered = stmt.order_by(column.desc() if descending else column.asc(), tiebreak)
    rows = db.execute(ordered.limit(params.page_size).offset((params.page - 1) * params.page_size)).all()
    return rows, total
