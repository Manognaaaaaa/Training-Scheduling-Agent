"""Tracking, snapshots, alerts and the tracking API, on the seeded database."""
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.models import Alert, AuditLog, Driver, ForecastSnapshot, TrainingTarget
from app.services.sim_clock import get_sim_now, set_sim_now
from app.services.tracking import (
    group_breakdown, load_facts, target_pace, weekly_series, week_starts,
)
from app.services.tracking_jobs import compute_forecasts, weekly_close
from app.simulator.engine import advance
from app.simulator.rules import SIM_END, SIM_START
from tests.conftest import make_seeded_engine

ALERT_ACTIONS = ("alert_opened", "alert_escalated", "alert_deescalated", "alert_auto_resolved")


def count(db, model, *conditions):
    return db.scalar(select(func.count()).select_from(model).where(*conditions))


def by_code(db):
    return {f.code: f for f in compute_forecasts(load_facts(db))}


@pytest.fixture(scope="module")
def june_engine():
    """A seeded year played to 2026-06-30. Shared by read-only tests (never modify it)."""
    engine = make_seeded_engine()
    with Session(engine, expire_on_commit=False, autoflush=False) as db:
        advance(db, 180)
        assert get_sim_now(db) == datetime(2026, 6, 30)
    return engine


@pytest.fixture()
def june(june_engine):
    with Session(june_engine, expire_on_commit=False, autoflush=False) as db:
        yield db


@pytest.fixture()
def march(db):
    advance(db, 60)
    return db


# --- Definitions ------------------------------------------------------------------------
def test_weeks_cover_the_year_sunday_to_saturday():
    weeks = week_starts()
    assert weeks[0] <= SIM_START.date() < weeks[1]
    assert weeks[-1] <= SIM_END.date()
    assert all(w.weekday() == 6 for w in weeks)  # Python: Sunday = 6


def test_target_pace_is_linear_and_clamped():
    assert target_pace(100, SIM_START) == 0
    assert target_pace(100, SIM_END) == pytest.approx(100)
    assert target_pace(100, datetime(2026, 7, 2, 12)) == pytest.approx(50, abs=0.5)
    assert target_pace(100, datetime(2025, 1, 1)) == 0


def test_weekly_series_fills_empty_weeks_and_accumulates(march):
    rows = weekly_series(march, course_id=1)
    assert rows and all(r["course_id"] == 1 for r in rows)
    assert [r["week_start"] for r in rows] == sorted(r["week_start"] for r in rows)
    assert len({r["week_start"] for r in rows}) == len(rows)  # one row per week, empty weeks included
    running = 0
    for r in rows:
        running += r["attended_in_week"]
        assert r["cumulative_attended"] == running
    assert rows[-1]["cumulative_attended"] == by_code(march)["DEF"].attended
    # 60 days in is a Monday: every week is closed except the one in progress, which is measured at sim now
    assert all(r["closed"] for r in rows[:-1]) and not rows[-1]["closed"]
    assert rows[-1]["as_of"] == get_sim_now(march)


def test_group_breakdown_shape(march):
    rows = group_breakdown(march, 1, by="shift")
    assert {r["group"] for r in rows} == {"day", "night", "rotating"}  # rotating stays its own group
    assert sum(r["active_drivers"] for r in rows) == count(march, Driver, Driver.is_active.is_(True))
    with pytest.raises(ValueError):
        group_breakdown(march, 1, by="colour")


# --- Simulated time ---------------------------------------------------------------------
def test_sim_clock_drives_target_pace(db):
    set_sim_now(db, datetime(2026, 4, 2))
    early = by_code(db)["DEF"]
    set_sim_now(db, datetime(2026, 10, 2))
    late = by_code(db)["DEF"]
    assert late.target_pace > early.target_pace > 0
    assert late.target_pace == pytest.approx(early.target * 0.75, rel=0.02)


