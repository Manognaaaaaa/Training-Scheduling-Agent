"""Domain rules for the training calendar.

Kept in one importable module because three things must agree on them: the seed script,
the simulator and (Phase 4) the constraint checker. Everything here is plain Python with
no database access.
"""
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from typing import Any

# --- Simulated year ---------------------------------------------------------------------
SIM_YEAR = 2026
SIM_START = datetime(2026, 1, 1, 0, 0)
SIM_END = datetime(2026, 12, 31, 23, 59)  # the clock never goes past this

# --- Shifts -----------------------------------------------------------------------------
SHIFT_DAY = "day"
SHIFT_NIGHT = "night"
SHIFT_ROTATING = "rotating"

# (start, end). The night shift ends on the *next* calendar day.
SHIFT_HOURS = {
    SHIFT_DAY: (time(6, 0), time(14, 0)),
    SHIFT_NIGHT: (time(22, 0), time(6, 0)),
}

# --- Sessions ---------------------------------------------------------------------------
SESSION_START_HOURS = (9, 14, 18)  # 09:00, 14:00, 18:00
SESSION_WEEKDAYS = (6, 0, 1, 2, 3)  # Python weekday(): Mon=0 ... Sun=6. So Sunday to Thursday (UAE week).
MAX_SESSION_HOURS = 4  # longer courses simply use 4h sessions

# --- Limits -----------------------------------------------------------------------------
REST_HOURS = 8  # min gap between the end of a shift and the start of a session
BOOKING_WINDOW_DAYS = 21  # drivers are booked into sessions starting within the next 21 days

# --- Seasons (dates are approximate; Ramadan moves with the moon) -----------------------
RAMADAN_START = date(2026, 2, 18)
RAMADAN_END = date(2026, 3, 19)
SUMMER_PEAK_START = date(2026, 7, 1)
SUMMER_PEAK_END = date(2026, 8, 31)

# --- Weekly roster (assumption, see is_driver_free) ---------------------------------------
# Each driver has two consecutive rest days a week. The pair starts on one of these weekdays
# (Fri+Sat is left out, otherwise that driver could never be trained on a session day).
ROSTER_REST_STARTS = (0, 1, 2, 3, 5, 6)


def is_ramadan(d: date) -> bool:
    return RAMADAN_START <= d <= RAMADAN_END


def is_summer_peak(d: date) -> bool:
    return SUMMER_PEAK_START <= d <= SUMMER_PEAK_END


def session_length_hours(course_duration_hours: int) -> int:
    """Length of one session: the course duration, capped at MAX_SESSION_HOURS."""
    return min(course_duration_hours, MAX_SESSION_HOURS)


def session_end(start: datetime, course_duration_hours: int) -> datetime:
    return start + timedelta(hours=session_length_hours(course_duration_hours))


def week_start(d: date) -> date:
    """The Sunday that starts the (Sunday to Saturday) week containing ``d``. Used for trainer weekly load."""
    days_since_sunday = (d.weekday() + 1) % 7
    return d - timedelta(days=days_since_sunday)


# --- Driver roster and shifts -------------------------------------------------------------
def rest_days(driver: Any) -> tuple[int, int]:
    """The driver's two weekly rest days (Python weekday numbers), derived from the driver id."""
    first = ROSTER_REST_STARTS[driver.id % len(ROSTER_REST_STARTS)]
    return first, (first + 1) % 7


def effective_shift(driver: Any, d: date) -> str:
    """'day' or 'night' for the shift starting on date ``d``.

    Rotating drivers alternate weekly: even ISO week number = day, odd = night.
    """
    if driver.shift == SHIFT_ROTATING:
        return SHIFT_DAY if d.isocalendar().week % 2 == 0 else SHIFT_NIGHT
    return driver.shift


def shift_interval(driver: Any, d: date) -> tuple[datetime, datetime] | None:
    """(start, end) of the shift that *starts* on date ``d``, or None on a rest day."""
    if d.weekday() in rest_days(driver):
        return None
    start_t, end_t = SHIFT_HOURS[effective_shift(driver, d)]
    start = datetime.combine(d, start_t)
    end = datetime.combine(d, end_t)
    if end <= start:  # night shift runs past midnight
        end += timedelta(days=1)
    return start, end


def is_driver_free(
    driver: Any, start: datetime, end: datetime, unavailability_rows: Iterable[Any]
) -> tuple[bool, str]:
    """Can this driver attend a session from ``start`` to ``end``? Returns (ok, reason).

    Checks, in order:
    1. unavailability (leave, sick days, known absences) overlapping the session;
    2. the session overlaps one of the driver's shifts;
    3. the session starts less than REST_HOURS after a shift ended (rest rule).

    ``driver`` needs ``.id`` and ``.shift``; unavailability rows need ``.driver_id``,
    ``.start_time``, ``.end_time`` and ``.reason``.

    Assumption: the rules alone would make every slot unbookable for a day-shift driver on a
    working day (shift ends 14:00, rest runs to 22:00). So drivers only work five days a week
    and have two rest days (see ``rest_days``); on a rest day there is no shift to clash with.
    """
    for row in unavailability_rows:
        if row.driver_id == driver.id and row.start_time < end and row.end_time > start:
            return False, f"unavailable: {row.reason}"

    rest = timedelta(hours=REST_HOURS)
    day = start.date() - timedelta(days=1)  # the previous day's night shift can still be running
    while day <= end.date():
        interval = shift_interval(driver, day)
        if interval is not None:
            shift_start, shift_end = interval
            if shift_start < end and shift_end > start:
                return False, "session overlaps the driver's shift"
            if shift_end <= start and start - shift_end < rest:
                return False, f"less than {REST_HOURS}h rest after the shift"
        day += timedelta(days=1)
    return True, "ok"
