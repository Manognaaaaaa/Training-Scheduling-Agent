from sqlalchemy import text

from app.simulator.engine import advance
from app.simulator.views import VIEW_NAMES


def rows(db, view):
    return db.execute(text(f"SELECT * FROM {view}")).mappings().all()


def test_all_views_exist_and_have_rows(db):
    advance(db, 30)
    for name in VIEW_NAMES:
        assert rows(db, name), f"{name} is empty"


def test_view_values_are_readable_and_consistent(db):
    advance(db, 30)
    session = rows(db, "v_sessions")[0]
    assert session["weekday"] in {"Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"}
    assert len(session["start_time"]) == 5 and session["course"] and session["trainer"]
    for s in rows(db, "v_sessions"):
        assert s["booked_count"] <= s["capacity"]

    progress = {r["course"]: r for r in rows(db, "v_course_progress")}
    assert len(progress) == 8 and progress["Defensive Driving"]["mandatory"] == "yes"

    leave = rows(db, "v_unavailability")[0]
    assert leave["number_of_days"] >= 1 and leave["end_date"] >= leave["start_date"]

    summaries = [r["summary"] for r in rows(db, "v_audit")]
    assert summaries[0] == "Seed 42 created the database"
    assert any(x.startswith("Advanced 30 days") for x in summaries)
