"""User accounts and session lifecycle.

Like the metadata services, this module knows nothing about HTTP: it takes a
session plus plain values and returns models. Cookies, headers and status codes
are the router's business (DEC-010).
"""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.locales import application_default_locale, resolve_locale, validate_locale
from backend.app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    needs_rehash,
    verify_password,
)
from backend.app.models import RefreshToken, User, Workspace, WorkspaceMembership, WorkspaceRole
from backend.app.services.errors import ConflictError, DomainError, NotFoundError, ValidationError, ValidationIssue

MIN_PASSWORD_LENGTH = 10


class AuthenticationError(DomainError):
    status_code = 401
    code = "authentication_failed"


def normalize_email(email: str) -> str:
    """Trim and lower-case.

    Local parts are case-sensitive per RFC 5321, but no mainstream provider
    treats them that way and users do not either. Folding the whole address
    keeps "Admin@Example.com" from becoming a second account.
    """
    return email.strip().lower()


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            "Password is too short.",
            [
                ValidationIssue(
                    field="password",
                    code="password_too_short",
                    message=f"Use at least {MIN_PASSWORD_LENGTH} characters.",
                )
            ],
        )


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #


def get_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} was not found.")
    return user


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(User.email == normalize_email(email))).first()


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    display_name: str | None = None,
    preferred_locale: str | None = None,
) -> User:
    normalized = normalize_email(email)
    if not normalized or "@" not in normalized:
        raise ValidationError(
            "A valid email address is required.",
            [ValidationIssue(field="email", code="invalid_email", message="Expected user@example.com.")],
        )
    _validate_password(password)
    if find_user_by_email(db, normalized) is not None:
        raise ConflictError(f"A user with email {normalized} already exists.")

    user = User(
        email=normalized,
        display_name=(display_name or normalized.split("@")[0]).strip(),
        password_hash=hash_password(password),
        preferred_locale=(
            validate_locale(preferred_locale, field="preferred_locale")
            if preferred_locale is not None
            else application_default_locale()
        ),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_profile(
    db: Session,
    user: User,
    *,
    display_name: str | None = None,
    preferred_locale: str | None = None,
) -> User:
    if display_name is not None:
        user.display_name = display_name.strip()
    if preferred_locale is not None:
        user.preferred_locale = validate_locale(preferred_locale, field="preferred_locale")
    db.commit()
    db.refresh(user)
    return user


def set_password(db: Session, user: User, password: str) -> User:
    _validate_password(password)
    user.password_hash = hash_password(password)
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #


def authenticate(db: Session, *, email: str, password: str) -> User:
    """Verify credentials.

    Every failure raises the same error with the same message: distinguishing
    "no such user" from "wrong password" turns the login form into an account
    enumeration oracle.
    """
    user = find_user_by_email(db, email)
    if user is None or not verify_password(user.password_hash, password):
        raise AuthenticationError("Invalid email or password.")
    if not user.is_active:
        raise AuthenticationError("Invalid email or password.")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    return user


def issue_session(db: Session, user: User) -> tuple[str, int, str]:
    """Start a session: ``(access_token, expires_in, refresh_token)``.

    The refresh token is returned in clear exactly once — only its digest is
    persisted.
    """
    settings = get_settings()
    access_token, expires_in = create_access_token(user.id)
    refresh_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.refresh_token_ttl_seconds),
        )
    )
    db.commit()
    return access_token, expires_in, refresh_token


def _load_refresh_token(db: Session, token: str) -> RefreshToken:
    stored = db.scalars(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(token))
    ).first()
    if stored is None or stored.revoked_at is not None:
        raise AuthenticationError("Invalid or expired session.")

    # SQLite returns naive datetimes even for timezone-aware columns.
    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise AuthenticationError("Invalid or expired session.")
    return stored


def rotate_session(db: Session, refresh_token: str) -> tuple[User, str, int, str]:
    """Exchange a refresh token for a new pair, revoking the presented one.

    Rotation means a stolen refresh token is usable at most once before the
    legitimate client's next refresh invalidates it.
    """
    stored = _load_refresh_token(db, refresh_token)
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid or expired session.")

    stored.revoked_at = datetime.now(UTC)
    db.commit()

    access_token, expires_in, new_refresh = issue_session(db, user)
    return user, access_token, expires_in, new_refresh


def revoke_session(db: Session, refresh_token: str | None) -> None:
    """Best-effort logout: an unknown or already-revoked token is not an error."""
    if not refresh_token:
        return
    stored = db.scalars(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(refresh_token))
    ).first()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        db.commit()


def revoke_all_sessions(db: Session, user_id: uuid.UUID) -> int:
    """Revoke every live session of a user. Used by password changes."""
    count = 0
    for stored in db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
    ):
        stored.revoked_at = datetime.now(UTC)
        count += 1
    db.commit()
    return count


# --------------------------------------------------------------------------- #
# Memberships
# --------------------------------------------------------------------------- #


def list_memberships(db: Session, user_id: uuid.UUID) -> list[tuple[WorkspaceMembership, Workspace]]:
    """Memberships of a user paired with their workspace, ordered by name."""
    statement = (
        select(WorkspaceMembership, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
        .where(WorkspaceMembership.user_id == user_id)
        .order_by(Workspace.name)
    )
    return [(membership, workspace) for membership, workspace in db.execute(statement)]


def get_membership(
    db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> WorkspaceMembership | None:
    return db.scalars(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
    ).first()


def create_workspace_with_owner(
    db: Session, *, user: User, name: str, default_locale: str | None = None
) -> Workspace:
    """Create a workspace and make its creator the OWNER.

    The two steps live together because a workspace with no members is
    unreachable — nobody can grant themselves access to it through the API. See
    :func:`adopt_orphan_workspaces` for repairing ones that predate membership.
    """
    resolved_default = resolve_locale(user.preferred_locale)
    if default_locale is not None:
        resolved_default = validate_locale(default_locale, field="default_locale")
    workspace = Workspace(name=name.strip(), default_locale=resolved_default)
    db.add(workspace)
    db.flush()
    db.add(
        WorkspaceMembership(
            workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.OWNER.value
        )
    )
    db.commit()
    db.refresh(workspace)
    return workspace


def list_orphan_workspaces(db: Session) -> list[Workspace]:
    """Workspaces with no members at all — typically pre-authentication data."""
    statement = (
        select(Workspace)
        .outerjoin(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .where(WorkspaceMembership.id.is_(None))
        .order_by(Workspace.created_at)
    )
    return list(db.scalars(statement))


def adopt_orphan_workspaces(db: Session, user: User) -> list[Workspace]:
    """Give ``user`` OWNER on every memberless workspace.

    Deliberately an explicit operator action rather than part of a migration:
    no migration can know who should own data created before there were users.
    """
    adopted = list_orphan_workspaces(db)
    for workspace in adopted:
        db.add(
            WorkspaceMembership(
                workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.OWNER.value
            )
        )
    db.commit()
    return adopted


def grant_membership(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    role: WorkspaceRole,
) -> WorkspaceMembership:
    """Create or update the membership of one user in one workspace."""
    existing = get_membership(db, workspace_id, user_id)
    if existing is not None:
        existing.role = role.value
        db.commit()
        db.refresh(existing)
        return existing

    membership = WorkspaceMembership(workspace_id=workspace_id, user_id=user_id, role=role.value)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership
