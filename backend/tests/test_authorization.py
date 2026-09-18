"""Workspace authorization and cross-workspace isolation.

Two rules are under test throughout:

* a role grants exactly the capabilities in ``authz.ROLE_CAPABILITIES``;
* the workspace that decides an operation is always resolved server-side from
  the object being touched, never taken from the request.
"""
import pytest

from backend.app.models import WorkspaceRole

# Every endpoint that must not answer an anonymous caller.
ANONYMOUS_REQUESTS = [
    ("get", "/api/v1/workspaces"),
    ("post", "/api/v1/workspaces"),
    ("get", "/api/v1/tables?workspace_id=00000000-0000-0000-0000-000000000000"),
    ("post", "/api/v1/tables"),
    ("get", "/api/v1/fields?table_id=00000000-0000-0000-0000-000000000000"),
    ("post", "/api/v1/fields"),
    ("get", "/api/v1/field-types"),
    ("get", "/api/v1/records?table_id=00000000-0000-0000-0000-000000000000"),
    ("post", "/api/v1/records"),
    ("get", "/api/v1/auth/me"),
]


@pytest.mark.parametrize(("method", "path"), ANONYMOUS_REQUESTS)
def test_unauthenticated_requests_are_rejected(anon_client, method, path):
    kwargs = {"json": {}} if method == "post" else {}
    response = anon_client.request(method.upper(), path, **kwargs)
    assert response.status_code == 401, f"{method.upper()} {path} -> {response.status_code}"
    assert response.json()["detail"]["code"] == "unauthenticated"


def test_health_stays_public(anon_client):
    """A load balancer has no credentials."""
    assert anon_client.get("/api/health").status_code == 200


def test_a_user_without_membership_cannot_see_the_workspace(workspace, make_user, login):
    make_user(email="stranger@example.com")
    stranger = login("stranger@example.com")

    assert stranger.get("/api/v1/workspaces").json() == []
    # 404 rather than 403: confirming existence would leak other people's data.
    assert stranger.get(f"/api/v1/workspaces/{workspace['id']}").status_code == 404
    assert stranger.get("/api/v1/tables", params={"workspace_id": workspace["id"]}).status_code == 404


def test_workspace_list_shows_only_your_own(client, workspace, other_workspace):
    _outsider_client, foreign = other_workspace
    listed = client.get("/api/v1/workspaces").json()
    ids = {item["id"] for item in listed}
    assert workspace["id"] in ids
    assert foreign["id"] not in ids


def test_creator_becomes_owner(client):
    created = client.post("/api/v1/workspaces", json={"name": "Mine"}).json()
    memberships = client.get("/api/v1/auth/me").json()["memberships"]
    mine = next(m for m in memberships if m["workspace_id"] == created["id"])
    assert mine["role"] == "OWNER"


# --------------------------------------------------------------------------- #
# Role capabilities
# --------------------------------------------------------------------------- #


def test_viewer_can_read(students_table, workspace, member_client):
    viewer = member_client(workspace["id"], WorkspaceRole.VIEWER)

    assert viewer.get(f"/api/v1/workspaces/{workspace['id']}").status_code == 200
    assert viewer.get("/api/v1/tables", params={"workspace_id": workspace["id"]}).status_code == 200
    assert viewer.get(f"/api/v1/tables/{students_table['id']}").status_code == 200
    assert viewer.get("/api/v1/records", params={"table_id": students_table["id"]}).status_code == 200


def test_viewer_cannot_modify_records(students_table, workspace, member_client, client):
    viewer = member_client(workspace["id"], WorkspaceRole.VIEWER)
    existing = client.post(
        "/api/v1/records",
        json={"table_id": students_table["id"], "data": {"first_name": "Moshe", "last_name": "Cohen"}},
    ).json()

    created = viewer.post(
        "/api/v1/records",
        json={"table_id": students_table["id"], "data": {"first_name": "David", "last_name": "Levi"}},
    )
    assert created.status_code == 403
    assert created.json()["detail"]["code"] == "forbidden"

    assert viewer.put(f"/api/v1/records/{existing['id']}", json={"data": {}}).status_code == 403
    assert viewer.patch(f"/api/v1/records/{existing['id']}", json={"data": {}}).status_code == 403
    assert viewer.delete(f"/api/v1/records/{existing['id']}").status_code == 403
    # Nothing was actually written.
    assert client.get("/api/v1/records", params={"table_id": students_table["id"]}).json()["total"] == 1


def test_editor_can_create_and_edit_records(students_table, workspace, member_client):
    editor = member_client(workspace["id"], WorkspaceRole.EDITOR)

    created = editor.post(
        "/api/v1/records",
        json={"table_id": students_table["id"], "data": {"first_name": "Moshe", "last_name": "Cohen"}},
    )
    assert created.status_code == 201, created.text
    record = created.json()

    patched = editor.patch(f"/api/v1/records/{record['id']}", json={"data": {"entry_year": 2024}})
    assert patched.status_code == 200
    assert patched.json()["data"]["entry_year"] == 2024
    assert editor.delete(f"/api/v1/records/{record['id']}").status_code == 204


def test_editor_cannot_change_table_structure(students_table, workspace, member_client):
    editor = member_client(workspace["id"], WorkspaceRole.EDITOR)

    new_table = editor.post("/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Sneaky"})
    assert new_table.status_code == 403

    new_field = editor.post(
        "/api/v1/fields",
        json={"table_id": students_table["id"], "label": "Sneaky", "field_type": "text"},
    )
    assert new_field.status_code == 403

    field_id = students_table["fields"][0]["id"]
    assert editor.patch(f"/api/v1/fields/{field_id}", json={"label": "x"}).status_code == 403
    assert editor.delete(f"/api/v1/fields/{field_id}").status_code == 403
    assert editor.delete(f"/api/v1/tables/{students_table['id']}").status_code == 403


