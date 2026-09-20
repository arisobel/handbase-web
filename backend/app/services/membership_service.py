"""Workspace membership administration and owner-safety invariants."""
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import User, WorkspaceMembership, WorkspaceRole
from backend.app.services import auth_service
from backend.app.services.errors import ConflictError, NotFoundError


def list_members(
    db: Session, workspace_id: uuid.UUID
) -> list[tuple[WorkspaceMembership, User]]:
    statement = (
        select(WorkspaceMembership, User)
        .join(User, User.id == WorkspaceMembership.user_id)
        .where(WorkspaceMembership.workspace_id == workspace_id)
        .order_by(User.display_name, User.email)
    )
    return list(db.execute(statement))


def add_existing_user(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    email: str,
    role: WorkspaceRole,
) -> tuple[WorkspaceMembership, User]:
    user = auth_service.find_user_by_email(db, email)
    if user is None:
        raise NotFoundError(
            "No account exists for that email. Invitation links are not implemented yet."
        )
    if auth_service.get_membership(db, workspace_id, user.id) is not None:
        raise ConflictError("That user is already a member of this workspace.")

    membership = WorkspaceMembership(
        workspace_id=workspace_id, user_id=user.id, role=role.value
    )
    db.add(membership)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("That user is already a member of this workspace.") from exc
    db.refresh(membership)
    return membership, user


def get_workspace_membership(
    db: Session, workspace_id: uuid.UUID, membership_id: uuid.UUID
) -> WorkspaceMembership:
    membership = db.scalars(
        select(WorkspaceMembership).where(
            WorkspaceMembership.id == membership_id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    ).first()
    if membership is None:
        raise NotFoundError("Membership not found.")
    return membership


def _locked_memberships(db: Session, workspace_id: uuid.UUID) -> list[WorkspaceMembership]:
    # PostgreSQL row locks serialize competing owner demotions/removals. SQLite
    # ignores FOR UPDATE, which is sufficient for the single-threaded fast suite.
    return list(
        db.scalars(
            select(WorkspaceMembership)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .with_for_update()
        )
    )


def change_role(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    membership_id: uuid.UUID,
    role: WorkspaceRole,
) -> WorkspaceMembership:
    memberships = _locked_memberships(db, workspace_id)
    membership = next((item for item in memberships if item.id == membership_id), None)
    if membership is None:
        raise NotFoundError("Membership not found.")

    if membership.role == WorkspaceRole.OWNER.value and role != WorkspaceRole.OWNER:
        owner_count = sum(item.role == WorkspaceRole.OWNER.value for item in memberships)
        if owner_count <= 1:
            raise ConflictError("The last OWNER cannot be demoted.")

    membership.role = role.value
    db.commit()
    db.refresh(membership)
    return membership


def remove_member(
    db: Session, *, workspace_id: uuid.UUID, membership_id: uuid.UUID
) -> None:
    memberships = _locked_memberships(db, workspace_id)
    membership = next((item for item in memberships if item.id == membership_id), None)
    if membership is None:
        raise NotFoundError("Membership not found.")

    if membership.role == WorkspaceRole.OWNER.value:
        owner_count = sum(item.role == WorkspaceRole.OWNER.value for item in memberships)
        if owner_count <= 1:
            raise ConflictError("The last OWNER cannot be removed.")

    db.delete(membership)
    db.commit()
