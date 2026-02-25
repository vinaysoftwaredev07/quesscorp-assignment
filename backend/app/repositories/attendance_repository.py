from datetime import date
from typing import Protocol

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attendance import Attendance, AttendanceStatus


class AttendanceRepositoryInterface(Protocol):
    def create(self, payload: dict) -> Attendance: ...
    def update_status(self, record: Attendance, status: AttendanceStatus) -> Attendance: ...
    def get_by_employee(self, employee_id: str) -> list[Attendance]: ...
    def find_by_employee_and_date(self, employee_id: str, on_date: date) -> Attendance | None: ...
    def count_present_days(self, employee_id: str) -> int: ...


class AttendanceRepository(AttendanceRepositoryInterface):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: dict) -> Attendance:
        record = Attendance(**payload)
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record

    def update_status(self, record: Attendance, status: AttendanceStatus) -> Attendance:
        record.status = status
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record

    def get_by_employee(self, employee_id: str) -> list[Attendance]:
        return (
            self.db.query(Attendance)
            .filter(Attendance.employee_id == employee_id)
            .order_by(Attendance.date.desc())
            .all()
        )

    def find_by_employee_and_date(self, employee_id: str, on_date: date) -> Attendance | None:
        return (
            self.db.query(Attendance)
            .filter(Attendance.employee_id == employee_id, Attendance.date == on_date)
            .first()
        )

    def count_present_days(self, employee_id: str) -> int:
        result = (
            self.db.query(func.count(Attendance.id))
            .filter(Attendance.employee_id == employee_id, Attendance.status == AttendanceStatus.PRESENT)
            .scalar()
        )
        return int(result or 0)
