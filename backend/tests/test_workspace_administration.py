"""Workspace-scoped membership administration and locale rules."""
import pytest

from backend.app.core.locales import resolve_locale
from backend.app.core.security import verify_password
from backend.app.models import WorkspaceRole
from backend.app.services import auth_service


def _members(client, workspace_id: str) -> list[dict]:
    response = client.get(f"/api/v1/workspaces/{workspace_id}/members")
    assert response.status_code == 200, response.text
    return response.json()


def test_owner_lists_members(client, workspace):
    members = _members(client, workspace["id"])
    assert [(member["email"], member["role"]) for member in members] == [
        ("owner@example.com", "OWNER")
    ]
    assert "password_hash" not in members[0]


def test_admin_lists_members(workspace, member_client):
    admin = member_client(workspace["id"], WorkspaceRole.ADMIN)
    assert admin.get(f"/api/v1/workspaces/{workspace['id']}/members").status_code == 200


def test_admin_adds_a_non_owner(workspace, member_client, make_user):
    admin = member_client(workspace["id"], WorkspaceRole.ADMIN)
    make_user(email="assistant@example.com")
    response = admin.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": "assistant@example.com", "role": "EDITOR"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "EDITOR"


@pytest.mark.parametrize("role", [WorkspaceRole.EDITOR, WorkspaceRole.VIEWER])
def test_editor_and_viewer_cannot_manage_members(workspace, member_client, role):
    member = member_client(workspace["id"], role)
    path = f"/api/v1/workspaces/{workspace['id']}/members"
    assert member.get(path).status_code == 403
    assert member.post(path, json={"email": "nobody@example.com", "role": "VIEWER"}).status_code == 403


def test_owner_adds_existing_user(client, workspace, make_user):
    user = make_user(email="teacher@example.com", locale="he", display_name="Teacher")
    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": user.email, "role": "EDITOR"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "teacher@example.com"
    assert body["display_name"] == "Teacher"
    assert body["role"] == "EDITOR"
    assert body["preferred_locale"] == "he"


def test_removed_global_user_can_be_added_again_without_changing_account(client, workspace, make_user):
    user = make_user(
        email="returning@example.com", locale="pt-BR", display_name="Returning User"
    )
    original_hash = user.password_hash
    added = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": "returning@example.com", "role": "VIEWER"},
    )
    assert added.status_code == 201, added.text
    assert client.delete(
        f"/api/v1/workspaces/{workspace['id']}/members/{added.json()['id']}"
    ).status_code == 204

    readded = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": "  RETURNING@EXAMPLE.COM  ", "role": "EDITOR"},
    )
    assert readded.status_code == 201, readded.text
    assert readded.json()["user_id"] == str(user.id)
    assert readded.json()["display_name"] == "Returning User"
    assert readded.json()["preferred_locale"] == "pt-BR"
    assert user.password_hash == original_hash
    assert user.must_change_password is False


def test_unknown_user_is_not_implicitly_invited(client, workspace):
    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": "unknown@example.com", "role": "VIEWER"},
    )
    assert response.status_code == 404
    assert "not implemented" in response.json()["detail"]["message"]


def test_duplicate_membership_is_rejected(client, workspace):
    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": "owner@example.com", "role": "OWNER"},
    )
    assert response.status_code == 409


def test_role_change_works(client, workspace, make_user):
    make_user(email="teacher@example.com")
    created = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": "teacher@example.com", "role": "VIEWER"},
    ).json()
    changed = client.patch(
        f"/api/v1/workspaces/{workspace['id']}/members/{created['id']}",
        json={"role": "EDITOR"},
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == "EDITOR"


def test_last_owner_cannot_be_demoted_or_removed(client, workspace):
    owner = next(member for member in _members(client, workspace["id"]) if member["role"] == "OWNER")
    path = f"/api/v1/workspaces/{workspace['id']}/members/{owner['id']}"
    assert client.patch(path, json={"role": "ADMIN"}).status_code == 409
    assert client.delete(path).status_code == 409


def test_one_owner_can_remove_another_when_a_second_owner_remains(client, workspace, make_user):
    make_user(email="second@example.com")
    second = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": "second@example.com", "role": "OWNER"},
    )
    assert second.status_code == 201
    assert client.delete(
        f"/api/v1/workspaces/{workspace['id']}/members/{second.json()['id']}"
    ).status_code == 204


