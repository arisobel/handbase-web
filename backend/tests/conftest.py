"""Test harness.

The suite runs against in-memory SQLite so it needs no PostgreSQL server.
PostgreSQL stays the production database (DEC-002); the models use dialect
variants (``backend.app.db.types``) that render as native UUID/JSONB there.

``create_all`` here is a test fixture only — production schema is Alembic's job.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import metadata  # noqa: F401  (registers the mappers)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def workspace(client):
    response = client.post("/api/v1/workspaces", json={"name": "Yeshiva", "default_locale": "he"})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def students_table(client, workspace):
    """The worked example from the brief: a Hebrew-labelled student table."""
    response = client.post(
        "/api/v1/tables",
        json={"workspace_id": workspace["id"], "name": "תלמידים", "description": "רשימת תלמידים"},
    )
    assert response.status_code == 201, response.text
    table = response.json()

    definitions = [
        {"label": "שם פרטי", "field_type": "text", "required": True, "key": "first_name"},
        {"label": "שם משפחה", "field_type": "text", "required": True, "key": "last_name"},
        {"label": "שנת כניסה", "field_type": "number", "required": False, "key": "entry_year"},
        {"label": "פעיל", "field_type": "boolean", "required": False, "key": "active"},
        {"label": "הערות", "field_type": "long_text", "required": False, "key": "notes"},
    ]
    fields = []
    for definition in definitions:
        created = client.post("/api/v1/fields", json={"table_id": table["id"], **definition})
        assert created.status_code == 201, created.text
        fields.append(created.json())

    table["fields"] = fields
    return table
