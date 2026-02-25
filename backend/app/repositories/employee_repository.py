from typing import Protocol

from sqlalchemy.orm import Session

from app.models.employee import Employee


class EmployeeRepositoryInterface(Protocol):
    def create(self, payload: dict) -> Employee: ...
    def get_all(self) -> list[Employee]: ...
    def get_by_employee_id(self, employee_id: str) -> Employee | None: ...
    def get_by_email(self, email: str) -> Employee | None: ...
    def delete(self, employee: Employee) -> None: ...


class EmployeeRepository(EmployeeRepositoryInterface):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: dict) -> Employee:
        employee = Employee(**payload)
        self.db.add(employee)
        self.db.flush()
        self.db.refresh(employee)
        return employee

    def get_all(self) -> list[Employee]:
        return self.db.query(Employee).order_by(Employee.created_at.desc()).all()

    def get_by_employee_id(self, employee_id: str) -> Employee | None:
        return self.db.query(Employee).filter(Employee.employee_id == employee_id).first()

    def get_by_email(self, email: str) -> Employee | None:
        return self.db.query(Employee).filter(Employee.email == email).first()

    def delete(self, employee: Employee) -> None:
        self.db.delete(employee)