def test_admin_cannot_cross_owner_boundary(workspace, member_client, make_user, client):
    admin = member_client(workspace["id"], WorkspaceRole.ADMIN)
    make_user(email="candidate@example.com")
    add_owner = admin.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": "candidate@example.com", "role": "OWNER"},
    )
    assert add_owner.status_code == 403

    owner = next(member for member in _members(client, workspace["id"]) if member["role"] == "OWNER")
    path = f"/api/v1/workspaces/{workspace['id']}/members/{owner['id']}"
    assert admin.patch(path, json={"role": "VIEWER"}).status_code == 403
    assert admin.delete(path).status_code == 403


def test_reset_member_password_hashes_password_requires_change_and_revokes_sessions(
    client, workspace, make_user, db_session
):
    user = make_user(email="reset-target@example.com")
    member = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": user.email, "role": "EDITOR"},
    ).json()
    _access, _ttl, refresh_token = auth_service.issue_session(db_session, user)

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/{member['id']}/reset-password"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user_id"] == str(user.id)
    assert body["email"] == user.email
    assert body["temporary_password"]
    assert body["temporary_password"] != user.password_hash
    assert verify_password(user.password_hash, body["temporary_password"])
    assert user.must_change_password is True
    with pytest.raises(auth_service.AuthenticationError):
        auth_service.rotate_session(db_session, refresh_token)


def test_owner_can_reset_the_last_owner_password(client, workspace):
    owner = next(member for member in _members(client, workspace["id"]) if member["role"] == "OWNER")
    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/{owner['id']}/reset-password"
    )
    assert response.status_code == 200, response.text
    assert response.json()["temporary_password"]


def test_admin_cannot_reset_an_owner_password(workspace, member_client, client):
    admin = member_client(workspace["id"], WorkspaceRole.ADMIN)
    owner = next(member for member in _members(client, workspace["id"]) if member["role"] == "OWNER")
    response = admin.post(
        f"/api/v1/workspaces/{workspace['id']}/members/{owner['id']}/reset-password"
    )
    assert response.status_code == 403


@pytest.mark.parametrize("role", [WorkspaceRole.EDITOR, WorkspaceRole.VIEWER])
def test_non_managers_cannot_reset_member_password(workspace, member_client, client, role):
    member = next(item for item in _members(client, workspace["id"]) if item["role"] == "OWNER")
    actor = member_client(workspace["id"], role)
    assert actor.post(
        f"/api/v1/workspaces/{workspace['id']}/members/{member['id']}/reset-password"
    ).status_code == 403


def test_cross_workspace_membership_access_returns_404(workspace, other_workspace):
    outsider, _foreign = other_workspace
    assert outsider.get(f"/api/v1/workspaces/{workspace['id']}/members").status_code == 404


def test_invalid_locales_are_rejected(client, workspace):
    assert client.patch("/api/v1/auth/me", json={"preferred_locale": "fr"}).status_code == 422
    assert client.patch(
        f"/api/v1/workspaces/{workspace['id']}", json={"default_locale": "fr"}
    ).status_code == 422


def test_workspace_default_locale_persists(client, workspace):
    response = client.patch(
        f"/api/v1/workspaces/{workspace['id']}", json={"default_locale": "pt-BR"}
    )
    assert response.status_code == 200
    assert client.get(f"/api/v1/workspaces/{workspace['id']}").json()["default_locale"] == "pt-BR"


def test_locale_resolution_prefers_user_then_workspace_then_application():
    assert resolve_locale("pt-BR", "he") == "pt-BR"
    assert resolve_locale(None, "he") == "he"
    assert resolve_locale(None, None) == "en"
