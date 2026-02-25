from pydantic import BaseModel, Field


class SuperAdminKeyRequest(BaseModel):
    key: str = Field(..., min_length=8, max_length=255)


class AuthResponse(BaseModel):
    message: str
