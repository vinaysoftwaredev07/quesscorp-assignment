from datetime import date


def create_employee(client, employee_id: str = "EMP001", email: str = "john@company.com") -> None:
    response = client.post(
        "/api/employees",
        json={
            "employee_id": employee_id,
            "full_name": "John Doe",
            "email": email,
            "department": "Engineering",
        },
    )
    assert response.status_code == 201


def test_mark_and_fetch_attendance_flow(client) -> None:
    create_employee(client)

    mark_response = client.post(
        "/api/attendance",
        json={
            "employee_id": "EMP001",
            "date": "2026-02-25",
            "status": "PRESENT",
        },
    )
    assert mark_response.status_code == 201
    assert mark_response.json()["status"] == "PRESENT"

    get_response = client.get("/api/attendance/EMP001")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["employee_id"] == "EMP001"
    assert data["total_records"] == 1
    assert data["total_present"] == 1


def test_mark_attendance_duplicate_for_same_date_updates_existing_record(client) -> None:
    create_employee(client)

    first_payload = {
        "employee_id": "EMP001",
        "date": "2026-02-25",
        "status": "PRESENT",
    }
    second_payload = {
        "employee_id": "EMP001",
        "date": "2026-02-25",
        "status": "ABSENT",
    }

    first = client.post("/api/attendance", json=first_payload)
    second = client.post("/api/attendance", json=second_payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["status"] == "ABSENT"

    summary = client.get("/api/attendance/EMP001")
    assert summary.status_code == 200
    summary_data = summary.json()
    assert summary_data["total_records"] == 1
    assert summary_data["total_present"] == 0


def test_mark_attendance_for_current_date_then_update_same_date(client) -> None:
    create_employee(client)
    today = date.today().isoformat()

    first = client.post(
        "/api/attendance",
        json={"employee_id": "EMP001", "date": today, "status": "PRESENT"},
    )
    second = client.post(
        "/api/attendance",
        json={"employee_id": "EMP001", "date": today, "status": "ABSENT"},
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["date"] == today
    assert second.json()["status"] == "ABSENT"


def test_mark_attendance_employee_not_found_returns_404(client) -> None:
    response = client.post(
        "/api/attendance",
        json={
            "employee_id": "EMP404",
            "date": "2026-02-25",
            "status": "ABSENT",
        },
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Employee not found"


def test_get_attendance_with_date_filter(client) -> None:
    create_employee(client)

    client.post(
        "/api/attendance",
        json={"employee_id": "EMP001", "date": "2026-02-25", "status": "PRESENT"},
    )
    client.post(
        "/api/attendance",
        json={"employee_id": "EMP001", "date": "2026-02-24", "status": "ABSENT"},
    )

    response = client.get("/api/attendance/EMP001?date=2026-02-25")
    assert response.status_code == 200

    data = response.json()
    assert data["total_records"] == 1
    assert data["total_present"] == 1
    assert data["records"][0]["date"] == "2026-02-25"


def test_get_attendance_with_month_filter(client) -> None:
    create_employee(client)

    client.post(
        "/api/attendance",
        json={"employee_id": "EMP001", "date": "2026-02-25", "status": "PRESENT"},
    )
    client.post(
        "/api/attendance",
        json={"employee_id": "EMP001", "date": "2026-02-24", "status": "ABSENT"},
    )
    client.post(
        "/api/attendance",
        json={"employee_id": "EMP001", "date": "2026-01-24", "status": "PRESENT"},
    )

    response = client.get("/api/attendance/EMP001?month=2026-02")
    assert response.status_code == 200

    data = response.json()
    assert data["total_records"] == 2
    assert data["total_present"] == 1
    assert all(record["date"].startswith("2026-02") for record in data["records"])


def test_get_attendance_with_invalid_month_filter(client) -> None:
    create_employee(client)

    response = client.get("/api/attendance/EMP001?month=2026/02")
    assert response.status_code == 400
    assert response.json()["message"] == "Invalid month format. Use YYYY-MM"
