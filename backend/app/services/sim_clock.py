"""The simulated clock. Use this instead of datetime.now() everywhere "now" matters."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import SimState


def get_sim_now(db: Session) -> datetime:
    """Current simulated time (single row, id=1)."""
    state = db.get(SimState, 1)
    if state is None:
        raise RuntimeError("sim_state is empty: run `python -m app.simulator.seed --seed 42 --reset` first")
    return state.current_time


def set_sim_now(db: Session, new_time: datetime) -> None:
    """Move the simulated clock (the caller commits)."""
    state = db.get(SimState, 1)
    if state is None:
        db.add(SimState(id=1, current_time=new_time))
    else:
        state.current_time = new_time
