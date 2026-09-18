import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.record import RecordCreate, RecordPage, RecordRead, RecordWrite
from backend.app.services import record_service

router = APIRouter(prefix="/records", tags=["records"])


@router.get("", response_model=RecordPage)
def list_records(
    table_id: uuid.UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = record_service.list_records(db, table_id, limit=limit, offset=offset)
    return RecordPage(
        items=[RecordRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=RecordRead, status_code=status.HTTP_201_CREATED)
def create_record(payload: RecordCreate, db: Session = Depends(get_db)):
    return record_service.create_record(db, table_id=payload.table_id, data=payload.data)


@router.get("/{record_id}", response_model=RecordRead)
def get_record(record_id: uuid.UUID, db: Session = Depends(get_db)):
    return record_service.get_record(db, record_id)


@router.put("/{record_id}", response_model=RecordRead)
def replace_record(record_id: uuid.UUID, payload: RecordWrite, db: Session = Depends(get_db)):
    """Replace the whole payload; validated exactly like a create."""
    return record_service.replace_record(db, record_id, data=payload.data)


@router.patch("/{record_id}", response_model=RecordRead)
def patch_record(record_id: uuid.UUID, payload: RecordWrite, db: Session = Depends(get_db)):
    """Merge a partial payload over the stored record, then validate the result."""
    return record_service.patch_record(db, record_id, data=payload.data)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record_service.delete_record(db, record_id)
