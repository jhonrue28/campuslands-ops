def test_loan_return_and_rejections(client):
    from tests.conftest import seed

    seed(client)
    created = client.post(
        "/api/loans",
        json={
            "resource_id": "portatil-01",
            "borrower_name": "Luis Gómez",
            "borrower_contact": "luis@example.edu",
            "purpose": "Clase de bases de datos",
            "due_at": "2026-10-23T18:00:00",
        },
    )
    assert created.status_code == 201, created.text
    loan_id = created.json()["id"]
    resources = client.get("/api/resources").json()
    laptop = next(item for item in resources if item["id"] == "portatil-01")
    assert laptop["status"] == "loaned"
    assert laptop["available"] is False

    second = client.post(
        "/api/loans",
        json={"resource_id": "portatil-01", "borrower_name": "Otra persona", "purpose": "Duplicado"},
    )
    assert second.status_code == 409
    assert "préstamo activo" in second.json()["detail"]

    damaged = client.post(
        "/api/loans",
        json={"resource_id": "proyector-02", "borrower_name": "Luis Gómez", "purpose": "Clase"},
    )
    assert damaged.status_code == 409
    disabled = client.post(
        "/api/loans",
        json={"resource_id": "tablet-01", "borrower_name": "Luis Gómez", "purpose": "Clase"},
    )
    assert disabled.status_code == 409
    missing = client.post(
        "/api/loans",
        json={"resource_id": "no-existe", "borrower_name": "Luis Gómez", "purpose": "Clase"},
    )
    assert missing.status_code == 404

    active = client.get("/api/loans", params={"status": "active"})
    assert any(item["id"] == loan_id for item in active.json())

    returned = client.post(f"/api/loans/{loan_id}/return")
    assert returned.status_code == 200, returned.text
    assert returned.json()["status"] == "returned"
    assert returned.json()["returned_at"]
    resources = client.get("/api/resources").json()
    laptop = next(item for item in resources if item["id"] == "portatil-01")
    assert laptop["status"] == "available"

    duplicate = client.post(f"/api/loans/{loan_id}/return")
    assert duplicate.status_code == 409
    assert "ya fue devuelto" in duplicate.json()["detail"]

    history = client.get("/api/loans", params={"status": "returned"})
    ids = {item["id"] for item in history.json()}
    assert loan_id in ids
    assert "prestamo-hist-01" in ids

    again = client.post(
        "/api/loans",
        json={"resource_id": "portatil-01", "borrower_name": "Luis Gómez", "purpose": "Nuevo préstamo"},
    )
    assert again.status_code == 201, again.text
