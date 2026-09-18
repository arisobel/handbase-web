import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.api.deps import CurrentUser, require_workspace
from backend.app.db.session import get_db
from backend.app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from backend.app.services import auth_service, metadata_service
from backend.app.services.authz import Capability

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


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