def test_admin_can_change_structure(students_table, workspace, member_client):
    admin = member_client(workspace["id"], WorkspaceRole.ADMIN)

    table = admin.post("/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Teachers"})
    assert table.status_code == 201, table.text

    field = admin.post(
        "/api/v1/fields",
        json={"table_id": table.json()["id"], "label": "Name", "field_type": "text"},
    )
    assert field.status_code == 201
    assert admin.delete(f"/api/v1/fields/{field.json()['id']}").status_code == 204
    assert admin.delete(f"/api/v1/tables/{table.json()['id']}").status_code == 204


def test_admin_cannot_manage_the_workspace_itself(workspace, member_client):
    """Renaming or deleting the workspace is reserved for OWNER."""
    admin = member_client(workspace["id"], WorkspaceRole.ADMIN)
    assert admin.patch(f"/api/v1/workspaces/{workspace['id']}", json={"name": "Renamed"}).status_code == 403
    assert admin.delete(f"/api/v1/workspaces/{workspace['id']}").status_code == 403


def test_owner_has_full_access(students_table, workspace, client):
    assert client.patch(
        f"/api/v1/workspaces/{workspace['id']}", json={"name": "Yeshiva Renamed"}
    ).status_code == 200

    record = client.post(
        "/api/v1/records",
        json={"table_id": students_table["id"], "data": {"first_name": "Moshe", "last_name": "Cohen"}},
    )
    assert record.status_code == 201

    field = client.post(
        "/api/v1/fields",
        json={"table_id": students_table["id"], "label": "Phone", "field_type": "text"},
    )
    assert field.status_code == 201
    assert client.delete(f"/api/v1/workspaces/{workspace['id']}").status_code == 204


# --------------------------------------------------------------------------- #
# Cross-workspace isolation
# --------------------------------------------------------------------------- #


def test_workspace_a_user_cannot_reach_workspace_b_data(students_table, other_workspace):
    outsider, foreign = other_workspace

    assert outsider.get(f"/api/v1/tables/{students_table['id']}").status_code == 404
    assert outsider.get("/api/v1/fields", params={"table_id": students_table["id"]}).status_code == 404
    assert outsider.get("/api/v1/records", params={"table_id": students_table["id"]}).status_code == 404

    # Naming their own workspace does not launder access to a foreign table.
    created = outsider.post(
        "/api/v1/fields",
        json={"table_id": students_table["id"], "label": "Injected", "field_type": "text"},
    )
    assert created.status_code == 404


def test_a_direct_record_id_cannot_bypass_workspace_authorization(
    students_table, client, other_workspace
):
    """The record -> table -> workspace walk happens server-side."""
    outsider, _foreign = other_workspace
    record = client.post(
        "/api/v1/records",
        json={"table_id": students_table["id"], "data": {"first_name": "Moshe", "last_name": "Cohen"}},
    ).json()

    assert outsider.get(f"/api/v1/records/{record['id']}").status_code == 404
    assert outsider.put(f"/api/v1/records/{record['id']}", json={"data": {}}).status_code == 404
    assert outsider.patch(f"/api/v1/records/{record['id']}", json={"data": {}}).status_code == 404
    assert outsider.delete(f"/api/v1/records/{record['id']}").status_code == 404

    # Still there.
    assert client.get(f"/api/v1/records/{record['id']}").status_code == 200


def test_a_direct_field_id_cannot_bypass_workspace_authorization(students_table, other_workspace):
    outsider, _foreign = other_workspace
    field_id = students_table["fields"][0]["id"]

    assert outsider.get(f"/api/v1/fields/{field_id}").status_code == 404
    assert outsider.patch(f"/api/v1/fields/{field_id}", json={"label": "x"}).status_code == 404
    assert outsider.delete(f"/api/v1/fields/{field_id}").status_code == 404


def test_creating_a_table_in_someone_elses_workspace_is_rejected(workspace, other_workspace):
    outsider, _foreign = other_workspace
    response = outsider.post("/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Nope"})
    assert response.status_code == 404


def test_creating_a_record_in_someone_elses_table_is_rejected(students_table, other_workspace):
    outsider, _foreign = other_workspace
    response = outsider.post(
        "/api/v1/records",
        json={"table_id": students_table["id"], "data": {"first_name": "A", "last_name": "B"}},
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Pre-authentication data
# --------------------------------------------------------------------------- #


def test_memberless_workspaces_are_invisible_but_intact(
    db_session, seed_workspace_without_members, client
):
    from backend.app.services import auth_service

    assert client.get("/api/v1/workspaces").json() == []
    assert client.get(f"/api/v1/workspaces/{seed_workspace_without_members.id}").status_code == 404
    # The row still exists; it is unreachable, not deleted.
    assert [w.id for w in auth_service.list_orphan_workspaces(db_session)] == [
        seed_workspace_without_members.id
    ]


def test_adopting_orphans_restores_access(db_session, seed_workspace_without_members, owner_user, client):
    from backend.app.services import auth_service

    adopted = auth_service.adopt_orphan_workspaces(db_session, owner_user)
    assert [w.id for w in adopted] == [seed_workspace_without_members.id]

    listed = client.get("/api/v1/workspaces").json()
    assert [item["id"] for item in listed] == [str(seed_workspace_without_members.id)]
    assert auth_service.list_orphan_workspaces(db_session) == []