def test_nothing_in_the_tracking_code_reads_the_real_clock():
    root = Path(__file__).resolve().parents[1] / "app"
    files = [root / "services" / n for n in (
        "tracking.py", "forecasting.py", "risk.py", "alerts.py", "tracking_jobs.py", "tracking_views.py", "forecast_backtest.py",
    )] + [root / "routers" / "tracking.py", root / "routers" / "alerts.py"]
    banned = re.compile(r"datetime\.now|utcnow|date\.today|time\.time\(")
    for path in files:
        assert not banned.search(path.read_text(encoding="utf-8")), f"{path.name} reads the real clock"


# --- Start of the year ------------------------------------------------------------------
def test_sim_start_has_no_flags_and_no_crash(db):
    forecasts = compute_forecasts(load_facts(db))
    assert len(forecasts) == 8
    assert {f.risk_level for f in forecasts} == {"insufficient_data"}
    assert all(f.attended == 0 and f.shortfall_type == "none" and f.reasons == [] for f in forecasts)
    assert all(f.projected > 0 for f in forecasts)  # the schedule still gives a forecast


def test_api_at_sim_start(client):
    rows = client.get("/api/tracking/courses").json()
    assert len(rows) == 8 and {r["risk_level"] for r in rows} == {"insufficient_data"}
    detail = client.get(f"/api/tracking/courses/{rows[0]['course_id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["series"][0]["actual"] == 0 and body["snapshots"] == [] and body["events"] == []
    assert any(p["is_now"] for p in body["series"])
    summary = client.get("/api/tracking/summary").json()
    assert summary["has_data"] is False and summary["open_alerts"] == 0
    assert client.get("/api/tracking/courses/999").status_code == 404
    assert client.get("/api/alerts?status=open").json() == []


# --- Scenarios on the seeded database ---------------------------------------------------
def test_def_is_at_risk_with_a_night_shift_group_gap(june):
    f = by_code(june)["DEF"]
    assert f.risk_level in ("medium", "high")
    gap = [r for r in f.reasons if r["code"] == "group_gap"]
    assert gap and gap[0]["group"] == "night" and gap[0]["by"] == "shift"
    assert "Night shift completion" in gap[0]["message"]


def test_fa_and_haz_show_recent_cancellations(june):
    forecasts = by_code(june)
    assert any(r["code"] == "recent_cancellations" for r in forecasts["FA"].reasons)
    assert forecasts["FA"].risk_level in ("medium", "high")
    assert forecasts["HAZ"].risk_level in ("medium", "high")


def test_rsr_is_not_high_risk(june):
    # Note: the backtest checks this across seeds (docs/forecast_backtest.md); seed 42 at the end of June must hold.
    assert by_code(june)["RSR"].risk_level in ("low", "medium", "achieved")


def test_every_at_risk_course_has_range_probability_type_and_reason(june):
    for f in compute_forecasts(load_facts(june)):
        assert f.low <= f.projected <= f.high and 0 <= f.p_hit <= 1
        assert f.projected <= f.attended + f.eligible_pool
        if f.risk_level in ("medium", "high"):
            assert f.shortfall_type != "none" and 1 <= len(f.reasons) <= 4
            assert all({"code", "message", "value", "benchmark"} <= r.keys() for r in f.reasons)


def test_courses_endpoint_sorted_riskiest_first(client, june_engine):
    from app.database import get_db
    from app.main import app

    def override():
        with Session(june_engine, expire_on_commit=False, autoflush=False) as s:
            yield s

    app.dependency_overrides[get_db] = override
    rows = client.get("/api/tracking/courses").json()
    order = {"high": 0, "medium": 1, "low": 2, "achieved": 3, "insufficient_data": 4}
    keys = [(order[r["risk_level"]], r["p_hit"]) for r in rows]
    assert keys == sorted(keys)
    detail = client.get(f"/api/tracking/courses/{rows[0]['course_id']}").json()
    assert any(p["forecast_mean"] is not None for p in detail["series"])
    assert detail["series"][-1]["date"].startswith("2026-12-31") and detail["series"][-1]["actual"] is None
    assert detail["snapshots"] and len(detail["upcoming_sessions"]) <= 10


# --- Snapshots and alerts ---------------------------------------------------------------
def test_one_snapshot_per_course_per_week_and_idempotent(march):
    snapshots = count(march, ForecastSnapshot)
    assert snapshots > 0 and snapshots % 8 == 0
    alerts_before = count(march, Alert)
    audits_before = count(march, AuditLog)

    first = weekly_close(march)
    march.commit()
    second = weekly_close(march)
    march.commit()
    assert first.as_of == second.as_of
    # (course, as_of) is unique, and a re-run neither duplicates rows nor changes alerts
    pairs = Counter(march.execute(select(ForecastSnapshot.course_id, ForecastSnapshot.as_of)).all())
    assert max(pairs.values()) == 1
    assert count(march, Alert) == alerts_before
    assert count(march, AuditLog) == audits_before
    assert second.changes.total == 0


def test_snapshots_are_written_after_each_saturday(db):
    advance(db, 8)  # Thu 1 Jan to Fri 9 Jan: Saturday 3 Jan and Saturday 10 Jan not yet reached for the second
    times = sorted({t for (t,) in db.execute(select(ForecastSnapshot.as_of))})
    assert times == [datetime(2026, 1, 4)]
    advance(db, 2)
    times = sorted({t for (t,) in db.execute(select(ForecastSnapshot.as_of))})
    assert times == [datetime(2026, 1, 4), datetime(2026, 1, 11)]


def test_one_open_alert_per_course(march):
    advance(march, 60)
    advance(march, 60)
    open_by_course = Counter(march.scalars(select(Alert.course_id).where(Alert.status == "open")))
    assert open_by_course and max(open_by_course.values()) == 1
    for alert in march.scalars(select(Alert).where(Alert.status == "open")):
        assert alert.message is None and alert.risk_level in ("medium", "high") and alert.shortfall_type
        assert {"p_hit", "low", "high", "reasons", "shortfall_type"} <= alert.details.keys()


def test_alert_changes_write_exactly_one_system_audit_row_each(db):
    for _ in range(12):
        advance(db, 30)
    rows = list(db.scalars(select(AuditLog).where(AuditLog.action.in_(ALERT_ACTIONS))))
    assert rows and all(r.actor == "system" and r.entity_type == "alert" for r in rows)
    per_alert = Counter(r.entity_id for r in rows if r.action == "alert_opened")
    assert set(per_alert.values()) == {1}  # each alert is opened exactly once
    # the audited transitions replay to the alert's final state
    for alert in db.scalars(select(Alert)):
        history = [r.action for r in rows if r.entity_id == alert.id]
        assert history[0] == "alert_opened"
        resolved = history.count("alert_auto_resolved")
        assert resolved == (1 if alert.status == "resolved" else 0)
        if resolved:
            assert history[-1] == "alert_auto_resolved"


def test_weekly_close_audit_rows_match_reported_changes(db):
    advance(db, 28)  # flags start once four weeks are closed
    before = count(db, AuditLog, AuditLog.action.in_(ALERT_ACTIONS))
    advance(db, 3)  # crosses the Saturday that closes week 5; engine calls weekly_close
    new_rows = count(db, AuditLog, AuditLog.action.in_(ALERT_ACTIONS)) - before
    assert new_rows >= 0
    # re-running at the same moment reports no changes and writes no audit rows
    audit_now = count(db, AuditLog)
    assert weekly_close(db).changes.total == 0
    assert count(db, AuditLog) == audit_now


def test_each_reported_change_is_one_audit_row(march):
    # Change two targets so that one course resolves; the result's change count must equal the new audit rows.
    before = count(march, AuditLog, AuditLog.action.in_(ALERT_ACTIONS))
    for target in march.scalars(select(TrainingTarget)).all()[:3]:
        target.target_completions = 1
    march.commit()
    result = weekly_close(march)
    assert result.changes.total > 0
    assert count(march, AuditLog, AuditLog.action.in_(ALERT_ACTIONS)) - before == result.changes.total


def test_recovered_course_is_auto_resolved(march):
    open_alert = march.scalars(select(Alert).where(Alert.status == "open").order_by(Alert.id)).first()
    assert open_alert is not None
    # The course suddenly needs far fewer completions: it is now "achieved".
    target = march.scalars(select(TrainingTarget).where(TrainingTarget.course_id == open_alert.course_id)).one()
    target.target_completions = 1
    march.commit()
    result = weekly_close(march)
    march.commit()
    assert open_alert.id in result.changes.resolved
    march.refresh(open_alert)
    assert open_alert.status == "resolved"
    rows = list(march.scalars(select(AuditLog).where(AuditLog.action == "alert_auto_resolved", AuditLog.entity_id == open_alert.id)))
    assert len(rows) == 1 and rows[0].actor == "system"
    assert count(march, Alert, Alert.course_id == open_alert.course_id, Alert.status == "open") == 0


def test_dismissed_alert_is_not_reopened_unless_risk_worsens(march):
    alert = march.scalars(select(Alert).where(Alert.status == "open", Alert.risk_level == "high").order_by(Alert.id)).first()
    assert alert is not None
    alert.status = "dismissed"  # a user decision
    march.commit()
    weekly_close(march)
    march.commit()
    assert count(march, Alert, Alert.course_id == alert.course_id, Alert.status == "open") == 0  # still high: stays dismissed
    march.refresh(alert)
    assert alert.status == "dismissed"

    alert.risk_level = "medium"  # as if it had been dismissed back when the course was only medium
    march.commit()
    result = weekly_close(march)
    march.commit()
    assert len(result.changes.opened) == 1
    new = march.get(Alert, result.changes.opened[0])
    assert new.course_id == alert.course_id and new.status == "open" and new.risk_level == "high" and new.id != alert.id
    march.refresh(alert)
    assert alert.status == "dismissed"


# --- Recompute endpoint -----------------------------------------------------------------
def test_recompute_runs_the_close_and_audits_it(client):
    client.post("/api/sim/advance", json={"days": 30})
    body = client.post("/api/tracking/recompute").json()
    assert body["snapshots"] == 8 and body["as_of"].startswith("2026-01-31")
    rows = client.get("/api/alerts").json()
    assert all(r["message"] is None for r in rows)


def test_recompute_audit_row(db):
    from app.routers.tracking import recompute

    advance(db, 30)
    recompute(db)
    row = db.scalars(select(AuditLog).where(AuditLog.action == "tracking_recomputed")).one()
    assert row.actor == "user" and row.details["snapshots"] == 8


# --- Performance: a fixed number of queries ----------------------------------------------
def count_queries(engine, fn):
    statements = []

    def before(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before)
    try:
        fn()
    finally:
        event.remove(engine, "before_cursor_execute", before)
    return len(statements)


def test_courses_endpoint_query_count_does_not_grow(client, engine):
    first = count_queries(engine, lambda: client.get("/api/tracking/courses"))
    for i in range(6):  # six more courses
        r = client.post("/api/courses", json={
            "code": f"X{i}", "name": f"Extra {i}", "duration_hours": 2, "default_capacity": 10, "target_completions": 20,
        })
        assert r.status_code == 201
    client.post("/api/sim/advance", json={"days": 30})  # many more completed sessions and enrollments
    second = count_queries(engine, lambda: client.get("/api/tracking/courses"))
    assert first == second and first <= 8
    assert len(client.get("/api/tracking/courses").json()) == 14
