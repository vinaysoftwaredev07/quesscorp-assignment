from datetime import date, datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.attendance import AttendanceStatus
from app.repositories.attendance_repository import AttendanceRepository, AttendanceRepositoryInterface
from app.repositories.employee_repository import EmployeeRepository, EmployeeRepositoryInterface
from app.schemas.attendance import AttendanceCreate, AttendanceSummary


class AttendanceServiceInterface(Protocol):
    def mark_attendance(self, payload: AttendanceCreate) -> tuple[object, bool]: ...
    def get_employee_attendance(
        self,
        employee_id: str,
        for_date: date | None = None,
        for_month: str | None = None,
    ) -> AttendanceSummary: ...


class AttendanceService(AttendanceServiceInterface):
    def __init__(
        self,
        db: Session,
        attendance_repository: AttendanceRepositoryInterface | None = None,
        employee_repository: EmployeeRepositoryInterface | None = None,
    ) -> None:
        self.db = db
        self.attendance_repository = attendance_repository or AttendanceRepository(db)
        self.employee_repository = employee_repository or EmployeeRepository(db)

    def mark_attendance(self, payload: AttendanceCreate) -> tuple[object, bool]:
        employee = self.employee_repository.get_by_employee_id(payload.employee_id)
        if not employee:
            raise NotFoundException(
                "Employee not found",
                details={"employee_id": payload.employee_id},
            )

        existing = self.attendance_repository.find_by_employee_and_date(payload.employee_id, payload.date)
        if existing:
            updated = self.attendance_repository.update_status(existing, payload.status)
            self.db.commit()
            return updated, False

        record = self.attendance_repository.create(payload.model_dump())
        self.db.commit()
        return record, True

    def get_employee_attendance(
        self,
        employee_id: str,
        for_date: date | None = None,
        for_month: str | None = None,
    ) -> AttendanceSummary:
        employee = self.employee_repository.get_by_employee_id(employee_id)
        if not employee:
            raise NotFoundException("Employee not found", details={"employee_id": employee_id})

        records = self.attendance_repository.get_by_employee(employee_id)
        month_start: date | None = None
        month_end: date | None = None

        if for_month:
            try:
                month_start = datetime.strptime(for_month, "%Y-%m").date().replace(day=1)
            except ValueError as error:
                raise BadRequestException(
                    "Invalid month format. Use YYYY-MM",
                    details={"month": for_month},
                ) from error

            if month_start.month == 12:
                next_month_start = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month_start = month_start.replace(month=month_start.month + 1)

            month_end = next_month_start
            records = [record for record in records if month_start <= record.date < month_end]

        if for_date:
            records = [record for record in records if record.date == for_date]

        if for_month or for_date:
            present_count = len([record for record in records if record.status == AttendanceStatus.PRESENT])
        else:
            present_count = self.attendance_repository.count_present_days(employee_id)

        return AttendanceSummary(
            employee_id=employee_id,
            total_records=len(records),
            total_present=present_count,
            records=records,
        )
