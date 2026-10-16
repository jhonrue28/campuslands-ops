import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_BASE_URL", "https://api.openai.com/v1")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.db.session import reset_engine

    reset_engine()
    from app.main import create_app

    application = create_app()
    with TestClient(application) as test_client:
        yield test_client
    reset_engine()
    get_settings.cache_clear()
    os.environ.pop("DATABASE_URL", None)


def seed(client: TestClient) -> dict:
    response = client.post("/api/import/synthetic")
    assert response.status_code == 200, response.text
    return response.json()
