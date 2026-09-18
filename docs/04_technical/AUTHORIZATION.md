# Authorization

> **Status:** Active | **Last updated:** 2026-09-18

Access is granted per workspace, through `WorkspaceMembership`. A user with no
membership in a workspace cannot see it at all. There is nothing global: there
is no superuser, and no role means anything outside the workspace it was granted
in.

## Roles and capabilities

The complete model lives in one table — `services/authz.ROLE_CAPABILITIES`:

| Capability | OWNER | ADMIN | EDITOR | VIEWER |
|---|:---:|:---:|:---:|:---:|
| `read` — tables, fields, records | ✔ | ✔ | ✔ | ✔ |
| `write_records` — create/edit/delete records | ✔ | ✔ | ✔ | |
| `change_structure` — create/edit/delete tables and fields | ✔ | ✔ | | |
| `manage_workspace` — rename or delete the workspace | ✔ | | | |

An unrecognized role string grants nothing rather than everything.

Creating a workspace is open to any authenticated user, and the creator becomes
its OWNER. A workspace with no members is unreachable through the API by design
— see [the bootstrap guide](BOOTSTRAP_OWNER.md).

## Where the decision is made

Authorization lives in FastAPI dependencies (`backend/app/api/deps.py`), in
front of the services. `metadata_service` and `record_service` contain no
permission checks at all (DEC-010): they are the same functions the CLI calls,
where there is no HTTP request and no bearer token.

A route declares what it needs:

```python
@router.delete("/{record_id}",
               dependencies=[Depends(require_record(Capability.WRITE_RECORDS))])
def delete_record(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record_service.delete_record(db, record_id)
```

## Server-side workspace resolution

**A `workspace_id` from the client is never treated as proof of access.** Every
guard resolves the owning workspace from the object being touched, in the
database:

| The client names | Resolved by | Walk |
|---|---|---|
| `{workspace_id}` | `require_workspace` | — |
| `{table_id}` | `require_table` | table → workspace |
| `{field_id}` | `require_field` | field → table → workspace |
| `{record_id}` | `require_record` | record → table → workspace |
| `?table_id=` | `require_table_query` | table → workspace |
| `?workspace_id=` | `require_workspace_query` | — |

Three endpoints name their target in the request body — creating a table, a
field, or a record. They call `authorize_workspace(...)` on the first line,
after resolving the body's id to its workspace. The id is a lookup key; the
resolved workspace is what gets authorized.

This is what stops `DELETE /api/v1/records/<id-from-another-workspace>` from
working, and it is covered by
`test_a_direct_record_id_cannot_bypass_workspace_authorization`.

## Not found vs forbidden

| Situation | Status |
|---|---|
| No or invalid bearer token | `401 unauthenticated` |
| Authenticated, not a member of the resolved workspace | `404 not_found` |
| Member, but the role lacks the capability | `403 forbidden` |

`404` for non-members is deliberate: replying "forbidden" would confirm that a
particular table or record id exists in somebody else's workspace. Once
membership is established the workspace is known to the caller, so an
insufficient role gets a truthful `403`.

## Explicitly out of scope for this phase

Field-level permissions, record-level/row policies, private notes, custom roles,
permission matrices, invitations and a membership-management API. Roles are
granted with the CLI (`python -m backend.app.cli grant`). These stay in the
backlog.
