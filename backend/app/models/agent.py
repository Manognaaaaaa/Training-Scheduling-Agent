from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)  # simulated time, not real time
    risk_level: Mapped[str] = mapped_column(String(20))  # low / medium / high
    projected_completions: Mapped[int] = mapped_column(Integer)
    target_completions: Mapped[int] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text, default=None)  # LLM-written text
    status: Mapped[str] = mapped_column(String(20), default="open")  # open / resolved / dismissed
    # Phase 3: why the course is at risk. details = {p_hit, low, high, reasons: [...], last_change, ...}
    shortfall_type: Mapped[str | None] = mapped_column(String(20), default=None)  # capacity_gap / attendance_gap / pool_gap
    details: Mapped[Any] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)  # simulated time


class ForecastSnapshot(Base):
    """The forecast for one course as it stood at the end of a simulated week (history for charts and the backtest)."""

    __tablename__ = "forecast_snapshots"
    __table_args__ = (UniqueConstraint("course_id", "as_of"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    as_of: Mapped[datetime] = mapped_column(DateTime)  # simulated time
    attended: Mapped[int] = mapped_column(Integer)
    projected: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    p_hit: Mapped[float] = mapped_column(Float)
    naive_projection: Mapped[float] = mapped_column(Float)
    linear_projection: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(20))
    shortfall_type: Mapped[str] = mapped_column(String(20))


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    actions: Mapped[Any] = mapped_column(JSON)  # list of structured actions proposed by the agent
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    rejection_reasons: Mapped[Any] = mapped_column(JSON, default=list)
    score: Mapped[float | None] = mapped_column(Float, default=None)
    rank: Mapped[int | None] = mapped_column(Integer, default=None)
    status: Mapped[str] = mapped_column(String(20), default="proposed")  # proposed / approved / rejected


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)  # simulated time
    actor: Mapped[str] = mapped_column(String(20))  # agent / user / system
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer, default=None)
    details: Mapped[Any] = mapped_column(JSON, default=dict)


class SimState(Base):
    """Single row (id=1) holding the current simulated time."""

    __tablename__ = "sim_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    current_time: Mapped[datetime] = mapped_column(DateTime)
