from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.attendance import AttendanceStatus


class AttendanceCreate(BaseModel):
    employee_id: str = Field(..., min_length=2, max_length=32)
    date: date
    status: AttendanceStatus


class AttendanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    date: date
    status: AttendanceStatus
    created_at: datetime


class AttendanceSummary(BaseModel):
    employee_id: str
    total_records: int
    total_present: int
    records: list[AttendanceRead]
