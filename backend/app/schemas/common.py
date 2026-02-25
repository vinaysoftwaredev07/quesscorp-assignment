from datetime import datetime
from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    message: str
    details: dict | None = None


class TimestampedSchema(BaseModel):
    created_at: datetime
