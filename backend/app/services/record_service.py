"""Record operations — the data half of the engine.

Every payload is validated against the table's ``FieldDefinition`` rows before
it reaches the JSONB column. A schemaless column is only as trustworthy as the
gate in front of it.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import FieldDefinition, Record, TableDefinition
from backend.app.services.errors import ConflictError, NotFoundError, ValidationError, ValidationIssue
from backend.app.services.field_types import RELATION, coerce_value, is_empty
from backend.app.services.metadata_service import get_table, list_fields


def validate_payload(db: Session, fields: list[FieldDefinition], payload: dict) -> dict:
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

        normalized, issue = coerce_value(key, field.label, field.field_type, field.config, value)
        if issue is None and field.field_type == RELATION:
            target_id = uuid.UUID(str(field.config.get("target_table_id")))
            related = db.get(Record, uuid.UUID(str(normalized)))
            if related is None:
                issue = ValidationIssue(field=key, code="missing_related_record", message=f"Related record for '{field.label}' was not found.")
            elif related.table_id != target_id:
                issue = ValidationIssue(field=key, code="wrong_relation_target", message=f"Related record for '{field.label}' belongs to a different table.")
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
    record = Record(table_id=table_id, data=validate_payload(db, fields, data))
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def replace_record(db: Session, record_id: uuid.UUID, *, data: dict) -> Record:
    """Full replacement: ``data`` becomes the record, validated as on create."""
    record = get_record(db, record_id)
    fields = list_fields(db, record.table_id)
    record.data = validate_payload(db, fields, data)
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
    record.data = validate_payload(db, fields, merged)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record_id: uuid.UUID) -> None:
    record = get_record(db, record_id)
    # JSONB does not give metadata-defined relationships real FK constraints,
    # so enforce the MVP's RESTRICT policy before deleting the target record.
    candidate_fields = db.scalars(select(FieldDefinition).where(FieldDefinition.field_type == RELATION)).all()
    for field in candidate_fields:
        if str(field.config.get("target_table_id")) != str(record.table_id):
            continue
        for dependent in db.scalars(select(Record).where(Record.table_id == field.table_id)):
            if str(dependent.data.get(field.key)) == str(record.id):
                raise ConflictError("This record is still referenced by another record.")
    db.delete(record)
    db.commit()


def relation_display_values(db: Session, fields: list[FieldDefinition], records: list[Record]) -> dict[uuid.UUID, dict[str, str]]:
    """Resolve visible relation labels in bounded batches, avoiding N+1 reads."""
    relation_fields = [field for field in fields if field.field_type == RELATION]
    ids_by_target: dict[uuid.UUID, set[uuid.UUID]] = {}
    for field in relation_fields:
        target_id = uuid.UUID(str(field.config["target_table_id"]))
        for record in records:
            raw = record.data.get(field.key)
            if raw:
                ids_by_target.setdefault(target_id, set()).add(uuid.UUID(str(raw)))
    related_by_id: dict[uuid.UUID, Record] = {}
    for target_id, ids in ids_by_target.items():
        related_by_id.update({item.id: item for item in db.scalars(select(Record).where(Record.table_id == target_id, Record.id.in_(ids)))})
    tables = {table.id: table for table in db.scalars(select(TableDefinition).where(TableDefinition.id.in_(ids_by_target))) }
    result: dict[uuid.UUID, dict[str, str]] = {}
    for record in records:
        labels: dict[str, str] = {}
        for field in relation_fields:
            raw = record.data.get(field.key)
            related = related_by_id.get(uuid.UUID(str(raw))) if raw else None
            if related:
                display_key = tables[related.table_id].display_field_key
                labels[field.key] = str(related.data.get(display_key, "—")) if display_key else "—"
        result[record.id] = labels
    return result
