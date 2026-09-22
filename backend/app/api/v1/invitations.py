import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.app.api.deps import CurrentUser, get_optional_user, require_workspace
from backend.app.db.session import get_db
from backend.app.models import User, Workspace, WorkspaceInvitation, WorkspaceMembership
from backend.app.schemas.invitation import InvitationAccept, InvitationCreate, InvitationCreatedRead, InvitationPinVerify, InvitationPublicRead, InvitationRead
from backend.app.services import auth_service, authz, invitation_service
from backend.app.services.authz import Capability

router = APIRouter(tags=["invitations"])


def _read(invitation: WorkspaceInvitation) -> InvitationRead:
    return InvitationRead.model_validate(invitation)


@router.post("/workspaces/{workspace_id}/invitations", response_model=InvitationCreatedRead, status_code=status.HTTP_201_CREATED)
def create_invitation(
    workspace_id: uuid.UUID, payload: InvitationCreate, request: Request, user: CurrentUser,
    actor: Annotated[WorkspaceMembership, Depends(require_workspace(Capability.MANAGE_MEMBERS))],
    db: Session = Depends(get_db),
):
    authz.authorize_member_role_change(actor, new_role=payload.role)
    invitation, token, pin = invitation_service.create(db, workspace_id=workspace_id, email=payload.email, role=payload.role, invited_by=user, verification_mode=payload.verification_mode)
    return InvitationCreatedRead(**_read(invitation).model_dump(), invitation_url=f"{str(request.base_url).rstrip('/')}/invite/{token}", pin=pin)


@router.get("/workspaces/{workspace_id}/invitations", response_model=list[InvitationRead])
def list_invitations(
    workspace_id: uuid.UUID,
    _actor: Annotated[WorkspaceMembership, Depends(require_workspace(Capability.MANAGE_MEMBERS))],
    db: Session = Depends(get_db),
):
    return [_read(item) for item in invitation_service.list_for_workspace(db, workspace_id)]


@router.delete("/workspaces/{workspace_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    workspace_id: uuid.UUID, invitation_id: uuid.UUID,
    actor: Annotated[WorkspaceMembership, Depends(require_workspace(Capability.MANAGE_MEMBERS))],
    db: Session = Depends(get_db),
):
    invitation = next((item for item in invitation_service.list_for_workspace(db, workspace_id) if item.id == invitation_id), None)
    if invitation is None:
        invitation_service.revoke(db, workspace_id=workspace_id, invitation_id=invitation_id)
        return
    authz.authorize_member_role_change(actor, current_role=authz.role_of(invitation))
    invitation_service.revoke(db, workspace_id=workspace_id, invitation_id=invitation_id)


@router.get("/invitations/{token}", response_model=InvitationPublicRead)
def inspect_invitation(token: str, db: Session = Depends(get_db)):
    invitation = invitation_service.by_token(db, token)
    workspace = db.get(Workspace, invitation.workspace_id)
    assert workspace is not None
    return InvitationPublicRead(
        workspace_name=workspace.name, workspace_default_locale=workspace.default_locale, email=invitation.email, role=invitation.role,
        expires_at=invitation.expires_at, account_exists=auth_service.find_user_by_email(db, invitation.email) is not None,
        verification_mode=invitation.verification_mode, pin_verified=invitation.pin_verified_at is not None,
    )


@router.post("/invitations/{token}/verify-pin", response_model=InvitationPublicRead)
def verify_invitation_pin(token: str, payload: InvitationPinVerify, db: Session = Depends(get_db)):
    invitation = invitation_service.verify_pin(db, token=token, pin=payload.pin)
    workspace = db.get(Workspace, invitation.workspace_id)
    assert workspace is not None
    return InvitationPublicRead(workspace_name=workspace.name, workspace_default_locale=workspace.default_locale,
        email=invitation.email, role=invitation.role, expires_at=invitation.expires_at,
        account_exists=auth_service.find_user_by_email(db, invitation.email) is not None,
        verification_mode=invitation.verification_mode, pin_verified=True)


@router.post("/invitations/{token}/accept")
def accept_invitation(
    token: str, payload: InvitationAccept, user: Annotated[User | None, Depends(get_optional_user)], db: Session = Depends(get_db)
):
    invitation, accepted_user, workspace = invitation_service.accept(
        db, token=token, authenticated_user=user, display_name=payload.display_name,
        password=payload.password, preferred_locale=payload.preferred_locale,
    )
    return {"workspace_id": workspace.id, "workspace_name": workspace.name, "email": accepted_user.email, "role": invitation.role}
