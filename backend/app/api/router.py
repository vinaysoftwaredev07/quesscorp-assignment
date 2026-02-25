from fastapi import APIRouter

from app.api.attendance import router as attendance_router
from app.api.employees import router as employees_router
from app.api.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(employees_router)
api_router.include_router(attendance_router)
