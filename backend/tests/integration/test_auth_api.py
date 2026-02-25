from app.core.config import get_settings


def test_enter_auth_success(public_client) -> None:
    response = public_client.post(
        "/api/auth/enter",
        json={"key": get_settings().superadmin_key},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Access granted"


def test_enter_auth_invalid_key(public_client) -> None:
    response = public_client.post("/api/auth/enter", json={"key": "invalid-key-value"})

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid superadmin key"


def test_protected_endpoint_requires_key(public_client) -> None:
    response = public_client.get("/api/employees")

    assert response.status_code == 401
    assert response.json()["message"] == "Missing superadmin key"
