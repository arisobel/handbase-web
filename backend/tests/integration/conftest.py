"""Fixtures for the PostgreSQL integration suite.

These tests are the counterweight to DEC-009: the fast suite proves the
behaviour, this suite proves it holds on the database the application actually
runs on — including the Alembic path, native ``UUID``/``JSONB`` columns and the
constraints only PostgreSQL enforces.

Run with::

    pytest -m postgres

pointing ``TEST_DATABASE_URL`` at a throwaway database. The schema is dropped
and rebuilt from migrations for every session, so never aim it at real data.
"""
import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from backend.app.db.migrations import PROJECT_ROOT
from backend.app.db.session import get_db
from backend.app.main import app

DEFAULT_URL = "postgresql+psycopg://handbase:handbase@localhost:5433/handbase_test"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_URL)


#: Probe result, memoized so an unreachable server costs one timeout for the
#: whole suite rather than one per test. A fixture cannot do this: pytest
#: re-runs a fixture that raised `Skipped`.
_probe: tuple[object | None, str | None] | None = None


def _probe_postgres(url: str) -> tuple[object | None, str | None]:
    """Return ``(engine, None)`` or ``(None, reason_to_skip)``. Runs once."""
    global _probe
    if _probe is not None:
        return _probe

    safe_url = make_url(url).render_as_string(hide_password=True)
    if not make_url(url).get_backend_name().startswith("postgresql"):
        _probe = (None, f"TEST_DATABASE_URL is not a PostgreSQL URL: {safe_url}")
        return _probe

    # A short timeout keeps "no server" fast; it is not a statement timeout.
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment dependent
        engine.dispose()
        _probe = (None, f"PostgreSQL is not reachable at {safe_url}: {exc}")
    else:
        _probe = (engine, None)
    return _probe


@pytest.fixture(scope="session")
def pg_engine():
    engine, reason = _probe_postgres(TEST_DATABASE_URL)
    if engine is None:
        pytest.skip(reason)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def migrated_database(pg_engine):
    """Drop the schema and bring it up with ``alembic upgrade head``.

    Starting from an genuinely empty database is the point: it exercises the
    migration chain the production container runs, not ``create_all``.
    """
    with pg_engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(config, "head")
    return pg_engine


#: Child tables first is unnecessary with CASCADE, but the explicit list keeps
#: the truncation honest if a table is added and forgotten here.
_TABLES = (
    "records",
    "field_definitions",
    "view_definitions",
    "table_definitions",
    "refresh_tokens",
    "workspace_memberships",
    "users",
    "workspaces",
)


@pytest.fixture()
def pg_session(migrated_database):
    """A real session against the migrated database, emptied before each test.

    Deliberately not a rolled-back outer transaction: the services commit, and
    an integration test should exercise the same commit path production uses.
    """
    with migrated_database.begin() as connection:
        connection.execute(text(f"TRUNCATE {', '.join(_TABLES)} RESTART IDENTITY CASCADE"))

    session = sessionmaker(bind=migrated_database, autoflush=False, autocommit=False)()
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()


@pytest.fixture()
def pg_client(pg_session):
    with TestClient(app) as client:
        yield client
