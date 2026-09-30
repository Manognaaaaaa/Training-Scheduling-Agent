from collections import defaultdict
from datetime import date, datetime, time
from types import SimpleNamespace

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Driver, DriverUnavailability, Enrollment, Trainer, TrainingSession
from app.services.sim_clock import get_sim_now
from app.simulator import scenarios
from app.simulator.engine import advance
from app.simulator.report import fingerprint
from app.simulator.rules import SIM_END, SIM_START, is_driver_free, week_start
from app.simulator.seed import table_counts
from tests.conftest import make_seeded_engine


def first_enrollments(db, n=20):
    rows = db.execute(
        select(Enrollment.session_id, Enrollment.driver_id, Enrollment.status).order_by(Enrollment.id).limit(n)
    )
    return [tuple(r) for r in rows]


def outcomes(db):
    """Every enrollment's final state, used to compare two runs."""
    rows = db.execute(
        select(Enrollment.session_id, Enrollment.driver_id, Enrollment.status).order_by(
            Enrollment.session_id, Enrollment.driver_id
        )
    )
    return [tuple(r) for r in rows]


# --- Determinism ------------------------------------------------------------------------
def test_same_seed_gives_identical_data(db):
    other = Session(make_seeded_engine())
    assert table_counts(db) == table_counts(other)
    assert len(first_enrollments(db)) == 20
    assert first_enrollments(db) == first_enrollments(other)
    assert fingerprint(db) == fingerprint(other)


def test_different_seed_gives_different_data(db):
    other = Session(make_seeded_engine(seed=7))
    assert fingerprint(db) != fingerprint(other)


def test_seven_plus_seven_days_equals_fourteen():
    a, b = Session(make_seeded_engine()), Session(make_seeded_engine())
    advance(a, 7)
    advance(a, 7)
    advance(b, 14)
    assert get_sim_now(a) == get_sim_now(b)
    assert outcomes(a) == outcomes(b)
    assert any(status == "attended" for _, _, status in outcomes(a))  # the comparison is not trivially empty


# --- Invariants (checked at seed and after a stretch of simulated time) -------------------
def check_invariants(db):
    sessions = list(db.scalars(select(TrainingSession).where(TrainingSession.status != "cancelled")))

    # No session over capacity
    used = defaultdict(int)
    for (session_id,) in db.execute(select(Enrollment.session_id).where(Enrollment.status != "cancelled")):
        used[session_id] += 1
    for s in sessions:
        assert used[s.id] <= s.capacity, f"session {s.id} over capacity"

    # Trainers: no double booking, weekly load within the limit
    max_week = {t.id: t.max_sessions_per_week for t in db.scalars(select(Trainer))}
    by_trainer = defaultdict(list)
    weekly = defaultdict(int)
    for s in sessions:
        by_trainer[s.trainer_id].append(s)
        weekly[(s.trainer_id, week_start(s.start_time.date()))] += 1
    for trainer_id, items in by_trainer.items():
        items.sort(key=lambda s: s.start_time)
        for earlier, later in zip(items, items[1:]):
            assert earlier.end_time <= later.start_time, f"trainer {trainer_id} double-booked"
    for (trainer_id, _), n in weekly.items():
        assert n <= max_week[trainer_id], f"trainer {trainer_id} over weekly load"

    # Drivers: no overlapping bookings
    session_times = {s.id: (s.start_time, s.end_time) for s in sessions}
    by_driver = defaultdict(list)
    for session_id, driver_id in db.execute(
        select(Enrollment.session_id, Enrollment.driver_id).where(Enrollment.status != "cancelled")
    ):
        by_driver[driver_id].append(session_times[session_id])
    for driver_id, times in by_driver.items():
        times.sort()
        for (_, end_1), (start_2, _) in zip(times, times[1:]):
            assert end_1 <= start_2, f"driver {driver_id} booked in overlapping sessions"

    # Every kept booking passes is_driver_free (shift overlap, rest rule, unavailability)
    drivers = {d.id: d for d in db.scalars(select(Driver))}
    unavailability = defaultdict(list)
    for row in db.scalars(select(DriverUnavailability)):
        unavailability[row.driver_id].append(row)
    kept = db.execute(
        select(Enrollment.session_id, Enrollment.driver_id, Enrollment.status).where(
            Enrollment.status.in_(["booked", "attended"])
        )
    )
    for session_id, driver_id, status in kept:
        start, end = session_times[session_id]
        ok, reason = is_driver_free(drivers[driver_id], start, end, unavailability[driver_id])
        assert ok, f"driver {driver_id} in session {session_id} ({status}) violates: {reason}"


