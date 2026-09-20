import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.api.deps import CurrentUser, require_workspace
from backend.app.db.session import get_db
from backend.app.models import WorkspaceMembership, WorkspaceRole
from backend.app.schemas.membership import MemberCreate, MemberRead, MemberUpdate
from backend.app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from backend.app.services import auth_service, authz, membership_service, metadata_service
from backend.app.services.authz import Capability

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _member_read(membership: WorkspaceMembership, user) -> MemberRead:
    return MemberRead(
        id=membership.id,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=membership.role,
        preferred_locale=user.preferred_locale,
        is_active=user.is_active,
        created_at=membership.created_at,
    )


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(user: CurrentUser, db: Session = Depends(get_db)):
    """Only the workspaces the caller belongs to — never the whole table."""
    return [workspace for _membership, workspace in auth_service.list_memberships(db, user.id)]


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, user: CurrentUser, db: Session = Depends(get_db)):
    """Any authenticated user may create a workspace and becomes its OWNER."""
    return auth_service.create_workspace_with_owner(
        db, user=user, name=payload.name, default_locale=payload.default_locale
    )


@router.get("/{workspace_id}/members", response_model=list[MemberRead])
def list_members(
    workspace_id: uuid.UUID,
    _actor: Annotated[
        WorkspaceMembership, Depends(require_workspace(Capability.MANAGE_MEMBERS))
    ],
    db: Session = Depends(get_db),
):
    return [
        _member_read(membership, user)
        for membership, user in membership_service.list_members(db, workspace_id)
    ]


@router.post(
    "/{workspace_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    workspace_id: uuid.UUID,
    payload: MemberCreate,
    actor: Annotated[
        WorkspaceMembership, Depends(require_workspace(Capability.MANAGE_MEMBERS))
    ],
    db: Session = Depends(get_db),
):
    authz.authorize_member_role_change(actor, new_role=payload.role)
    membership, user = membership_service.add_existing_user(
        db, workspace_id=workspace_id, email=payload.email, role=payload.role
    )
    return _member_read(membership, user)


@router.patch("/{workspace_id}/members/{membership_id}", response_model=MemberRead)
def update_member(
    workspace_id: uuid.UUID,
    membership_id: uuid.UUID,
    payload: MemberUpdate,
    actor: Annotated[
        WorkspaceMembership, Depends(require_workspace(Capability.MANAGE_MEMBERS))
    ],
    db: Session = Depends(get_db),
):
    current = membership_service.get_workspace_membership(db, workspace_id, membership_id)
    authz.authorize_member_role_change(
        actor, current_role=authz.role_of(current), new_role=payload.role
    )
    membership = membership_service.change_role(
        db, workspace_id=workspace_id, membership_id=membership_id, role=payload.role
    )
    return _member_read(membership, auth_service.get_user(db, membership.user_id))


@router.delete(
    "/{workspace_id}/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    workspace_id: uuid.UUID,
    membership_id: uuid.UUID,
    actor: Annotated[
        WorkspaceMembership, Depends(require_workspace(Capability.MANAGE_MEMBERS))
    ],
    db: Session = Depends(get_db),
):
    current = membership_service.get_workspace_membership(db, workspace_id, membership_id)
    authz.authorize_member_role_change(actor, current_role=authz.role_of(current))
    membership_service.remove_member(
        db, workspace_id=workspace_id, membership_id=membership_id
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    dependencies=[Depends(require_workspace(Capability.READ))],
)
def get_workspace(workspace_id: uuid.UUID, db: Session = Depends(get_db)):
    return metadata_service.get_workspace(db, workspace_id)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    dependencies=[Depends(require_workspace(Capability.MANAGE_WORKSPACE))],
)
def update_workspace(workspace_id: uuid.UUID, payload: WorkspaceUpdate, db: Session = Depends(get_db)):
    return metadata_service.update_workspace(
        db, workspace_id, name=payload.name, default_locale=payload.default_locale
    )


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_workspace(Capability.MANAGE_WORKSPACE))],
)
def delete_workspace(workspace_id: uuid.UUID, db: Session = Depends(get_db)):
    metadata_service.delete_workspace(db, workspace_id)
