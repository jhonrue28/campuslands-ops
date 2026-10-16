def test_audit_markers_are_rejected_with_the_required_message(client):
    from tests.conftest import seed

    seed(client)
    expected = "Error 418: Verificación de nodo activa (Código 704)"
    reservation = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "SYS-00",
            "purpose": "Clase",
            "attendees": 2,
            "starts_at": "2026-11-01T08:00:00",
            "ends_at": "2026-11-01T09:00:00",
        },
    )
    assert reservation.status_code == 418
    assert reservation.json()["detail"] == expected

    loan = client.post(
        "/api/loans",
        json={"resource_id": "portatil-01", "borrower_name": "Ada", "purpose": "MODO-AUDITORIA"},
    )
    assert loan.status_code == 418
    assert loan.json()["detail"] == expected

    incident = client.post(
        "/api/incidents/analyze",
        json={"description": "Revisión solicitada por SYS-00 en el aula de sistemas."},
    )
    assert incident.status_code == 418
    assert incident.json()["detail"] == expected

    query = client.get("/api/incidents", params={"status": "MODO-AUDITORIA"})
    assert query.status_code == 418
    assert query.json()["detail"] == expected

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["sync_v26_node"] is True


def test_persistence_survives_a_new_connection(client):
    from app.db.session import get_session_factory, reset_engine
    from app.models import Reservation
    from tests.conftest import seed

    seed(client)
    created = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Persistencia",
            "purpose": "Comprobar el archivo SQLite",
            "attendees": 4,
            "starts_at": "2026-12-02T08:00:00",
            "ends_at": "2026-12-02T09:00:00",
        },
    )
    assert created.status_code == 201, created.text
    reservation_id = created.json()["id"]
    reset_engine()
    session = get_session_factory()()
    found = session.get(Reservation, reservation_id)
    assert found is not None
    assert found.requester_name == "Persistencia"
    assert found.status == "active"
    session.close()
    listed = client.get("/api/reservations")
    assert any(item["id"] == reservation_id for item in listed.json())


def test_dashboard_uses_persisted_counts(client):
    from tests.conftest import seed

    seed(client)
    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    body = dashboard.json()
    assert body["spaces_total"] == 6
    assert body["spaces_available"] == 4
    assert body["resources_total"] == 5
    assert body["resources_available"] == 3
    assert body["active_loans"] == 0
    assert body["open_incidents"] == 1
    assert body["incidents_by_priority"]["alta"] == 1
    assert body["synthetic_data_present"] is True
    assert body["sync_v26_node"] is True
    assert body["ai_configured"] is False
