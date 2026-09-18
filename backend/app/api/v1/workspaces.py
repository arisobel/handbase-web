import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from backend.app.services import metadata_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(db: Session = Depends(get_db)):
    return metadata_service.list_workspaces(db)


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db)):
    return metadata_service.create_workspace(
        db, name=payload.name, default_locale=payload.default_locale
    )


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(workspace_id: uuid.UUID, db: Session = Depends(get_db)):
    return metadata_service.get_workspace(db, workspace_id)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(workspace_id: uuid.UUID, payload: WorkspaceUpdate, db: Session = Depends(get_db)):
    return metadata_service.update_workspace(
        db, workspace_id, name=payload.name, default_locale=payload.default_locale
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(workspace_id: uuid.UUID, db: Session = Depends(get_db)):
    metadata_service.delete_workspace(db, workspace_id)
