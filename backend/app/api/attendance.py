from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_attendance_service, require_superadmin_key
from app.schemas.attendance import AttendanceCreate, AttendanceRead, AttendanceSummary
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/attendance", tags=["Attendance"], dependencies=[Depends(require_superadmin_key)])


@router.post("", response_model=AttendanceRead, status_code=status.HTTP_200_OK)
def mark_attendance(
    payload: AttendanceCreate,
    service: Annotated[AttendanceService, Depends(get_attendance_service)],
    response: Response,
):
    record, created = service.mark_attendance(payload)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return record


@router.get("/{employee_id}", response_model=AttendanceSummary, status_code=status.HTTP_200_OK)
def get_attendance(
    employee_id: str,
    service: Annotated[AttendanceService, Depends(get_attendance_service)],
    date_filter: Annotated[date | None, Query(alias="date")] = None,
    month_filter: Annotated[str | None, Query(alias="month")] = None,
):
    return service.get_employee_attendance(employee_id, date_filter, month_filter)
