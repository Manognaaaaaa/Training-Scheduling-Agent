from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    duration_hours: int = Field(ge=1, le=40)
    default_capacity: int = Field(ge=1, le=30)
    is_mandatory: bool = False
    target_completions: int | None = Field(None, ge=0)  # target for SIM_YEAR


class CourseUpdate(BaseModel):
    code: str | None = Field(None, min_length=1, max_length=20)
    name: str | None = Field(None, min_length=1, max_length=100)
    duration_hours: int | None = Field(None, ge=1, le=40)
    default_capacity: int | None = Field(None, ge=1, le=30)
    is_mandatory: bool | None = None
    target_completions: int | None = Field(None, ge=0)


class CourseOut(BaseModel):
    id: int
    code: str
    name: str
    duration_hours: int
    default_capacity: int
    is_mandatory: bool
    target_completions: int | None  # for SIM_YEAR; None if no target row
