from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    trainer_id: Mapped[int] = mapped_column(ForeignKey("trainers.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    location: Mapped[str] = mapped_column(String(100))
    capacity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")  # scheduled / completed / cancelled
    source: Mapped[str] = mapped_column(String(20), default="seed")  # seed / manual / agent
    gcal_event_id: Mapped[str | None] = mapped_column(String(200), default=None)


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("session_id", "driver_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"))
    status: Mapped[str] = mapped_column(String(20), default="booked")  # booked / attended / no_show / cancelled


class DriverUnavailability(Base):
    __tablename__ = "driver_unavailability"

    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    reason: Mapped[str] = mapped_column(String(100))
