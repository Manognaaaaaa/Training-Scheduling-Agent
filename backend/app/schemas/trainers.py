from pydantic import BaseModel, ConfigDict, Field


class TrainerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    max_sessions_per_week: int = Field(5, ge=1, le=20)


class TrainerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    max_sessions_per_week: int | None = Field(None, ge=1, le=20)


class TrainerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    max_sessions_per_week: int
    sessions_this_week: int = 0  # week containing sim now (Sunday to Saturday), cancelled not counted
    warnings: list[str] = []  # filled on update when the new limit is already exceeded in a future week
