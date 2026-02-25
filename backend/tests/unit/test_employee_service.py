from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exceptions import ConflictException, NotFoundException
from app.schemas.employee import EmployeeCreate
from app.services.employee_service import EmployeeService


def build_payload() -> EmployeeCreate:
    return EmployeeCreate(
        employee_id="EMP001",
        full_name="John Doe",
        email="john@company.com",
        department="Engineering",
    )


def test_create_employee_success() -> None:
    db = Mock()
    repo = Mock()
    payload = build_payload()

    repo.get_by_employee_id.return_value = None
    repo.get_by_email.return_value = None
    repo.create.return_value = SimpleNamespace(employee_id="EMP001")

    service = EmployeeService(db=db, repository=repo)
    result = service.create_employee(payload)

    assert result.employee_id == "EMP001"
    repo.create.assert_called_once()
    db.commit.assert_called_once()


def test_create_employee_raises_conflict_on_duplicate_id() -> None:
    db = Mock()
    repo = Mock()
    payload = build_payload()

    repo.get_by_employee_id.return_value = SimpleNamespace(employee_id="EMP001")

    service = EmployeeService(db=db, repository=repo)

    with pytest.raises(ConflictException):
        service.create_employee(payload)

    db.commit.assert_not_called()


def test_create_employee_raises_conflict_on_duplicate_email() -> None:
    db = Mock()
    repo = Mock()
    payload = build_payload()

    repo.get_by_employee_id.return_value = None
    repo.get_by_email.return_value = SimpleNamespace(email="john@company.com")

    service = EmployeeService(db=db, repository=repo)

    with pytest.raises(ConflictException):
        service.create_employee(payload)

    db.commit.assert_not_called()


def test_delete_employee_not_found() -> None:
    db = Mock()
    repo = Mock()
    repo.get_by_employee_id.return_value = None

    service = EmployeeService(db=db, repository=repo)

    with pytest.raises(NotFoundException):
        service.delete_employee("EMP404")

    db.commit.assert_not_called()


def test_delete_employee_success() -> None:
    db = Mock()
    repo = Mock()
    employee = SimpleNamespace(employee_id="EMP001")
    repo.get_by_employee_id.return_value = employee

    service = EmployeeService(db=db, repository=repo)
    service.delete_employee("EMP001")

    repo.delete.assert_called_once_with(employee)
    db.commit.assert_called_once()
