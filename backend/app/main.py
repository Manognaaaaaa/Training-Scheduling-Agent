from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registers all tables on Base.metadata)
from app.config import settings
from app.database import Base, engine
from app.routers import health, sim


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create any missing tables when the server starts."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Lets the React app (port 5173) call this API (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(sim.router, prefix="/api")
