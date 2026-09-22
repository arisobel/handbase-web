import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import (
    CurrentUser,
    authorize_workspace,
    require_record,
    require_table_query,
)
from backend.app.db.session import get_db
from backend.app.schemas.record import RecordCreate, RecordPage, RecordRead, RecordWrite
from backend.app.services import authz, metadata_service, record_service
from backend.app.services.authz import Capability

router = APIRouter(prefix="/records", tags=["records"])


@router.get(
    "",
    response_model=RecordPage,
    dependencies=[Depends(require_table_query(Capability.READ))],
)
def list_records(
    table_id: uuid.UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = record_service.list_records(db, table_id, limit=limit, offset=offset)
    relation_display = record_service.relation_display_values(db, metadata_service.list_fields(db, table_id), items)
    return RecordPage(
        items=[RecordRead.model_validate(item).model_copy(update={"relation_display": relation_display[item.id]}) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=RecordRead, status_code=status.HTTP_201_CREATED)
def create_record(payload: RecordCreate, user: CurrentUser, db: Session = Depends(get_db)):
    authorize_workspace(
        db, user, authz.workspace_of_table(db, payload.table_id), Capability.WRITE_RECORDS
    )
    return record_service.create_record(db, table_id=payload.table_id, data=payload.data)


@router.get(
    "/{record_id}",
    response_model=RecordRead,
    dependencies=[Depends(require_record(Capability.READ))],
)
def get_record(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record = record_service.get_record(db, record_id)
    fields = metadata_service.list_fields(db, record.table_id)
    return RecordRead.model_validate(record).model_copy(update={"relation_display": record_service.relation_display_values(db, fields, [record])[record.id]})


@router.put(
    "/{record_id}",
    response_model=RecordRead,
    dependencies=[Depends(require_record(Capability.WRITE_RECORDS))],
)
def replace_record(record_id: uuid.UUID, payload: RecordWrite, db: Session = Depends(get_db)):
    """Replace the whole payload; validated exactly like a create."""
    return record_service.replace_record(db, record_id, data=payload.data)


@router.patch(
    "/{record_id}",
    response_model=RecordRead,
    dependencies=[Depends(require_record(Capability.WRITE_RECORDS))],
)
def patch_record(record_id: uuid.UUID, payload: RecordWrite, db: Session = Depends(get_db)):
    """Merge a partial payload over the stored record, then validate the result."""
    return record_service.patch_record(db, record_id, data=payload.data)


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_record(Capability.WRITE_RECORDS))],
)
def delete_record(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record_service.delete_record(db, record_id)
