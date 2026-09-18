import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import (
    CurrentUser,
    authorize_workspace,
    require_field,
    require_table_query,
)
from backend.app.db.session import get_db
from backend.app.schemas.field import FieldCreate, FieldRead, FieldTypeCatalog, FieldUpdate
from backend.app.services import authz, metadata_service
from backend.app.services.authz import Capability
from backend.app.services.field_types import PLANNED_FIELD_TYPES, SUPPORTED_FIELD_TYPES

router = APIRouter(tags=["fields"])


@router.get("/field-types", response_model=FieldTypeCatalog)
def field_types(user: CurrentUser):
    """Field types the engine accepts today, and the ones still on the roadmap."""
    return FieldTypeCatalog(supported=list(SUPPORTED_FIELD_TYPES), planned=list(PLANNED_FIELD_TYPES))


@router.get(
    "/fields",
    response_model=list[FieldRead],
    dependencies=[Depends(require_table_query(Capability.READ))],
)
def list_fields(table_id: uuid.UUID = Query(...), db: Session = Depends(get_db)):
    return metadata_service.list_fields(db, table_id)


@router.post("/fields", response_model=FieldRead, status_code=status.HTTP_201_CREATED)
def create_field(payload: FieldCreate, user: CurrentUser, db: Session = Depends(get_db)):
    # `table_id` arrives in the body; resolve it to its workspace before deciding.
    authorize_workspace(
        db, user, authz.workspace_of_table(db, payload.table_id), Capability.CHANGE_STRUCTURE
    )
    return metadata_service.create_field(
        db,
        table_id=payload.table_id,
        label=payload.label,
        field_type=payload.field_type,
        key=payload.key,
        required=payload.required,
        position=payload.position,
        config=payload.config,
    )


@router.get(
    "/fields/{field_id}",
    response_model=FieldRead,
    dependencies=[Depends(require_field(Capability.READ))],
)
def get_field(field_id: uuid.UUID, db: Session = Depends(get_db)):
    return metadata_service.get_field(db, field_id)


@router.patch(
    "/fields/{field_id}",
    response_model=FieldRead,
    dependencies=[Depends(require_field(Capability.CHANGE_STRUCTURE))],
)
def update_field(field_id: uuid.UUID, payload: FieldUpdate, db: Session = Depends(get_db)):
    return metadata_service.update_field(
        db,
        field_id,
        label=payload.label,
        required=payload.required,
        position=payload.position,
        config=payload.config,
    )


@router.delete(
    "/fields/{field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_field(Capability.CHANGE_STRUCTURE))],
)
def delete_field(field_id: uuid.UUID, db: Session = Depends(get_db)):
    metadata_service.delete_field(db, field_id)
