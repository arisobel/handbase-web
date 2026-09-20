"""End-to-end verification against a real PostgreSQL server.

Covers what SQLite cannot: the Alembic chain from an empty database, native
``UUID``/``JSONB`` storage, PostgreSQL-enforced constraints, and the full
authenticated CRUD path on top of all of it.
"""
import pytest
from sqlalchemy import inspect, text

from backend.app.db.migrations import current_revisions, expected_head
from backend.app.models import WorkspaceRole
from backend.app.services import auth_service

pytestmark = pytest.mark.postgres

PASSWORD = "correct-horse-battery"


@pytest.fixture()
def owner(pg_session):
    return auth_service.create_user(
        pg_session, email="owner@example.com", password=PASSWORD, preferred_locale="he"
    )


@pytest.fixture()
def owner_client(pg_client, owner):
    response = pg_client.post(
        "/api/v1/auth/login", json={"email": owner.email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    pg_client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return pg_client


# --------------------------------------------------------------------------- #
# Migrations
# --------------------------------------------------------------------------- #


def test_migrations_bring_an_empty_database_to_head(pg_session):
    applied = current_revisions(pg_session)
    assert expected_head() in applied

    tables = set(inspect(pg_session.get_bind()).get_table_names())
    assert {
        "workspaces",
        "table_definitions",
        "field_definitions",
        "records",
        "view_definitions",
        "users",
        "workspace_memberships",
        "refresh_tokens",
        "alembic_version",
    } <= tables


def test_columns_are_native_postgres_types(pg_session):
    columns = {
        column["name"]: column["type"]
        for column in inspect(pg_session.get_bind()).get_columns("records")
    }
    assert type(columns["id"]).__name__ == "UUID"
    assert type(columns["data"]).__name__ == "JSONB"

    user_columns = {
        column["name"]: column
        for column in inspect(pg_session.get_bind()).get_columns("users")
    }
    assert user_columns["preferred_locale"]["nullable"] is True


def test_expected_indexes_exist(pg_session):
    indexes = {index["name"] for index in inspect(pg_session.get_bind()).get_indexes("records")}
    assert "ix_records_table_created" in indexes
    assert "ix_records_data_gin" in indexes
    # Superseded by the composite index in revision 20260918_02.
    assert "ix_records_table_id" not in indexes


def test_readiness_endpoint_reports_a_migrated_schema(pg_client):
    response = pg_client.get("/api/ready")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready"
    assert body["expected_revision"] in body["schema_revision"]


# --------------------------------------------------------------------------- #
# Constraints PostgreSQL actually enforces
# --------------------------------------------------------------------------- #


def test_duplicate_membership_is_rejected_by_the_database(pg_session, owner):
    workspace = auth_service.create_workspace_with_owner(pg_session, user=owner, name="Yeshiva")
    with pytest.raises(Exception):
        pg_session.execute(
            text(
                "INSERT INTO workspace_memberships (id, workspace_id, user_id, role) "
                "VALUES (gen_random_uuid(), :w, :u, 'VIEWER')"
            ),
            {"w": workspace.id, "u": owner.id},
        )
        pg_session.commit()
    pg_session.rollback()


def test_deleting_a_workspace_cascades_to_records(pg_session, owner_client, owner):
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Temp"}).json()
    table = owner_client.post(
        "/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Rows"}
    ).json()
    owner_client.post(
        "/api/v1/fields", json={"table_id": table["id"], "label": "Name", "field_type": "text"}
    )
    owner_client.post(
        "/api/v1/records", json={"table_id": table["id"], "data": {"name": "Moshe"}}
    )

    assert owner_client.delete(f"/api/v1/workspaces/{workspace['id']}").status_code == 204
    remaining = pg_session.execute(
        text("SELECT count(*) FROM records WHERE table_id = :t"), {"t": table["id"]}
    ).scalar()
    assert remaining == 0


# --------------------------------------------------------------------------- #
# Full authenticated CRUD
# --------------------------------------------------------------------------- #


def test_full_crud_cycle_on_postgres(pg_session, owner_client):
    # Workspace
    workspace = owner_client.post(
        "/api/v1/workspaces", json={"name": "Yeshiva", "default_locale": "he"}
    )
    assert workspace.status_code == 201, workspace.text
    workspace = workspace.json()

    # Table
    table = owner_client.post(
        "/api/v1/tables", json={"workspace_id": workspace["id"], "name": "תלמידים"}
    )
    assert table.status_code == 201, table.text
    table = table.json()

    # Fields
    definitions = [
        {"label": "שם פרטי", "field_type": "text", "required": True, "key": "first_name"},
        {"label": "שם משפחה", "field_type": "text", "required": True, "key": "last_name"},
        {"label": "שנת כניסה", "field_type": "number", "key": "entry_year"},
        {"label": "פעיל", "field_type": "boolean", "key": "active"},
        {"label": "הערות", "field_type": "long_text", "key": "notes"},
    ]
    for definition in definitions:
        created = owner_client.post("/api/v1/fields", json={"table_id": table["id"], **definition})
        assert created.status_code == 201, created.text

    # Create
    record = owner_client.post(
        "/api/v1/records",
        json={
            "table_id": table["id"],
            "data": {
                "first_name": "Moshe",
                "last_name": "Cohen",
                "entry_year": 2024,
                "active": True,
                "notes": "משה כהן - Class 3 - 2026",
            },
        },
    )
    assert record.status_code == 201, record.text
    record = record.json()

    # Hebrew round-trips through JSONB unharmed.
    stored = pg_session.execute(
        text("SELECT data ->> 'notes' FROM records WHERE id = :id"), {"id": record["id"]}
    ).scalar()
    assert stored == "משה כהן - Class 3 - 2026"

    # List
    page = owner_client.get("/api/v1/records", params={"table_id": table["id"]})
    assert page.status_code == 200
    assert page.json()["total"] == 1

    # Validation still strict on PostgreSQL (DEC-012).
    rejected = owner_client.post(
        "/api/v1/records",
        json={
            "table_id": table["id"],
            "data": {"first_name": "A", "last_name": "B", "entry_year": "2024"},
        },
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["errors"][0]["code"] == "invalid_type"

    # Update
    updated = owner_client.put(
        f"/api/v1/records/{record['id']}",
        json={"data": {"first_name": "David", "last_name": "Levi", "entry_year": 2023}},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["entry_year"] == 2023

    # Delete
    assert owner_client.delete(f"/api/v1/records/{record['id']}").status_code == 204
    assert owner_client.get("/api/v1/records", params={"table_id": table["id"]}).json()["total"] == 0


def test_authorization_holds_on_postgres(pg_session, owner_client, owner):
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Yeshiva"}).json()
    table = owner_client.post(
        "/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Students"}
    ).json()
    owner_client.post(
        "/api/v1/fields", json={"table_id": table["id"], "label": "Name", "field_type": "text"}
    )
    record = owner_client.post(
        "/api/v1/records", json={"table_id": table["id"], "data": {"name": "Moshe"}}
    ).json()

    # A viewer in the same workspace reads but cannot write.
    viewer = auth_service.create_user(pg_session, email="viewer@example.com", password=PASSWORD)
    auth_service.grant_membership(
        pg_session, workspace_id=workspace["id"], user_id=viewer.id, role=WorkspaceRole.VIEWER
    )
    from fastapi.testclient import TestClient

    from backend.app.main import app

    with TestClient(app) as viewer_client:
        token = viewer_client.post(
            "/api/v1/auth/login", json={"email": viewer.email, "password": PASSWORD}
        ).json()["access_token"]
        viewer_client.headers["Authorization"] = f"Bearer {token}"
        assert viewer_client.get(f"/api/v1/records/{record['id']}").status_code == 200
        assert viewer_client.delete(f"/api/v1/records/{record['id']}").status_code == 403

    # An outsider cannot reach the record by id at all.
    outsider = auth_service.create_user(pg_session, email="outsider@example.com", password=PASSWORD)
    auth_service.create_workspace_with_owner(pg_session, user=outsider, name="Other")
    with TestClient(app) as outsider_client:
        token = outsider_client.post(
            "/api/v1/auth/login", json={"email": outsider.email, "password": PASSWORD}
        ).json()["access_token"]
        outsider_client.headers["Authorization"] = f"Bearer {token}"
        assert outsider_client.get(f"/api/v1/records/{record['id']}").status_code == 404


def test_sessions_persist_in_postgres(pg_session, pg_client, owner):
    login = pg_client.post("/api/v1/auth/login", json={"email": owner.email, "password": PASSWORD})
    assert login.status_code == 200

    live = pg_session.execute(
        text("SELECT count(*) FROM refresh_tokens WHERE user_id = :u AND revoked_at IS NULL"),
        {"u": owner.id},
    ).scalar()
    assert live == 1

    assert pg_client.post("/api/v1/auth/refresh").status_code == 200
    # Rotation revokes the old row and stores a new one.
    rows = pg_session.execute(
        text("SELECT count(*) FILTER (WHERE revoked_at IS NULL), count(*) FROM refresh_tokens "
             "WHERE user_id = :u"),
        {"u": owner.id},
    ).one()
    assert rows == (1, 2)

    assert pg_client.post("/api/v1/auth/logout").status_code == 204
    still_live = pg_session.execute(
        text("SELECT count(*) FROM refresh_tokens WHERE user_id = :u AND revoked_at IS NULL"),
        {"u": owner.id},
    ).scalar()
    assert still_live == 0


def test_locale_preference_persists_across_sessions_on_postgres(pg_session, pg_client, owner):
    login = pg_client.post("/api/v1/auth/login", json={"email": owner.email, "password": PASSWORD})
    assert login.json()["user"]["preferred_locale"] == "he"
    stored = pg_session.execute(
        text("SELECT preferred_locale FROM users WHERE id = :id"), {"id": owner.id}
    ).scalar()
    assert stored == "he"
