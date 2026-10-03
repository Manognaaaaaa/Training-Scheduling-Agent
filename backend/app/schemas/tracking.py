from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

RiskLevel = Literal["high", "medium", "low", "achieved", "insufficient_data"]
ShortfallType = Literal["capacity_gap", "attendance_gap", "pool_gap", "none"]


class Reason(BaseModel):
    """One structured reason a course is at risk. ``impact`` is roughly "completions explained"."""

    code: str
    message: str
    value: float
    benchmark: float
    impact: float = 0.0
    group: str | None = None  # group_gap only: which group is behind
    by: str | None = None  # group_gap only: shift / nationality / depot


class CourseRow(BaseModel):
    course_id: int
    code: str
    name: str
    is_mandatory: bool
    target: int
    attended: int
    target_pace: float
    pace_gap: float
    p_show: float
    p_fill: float
    remaining_sessions: int
    remaining_seats: int
    eligible_pool: int
    projected: float
    low: float
    high: float
    p_hit: float
    naive_projection: float
    linear_projection: float
    risk_level: RiskLevel
    shortfall_type: ShortfallType
    seats_needed: float
    weeks_observed: int
    reasons: list[Reason]
    open_alert_id: int | None = None


class RiskCounts(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0
    achieved: int = 0
    insufficient_data: int = 0


class TrackingSummary(BaseModel):
    current_time: datetime
    percent_year_elapsed: float
    has_data: bool  # False until at least one session has been completed
    total_attended: int
    total_target: int
    mandatory_compliance_pct: float  # Σ min(attended, target) ÷ Σ target over mandatory courses
    risk_counts: RiskCounts
    open_alerts: int


class SeriesPoint(BaseModel):
    """One x position on the course chart. Past points have ``actual``, future points have the forecast."""

    date: datetime
    target_pace: float
    actual: int | None = None
    forecast_mean: float | None = None
    forecast_low: float | None = None
    forecast_high: float | None = None
    is_now: bool = False


class WeekBar(BaseModel):
    week_start: date
    attended: int
    no_shows: int
    closed: bool


class SnapshotOut(BaseModel):
    as_of: datetime
    attended: int
    projected: float
    low: float
    high: float
    p_hit: float
    naive_projection: float
    risk_level: RiskLevel


class GroupRow(BaseModel):
    group: str
    active_drivers: int
    completed: int
    completion_pct: float
    no_show_rate: float | None


class Breakdown(BaseModel):
    shift: list[GroupRow]
    nationality: list[GroupRow]


class CourseEvent(BaseModel):
    date: datetime
    kind: str
    label: str


class UpcomingSession(BaseModel):
    id: int
    start_time: datetime
    capacity: int
    booked: int
    fill_rate: float | None
    fill_band: str


class CourseDetail(BaseModel):
    course: CourseRow
    series: list[SeriesPoint]
    weekly: list[WeekBar]
    snapshots: list[SnapshotOut]
    breakdown: Breakdown
    events: list[CourseEvent]
    upcoming_sessions: list[UpcomingSession]


class RecomputeResult(BaseModel):
    as_of: datetime
    snapshots: int
    alerts_opened: int
    alerts_escalated: int
    alerts_deescalated: int
    alerts_resolved: int


class AlertOut(BaseModel):
    id: int
    course_id: int
    course_code: str
    course_name: str
    created_at: datetime
    updated_at: datetime | None
    risk_level: str
    shortfall_type: str | None
    projected_completions: int
    target_completions: int
    message: str | None
    status: str
    details: dict
