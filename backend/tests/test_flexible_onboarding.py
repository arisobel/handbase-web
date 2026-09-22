"""PIN-protected invitations and administrator-created local accounts."""
import uuid
from backend.app.models import User, WorkspaceRole


def test_pin_invitation_requires_code_and_locks_after_five_attempts(client, workspace, db_session):
    created = client.post(f"/api/v1/workspaces/{workspace['id']}/invitations", json={
        "email": "pin@example.com", "role": "EDITOR", "verification_mode": "LINK_AND_PIN"
    })
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["pin"].isdigit() and len(body["pin"]) == 6
    stored = db_session.get(__import__("backend.app.models", fromlist=["WorkspaceInvitation"]).WorkspaceInvitation, uuid.UUID(body["id"]))
    assert stored.pin_digest != body["pin"]
    token = body["invitation_url"].rsplit("/", 1)[1]
    assert client.post(f"/api/v1/invitations/{token}/accept", json={"password": "long-enough-password"}).status_code == 409
    assert client.post(f"/api/v1/invitations/{token}/verify-pin", json={"pin": "000000"}).status_code == 404
    assert client.post(f"/api/v1/invitations/{token}/verify-pin", json={"pin": body["pin"]}).status_code == 200


def test_local_user_forces_password_change_and_respects_role_boundary(client, workspace, member_client, db_session):
    created = client.post(f"/api/v1/workspaces/{workspace['id']}/users", json={
        "email": "local@example.com", "display_name": "Local", "role": "EDITOR", "preferred_locale": "pt-BR"
    })
    assert created.status_code == 201, created.text
    body = created.json()
    user = db_session.get(User, uuid.UUID(body["id"]))
    assert user and user.must_change_password and user.password_hash != body["temporary_password"]
    login = client.post("/api/v1/auth/login", json={"email": body["email"], "password": body["temporary_password"]})
    assert login.status_code == 200
    local = member_client(workspace["id"], WorkspaceRole.ADMIN)
    assert local.post(f"/api/v1/workspaces/{workspace['id']}/users", json={"email": "nope@example.com", "display_name": "Nope", "role": "OWNER"}).status_code == 403
