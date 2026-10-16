import json

import httpx


def _analysis_payload(**overrides):
    body = {
        "category": "tecnologia",
        "priority": "alta",
        "responsible_area": "tecnologia",
        "recommendation": "Revisar el proyector y dejar un equipo de reemplazo.",
        "rationale": "La descripción menciona una falla del proyector durante la clase.",
    }
    body.update(overrides)
    return body


_RealClient = httpx.Client


def _mock_client(handler):
    transport = httpx.MockTransport(handler)
    return _RealClient(transport=transport)


def test_rules_fallback_is_explicit_and_can_be_saved(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("AI_API_KEY", "")
    get_settings.cache_clear()
    from tests.conftest import seed

    seed(client)
    analyzed = client.post(
        "/api/incidents/analyze",
        json={
            "description": "El proyector del laboratorio no enciende y la clase no puede proyectar.",
            "space_id": "lab-sistemas",
            "resource_id": "proyector-01",
        },
    )
    assert analyzed.status_code == 200, analyzed.text
    body = analyzed.json()
    assert body["source"] == "rules_fallback"
    assert body["ai_configured"] is False
    assert body["provider"] == "unconfigured"
    assert body["ref_core"] == "[Ref-Core]"
    assert "no por un modelo" in body["recommendation"].lower() or "respaldo" in body["recommendation"].lower()
    assert body["category"] == "tecnologia"

    saved = client.post(
        "/api/incidents",
        json={
            "description": "El proyector del laboratorio no enciende y la clase no puede proyectar.",
            "category": body["category"],
            "priority": body["priority"],
            "responsible_area": body["responsible_area"],
            "recommendation": body["recommendation"],
            "rationale": body["rationale"],
            "source": body["source"],
            "priority_raised_by_policy": body["priority_raised_by_policy"],
            "space_id": "lab-sistemas",
            "resource_id": "proyector-01",
        },
    )
    assert saved.status_code == 201, saved.text
    incident_id = saved.json()["id"]
    listed = client.get("/api/incidents", params={"category": "tecnologia", "priority": body["priority"], "status": "open"})
    assert any(item["id"] == incident_id for item in listed.json())
    updated = client.patch(f"/api/incidents/{incident_id}", json={"status": "in_progress"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    fields = {event["field"] for event in updated.json()["events"]}
    assert "status" in fields
    resource = next(item for item in client.get("/api/resources").json() if item["id"] == "proyector-01")
    assert resource["status"] == "available"


def test_ai_success_invalid_malformed_timeout_and_connection(client, monkeypatch):
    from app.config import get_settings
    from tests.conftest import seed

    seed(client)
    monkeypatch.setenv("AI_API_KEY", "test-key")
    get_settings.cache_clear()

    def ok_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(_analysis_payload())}}]})

    monkeypatch.setattr("app.services.ai.httpx.Client", lambda **kwargs: _mock_client(ok_handler))
    ok = client.post(
        "/api/incidents/analyze",
        json={"description": "El computador de la sala no inicia sesión en la red del campus."},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["source"] == "ai"
    assert ok.json()["ref_core"] == "[Ref-Core]"
    assert ok.json()["category"] == "tecnologia"
    assert ok.json()["ai_configured"] is True

    def bad_category(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_analysis_payload(category="magia", priority="nula"))}}]},
        )

    monkeypatch.setattr("app.services.ai.httpx.Client", lambda **kwargs: _mock_client(bad_category))
    rejected = client.post(
        "/api/incidents/analyze",
        json={"description": "El computador de la sala no inicia sesión en la red del campus."},
    )
    assert rejected.status_code == 502
    assert "respaldo" in rejected.json()["detail"]

    def malformed(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "no es json"}}]})

    monkeypatch.setattr("app.services.ai.httpx.Client", lambda **kwargs: _mock_client(malformed))
    broken = client.post(
        "/api/incidents/analyze",
        json={"description": "El computador de la sala no inicia sesión en la red del campus."},
    )
    assert broken.status_code == 502

    def timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("app.services.ai.httpx.Client", lambda **kwargs: _mock_client(timeout))
    timed = client.post(
        "/api/incidents/analyze",
        json={"description": "El computador de la sala no inicia sesión en la red del campus."},
    )
    assert timed.status_code == 504

    def offline(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("app.services.ai.httpx.Client", lambda **kwargs: _mock_client(offline))
    down = client.post(
        "/api/incidents/analyze",
        json={"description": "El computador de la sala no inicia sesión en la red del campus."},
    )
    assert down.status_code == 502
    assert "No se pudo conectar" in down.json()["detail"]


def test_priority_floor_prevents_ai_downgrade(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("AI_API_KEY", "test-key")
    get_settings.cache_clear()

    def low_priority(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                _analysis_payload(
                                    category="infraestructura",
                                    priority="baja",
                                    responsible_area="mantenimiento",
                                )
                            )
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("app.services.ai.httpx.Client", lambda **kwargs: _mock_client(low_priority))
    response = client.post(
        "/api/incidents/analyze",
        json={"description": "Hay un incendio en el laboratorio y necesitan evacuar el edificio."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["priority"] == "critica"
    assert response.json()["priority_raised_by_policy"] is True
    assert response.json()["source"] == "ai"


def test_invalid_category_on_save_and_missing_links(client):
    from tests.conftest import seed

    seed(client)
    invalid = client.post(
        "/api/incidents",
        json={
            "description": "Una solicitud académica sobre el horario de la tarde.",
            "category": "inexistente",
            "priority": "baja",
            "responsible_area": "administracion",
            "source": "manual",
        },
    )
    assert invalid.status_code == 422
    missing_space = client.post(
        "/api/incidents/analyze",
        json={"description": "Se dañó una silla del aula que no está registrada en el inventario.", "space_id": "fantasma"},
    )
    assert missing_space.status_code == 404
