from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Shift = Literal["day", "night", "rotating"]


class DriverCreate(BaseModel):
    employee_code: str | None = Field(None, min_length=1, max_length=20)  # auto DRV-xxxx if empty
    name: str = Field(min_length=1, max_length=100)
    nationality: str = Field(min_length=1, max_length=50)
    shift: Shift
    depot: str = Field(min_length=1, max_length=50)
    hire_date: date
    is_active: bool = True


class DriverUpdate(BaseModel):
    employee_code: str | None = Field(None, min_length=1, max_length=20)
    name: str | None = Field(None, min_length=1, max_length=100)
    nationality: str | None = Field(None, min_length=1, max_length=50)
    shift: Shift | None = None
    depot: str | None = Field(None, min_length=1, max_length=50)
    hire_date: date | None = None
    is_active: bool | None = None


class DriverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    name: str
    nationality: str
    shift: str
    depot: str
    hire_date: date
    is_active: bool


class DriverBooking(BaseModel):
    enrollment_id: int
    session_id: int
    course_code: str
    course_name: str
    session_start: datetime
    session_status: str
    status: str  # enrollment status


class DriverDetail(DriverOut):
    history: list[DriverBooking]
    upcoming: list[DriverBooking]


class DriverDeactivated(DriverOut):
    cancelled_bookings: int


class DriverOptions(BaseModel):
    nationalities: list[str]
    shifts: list[str]
    depots: list[str]


class UnavailabilityCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    reason: str = Field(min_length=1, max_length=100)


class UnavailabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    driver_id: int
    start_time: datetime
    end_time: datetime
    reason: str
    cancelled_bookings: int = 0  # only filled when a block was just added
