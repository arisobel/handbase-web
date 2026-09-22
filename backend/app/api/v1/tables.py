import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import (
    CurrentUser,
    authorize_workspace,
    require_table,
    require_workspace_query,
)
from backend.app.db.session import get_db
from backend.app.schemas.table import TableCreate, TableDetail, TableRead, TableUpdate
from backend.app.services import metadata_service
from backend.app.services.authz import Capability

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get(
    "",
    response_model=list[TableRead],
    dependencies=[Depends(require_workspace_query(Capability.READ))],
)
def list_tables(workspace_id: uuid.UUID = Query(...), db: Session = Depends(get_db)):
    return metadata_service.list_tables(db, workspace_id)


@router.post("", response_model=TableRead, status_code=status.HTTP_201_CREATED)
def create_table(payload: TableCreate, user: CurrentUser, db: Session = Depends(get_db)):
    # The workspace comes from the body, so it is authorized here rather than by
    # a dependency — the id is a lookup key, never proof of access.
    authorize_workspace(db, user, payload.workspace_id, Capability.CHANGE_STRUCTURE)
    return metadata_service.create_table(
        db,
        workspace_id=payload.workspace_id,
        name=payload.name,
        description=payload.description,
        icon=payload.icon,
    )


@router.get(
    "/{table_id}",
    response_model=TableDetail,
    dependencies=[Depends(require_table(Capability.READ))],
)
def get_table(table_id: uuid.UUID, db: Session = Depends(get_db)):
    """Return the table with its field definitions — the payload a form needs."""
    return metadata_service.get_table(db, table_id, with_fields=True)


@router.patch(
    "/{table_id}",
    response_model=TableRead,
    dependencies=[Depends(require_table(Capability.CHANGE_STRUCTURE))],
)
def update_table(table_id: uuid.UUID, payload: TableUpdate, db: Session = Depends(get_db)):
    return metadata_service.update_table(
        db, table_id, name=payload.name, description=payload.description, icon=payload.icon,
        display_field_key=payload.display_field_key,
    )


@router.delete(
    "/{table_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_table(Capability.CHANGE_STRUCTURE))],
)
def delete_table(table_id: uuid.UUID, db: Session = Depends(get_db)):
    metadata_service.delete_table(db, table_id)
