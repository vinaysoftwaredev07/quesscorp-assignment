from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_employee_service, require_superadmin_key
from app.schemas.common import MessageResponse
from app.schemas.employee import EmployeeCreate, EmployeeRead
from app.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["Employees"], dependencies=[Depends(require_superadmin_key)])


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    service: Annotated[EmployeeService, Depends(get_employee_service)],
):
    return service.create_employee(payload)


@router.get("", response_model=list[EmployeeRead], status_code=status.HTTP_200_OK)
def list_employees(service: Annotated[EmployeeService, Depends(get_employee_service)]):
    return service.list_employees()


@router.delete("/{employee_id}", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def delete_employee(
    employee_id: str,
    service: Annotated[EmployeeService, Depends(get_employee_service)],
):
    service.delete_employee(employee_id)
    return MessageResponse(message="Employee deleted successfully")
