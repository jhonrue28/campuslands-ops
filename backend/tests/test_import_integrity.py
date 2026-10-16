import json

from sqlalchemy import text


def test_import_valid_invalid_duplicate_and_quantity(client):
    payload = {
        "dataset": "official",
        "spaces": [
            {
                "id": "aula-norte",
                "name": "Aula norte",
                "location": "Bloque N",
                "capacity": 15,
                "status": "available",
                "features": ["pizarra"],
            },
            {"id": "aula-mala", "name": "Sin capacidad", "capacity": 0},
        ],
        "resources": [
            {"id": "kit-audio", "name": "Kit de audio", "category": "audiovisual", "quantity": 2, "status": "available"}
        ],
        "reservations": [
            {
                "id": "res-ok",
                "space_id": "aula-norte",
                "requester_name": "Equipo académico",
                "purpose": "Inducción",
                "attendees": 10,
                "starts_at": "2026-11-02T08:00:00",
                "ends_at": "2026-11-02T09:00:00",
            },
            {
                "id": "res-huerfana",
                "space_id": "no-esta",
                "requester_name": "Equipo académico",
                "purpose": "Inducción",
                "attendees": 2,
                "starts_at": "2026-11-02T08:00:00",
                "ends_at": "2026-11-02T09:00:00",
            },
        ],
        "loans": [],
        "incidents": [],
    }
    response = client.post(
        "/api/import",
        files={"file": ("campus.json", json.dumps(payload), "application/json")},
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["accepted"] == 4
    assert report["rejected"] == 2
    assert any("capacidad" in item["reason"].lower() for item in report["issues"])
    assert any("no existe" in item["reason"].lower() for item in report["issues"])
    assert any("kit-audio-1" in notice for notice in report["notices"])
    resources = {item["id"]: item for item in client.get("/api/resources").json()}
    assert "kit-audio-1" in resources and "kit-audio-2" in resources

    again = client.post(
        "/api/import",
        files={"file": ("campus.json", json.dumps(payload), "application/json")},
    )
    assert again.status_code == 200, again.text
    second = again.json()
    assert second["skipped_duplicates"] >= 3
    assert second["accepted"] == 0

    conflict = {
        "spaces": [
            {
                "id": "aula-norte",
                "name": "Aula norte modificada",
                "location": "Otro lugar",
                "capacity": 40,
                "status": "available",
            }
        ]
    }
    changed = client.post(
        "/api/import",
        files={"file": ("cambio.json", json.dumps(conflict), "application/json")},
    )
    assert changed.status_code == 200
    assert changed.json()["rejected"] == 1
    assert client.get("/api/spaces/aula-norte").json()["capacity"] == 15

    csv_body = "id,name,location,capacity,status,features\naula-csv,Aula CSV,Bloque C,12,available,pizarra\n"
    csv_response = client.post(
        "/api/import",
        params={"entity": "spaces"},
        files={"file": ("spaces.csv", csv_body, "text/csv")},
    )
    assert csv_response.status_code == 200, csv_response.text
    assert csv_response.json()["accepted"] == 1
    assert client.get("/api/spaces/aula-csv").status_code == 200

    reports = client.get("/api/import/reports")
    assert reports.status_code == 200
    assert len(reports.json()) >= 3


def test_import_rolls_back_when_the_file_is_invalid(client):
    before = client.get("/api/spaces").json()
    response = client.post(
        "/api/import",
        files={"file": ("malo.json", "{esto no es json", "application/json")},
    )
    assert response.status_code == 422
    assert client.get("/api/spaces").json() == before


def test_integrity_detects_orphan_inserted_outside_the_service(client):
    from app.db.session import get_session_factory
    from app.services.integrity import verifyIntegrityMatrix

    session = get_session_factory()()
    session.execute(text("PRAGMA foreign_keys=OFF"))
    session.execute(
        text(
            """
            INSERT INTO reservations (
                id, space_id, requester_name, purpose, attendees, starts_at, ends_at, status, created_at
            ) VALUES (
                'huerfana', 'espacio-fantasma', 'Nadie', 'Prueba', 2,
                '2026-12-01 08:00:00', '2026-12-01 09:00:00', 'active', '2026-12-01 07:00:00'
            )
            """
        )
    )
    session.commit()
    report = verifyIntegrityMatrix(session)
    session.close()
    names = {item.name: item.passed for item in report.checks}
    assert names["reservations_reference_spaces"] is False
    assert report.all_passed is False
    assert report.sync_v26_node is True
    assert report.audit_threshold_factor == 1.08


def test_pressure_threshold_does_not_block_valid_reservations(client):
    from tests.conftest import seed

    seed(client)
    for space_id, start in (("aula-101", "08:00:00"), ("aula-102", "08:00:00"), ("auditorio", "14:00:00")):
        response = client.post(
            "/api/reservations",
            json={
                "space_id": space_id,
                "requester_name": "Coordinación",
                "purpose": "Jornada",
                "attendees": 20 if space_id != "aula-102" else 24,
                "starts_at": f"2026-10-28T{start}",
                "ends_at": "2026-10-28T18:00:00" if space_id == "auditorio" else f"2026-10-28T10:00:00",
            },
        )
        assert response.status_code == 201, response.text
    # auditorio attendees 20 is within 120. Total demand: 20+24+20 = 64.
    # Available capacity: 30+24+20+120 = 194. Ratio below 1.08.
    report = client.get("/api/integrity")
    assert report.status_code == 200
    body = report.json()
    assert body["all_passed"] is True
    assert body["audit_threshold_factor"] == 1.08
    assert body["pressure_above_threshold"] is False
    assert "AUDIT_THRESHOLD_FACTOR" in body["threshold_meaning"]

    heavy = client.post(
        "/api/reservations",
        json={
            "space_id": "auditorio",
            "requester_name": "Coordinación",
            "purpose": "Evento grande",
            "attendees": 120,
            "starts_at": "2026-10-29T08:00:00",
            "ends_at": "2026-10-29T12:00:00",
        },
    )
    assert heavy.status_code == 201, heavy.text
    # Demand becomes 64 + 120 = 184, capacity 194, still under 1.08.
    # Add another full auditorium day and aula to cross the threshold.
    extra = client.post(
        "/api/reservations",
        json={
            "space_id": "auditorio",
            "requester_name": "Coordinación",
            "purpose": "Segundo evento",
            "attendees": 120,
            "starts_at": "2026-10-30T08:00:00",
            "ends_at": "2026-10-30T12:00:00",
        },
    )
    assert extra.status_code == 201, extra.text
    pressured = client.get("/api/integrity").json()
    assert pressured["all_passed"] is True
    assert pressured["pressure_ratio"] > 1.08
    assert pressured["pressure_above_threshold"] is True
