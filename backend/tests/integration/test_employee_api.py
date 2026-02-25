def test_create_list_delete_employee_flow(client) -> None:
    create_response = client.post(
        "/api/employees",
        json={
            "employee_id": "EMP001",
            "full_name": "John Doe",
            "email": "john@company.com",
            "department": "Engineering",
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["employee_id"] == "EMP001"

    list_response = client.get("/api/employees")
    assert list_response.status_code == 200
    employees = list_response.json()
    assert len(employees) == 1
    assert employees[0]["email"] == "john@company.com"

    delete_response = client.delete("/api/employees/EMP001")
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Employee deleted successfully"

    list_after_delete = client.get("/api/employees")
    assert list_after_delete.status_code == 200
    assert list_after_delete.json() == []


def test_create_employee_duplicate_employee_id_returns_409(client) -> None:
    payload = {
        "employee_id": "EMP001",
        "full_name": "John Doe",
        "email": "john@company.com",
        "department": "Engineering",
    }

    first = client.post("/api/employees", json=payload)
    second = client.post(
        "/api/employees",
        json={
            **payload,
            "email": "john2@company.com",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["message"] == "Employee with this employee_id already exists"


def test_delete_employee_not_found_returns_404(client) -> None:
    response = client.delete("/api/employees/EMP404")

    assert response.status_code == 404
    assert response.json()["message"] == "Employee not found"


def test_create_employee_validation_error_422(client) -> None:
    response = client.post(
        "/api/employees",
        json={
            "employee_id": "",
            "full_name": "",
            "email": "invalid",
            "department": "",
        },
    )

    assert response.status_code == 422
    assert response.json()["message"] == "Validation error"
