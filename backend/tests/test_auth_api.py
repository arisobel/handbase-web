"""Authentication: accounts, login, session lifecycle."""
import uuid

import pytest

from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import app
from backend.app.models import WorkspaceRole
from backend.app.services import auth_service
from backend.app.services.errors import ConflictError, ValidationError

from .conftest import DEFAULT_PASSWORD

COOKIE = get_settings().auth_cookie_name


def test_bootstrap_owner_creates_user_and_owned_workspace(db_session, make_user):
    user = make_user(email="Admin@Example.COM", locale="he")
    # Email is normalized on the way in, so casing cannot create a second account.
    assert user.email == "admin@example.com"
    assert user.password_hash.startswith("$argon2id$")
    assert DEFAULT_PASSWORD not in user.password_hash

    workspace = auth_service.create_workspace_with_owner(db_session, user=user, name="Yeshiva")
    membership = auth_service.get_membership(db_session, workspace.id, user.id)
    assert membership is not None
    assert membership.role == WorkspaceRole.OWNER.value


def test_duplicate_email_is_rejected(make_user):
    make_user(email="dup@example.com")
    with pytest.raises(ConflictError):
        # Same address, different casing.
        make_user(email="DUP@example.com")


def test_valid_login_returns_access_token_and_refresh_cookie(anon_client, make_user):
    make_user(email="user@example.com")
    response = anon_client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["email"] == "user@example.com"
    assert body["memberships"] == []

    # The refresh token travels only as a cookie, never in the body.
    assert "refresh" not in response.text.lower()
    cookie = response.cookies.get(COOKIE)
    assert cookie
    set_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "Path=/api/v1/auth" in set_cookie


def test_login_is_case_insensitive_on_email(anon_client, make_user):
    make_user(email="mixed@example.com")
    response = anon_client.post(
        "/api/v1/auth/login", json={"email": "MiXeD@Example.com", "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 200


def test_invalid_login_is_rejected_without_revealing_the_cause(anon_client, make_user):
    make_user(email="user@example.com")

    wrong_password = anon_client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": "not-the-password"}
    )
    unknown_user = anon_client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": DEFAULT_PASSWORD}
    )

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    # Identical responses: the login form must not be an account-enumeration oracle.
    assert wrong_password.json() == unknown_user.json()
    assert wrong_password.cookies.get(COOKIE) is None


def test_inactive_user_cannot_log_in(db_session, anon_client, make_user):
    user = make_user(email="retired@example.com")
    user.is_active = False
    db_session.commit()

    response = anon_client.post(
        "/api/v1/auth/login", json={"email": "retired@example.com", "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 401


def test_me_returns_the_user_and_their_memberships(client, workspace):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["email"] == "owner@example.com"
    assert len(body["memberships"]) == 1
    membership = body["memberships"][0]
    assert membership["workspace_id"] == workspace["id"]
    assert membership["workspace_name"] == "Yeshiva"
    assert membership["role"] == "OWNER"
    assert "manage_workspace" in membership["capabilities"]


def test_me_requires_authentication(anon_client):
    response = anon_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthenticated"


def test_me_rejects_a_garbage_token(anon_client):
    anon_client.headers["Authorization"] = "Bearer not-a-jwt"
    assert anon_client.get("/api/v1/auth/me").status_code == 401


def test_refresh_rotates_the_cookie_and_returns_a_working_token(db_session, make_user):
    make_user(email="rotate@example.com")
    with TestClient(app) as session_client:
        login = session_client.post(
            "/api/v1/auth/login", json={"email": "rotate@example.com", "password": DEFAULT_PASSWORD}
        )
        first_cookie = login.cookies.get(COOKIE)

        refreshed = session_client.post("/api/v1/auth/refresh")
        assert refreshed.status_code == 200, refreshed.text
        second_cookie = refreshed.cookies.get(COOKIE)
        assert second_cookie and second_cookie != first_cookie

        # The new access token works.
        session_client.headers["Authorization"] = f"Bearer {refreshed.json()['access_token']}"
        assert session_client.get("/api/v1/auth/me").status_code == 200


def test_a_rotated_refresh_token_cannot_be_reused(db_session, make_user):
    make_user(email="replay@example.com")
    with TestClient(app) as session_client:
        login = session_client.post(
            "/api/v1/auth/login", json={"email": "replay@example.com", "password": DEFAULT_PASSWORD}
        )
        stolen = login.cookies.get(COOKIE)
        assert session_client.post("/api/v1/auth/refresh").status_code == 200

        # Replaying the pre-rotation token must fail.
        session_client.cookies.set(COOKIE, stolen, path="/api/v1/auth")
        assert session_client.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_without_a_cookie_is_rejected(anon_client):
    assert anon_client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_the_session(db_session, make_user):
    make_user(email="bye@example.com")
    with TestClient(app) as session_client:
        session_client.post(
            "/api/v1/auth/login", json={"email": "bye@example.com", "password": DEFAULT_PASSWORD}
        )
        assert session_client.post("/api/v1/auth/logout").status_code == 204
        # The cookie is cleared and the old refresh token no longer works.
        assert session_client.post("/api/v1/auth/refresh").status_code == 401


def test_hebrew_locale_preference_survives_login_and_refresh(db_session, make_user):
    make_user(email="hebrew@example.com", locale="he")
    with TestClient(app) as session_client:
        login = session_client.post(
            "/api/v1/auth/login", json={"email": "hebrew@example.com", "password": DEFAULT_PASSWORD}
        )
        assert login.json()["user"]["preferred_locale"] == "he"

        refreshed = session_client.post("/api/v1/auth/refresh")
        assert refreshed.json()["user"]["preferred_locale"] == "he"

        session_client.headers["Authorization"] = f"Bearer {refreshed.json()['access_token']}"
        assert session_client.get("/api/v1/auth/me").json()["user"]["preferred_locale"] == "he"


def test_locale_preference_can_be_updated_and_persists(client):
    updated = client.patch("/api/v1/auth/me", json={"preferred_locale": "pt-BR"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["user"]["preferred_locale"] == "pt-BR"
    assert client.get("/api/v1/auth/me").json()["user"]["preferred_locale"] == "pt-BR"


def test_short_passwords_are_rejected(db_session):
    with pytest.raises(ValidationError) as excinfo:
        auth_service.create_user(db_session, email="weak@example.com", password="short")
    assert excinfo.value.issues[0].code == "password_too_short"


def test_password_reset_revokes_existing_sessions(db_session, make_user):
    user = make_user(email="reset@example.com")
    with TestClient(app) as session_client:
        session_client.post(
            "/api/v1/auth/login", json={"email": "reset@example.com", "password": DEFAULT_PASSWORD}
        )
        auth_service.set_password(db_session, user, "a-brand-new-password")
        revoked = auth_service.revoke_all_sessions(db_session, user.id)
        assert revoked == 1
        assert session_client.post("/api/v1/auth/refresh").status_code == 401


def test_unknown_user_id_in_a_valid_token_is_rejected(anon_client):
    from backend.app.core.security import create_access_token

    token, _ = create_access_token(uuid.uuid4())
    anon_client.headers["Authorization"] = f"Bearer {token}"
    assert anon_client.get("/api/v1/auth/me").status_code == 401
