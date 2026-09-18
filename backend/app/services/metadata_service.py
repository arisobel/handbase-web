"""Workspace / table / field operations — the structural half of the engine.

Authorization is deliberately absent here. When memberships and roles land they
belong in a separate layer that decides *whether* a caller may reach these
functions, not inside them.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import FieldDefinition, Record, TableDefinition, Workspace
from backend.app.services.errors import ConflictError, NotFoundError, ValidationError, ValidationIssue
from backend.app.services.field_types import SINGLE_SELECT, SUPPORTED_FIELD_TYPES, select_options
from backend.app.services.identifiers import unique_identifier

# --------------------------------------------------------------------------- #
# Workspaces
# --------------------------------------------------------------------------- #


def list_workspaces(db: Session) -> list[Workspace]:
    return list(db.scalars(select(Workspace).order_by(Workspace.created_at)))


def get_workspace(db: Session, workspace_id: uuid.UUID) -> Workspace:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise NotFoundError(f"Workspace {workspace_id} was not found.")
    return workspace


def create_workspace(db: Session, *, name: str, default_locale: str = "en") -> Workspace:
    workspace = Workspace(name=name.strip(), default_locale=default_locale)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def update_workspace(
    db: Session,
    workspace_id: uuid.UUID,
    *,
    name: str | None = None,
    default_locale: str | None = None,
) -> Workspace:
    workspace = get_workspace(db, workspace_id)
    if name is not None:
        workspace.name = name.strip()
    if default_locale is not None:
        workspace.default_locale = default_locale
    db.commit()
    db.refresh(workspace)
    return workspace


def delete_workspace(db: Session, workspace_id: uuid.UUID) -> None:
    db.delete(get_workspace(db, workspace_id))
    db.commit()


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #


def list_tables(db: Session, workspace_id: uuid.UUID) -> list[TableDefinition]:
    get_workspace(db, workspace_id)
    statement = (
        select(TableDefinition)
        .where(TableDefinition.workspace_id == workspace_id)
        .order_by(TableDefinition.created_at)
    )
    return list(db.scalars(statement))


def get_table(db: Session, table_id: uuid.UUID, *, with_fields: bool = False) -> TableDefinition:
    if with_fields:
        statement = (
            select(TableDefinition)
            .where(TableDefinition.id == table_id)
            .options(selectinload(TableDefinition.fields))
        )
        table = db.scalars(statement).first()
    else:
        table = db.get(TableDefinition, table_id)
    if table is None:
        raise NotFoundError(f"Table {table_id} was not found.")
    return table


def create_table(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    name: str,
    description: str | None = None,
    icon: str | None = None,
) -> TableDefinition:
    get_workspace(db, workspace_id)
    taken = db.scalars(select(TableDefinition.slug).where(TableDefinition.workspace_id == workspace_id))
    table = TableDefinition(
        workspace_id=workspace_id,
        name=name.strip(),
        slug=unique_identifier(name, taken, fallback_prefix="table"),
        description=description,
        icon=icon,
    )
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


def update_table(
    db: Session,
    table_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    icon: str | None = None,
) -> TableDefinition:
    table = get_table(db, table_id)
    if name is not None:
        # The slug is a stable identifier: renaming the table does not move it.
        table.name = name.strip()
    if description is not None:
        table.description = description
    if icon is not None:
        table.icon = icon
    db.commit()
    db.refresh(table)
    return table


def delete_table(db: Session, table_id: uuid.UUID) -> None:
    db.delete(get_table(db, table_id))
    db.commit()


# --------------------------------------------------------------------------- #
# Fields
# --------------------------------------------------------------------------- #


def list_fields(db: Session, table_id: uuid.UUID) -> list[FieldDefinition]:
    get_table(db, table_id)
    statement = (
        select(FieldDefinition)
        .where(FieldDefinition.table_id == table_id)
        .order_by(FieldDefinition.position, FieldDefinition.key)
    )
    return list(db.scalars(statement))


def get_field(db: Session, field_id: uuid.UUID) -> FieldDefinition:
    field = db.get(FieldDefinition, field_id)
    if field is None:
        raise NotFoundError(f"Field {field_id} was not found.")
    return field


def create_field(
    db: Session,
    *,
    table_id: uuid.UUID,
    label: str,
    field_type: str,
    key: str | None = None,
    required: bool = False,
    position: int | None = None,
    config: dict | None = None,
) -> FieldDefinition:
    get_table(db, table_id)
    _validate_field_definition(field_type, config)

    existing = list_fields(db, table_id)
    taken = {f.key for f in existing}
    if key:
        if key in taken:
            raise ConflictError(f"Field key '{key}' already exists in this table.")
        resolved_key = key
    else:
        resolved_key = unique_identifier(label, taken, separator="_", fallback_prefix="field")

    field = FieldDefinition(
        table_id=table_id,
        key=resolved_key,
        label=label.strip(),
        field_type=field_type,
        required=required,
        position=position if position is not None else len(existing),
        config=config or {},
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


def update_field(
    db: Session,
    field_id: uuid.UUID,
    *,
    label: str | None = None,
    required: bool | None = None,
    position: int | None = None,
    config: dict | None = None,
) -> FieldDefinition:
    """Update presentation-level attributes.

    ``key`` and ``field_type`` are immutable for now: changing either would
    require rewriting every JSONB payload in the table, which belongs in a
    dedicated schema-change feature rather than in a PATCH.
    """
    field = get_field(db, field_id)
    if config is not None:
        _validate_field_definition(field.field_type, config)
        field.config = config
    if label is not None:
        field.label = label.strip()
    if required is not None:
        field.required = required
    if position is not None:
        field.position = position
    db.commit()
    db.refresh(field)
    return field


def delete_field(db: Session, field_id: uuid.UUID) -> None:
    """Remove a field definition and drop its key from existing records."""
    field = get_field(db, field_id)
    table_id, key = field.table_id, field.key
    db.delete(field)
    db.flush()

    for record in db.scalars(select(Record).where(Record.table_id == table_id)):
        if key in record.data:
            # Reassign: JSON columns are not tracked for in-place mutation.
            remaining = dict(record.data)
            remaining.pop(key, None)
            record.data = remaining
    db.commit()


def _validate_field_definition(field_type: str, config: dict | None) -> None:
    if field_type not in SUPPORTED_FIELD_TYPES:
        raise ValidationError(
            f"Field type '{field_type}' is not supported yet.",
            [
                ValidationIssue(
                    field="field_type",
                    code="unsupported_type",
                    message="Supported types: " + ", ".join(SUPPORTED_FIELD_TYPES) + ".",
                )
            ],
        )
    if field_type == SINGLE_SELECT and not select_options(config):
        raise ValidationError(
            "A single_select field needs at least one option.",
            [
                ValidationIssue(
                    field="config.options",
                    code="missing_options",
                    message="Provide config.options as a list of strings or {value,label} objects.",
                )
            ],
        )
