import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.table import TableCreate, TableDetail, TableRead, TableUpdate
from backend.app.services import metadata_service

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get("", response_model=list[TableRead])
def list_tables(workspace_id: uuid.UUID = Query(...), db: Session = Depends(get_db)):
    return metadata_service.list_tables(db, workspace_id)


@router.post("", response_model=TableRead, status_code=status.HTTP_201_CREATED)
def create_table(payload: TableCreate, db: Session = Depends(get_db)):
    return metadata_service.create_table(
        db,
        workspace_id=payload.workspace_id,
        name=payload.name,
        description=payload.description,
        icon=payload.icon,
    )


@router.get("/{table_id}", response_model=TableDetail)
def get_table(table_id: uuid.UUID, db: Session = Depends(get_db)):
    """Return the table with its field definitions — the payload a form needs."""
    return metadata_service.get_table(db, table_id, with_fields=True)


@router.patch("/{table_id}", response_model=TableRead)
def update_table(table_id: uuid.UUID, payload: TableUpdate, db: Session = Depends(get_db)):
    return metadata_service.update_table(
        db, table_id, name=payload.name, description=payload.description, icon=payload.icon
    )


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table(table_id: uuid.UUID, db: Session = Depends(get_db)):
    metadata_service.delete_table(db, table_id)
