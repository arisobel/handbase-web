"""Authentication endpoints.

Token model (see `docs/04_technical/AUTHENTICATION.md`):

* a short-lived **access token** (JWT) returned in the response body, which the
  browser keeps in memory only;
* a long-lived **refresh token** (opaque, rotated on every use) carried in an
  HttpOnly cookie so that page JavaScript — and therefore an XSS payload —
  cannot read it.
"""
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.api.deps import CurrentUser
from backend.app.core.config import get_settings
from backend.app.core.locales import resolve_locale
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.auth import (
    LoginRequest,
    MeRead,
    MembershipRead,
    ProfileUpdate,
    SessionRead,
    UserRead,
)
from backend.app.services import auth_service, authz

router = APIRouter(prefix="/auth", tags=["auth"])


def _memberships(db: Session, user: User) -> list[MembershipRead]:
    return [
        MembershipRead(
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            role=membership.role,
            capabilities=sorted(
                capability.value for capability in authz.capabilities_of(authz.role_of(membership))
            ),
        )
        for membership, workspace in auth_service.list_memberships(db, user.id)
    ]


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.refresh_token_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.auth_cookie_samesite,
        # Scoped to the endpoints that consume it, so it is not attached to
        # every API request.
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/api/v1/auth",
    )


def _session_payload(db: Session, user: User, access_token: str, expires_in: int) -> SessionRead:
    return SessionRead(
        access_token=access_token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
        memberships=_memberships(db, user),
        effective_locale=resolve_locale(user.preferred_locale),
    )


@router.post("/login", response_model=SessionRead)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, email=payload.email, password=payload.password)
    access_token, expires_in, refresh_token = auth_service.issue_session(db, user)
    _set_refresh_cookie(response, refresh_token)
    return _session_payload(db, user, access_token, expires_in)


@router.post("/refresh", response_model=SessionRead)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    """Exchange the refresh cookie for a new access token, rotating the cookie."""
    settings = get_settings()
    presented = request.cookies.get(settings.auth_cookie_name)
    if not presented:
        raise auth_service.AuthenticationError("No active session.")

    user, access_token, expires_in, new_refresh = auth_service.rotate_session(db, presented)
    _set_refresh_cookie(response, new_refresh)
    return _session_payload(db, user, access_token, expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Revoke the presented refresh token and clear the cookie.

    Unauthenticated on purpose: logging out must work even once the access token
    has expired. The access token itself is not revocable, which is why its TTL
    is short.
    """
    settings = get_settings()
    auth_service.revoke_session(db, request.cookies.get(settings.auth_cookie_name))
    _clear_refresh_cookie(response)


@router.get("/me", response_model=MeRead)
def me(user: CurrentUser, db: Session = Depends(get_db)):
    return MeRead(
        user=UserRead.model_validate(user),
        memberships=_memberships(db, user),
        effective_locale=resolve_locale(user.preferred_locale),
    )


@router.patch("/me", response_model=MeRead)
def update_me(payload: ProfileUpdate, user: CurrentUser, db: Session = Depends(get_db)):
    """Update the caller's own profile — currently display name and locale."""
    updated = auth_service.update_profile(
        db, user, display_name=payload.display_name, preferred_locale=payload.preferred_locale
    )
    return MeRead(
        user=UserRead.model_validate(updated),
        memberships=_memberships(db, updated),
        effective_locale=resolve_locale(updated.preferred_locale),
    )
