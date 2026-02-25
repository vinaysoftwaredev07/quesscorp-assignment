from typing import Protocol

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.employee_repository import EmployeeRepository, EmployeeRepositoryInterface
from app.schemas.employee import EmployeeCreate


class EmployeeServiceInterface(Protocol):
    def create_employee(self, payload: EmployeeCreate): ...
    def list_employees(self): ...
    def delete_employee(self, employee_id: str) -> None: ...


class EmployeeService(EmployeeServiceInterface):
    def __init__(self, db: Session, repository: EmployeeRepositoryInterface | None = None) -> None:
        self.db = db
        self.repository = repository or EmployeeRepository(db)

    def create_employee(self, payload: EmployeeCreate):
        if self.repository.get_by_employee_id(payload.employee_id):
            raise ConflictException(
                "Employee with this employee_id already exists",
                details={"employee_id": payload.employee_id},
            )

        if self.repository.get_by_email(payload.email):
            raise ConflictException(
                "Employee with this email already exists",
                details={"email": payload.email},
            )

        employee = self.repository.create(payload.model_dump())
        self.db.commit()
        return employee

    def list_employees(self):
        return self.repository.get_all()

    def delete_employee(self, employee_id: str) -> None:
        employee = self.repository.get_by_employee_id(employee_id)
        if not employee:
            raise NotFoundException(
                "Employee not found",
                details={"employee_id": employee_id},
            )

        self.repository.delete(employee)
        self.db.commit()
