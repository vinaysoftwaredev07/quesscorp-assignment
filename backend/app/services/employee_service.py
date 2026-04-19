from typing import Callable, Protocol

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.employee_repository import EmployeeRepository, EmployeeRepositoryInterface
from app.schemas.employee import EmployeeCreate


class EmployeeServiceInterface(Protocol):
    def create_employee(self, payload: EmployeeCreate): ...
    def list_employees(self): ...
    def delete_employee(self, employee_id: str) -> None: ...


class EmployeeService(EmployeeServiceInterface):
    def __init__(
        self,
        db: Session,
        repository: EmployeeRepositoryInterface | None = None,
        event_publisher: Callable[..., None] | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or EmployeeRepository(db)
        self.event_publisher = event_publisher

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
        if self.event_publisher:
            self.event_publisher(
                domain="employee",
                action="created",
                payload={
                    "employee_id": employee.employee_id,
                    "full_name": employee.full_name,
                    "email": employee.email,
                    "department": employee.department,
                },
            )
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
        if self.event_publisher:
            self.event_publisher(
                domain="employee",
                action="deleted",
                payload={
                    "employee_id": employee.employee_id,
                    "email": employee.email,
                },
            )
