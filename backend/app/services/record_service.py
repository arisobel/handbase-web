"""Record operations — the data half of the engine.

Every payload is validated against the table's ``FieldDefinition`` rows before
it reaches the JSONB column. A schemaless column is only as trustworthy as the
gate in front of it.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import FieldDefinition, Record
from backend.app.services.errors import NotFoundError, ValidationError, ValidationIssue
from backend.app.services.field_types import coerce_value, is_empty
from backend.app.services.metadata_service import get_table, list_fields


def validate_payload(fields: list[FieldDefinition], payload: dict) -> dict:
    """Validate ``payload`` against ``fields`` and return the stored form.

    Rules:

    * keys with no matching field definition are rejected;
    * required fields must be present and non-empty;
    * each value must match its declared type;
    * optional empty values are dropped rather than stored as ``null``.
    """
    if not isinstance(payload, dict):
        raise ValidationError(
            "Record data must be an object.",
            [ValidationIssue(field=None, code="invalid_payload", message="Expected a JSON object.")],
        )

    by_key = {field.key: field for field in fields}
    issues: list[ValidationIssue] = []

    for key in payload:
        if key not in by_key:
            issues.append(
                ValidationIssue(
                    field=key,
                    code="unknown_field",
                    message=f"Field '{key}' is not defined on this table.",
                )
            )

    stored: dict = {}
    for key, field in by_key.items():
        provided = key in payload
        value = payload.get(key)

        if not provided or is_empty(value):
            if field.required:
                issues.append(
                    ValidationIssue(
                        field=key,
                        code="required",
                        message=f"Field '{field.label}' is required.",
                    )
                )
            continue

        normalized, issue = coerce_value(key, field.field_type, field.config, value)
        if issue is not None:
            issues.append(issue)
        else:
            stored[key] = normalized

    if issues:
        raise ValidationError("Record validation failed.", issues)
    return stored


def list_records(
    db: Session, table_id: uuid.UUID, *, limit: int = 50, offset: int = 0
) -> tuple[list[Record], int]:
    """Return one page of records plus the total row count for the table."""
    get_table(db, table_id)
    total = db.scalar(select(func.count()).select_from(Record).where(Record.table_id == table_id)) or 0
    statement = (
        select(Record)
        .where(Record.table_id == table_id)
        .order_by(Record.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement)), total


def get_record(db: Session, record_id: uuid.UUID) -> Record:
    record = db.get(Record, record_id)
    if record is None:
        raise NotFoundError(f"Record {record_id} was not found.")
    return record


def create_record(db: Session, *, table_id: uuid.UUID, data: dict) -> Record:
    fields = list_fields(db, table_id)
    record = Record(table_id=table_id, data=validate_payload(fields, data))
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def replace_record(db: Session, record_id: uuid.UUID, *, data: dict) -> Record:
    """Full replacement: ``data`` becomes the record, validated as on create."""
    record = get_record(db, record_id)
    fields = list_fields(db, record.table_id)
    record.data = validate_payload(fields, data)
    db.commit()
    db.refresh(record)
    return record


def patch_record(db: Session, record_id: uuid.UUID, *, data: dict) -> Record:
    """Partial update: merge ``data`` over the stored payload, then validate.

    An explicit ``null`` clears a field, which is why the merge happens before
    validation — required-field checks must see the resulting record, not the
    fragment that was sent.
    """
    if not isinstance(data, dict):
        raise ValidationError(
            "Record data must be an object.",
            [ValidationIssue(field=None, code="invalid_payload", message="Expected a JSON object.")],
        )
    record = get_record(db, record_id)
    fields = list_fields(db, record.table_id)
    merged = {**record.data, **data}
    record.data = validate_payload(fields, merged)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record_id: uuid.UUID) -> None:
    db.delete(get_record(db, record_id))
    db.commit()
