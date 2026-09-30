from fastapi import APIRouter
from sqlalchemy import inspect

from app.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Report API status plus whether the database is reachable and how many tables exist."""
    try:
        tables = len(inspect(engine).get_table_names())
        return {"status": "ok", "database": "ok", "tables": tables}
    except Exception:
        return {"status": "ok", "database": "error", "tables": 0}
