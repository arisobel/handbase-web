"""Test harness.

The fast suite runs against in-memory SQLite so it needs no database server.
PostgreSQL remains the only supported application database (DEC-009); it is
exercised by the separate `postgres`-marked integration suite in
``backend/tests/integration/``.

``create_all`` here is a test fixture only — the production schema comes from
Alembic, and the integration suite verifies that path specifically.
"""
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import User, Workspace, WorkspaceRole
from backend.app.models import auth as auth_models  # noqa: F401  (registers the mappers)
from backend.app.models import metadata as metadata_models  # noqa: F401
from backend.app.services import auth_service

DEFAULT_PASSWORD = "correct-horse-battery"


@pytest.fixture()
def db_session():
    """One in-memory database per test, wired into the app for that test.

    The dependency override lives here rather than in the client fixtures so
    that a test can build extra ``TestClient`` instances — several roles, or a
    cookie-carrying session — and have them all hit the same database.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def anon_client(db_session):
    """An unauthenticated client. Use it to assert that endpoints reject anonymity."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def make_user(db_session) -> Callable[..., User]:
    """Create a user directly through the service, bypassing HTTP."""

    def _make(
        email: str = "owner@example.com",
        password: str = DEFAULT_PASSWORD,
        locale: str = "en",
        display_name: str | None = None,
    ) -> User:
        return auth_service.create_user(
            db_session,
            email=email,
            password=password,
            display_name=display_name,
            preferred_locale=locale,
        )

    return _make


@pytest.fixture()
def login(db_session) -> Callable[..., TestClient]:
    """Return a TestClient already carrying a bearer token for the given user.

    Each call builds its own client so that several roles can be exercised
    side by side within one test.
    """

    def _login(email: str, password: str = DEFAULT_PASSWORD) -> TestClient:
        test_client = TestClient(app)
        response = test_client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        test_client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        return test_client

    return _login


@pytest.fixture()
def owner_user(make_user) -> User:
    return make_user(email="owner@example.com")


@pytest.fixture()
def client(owner_user, login) -> TestClient:
    """The default client: authenticated as a user who owns everything it creates."""
    return login(owner_user.email)


@pytest.fixture()
def member_client(db_session, make_user, login) -> Callable[..., TestClient]:
    """Build a client for a fresh user holding ``role`` in ``workspace_id``."""

    def _member(workspace_id: uuid.UUID | str, role: WorkspaceRole) -> TestClient:
        user = make_user(email=f"{role.value.lower()}-{uuid.uuid4().hex[:8]}@example.com")
        auth_service.grant_membership(
            db_session,
            workspace_id=uuid.UUID(str(workspace_id)),
            user_id=user.id,
            role=role,
        )
        return login(user.email)

    return _member


@pytest.fixture()
def workspace(client) -> dict:
    """A workspace created — and therefore owned — by the default client."""
    response = client.post("/api/v1/workspaces", json={"name": "Yeshiva", "default_locale": "he"})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def students_table(client, workspace) -> dict:
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


@pytest.fixture()
def other_workspace(db_session, make_user, login) -> tuple[TestClient, dict]:
    """A second, unrelated workspace with its own owner — for isolation tests."""
    outsider = make_user(email="outsider@example.com")
    outsider_client = login(outsider.email)
    response = outsider_client.post("/api/v1/workspaces", json={"name": "Other org"})
    assert response.status_code == 201, response.text
    return outsider_client, response.json()


@pytest.fixture()
def seed_workspace_without_members(db_session) -> Workspace:
    """A workspace created outside the API, as pre-authentication data would be."""
    workspace = Workspace(name="Legacy workspace", default_locale="he")
    db_session.add(workspace)
    db_session.commit()
    db_session.refresh(workspace)
    return workspace
