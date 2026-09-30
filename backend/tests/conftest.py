import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.simulator.seed import reseed

SEED = 42


def make_seeded_engine(seed: int = SEED):
    """A brand-new in-memory SQLite database, already seeded."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    reseed(engine, seed)
    return engine


@pytest.fixture()
def engine():
    return make_seeded_engine()


@pytest.fixture()
def db(engine):
    with Session(engine, expire_on_commit=False, autoflush=False) as session:
        yield session
