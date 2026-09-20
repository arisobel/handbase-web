"""Workspace authorization.

Two responsibilities, both of which have to stay server-side:

1. **Resolution** — given the id of any object the client names, walk the
   relational graph to the workspace that owns it
   (``record -> table -> workspace``). A ``workspace_id`` sent by the client is
   never accepted as proof of anything; it is at most a lookup key whose
   resolved owner is then authorized.
2. **Capability checks** — map a role to what it may do.

The metadata and record services stay free of all of this (DEC-010); the FastAPI
dependencies in ``backend/app/api/deps.py`` are what call into here.
"""
import enum
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import FieldDefinition, Record, TableDefinition, WorkspaceMembership, WorkspaceRole
from backend.app.services.errors import DomainError, NotFoundError


class AuthorizationError(DomainError):
    status_code = 403
    code = "forbidden"


class Capability(enum.StrEnum):
    """What a caller wants to do, independent of which endpoint they hit."""

    #: Read workspace content: tables, fields, records.
    READ = "read"
    #: Create, edit or delete records.
    WRITE_RECORDS = "write_records"
    #: Create, edit or delete tables and fields.
    CHANGE_STRUCTURE = "change_structure"
    #: Add, update or remove memberships inside the workspace.
    MANAGE_MEMBERS = "manage_members"
    #: Rename or delete the workspace itself.
    MANAGE_WORKSPACE = "manage_workspace"


#: The whole authorization model for this phase, in one table.
#: Field-level, record-level and custom roles are explicitly out of scope.
ROLE_CAPABILITIES: dict[WorkspaceRole, frozenset[Capability]] = {
    WorkspaceRole.OWNER: frozenset(Capability),
    WorkspaceRole.ADMIN: frozenset(
        {
            Capability.READ,
            Capability.WRITE_RECORDS,
            Capability.CHANGE_STRUCTURE,
            Capability.MANAGE_MEMBERS,
        }
    ),
    WorkspaceRole.EDITOR: frozenset({Capability.READ, Capability.WRITE_RECORDS}),
    WorkspaceRole.VIEWER: frozenset({Capability.READ}),
}


def role_of(membership: WorkspaceMembership) -> WorkspaceRole:
    try:
        return WorkspaceRole(membership.role)
    except ValueError:
        # An unrecognized role grants nothing rather than everything.
        return WorkspaceRole.VIEWER


def capabilities_of(role: WorkspaceRole) -> frozenset[Capability]:
    return ROLE_CAPABILITIES.get(role, frozenset())


def has_capability(membership: WorkspaceMembership, capability: Capability) -> bool:
    return capability in capabilities_of(role_of(membership))


def authorize_member_role_change(
    actor: WorkspaceMembership,
    *,
    current_role: WorkspaceRole | None = None,
    new_role: WorkspaceRole | None = None,
) -> None:
    """Prevent ADMIN from crossing the OWNER privilege boundary."""
    if role_of(actor) is WorkspaceRole.OWNER:
        return
    if current_role is WorkspaceRole.OWNER or new_role is WorkspaceRole.OWNER:
        raise AuthorizationError("Only an OWNER can manage OWNER memberships.")


# --------------------------------------------------------------------------- #
# Server-side workspace resolution
# --------------------------------------------------------------------------- #


def workspace_of_table(db: Session, table_id: uuid.UUID) -> uuid.UUID:
    workspace_id = db.scalar(
        select(TableDefinition.workspace_id).where(TableDefinition.id == table_id)
    )
    if workspace_id is None:
        raise NotFoundError(f"Table {table_id} was not found.")
    return workspace_id


def workspace_of_field(db: Session, field_id: uuid.UUID) -> uuid.UUID:
    workspace_id = db.scalar(
        select(TableDefinition.workspace_id)
        .join(FieldDefinition, FieldDefinition.table_id == TableDefinition.id)
        .where(FieldDefinition.id == field_id)
    )
    if workspace_id is None:
        raise NotFoundError(f"Field {field_id} was not found.")
    return workspace_id


def workspace_of_record(db: Session, record_id: uuid.UUID) -> uuid.UUID:
    """``record -> table -> workspace``, resolved in the database."""
    workspace_id = db.scalar(
        select(TableDefinition.workspace_id)
        .join(Record, Record.table_id == TableDefinition.id)
        .where(Record.id == record_id)
    )
    if workspace_id is None:
        raise NotFoundError(f"Record {record_id} was not found.")
    return workspace_id
