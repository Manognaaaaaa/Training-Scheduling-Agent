from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    nationality: Mapped[str] = mapped_column(String(50))
    shift: Mapped[str] = mapped_column(String(10))  # day / night / rotating
    depot: Mapped[str] = mapped_column(String(50))
    hire_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Trainer(Base):
    __tablename__ = "trainers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    max_sessions_per_week: Mapped[int] = mapped_column(Integer, default=5)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    duration_hours: Mapped[int] = mapped_column(Integer)
    default_capacity: Mapped[int] = mapped_column(Integer)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)


class TrainingTarget(Base):
    """Annual number of completions we want for one course."""

    __tablename__ = "training_targets"
    __table_args__ = (UniqueConstraint("course_id", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    year: Mapped[int] = mapped_column(Integer)
    target_completions: Mapped[int] = mapped_column(Integer)
