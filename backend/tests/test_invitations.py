"""Invitation lifecycle: digest-only links, role boundaries and acceptance."""
import uuid
from backend.app.models import WorkspaceInvitation, WorkspaceRole


def _create(client, workspace, email="invitee@example.com", role="EDITOR"):
    response = client.post(f"/api/v1/workspaces/{workspace['id']}/invitations", json={"email": email, "role": role})
    assert response.status_code == 201, response.text
    return response.json()


def _token(created):
    return created["invitation_url"].rsplit("/", 1)[1]


def test_owner_invites_unknown_email_with_digest_only_token(client, workspace, db_session):
    created = _create(client, workspace)
    stored = db_session.get(WorkspaceInvitation, uuid.UUID(created["id"]))
    assert stored is not None
    assert _token(created) not in stored.token_digest
    assert len(stored.token_digest) == 64


def test_admin_cannot_invite_owner(workspace, member_client):
    admin = member_client(workspace["id"], WorkspaceRole.ADMIN)
    response = admin.post(f"/api/v1/workspaces/{workspace['id']}/invitations", json={"email": "new@example.com", "role": "OWNER"})
    assert response.status_code == 403


def test_invitation_acceptance_creates_user_and_membership(client, anon_client, workspace):
    created = _create(client, workspace, role="ADMIN")
    token = _token(created)
    assert anon_client.get(f"/api/v1/invitations/{token}").json()["role"] == "ADMIN"
    accepted = anon_client.post(f"/api/v1/invitations/{token}/accept", json={"display_name": "Invitee", "password": "long-enough-password", "preferred_locale": "he"})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["role"] == "ADMIN"
    assert anon_client.get(f"/api/v1/invitations/{token}").status_code == 404


def test_replacement_revokes_old_token(client, anon_client, workspace):
    first = _create(client, workspace)
    second = _create(client, workspace)
    assert anon_client.get(f"/api/v1/invitations/{_token(first)}").status_code == 404
    assert anon_client.get(f"/api/v1/invitations/{_token(second)}").status_code == 200


def test_existing_account_must_authenticate_then_can_accept(client, anon_client, workspace, make_user, login):
    user = make_user(email="known@example.com")
    created = _create(client, workspace, user.email)
    token = _token(created)
    assert anon_client.post(f"/api/v1/invitations/{token}/accept", json={}).status_code == 409
    known = login(user.email)
    assert known.post(f"/api/v1/invitations/{token}/accept", json={}).status_code == 200
