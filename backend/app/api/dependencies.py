from fastapi import Depends
from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated
import hmac

from app.core.config import get_settings
from app.db.session import get_db
from app.services.attendance_service import AttendanceService
from app.services.employee_service import EmployeeService


def get_employee_service(db: Session = Depends(get_db)) -> EmployeeService:
    return EmployeeService(db)


def get_attendance_service(db: Session = Depends(get_db)) -> AttendanceService:
    return AttendanceService(db)


def require_superadmin_key(
    x_superadmin_key: Annotated[str | None, Header(alias="X-Superadmin-Key")] = None,
) -> None:
    settings = get_settings()
    expected = (settings.superadmin_key or "").strip()
    provided = (x_superadmin_key or "").strip()

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPERADMIN_KEY is not configured",
        )

    if not provided:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing superadmin key")

    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid superadmin key")
