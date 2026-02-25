import hmac

from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.schemas.auth import AuthResponse, SuperAdminKeyRequest

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/enter", response_model=AuthResponse, status_code=status.HTTP_200_OK)
def enter_admin(payload: SuperAdminKeyRequest) -> AuthResponse:
    settings = get_settings()
    expected = (settings.superadmin_key or "").strip()
    provided = (payload.key or "").strip()

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPERADMIN_KEY is not configured",
        )

    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid superadmin key")

    return AuthResponse(message="Access granted")
