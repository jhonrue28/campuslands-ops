def test_reject_outside_business_hours_and_sunday(client):
    from tests.conftest import seed

    seed(client)

    # Domingo 2026-10-18
    sunday = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Laura Gómez",
            "purpose": "Clase",
            "attendees": 5,
            "starts_at": "2026-10-18T10:00:00",
            "ends_at": "2026-10-18T12:00:00",
        },
    )
    assert sunday.status_code == 422
    assert "domingo" in sunday.json()["detail"].lower()

    # Antes de las 06:00
    early = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Laura Gómez",
            "purpose": "Clase",
            "attendees": 5,
            "starts_at": "2026-10-20T05:00:00",
            "ends_at": "2026-10-20T07:00:00",
        },
    )
    assert early.status_code == 422
    assert "horario laboral" in early.json()["detail"].lower()

    # Después de las 22:00
    late = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Laura Gómez",
            "purpose": "Clase",
            "attendees": 5,
            "starts_at": "2026-10-20T21:00:00",
            "ends_at": "2026-10-20T23:00:00",
        },
    )
    assert late.status_code == 422

    # Cruza medianoche / dos días
    overnight = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Laura Gómez",
            "purpose": "Clase",
            "attendees": 5,
            "starts_at": "2026-10-20T21:00:00",
            "ends_at": "2026-10-21T08:00:00",
        },
    )
    assert overnight.status_code == 422
    assert "mismo día" in overnight.json()["detail"].lower()

    # Duración mínima
    short = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Laura Gómez",
            "purpose": "Clase",
            "attendees": 5,
            "starts_at": "2026-10-20T10:00:00",
            "ends_at": "2026-10-20T10:10:00",
        },
    )
    assert short.status_code == 422
    assert "15" in short.json()["detail"]

    # Válida dentro de horario
    ok = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Laura Gómez",
            "purpose": "Clase",
            "attendees": 5,
            "starts_at": "2026-10-20T08:00:00",
            "ends_at": "2026-10-20T10:00:00",
        },
    )
    assert ok.status_code == 201, ok.text
