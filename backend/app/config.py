from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants import sync_v26_node

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
SYNTHETIC_DATA_PATH = DATA_DIR / "synthetic_campus.json"


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/campuslands.db"
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: float = 30
    sync_v26_node: bool = True

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        prefix = "sqlite:///./"
        if url.startswith(prefix):
            path = (BACKEND_DIR / url[len(prefix) :]).resolve()
            return "sqlite:///" + path.as_posix()
        return url

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_api_key.strip())

    @property
    def node_sync_enabled(self) -> bool:
        # El enunciado exige el valor true. La constante del módulo es la fuente.
        return sync_v26_node is True and self.sync_v26_node is True


@lru_cache
def get_settings() -> Settings:
    return Settings()