def test_invariants_hold_at_seed(db):
    check_invariants(db)


def test_invariants_hold_after_advancing(db):
    advance(db, 120)  # crosses Ramadan and the trainer-leave event
    check_invariants(db)


# --- is_driver_free rules ---------------------------------------------------------------
def make_driver(shift):
    return SimpleNamespace(id=1, shift=shift)  # id 1 -> rest days Tuesday + Wednesday


def test_day_driver_blocked_on_working_day_free_on_rest_day():
    driver = make_driver("day")
    working = datetime(2026, 1, 4, 9)  # Sunday, a working day for this driver
    ok, reason = is_driver_free(driver, working, working.replace(hour=13), [])
    assert not ok and "shift" in reason
    rest = datetime(2026, 1, 6, 9)  # Tuesday, rest day
    assert is_driver_free(driver, rest, rest.replace(hour=13), []) == (True, "ok")


def test_night_driver_rest_rule():
    driver = make_driver("night")
    # Sunday night shift ends Monday 06:00, so Monday 09:00 is only 3h later.
    morning = datetime(2026, 1, 5, 9)
    ok, reason = is_driver_free(driver, morning, morning.replace(hour=13), [])
    assert not ok and "rest" in reason
    afternoon = datetime(2026, 1, 5, 14)  # exactly 8h after 06:00, allowed
    assert is_driver_free(driver, afternoon, afternoon.replace(hour=18), [])[0]


def test_unavailability_blocks_booking():
    driver = make_driver("day")
    row = SimpleNamespace(
        driver_id=1, start_time=datetime(2026, 1, 6), end_time=datetime(2026, 1, 8), reason="annual leave"
    )
    start = datetime(2026, 1, 6, 9)
    ok, reason = is_driver_free(driver, start, start.replace(hour=13), [row])
    assert not ok and "annual leave" in reason


# --- Scenario: trainer leave ------------------------------------------------------------
def count_where(db, model, *conditions):
    return db.scalar(select(func.count()).select_from(model).where(*conditions))


def test_trainer_leave_only_cancels_after_event_date(db):
    event = scenarios.SCENARIO_EVENTS[0]
    trainer_id = event.params["trainer_id"]
    event_start = datetime.combine(event.date, time.min)
    in_window = count_where(
        db, TrainingSession, TrainingSession.trainer_id == trainer_id, TrainingSession.start_time >= event_start
    )
    assert in_window > 0  # on paper the trainer has sessions in the window

    advance(db, (event.date - SIM_START.date()).days)  # clock at event date 00:00; event day not processed yet
    assert get_sim_now(db).date() == event.date
    assert count_where(db, TrainingSession, TrainingSession.status == "cancelled") == 0
    assert count_where(db, AuditLog, AuditLog.action == "scenario_event_applied") == 0

    summary = advance(db, 1)
    assert summary.scenario_events_applied == [event.key]
    cancelled = list(db.scalars(select(TrainingSession).where(TrainingSession.status == "cancelled")))
    assert cancelled and all(s.trainer_id == trainer_id for s in cancelled)
    assert all(s.start_time >= event_start for s in cancelled)

    advance(db, 30)  # the event never runs twice
    assert count_where(db, AuditLog, AuditLog.action == "scenario_event_applied") == 1


# --- Year end ---------------------------------------------------------------------------
def test_cannot_advance_past_year_end(db):
    summary = advance(db, 500)
    assert summary.hit_year_end
    assert get_sim_now(db) == SIM_END
    assert summary.days_advanced == 365

    again = advance(db, 5)
    assert again.days_advanced == 0
    assert get_sim_now(db) == SIM_END


def test_one_audit_row_per_advance_call(db):
    advance(db, 3)
    advance(db, 2)
    rows = list(db.scalars(select(AuditLog).where(AuditLog.action == "sim_advanced").order_by(AuditLog.id)))
    assert len(rows) == 2 and rows[0].details["days_advanced"] == 3
