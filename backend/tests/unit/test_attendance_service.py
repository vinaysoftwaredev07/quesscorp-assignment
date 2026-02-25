from datetime import date
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.attendance import AttendanceStatus
from app.schemas.attendance import AttendanceCreate
from app.services.attendance_service import AttendanceService


def test_mark_attendance_employee_not_found() -> None:
    db = Mock()
    attendance_repo = Mock()
    employee_repo = Mock()
    employee_repo.get_by_employee_id.return_value = None

    service = AttendanceService(db, attendance_repo, employee_repo)
    payload = AttendanceCreate(employee_id="EMP1", date=date(2026, 2, 25), status=AttendanceStatus.PRESENT)

    with pytest.raises(NotFoundException):
        service.mark_attendance(payload)

    db.commit.assert_not_called()


def test_mark_attendance_duplicate_same_date_updates_record() -> None:
    db = Mock()
    attendance_repo = Mock()
    employee_repo = Mock()

    employee_repo.get_by_employee_id.return_value = SimpleNamespace(employee_id="EMP1")
    existing = SimpleNamespace(id=1, employee_id="EMP1", status=AttendanceStatus.PRESENT)
    attendance_repo.find_by_employee_and_date.return_value = existing
    attendance_repo.update_status.return_value = existing

    service = AttendanceService(db, attendance_repo, employee_repo)
    payload = AttendanceCreate(employee_id="EMP1", date=date(2026, 2, 25), status=AttendanceStatus.ABSENT)

    result, created = service.mark_attendance(payload)

    assert created is False
    assert result.id == 1
    attendance_repo.update_status.assert_called_once_with(existing, AttendanceStatus.ABSENT)
    db.commit.assert_called_once()


def test_mark_attendance_success() -> None:
    db = Mock()
    attendance_repo = Mock()
    employee_repo = Mock()

    employee_repo.get_by_employee_id.return_value = SimpleNamespace(employee_id="EMP1")
    attendance_repo.find_by_employee_and_date.return_value = None
    attendance_repo.create.return_value = SimpleNamespace(id=11, employee_id="EMP1")

    service = AttendanceService(db, attendance_repo, employee_repo)
    payload = AttendanceCreate(employee_id="EMP1", date=date(2026, 2, 25), status=AttendanceStatus.PRESENT)

    result, created = service.mark_attendance(payload)

    assert created is True
    assert result.id == 11
    db.commit.assert_called_once()


def test_get_employee_attendance_with_date_filter() -> None:
    db = Mock()
    attendance_repo = Mock()
    employee_repo = Mock()

    employee_repo.get_by_employee_id.return_value = SimpleNamespace(employee_id="EMP1")
    attendance_repo.get_by_employee.return_value = [
        SimpleNamespace(
            id=1,
            employee_id="EMP1",
            date=date(2026, 2, 25),
            status=AttendanceStatus.PRESENT,
            created_at=datetime(2026, 2, 25, 10, 0, 0),
        ),
        SimpleNamespace(
            id=2,
            employee_id="EMP1",
            date=date(2026, 2, 24),
            status=AttendanceStatus.ABSENT,
            created_at=datetime(2026, 2, 24, 10, 0, 0),
        ),
    ]
    attendance_repo.count_present_days.return_value = 1

    service = AttendanceService(db, attendance_repo, employee_repo)
    summary = service.get_employee_attendance("EMP1", date(2026, 2, 25))

    assert summary.total_records == 1
    assert summary.total_present == 1
    assert summary.employee_id == "EMP1"


def test_get_employee_attendance_not_found() -> None:
    db = Mock()
    attendance_repo = Mock()
    employee_repo = Mock()
    employee_repo.get_by_employee_id.return_value = None

    service = AttendanceService(db, attendance_repo, employee_repo)

    with pytest.raises(NotFoundException):
        service.get_employee_attendance("UNKNOWN")


def test_get_employee_attendance_with_month_filter() -> None:
    db = Mock()
    attendance_repo = Mock()
    employee_repo = Mock()

    employee_repo.get_by_employee_id.return_value = SimpleNamespace(employee_id="EMP1")
    attendance_repo.get_by_employee.return_value = [
        SimpleNamespace(
            id=1,
            employee_id="EMP1",
            date=date(2026, 2, 25),
            status=AttendanceStatus.PRESENT,
            created_at=datetime(2026, 2, 25, 10, 0, 0),
        ),
        SimpleNamespace(
            id=2,
            employee_id="EMP1",
            date=date(2026, 2, 24),
            status=AttendanceStatus.ABSENT,
            created_at=datetime(2026, 2, 24, 10, 0, 0),
        ),
        SimpleNamespace(
            id=3,
            employee_id="EMP1",
            date=date(2026, 1, 30),
            status=AttendanceStatus.PRESENT,
            created_at=datetime(2026, 1, 30, 10, 0, 0),
        ),
    ]

    service = AttendanceService(db, attendance_repo, employee_repo)
    summary = service.get_employee_attendance("EMP1", for_month="2026-02")

    assert summary.total_records == 2
    assert summary.total_present == 1
    assert summary.records[0].date == date(2026, 2, 25)


def test_get_employee_attendance_with_invalid_month_filter() -> None:
    db = Mock()
    attendance_repo = Mock()
    employee_repo = Mock()

    employee_repo.get_by_employee_id.return_value = SimpleNamespace(employee_id="EMP1")
    attendance_repo.get_by_employee.return_value = []

    service = AttendanceService(db, attendance_repo, employee_repo)

    with pytest.raises(BadRequestException):
        service.get_employee_attendance("EMP1", for_month="2026/02")
