from fastapi.testclient import TestClient


def test_login_and_user_crud(client: TestClient):
    bad = client.post("/api/auth/login", json={"username": "mafe.cala", "password": "wrong"})
    assert bad.status_code == 401

    login = client.post("/api/auth/login", json={"username": "mafe.cala", "password": "HolaMundo*"})
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    assert login.json()["user"]["full_name"] == "Mafe Cala"
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "mafe.cala"

    created = client.post(
        "/api/users",
        headers=headers,
        json={
            "full_name": "Ana Ops",
            "username": "ana.ops",
            "password": "Campus123",
            "role": "operator",
            "notes": "Operadora de prueba",
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    listed = client.get("/api/users", headers=headers)
    assert listed.status_code == 200
    assert any(item["username"] == "ana.ops" for item in listed.json())

    patched = client.patch(
        f"/api/users/{user_id}",
        headers=headers,
        json={"full_name": "Ana Operaciones", "active": True},
    )
    assert patched.status_code == 200
    assert patched.json()["full_name"] == "Ana Operaciones"

    deleted = client.delete(f"/api/users/{user_id}", headers=headers)
    assert deleted.status_code == 200

    blocked = client.delete("/api/users/user-mafe-cala", headers=headers)
    assert blocked.status_code == 409
