from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from tests.conftest import make_seeded_engine


def test_state_advance_progress_reset():
    engine = make_seeded_engine()

    def override_db():
        with Session(engine, expire_on_commit=False, autoflush=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)  # no `with`: skips startup, so training.db is untouched
        state = client.get("/api/sim/state").json()
        assert state["current_time"].startswith("2026-01-01") and state["totals"]["drivers"] == 300

        summary = client.post("/api/sim/advance", json={"days": 7}).json()
        assert summary["days_advanced"] == 7 and len(summary["days"]) == 7

        assert client.post("/api/sim/advance", json={"days": 0}).status_code == 422
        assert client.post("/api/sim/advance", json={"days": 91}).status_code == 422

        progress = client.get("/api/sim/progress").json()
        assert len(progress) == 8 and {"target", "attended", "booked_upcoming"} <= set(progress[0])

        state = client.post("/api/sim/reset", json={"seed": 42}).json()
        assert state["current_time"].startswith("2026-01-01") and state["seed"] == 42
    finally:
        app.dependency_overrides.clear()
