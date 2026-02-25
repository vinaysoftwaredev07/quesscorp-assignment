from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmployeeCreate(BaseModel):
    employee_id: str = Field(..., min_length=2, max_length=32)
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    department: str = Field(..., min_length=2, max_length=100)


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    full_name: str
    email: EmailStr
    department: str
    created_at: datetime
