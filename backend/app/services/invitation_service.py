"""One-time workspace invitations and transactional acceptance."""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.locales import validate_locale
from backend.app.core.security import generate_invitation_token, hash_invitation_token, hash_password
from backend.app.models import User, Workspace, WorkspaceInvitation, WorkspaceMembership, WorkspaceRole
from backend.app.services import auth_service
from backend.app.services.errors import ConflictError, NotFoundError

INVALID_INVITATION = "Invitation is invalid or no longer available."


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _active(invitation: WorkspaceInvitation) -> bool:
    return invitation.accepted_at is None and invitation.revoked_at is None and _utc(invitation.expires_at) > datetime.now(UTC)


def create(db: Session, *, workspace_id: uuid.UUID, email: str, role: WorkspaceRole, invited_by: User) -> tuple[WorkspaceInvitation, str]:
    normalized = auth_service.normalize_email(email)
    # Replacement prevents multiple simultaneously usable links for one address/workspace.
    for old in db.scalars(select(WorkspaceInvitation).where(
        WorkspaceInvitation.workspace_id == workspace_id,
        WorkspaceInvitation.email == normalized,
        WorkspaceInvitation.accepted_at.is_(None),
        WorkspaceInvitation.revoked_at.is_(None),
    )):
        old.revoked_at = datetime.now(UTC)
    token = generate_invitation_token()
    invitation = WorkspaceInvitation(
        workspace_id=workspace_id,
        email=normalized,
        role=role.value,
        token_digest=hash_invitation_token(token),
        invited_by_user_id=invited_by.id,
        expires_at=datetime.now(UTC) + timedelta(hours=get_settings().invitation_ttl_hours),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation, token


def by_token(db: Session, token: str) -> WorkspaceInvitation:
    invitation = db.scalars(select(WorkspaceInvitation).where(
        WorkspaceInvitation.token_digest == hash_invitation_token(token)
    )).first()
    if invitation is None or not _active(invitation):
        raise NotFoundError(INVALID_INVITATION)
    return invitation


def list_for_workspace(db: Session, workspace_id: uuid.UUID) -> list[WorkspaceInvitation]:
    return list(db.scalars(select(WorkspaceInvitation).where(
        WorkspaceInvitation.workspace_id == workspace_id
    ).order_by(WorkspaceInvitation.created_at.desc())))


def revoke(db: Session, *, workspace_id: uuid.UUID, invitation_id: uuid.UUID) -> None:
    invitation = db.scalars(select(WorkspaceInvitation).where(
        WorkspaceInvitation.id == invitation_id, WorkspaceInvitation.workspace_id == workspace_id
    )).first()
    if invitation is None:
        raise NotFoundError("Invitation not found.")
    if invitation.accepted_at is None and invitation.revoked_at is None:
        invitation.revoked_at = datetime.now(UTC)
        db.commit()


def accept(
    db: Session,
    *,
    token: str,
    authenticated_user: User | None,
    display_name: str | None,
    password: str | None,
    preferred_locale: str | None,
) -> tuple[WorkspaceInvitation, User, Workspace]:
    invitation = by_token(db, token)
    user = authenticated_user or auth_service.find_user_by_email(db, invitation.email)
    if authenticated_user is not None and authenticated_user.email != invitation.email:
        raise ConflictError("Sign in with the invited email to accept this invitation.")
    if user is not None and authenticated_user is None:
        raise ConflictError("This email already has an account. Sign in to accept the invitation.")
    if user is None:
        if not password:
            raise ConflictError("Create an account to accept this invitation.")
        auth_service._validate_password(password)
        user = User(
            email=invitation.email,
            display_name=(display_name or invitation.email.split("@")[0]).strip(),
            password_hash=hash_password(password),
            preferred_locale=validate_locale(preferred_locale or "en", field="preferred_locale"),
            is_active=True,
        )
        db.add(user)
        db.flush()
    if auth_service.get_membership(db, invitation.workspace_id, user.id) is None:
        db.add(WorkspaceMembership(workspace_id=invitation.workspace_id, user_id=user.id, role=invitation.role))
    invitation.accepted_at = datetime.now(UTC)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    workspace = db.get(Workspace, invitation.workspace_id)
    assert workspace is not None
    return invitation, user, workspace
