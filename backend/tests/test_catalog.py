from fastapi.testclient import TestClient

from app.catalog import OFFICIAL_ROOMS


def test_official_rooms_are_idempotent_and_match_the_table(client: TestClient):
    first = client.post("/api/catalog/official")
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["created_rooms"] == 12
    assert body["created_computers"] == 126
    assert body["capacity_sum"] == 295
    assert body["expected_computer_count"] == 126
    rooms = {item["name"]: item for item in body["rooms"]}
    assert set(rooms) == {item["name"] for item in OFFICIAL_ROOMS}
    for spec in OFFICIAL_ROOMS:
        room = rooms[spec["name"]]
        assert room["capacity"] == spec["capacity"]
        assert room["expected_computers"] == spec["expected_computers"]
        assert room["registered_computers"] == spec["expected_computers"]
        assert room["matches_expected"] is True
    assert rooms["Auditorio"]["registered_computers"] == 0
    assert rooms["Artemis"]["capacity"] == 32
    assert rooms["Artemis"]["registered_computers"] == 34
    assert rooms["Artemis"]["pending_identification"] == 0

    second = client.post("/api/catalog/official")
    assert second.status_code == 200, second.text
    again = second.json()
    assert again["created_rooms"] == 0
    assert again["created_computers"] == 0
    assert again["conflicts"] == []
    spaces = client.get("/api/spaces").json()
    assert len(spaces) == 12
    artemis = next(item for item in spaces if item["id"] == "aula-artemis")
    assert artemis["computers_registered"] == 34
    computers = client.get("/api/spaces/sala-blanca/computers")
    assert computers.status_code == 200
    assert computers.json() == []


def test_zero_computer_room_can_be_reserved(client: TestClient):
    assert client.post("/api/catalog/official").status_code == 200
    created = client.post(
        "/api/reservations",
        json={
            "space_id": "sala-blanca",
            "requester_name": "Ana",
            "purpose": "Reunión de coordinación",
            "attendees": 6,
            "starts_at": "2026-11-02T08:00:00",
            "ends_at": "2026-11-02T09:00:00",
        },
    )
    assert created.status_code == 201, created.text
    overflow = client.post(
        "/api/reservations",
        json={
            "space_id": "sala-blanca",
            "requester_name": "Ana",
            "purpose": "Reunión demasiado grande",
            "attendees": 13,
            "starts_at": "2026-11-02T10:00:00",
            "ends_at": "2026-11-02T11:00:00",
        },
    )
    assert overflow.status_code == 422


def test_computer_identity_loans_and_history(client: TestClient):
    assert client.post("/api/catalog/official").status_code == 200
    computers = client.get("/api/computers", params={"space_id": "aula-artemis"}).json()
    assert len(computers) == 34
    codes = [item["asset_code"] for item in computers]
    assert len(codes) == len(set(codes))
    assert all(item["provisional"] is False for item in computers)
    assert all(item["space_id"] == "aula-artemis" for item in computers)
    unit = computers[0]

    damaged = client.post(f"/api/computers/{unit['id']}/status", json={"status": "damaged"})
    assert damaged.status_code == 200
    refused = client.post(
        "/api/loans",
        json={"resource_id": unit["id"], "borrower_name": "Luis", "purpose": "salida"},
    )
    assert refused.status_code == 409

    restored = client.post(f"/api/computers/{unit['id']}/status", json={"status": "available"})
    assert restored.status_code == 200
    loan = client.post(
        "/api/loans",
        json={"resource_id": unit["id"], "borrower_name": "Luis", "purpose": "salida"},
    )
    assert loan.status_code == 201, loan.text
    second = client.post(
        "/api/loans",
        json={"resource_id": unit["id"], "borrower_name": "Marta", "purpose": "otra salida"},
    )
    assert second.status_code == 409
    held = client.get(f"/api/computers/{unit['id']}").json()
    assert held["computer"]["status"] == "loaned"
    assert held["computer"]["space_id"] == "aula-artemis"
    assert len(held["loans"]) == 1

    maintenance = client.post(f"/api/computers/{unit['id']}/status", json={"status": "maintenance", "note": "revisión"})
    assert maintenance.status_code == 200
    returned = client.post(f"/api/loans/{loan.json()['id']}/return")
    assert returned.status_code == 200
    after = client.get(f"/api/computers/{unit['id']}").json()
    assert after["computer"]["status"] == "maintenance"
    duplicate = client.post(f"/api/loans/{loan.json()['id']}/return")
    assert duplicate.status_code == 409

    moved = client.post(
        f"/api/computers/{unit['id']}/location",
        json={"space_id": "aula-skylab"},
    )
    assert moved.status_code == 200
    detail = client.get(f"/api/computers/{unit['id']}").json()
    assert detail["computer"]["space_id"] == "aula-skylab"
    fields = {event["field"] for event in detail["events"]}
    assert "space_id" in fields
    assert "status" in fields
    assert len(detail["loans"]) == 1


def test_peripherals_do_not_change_the_computer(client: TestClient):
    assert client.post("/api/catalog/official").status_code == 200
    computer = client.get("/api/computers", params={"space_id": "aula-apolo"}).json()[0]
    created = client.post(
        "/api/peripherals",
        json={
            "name": "Monitor pendiente de placa",
            "peripheral_type": "monitor",
            "host_resource_id": computer["id"],
            "notes": "Dato ingresado a mano. No es inventario verificado.",
        },
    )
    assert created.status_code == 201, created.text
    duplicate = client.post(
        "/api/peripherals",
        json={
            "name": "Otro monitor",
            "peripheral_type": "monitor",
            "host_resource_id": computer["id"],
            "asset_code": created.json()["asset_code"],
        },
    )
    assert created.json()["asset_code"] == ""
    labeled = client.post(
        "/api/peripherals",
        json={
            "name": "Teclado pendiente",
            "peripheral_type": "teclado",
            "host_resource_id": computer["id"],
            "asset_code": "DEMO-TECLADO-1",
        },
    )
    assert labeled.status_code == 201
    repeated = client.post(
        "/api/peripherals",
        json={
            "name": "Teclado repetido",
            "peripheral_type": "teclado",
            "host_resource_id": computer["id"],
            "asset_code": "DEMO-TECLADO-1",
        },
    )
    assert repeated.status_code == 409
    listed = client.get("/api/peripherals", params={"host_id": computer["id"]})
    assert listed.status_code == 200
    assert len(listed.json()) == 3

    other = client.get("/api/computers", params={"space_id": "aula-skylab"}).json()[0]
    moved = client.post(
        f"/api/peripherals/{labeled.json()['id']}/host",
        json={"host_resource_id": other["id"]},
    )
    assert moved.status_code == 200
    assert moved.json()["host_resource_id"] == other["id"]
    assert client.get(f"/api/computers/{computer['id']}").json()["computer"]["status"] == "available"

    incident = client.post(
        "/api/incidents",
        json={
            "title": "Monitor sin imagen",
            "description": "El monitor asociado no enciende durante la clase.",
            "category": "tecnologia",
            "priority": "media",
            "responsible_area": "tecnologia",
            "recommendation": "Revisar cable",
            "source": "manual",
            "resource_id": created.json()["id"],
        },
    )
    assert incident.status_code == 201, incident.text
    assert client.get(f"/api/computers/{computer['id']}").json()["computer"]["status"] == "available"
    assert duplicate.status_code == 201


def test_catalog_survives_a_new_process(client: TestClient):
    assert client.post("/api/catalog/official").status_code == 200
    from app.config import get_settings
    from app.db.session import reset_engine
    from app.main import create_app

    reset_engine()
    get_settings.cache_clear()
    with TestClient(create_app()) as restarted:
        summary = restarted.get("/api/catalog/rooms").json()
        assert sum(item["registered_computers"] for item in summary) == 126
        dashboard = restarted.get("/api/dashboard").json()
        assert dashboard["computers_total"] == 126
        assert dashboard["computers_available"] == 126
        assert dashboard["spaces_total"] == 12
    reset_engine()
    get_settings.cache_clear()
