def test_demonstrable_flow_persists(client):
    from app.db.session import get_session_factory, reset_engine
    from app.models import Incident, Loan, Reservation
    from tests.conftest import seed

    seed(client)
    reservation = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Laura Gómez",
            "purpose": "Clase de algoritmos",
            "attendees": 18,
            "starts_at": "2026-10-20T08:00:00",
            "ends_at": "2026-10-20T10:00:00",
        },
    )
    assert reservation.status_code == 201, reservation.text
    overlap = client.post(
        "/api/reservations",
        json={
            "space_id": "aula-101",
            "requester_name": "Pedro Ruiz",
            "purpose": "Misma aula",
            "attendees": 10,
            "starts_at": "2026-10-20T09:00:00",
            "ends_at": "2026-10-20T11:00:00",
        },
    )
    assert overlap.status_code == 409

    loan = client.post(
        "/api/loans",
        json={"resource_id": "portatil-01", "borrower_name": "Luis Gómez", "purpose": "Clase"},
    )
    assert loan.status_code == 201, loan.text
    duplicate = client.post(
        "/api/loans",
        json={"resource_id": "portatil-01", "borrower_name": "Otra persona", "purpose": "Otro uso"},
    )
    assert duplicate.status_code == 409
    returned = client.post(f"/api/loans/{loan.json()['id']}/return")
    assert returned.status_code == 200
    assert client.get("/api/resources").json()
    laptop = next(item for item in client.get("/api/resources").json() if item["id"] == "portatil-01")
    assert laptop["status"] == "available"

    analysis = client.post(
        "/api/incidents/analyze",
        json={"description": "El proyector del laboratorio no enciende durante la clase.", "resource_id": "proyector-01"},
    )
    assert analysis.status_code == 200, analysis.text
    assert analysis.json()["source"] == "rules_fallback"
    saved = client.post(
        "/api/incidents",
        json={
            "description": "El proyector del laboratorio no enciende durante la clase.",
            "category": analysis.json()["category"],
            "priority": analysis.json()["priority"],
            "responsible_area": analysis.json()["responsible_area"],
            "recommendation": analysis.json()["recommendation"],
            "rationale": analysis.json()["rationale"],
            "source": analysis.json()["source"],
            "resource_id": "proyector-01",
        },
    )
    assert saved.status_code == 201, saved.text
    changed = client.patch(f"/api/incidents/{saved.json()['id']}", json={"status": "resolved"})
    assert changed.status_code == 200

    reservation_id = reservation.json()["id"]
    incident_id = saved.json()["id"]
    loan_id = loan.json()["id"]
    reset_engine()
    session = get_session_factory()()
    assert session.get(Reservation, reservation_id).status == "active"
    assert session.get(Loan, loan_id).status == "returned"
    assert session.get(Incident, incident_id).status == "resolved"
    session.close()
