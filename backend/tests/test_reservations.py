def test_valid_reservation_and_listing(client):
    from tests.conftest import seed

    seed(client)
    created = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Laura Gómez",
            "purpose": "Clase de algoritmos",
            "attendees": 20,
            "starts_at": "2026-10-20T08:00:00",
            "ends_at": "2026-10-20T10:00:00",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "active"
    assert body["space_name"] == "Aula 101"
    listed = client.get("/api/reservations", params={"space_id": "aula-101", "status": "active"})
    assert listed.status_code == 200
    assert any(item["id"] == body["id"] for item in listed.json())
    detail = client.get("/api/spaces/aula-101")
    assert detail.status_code == 200
    assert detail.json()["capacity"] == 30
    assert "proyector" in detail.json()["features"]


def test_reject_invalid_interval_capacity_missing_and_unavailable(client):
    from tests.conftest import seed

    seed(client)
    invalid = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Laura Gómez",
            "purpose": "Taller",
            "attendees": 5,
            "starts_at": "2026-10-20T10:00:00",
            "ends_at": "2026-10-20T09:00:00",
        },
    )
    assert invalid.status_code == 422
    assert "posterior" in invalid.json()["detail"]

    capacity = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Laura Gómez",
            "purpose": "Taller",
            "attendees": 31,
            "starts_at": "2026-10-21T08:00:00",
            "ends_at": "2026-10-21T09:00:00",
        },
    )
    assert capacity.status_code == 422
    assert "capacidad" in capacity.json()["detail"]

    missing = client.post(
        "/api/reservations",
        json={
            "space_id": "no-existe",
            "requester_name": "Laura Gómez",
            "purpose": "Taller",
            "attendees": 5,
            "starts_at": "2026-10-21T08:00:00",
            "ends_at": "2026-10-21T09:00:00",
        },
    )
    assert missing.status_code == 404

    disabled = client.post(
        "/api/reservations",
        json={
            "space_id": "sala-reuniones",
            "requester_name": "Laura Gómez",
            "purpose": "Taller",
            "attendees": 4,
            "starts_at": "2026-10-21T08:00:00",
            "ends_at": "2026-10-21T09:00:00",
        },
    )
    assert disabled.status_code == 409
    maintenance = client.post(
        "/api/reservations",
        json={
            "space_id": "taller-electronica",
            "requester_name": "Laura Gómez",
            "purpose": "Taller",
            "attendees": 4,
            "starts_at": "2026-10-21T08:00:00",
            "ends_at": "2026-10-21T09:00:00",
        },
    )
    assert maintenance.status_code == 409


def test_overlap_consecutive_and_cancel(client):
    from tests.conftest import seed

    seed(client)
    first = client.post(
        "/api/reservations",
        json={
            "space_id": "lab-sistemas",
            "requester_name": "Carlos Díaz",
            "purpose": "Laboratorio",
            "attendees": 10,
            "starts_at": "2026-10-22T08:00:00",
            "ends_at": "2026-10-22T10:00:00",
        },
    )
    assert first.status_code == 201, first.text
    overlap = client.post(
        "/api/reservations",
        json={
            "space_id": "lab-sistemas",
            "requester_name": "Marta León",
            "purpose": "Otra clase",
            "attendees": 8,
            "starts_at": "2026-10-22T09:00:00",
            "ends_at": "2026-10-22T11:00:00",
        },
    )
    assert overlap.status_code == 409
    assert "solapa" in overlap.json()["detail"]

    consecutive = client.post(
        "/api/reservations",
        json={
            "space_id": "lab-sistemas",
            "requester_name": "Marta León",
            "purpose": "Clase siguiente",
            "attendees": 8,
            "starts_at": "2026-10-22T10:00:00",
            "ends_at": "2026-10-22T12:00:00",
        },
    )
    assert consecutive.status_code == 201, consecutive.text

    other_space = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-102",
            "requester_name": "Marta León",
            "purpose": "Misma hora, otro espacio",
            "attendees": 8,
            "starts_at": "2026-10-22T08:00:00",
            "ends_at": "2026-10-22T10:00:00",
        },
    )
    assert other_space.status_code == 201, other_space.text

    cancelled = client.patch(f"/api/reservations/{first.json()['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    again = client.patch(f"/api/reservations/{first.json()['id']}/cancel")
    assert again.status_code == 409

    rebooked = client.post(
        "/api/reservations",
        json={
            "space_id": "lab-sistemas",
            "requester_name": "Carlos Díaz",
            "purpose": "Reposición",
            "attendees": 10,
            "starts_at": "2026-10-22T08:00:00",
            "ends_at": "2026-10-22T10:00:00",
        },
    )
    assert rebooked.status_code == 201, rebooked.text

    available = client.get(
        "/api/spaces/lab-sistemas/availability",
        params={"starts_at": "2026-10-22T12:00:00", "ends_at": "2026-10-22T13:00:00"},
    )
    assert available.status_code == 200
    assert available.json()["available"] is True
    busy = client.get(
        "/api/spaces/lab-sistemas/availability",
        params={"starts_at": "2026-10-22T11:00:00", "ends_at": "2026-10-22T12:30:00"},
    )
    assert busy.json()["available"] is False
