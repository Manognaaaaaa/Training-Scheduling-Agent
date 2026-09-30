from datetime import date, datetime

from pydantic import BaseModel, Field


class DayBreakdown(BaseModel):
    """What happened on one simulated day."""

    day: date
    sessions_completed: int = 0
    attended: int = 0
    no_shows: int = 0
    new_bookings: int = 0
    enrollments_cancelled: int = 0
    sessions_cancelled: int = 0
    sick_events: int = 0
    drivers_activated: int = 0
    scenario_events: list[str] = Field(default_factory=list)


class AdvanceSummary(BaseModel):
    """Totals for one advance() call, plus the per-day breakdown."""

    from_time: datetime
    to_time: datetime
    days_advanced: int
    hit_year_end: bool
    sessions_completed: int
    attended: int
    no_shows: int
    new_bookings: int
    enrollments_cancelled: int
    sessions_cancelled: int
    sick_events: int
    drivers_activated: int
    scenario_events_applied: list[str]
    days: list[DayBreakdown]


class AdvanceRequest(BaseModel):
    days: int = Field(ge=1, le=90)


class ResetRequest(BaseModel):
    seed: int | None = None


class SimTotals(BaseModel):
    drivers: int
    active_drivers: int
    sessions_scheduled: int
    sessions_completed: int
    sessions_cancelled: int
    enrollments_booked: int
    enrollments_attended: int
    enrollments_no_show: int
    enrollments_cancelled: int


class SimStateOut(BaseModel):
    current_time: datetime
    year_start: datetime
    year_end: datetime
    percent_year_elapsed: float
    year_ended: bool
    seed: int | None
    totals: SimTotals


class CourseProgress(BaseModel):
    course_id: int
    code: str
    name: str
    is_mandatory: bool
    target: int
    attended: int
    percent_of_target: float
    booked_upcoming: int
    planned_capacity_remaining: int
