def test_space_status_and_reservation_patch(client):
    from tests.conftest import seed

    seed(client)
    official = client.post("/api/catalog/official")
    assert official.status_code == 200

    disabled = client.patch("/api/spaces/aula-apolo/status", json={"status": "disabled", "note": "prueba"})
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["status"] == "disabled"

    blocked = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-apolo",
            "requester_name": "Mafe Cala",
            "purpose": "Clase",
            "attendees": 10,
            "starts_at": "2026-11-02T08:00:00",
            "ends_at": "2026-11-02T10:00:00",
        },
    )
    assert blocked.status_code == 409

    enabled = client.patch("/api/spaces/aula-apolo/status", json={"status": "available"})
    assert enabled.status_code == 200
    assert enabled.json()["status"] == "available"

    created = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-apolo",
            "requester_name": "Mafe Cala",
            "purpose": "Clase inicial",
            "attendees": 12,
            "starts_at": "2026-11-02T08:00:00",
            "ends_at": "2026-11-02T10:00:00",
        },
    )
    assert created.status_code == 201, created.text
    reservation_id = created.json()["id"]

    patched = client.patch(
        f"/api/reservations/{reservation_id}",
        json={
            "purpose": "Clase actualizada",
            "attendees": 15,
            "starts_at": "2026-11-02T09:00:00",
            "ends_at": "2026-11-02T11:00:00",
        },
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["purpose"] == "Clase actualizada"
    assert body["attendees"] == 15
    assert body["status"] == "active"

    cancelled = client.patch(f"/api/reservations/{reservation_id}", json={"status": "cancelled"})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    reactivated = client.patch(f"/api/reservations/{reservation_id}", json={"status": "active"})
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"
