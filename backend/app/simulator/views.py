"""Read-only SQL views that make the synthetic data readable (names instead of ids).

Views only: no tables change. They are plain CREATE VIEW statements. SQLite and Postgres
spell a few things differently (dates, weekday names, JSON), so ``_dialect_snippets`` supplies
those few expressions and everything else in the views is shared SQL.

Run automatically at the end of the seed. Drop them before dropping tables (Postgres refuses to
drop a table that a view depends on).
"""
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

VIEW_NAMES = ["v_sessions", "v_enrollments", "v_course_progress", "v_unavailability", "v_audit"]


def _dialect_snippets(dialect: str) -> dict:
    """Small per-database SQL pieces. Each function takes a SQL expression and returns SQL."""
    if dialect == "sqlite":
        weekday_names = " ".join(
            f"WHEN '{n}' THEN '{name}'"
            for n, name in enumerate(["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
        )
        return {
            "date": lambda c: f"date({c})",
            "time": lambda c: f"strftime('%H:%M', {c})",
            "weekday": lambda c: f"CASE strftime('%w', {c}) {weekday_names} END",
            "days_between": lambda a, b: f"CAST(julianday({b}) - julianday({a}) AS INTEGER)",
            "day_before": lambda c: f"date({c}, '-1 day')",
            "json_text": lambda c, key: f"json_extract({c}, '$.{key}')",
            "json_len": lambda c, key: f"json_array_length({c}, '$.{key}')",
        }
    if dialect == "postgresql":
        return {
            "date": lambda c: f"CAST({c} AS DATE)",
            "time": lambda c: f"to_char({c}, 'HH24:MI')",
            "weekday": lambda c: f"trim(to_char({c}, 'Day'))",
            "days_between": lambda a, b: f"(CAST({b} AS DATE) - CAST({a} AS DATE))",
            "day_before": lambda c: f"(CAST({c} AS DATE) - 1)",
            "json_text": lambda c, key: f"(CAST({c} AS JSONB) ->> '{key}')",
            "json_len": lambda c, key: f"jsonb_array_length(CAST({c} AS JSONB) -> '{key}')",
        }
    raise NotImplementedError(f"No view SQL for database dialect '{dialect}'")


def _view_sql(dialect: str) -> dict[str, str]:
    s = _dialect_snippets(dialect)
    txt = lambda expr: f"CAST({expr} AS TEXT)"  # noqa: E731  (tiny helper to keep the SQL below readable)

    # booked_count = seats in use (booked + attended + no_show); cancelled bookings are not counted.
    v_sessions = f"""
    CREATE VIEW v_sessions AS
    SELECT
        ts.id AS session_id,
        c.name AS course,
        t.name AS trainer,
        {s['weekday']('ts.start_time')} AS weekday,
        {s['date']('ts.start_time')} AS session_date,
        {s['time']('ts.start_time')} AS start_time,
        {s['time']('ts.end_time')} AS end_time,
        ts.location AS location,
        ts.capacity AS capacity,
        (SELECT COUNT(*) FROM enrollments e
          WHERE e.session_id = ts.id AND e.status <> 'cancelled') AS booked_count,
        (SELECT COUNT(*) FROM enrollments e
          WHERE e.session_id = ts.id AND e.status = 'attended') AS attended_count,
        ROUND(100.0 * (SELECT COUNT(*) FROM enrollments e
          WHERE e.session_id = ts.id AND e.status <> 'cancelled') / NULLIF(ts.capacity, 0), 1) AS fill_rate_pct,
        ts.status AS status
    FROM training_sessions ts
    JOIN courses c ON c.id = ts.course_id
    JOIN trainers t ON t.id = ts.trainer_id
    ORDER BY ts.start_time, ts.id
    """

    v_enrollments = f"""
    CREATE VIEW v_enrollments AS
    SELECT
        d.employee_code AS driver_code,
        d.name AS driver_name,
        d.shift AS shift,
        d.nationality AS nationality,
        c.name AS course,
        {s['date']('ts.start_time')} AS session_date,
        {s['time']('ts.start_time')} AS session_time,
        t.name AS trainer,
        e.status AS enrollment_status
    FROM enrollments e
    JOIN drivers d ON d.id = e.driver_id
    JOIN training_sessions ts ON ts.id = e.session_id
    JOIN courses c ON c.id = ts.course_id
    JOIN trainers t ON t.id = ts.trainer_id
    ORDER BY ts.start_time, d.employee_code
    """

    v_course_progress = """
    CREATE VIEW v_course_progress AS
    SELECT
        c.name AS course,
        CASE WHEN c.is_mandatory THEN 'yes' ELSE 'no' END AS mandatory,
        tt.year AS target_year,
        tt.target_completions AS target,
        (SELECT COUNT(*) FROM enrollments e JOIN training_sessions ts ON ts.id = e.session_id
          WHERE ts.course_id = c.id AND e.status = 'attended') AS attended_so_far,
        (SELECT COUNT(*) FROM enrollments e JOIN training_sessions ts ON ts.id = e.session_id
          WHERE ts.course_id = c.id AND e.status = 'booked' AND ts.status = 'scheduled') AS upcoming_booked,
        ROUND(100.0 * (SELECT COUNT(*) FROM enrollments e JOIN training_sessions ts ON ts.id = e.session_id
          WHERE ts.course_id = c.id AND e.status = 'attended') / NULLIF(tt.target_completions, 0), 1) AS pct_of_target
    FROM courses c
    JOIN training_targets tt ON tt.course_id = c.id
    ORDER BY c.id
    """

    # end_time is stored as midnight *after* the last day, so the last day shown is one day earlier.
    v_unavailability = f"""
    CREATE VIEW v_unavailability AS
    SELECT
        d.employee_code AS driver_code,
        d.name AS driver_name,
        d.shift AS shift,
        {s['date']('u.start_time')} AS start_date,
        {s['day_before']('u.end_time')} AS end_date,
        {s['days_between']('u.start_time', 'u.end_time')} AS number_of_days,
        u.reason AS reason
    FROM driver_unavailability u
    JOIN drivers d ON d.id = u.driver_id
    ORDER BY u.start_time, d.employee_code
    """

    details = "a.details"
    v_audit = f"""
    CREATE VIEW v_audit AS
    SELECT
        a.timestamp AS timestamp,
        a.actor AS actor,
        a.action AS action,
        CASE a.action
            WHEN 'seed_created' THEN
                'Seed ' || {txt(s['json_text'](details, 'seed'))} || ' created the database'
            WHEN 'sim_advanced' THEN
                'Advanced ' || {txt(s['json_text'](details, 'days_advanced'))} || ' days: '
                || {txt(s['json_text'](details, 'attended'))} || ' attended, '
                || {txt(s['json_text'](details, 'no_shows'))} || ' no-shows, '
                || {txt(s['json_text'](details, 'new_bookings'))} || ' new bookings'
            WHEN 'scenario_event_applied' THEN
                {txt(s['json_text'](details, 'description'))} || ' ('
                || {txt(s['json_len'](details, 'sessions_cancelled'))} || ' sessions cancelled)'
            ELSE SUBSTR({txt(details)}, 1, 120)
        END AS summary
    FROM audit_log a
    ORDER BY a.id
    """
    return {
        "v_sessions": v_sessions,
        "v_enrollments": v_enrollments,
        "v_course_progress": v_course_progress,
        "v_unavailability": v_unavailability,
        "v_audit": v_audit,
    }


def drop_views(engine: Engine) -> None:
    """Remove the views (safe if they do not exist). Call before dropping tables."""
    with engine.begin() as conn:
        for name in VIEW_NAMES:
            conn.execute(text(f"DROP VIEW IF EXISTS {name}"))


def create_views(db: Session) -> None:
    """(Re)create all views on the database behind ``db`` and commit."""
    dialect = db.get_bind().dialect.name
    statements = _view_sql(dialect)
    for name in VIEW_NAMES:
        db.execute(text(f"DROP VIEW IF EXISTS {name}"))
        db.execute(text(statements[name]))
    db.commit()
