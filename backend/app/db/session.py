from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    pass


def _sqlite_path(url: str) -> str | None:
    marker = "sqlite:///"
    if not url.startswith(marker) or url.startswith("sqlite:///:memory:"):
        return None
    return url[len(marker) :]


def get_engine() -> Engine:
    global _engine, _session_factory
    if _engine is None:
        url = get_settings().sqlalchemy_url
        path = _sqlite_path(url)
        connect_args: dict = {}
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False, "timeout": 30}
            if path:
                from pathlib import Path

                Path(path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url, connect_args=connect_args)
        if url.startswith("sqlite"):

            @event.listens_for(_engine, "connect")
            def _enable_sqlite(dbapi_connection, _connection_record) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()

        _session_factory = sessionmaker(
            bind=_engine,
            autoflush=True,
            autocommit=False,
            expire_on_commit=False,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


def reset_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def _migrate_sqlite(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    additions = {
        "spaces": {
            "room_type": "VARCHAR(64) NOT NULL DEFAULT 'general'",
            "expected_computers": "INTEGER NOT NULL DEFAULT 0",
        },
        "resources": {
            "asset_code": "VARCHAR(80) NOT NULL DEFAULT ''",
            "kind": "VARCHAR(32) NOT NULL DEFAULT 'equipment'",
            "space_id": "VARCHAR(64)",
            "host_resource_id": "VARCHAR(64)",
            "peripheral_type": "VARCHAR(32) NOT NULL DEFAULT ''",
            "brand": "VARCHAR(120) NOT NULL DEFAULT ''",
            "model_name": "VARCHAR(120) NOT NULL DEFAULT ''",
            "provisional": "BOOLEAN NOT NULL DEFAULT 0",
            "hardware_notes": "TEXT NOT NULL DEFAULT ''",
        },
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table})")}
            for name, declaration in columns.items():
                if name not in existing:
                    connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_resources_asset_code "
            "ON resources(asset_code) WHERE asset_code <> ''"
        )


def init_db() -> None:
    from app import models  # noqa: F401
    from app.services.auth import ensure_default_admin

    engine = get_engine()
    Base.metadata.create_all(engine)
    _migrate_sqlite(engine)
    session = get_session_factory()()
    try:
        ensure_default_admin(session)
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
