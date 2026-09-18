# API v1 — Metadata Engine

> **Status:** Active | **Last updated:** 2026-09-18

Base path: `/api/v1`. Interactive reference: `/docs`.

**Every endpoint below requires a bearer access token** and membership in the
workspace that owns the object being touched. See
[AUTHENTICATION.md](AUTHENTICATION.md) for how to obtain a token and
[AUTHORIZATION.md](AUTHORIZATION.md) for which role may do what.

The capability each endpoint needs is listed in its table. A caller who is not a
member of the resolved workspace gets `404`, not `403`.

## Auth

See [AUTHENTICATION.md](AUTHENTICATION.md).

| Method | Path | Requires |
|---|---|---|
| `POST` | `/auth/login` | — |
| `POST` | `/auth/refresh` | refresh cookie |
| `POST` | `/auth/logout` | — |
| `GET` | `/auth/me` | bearer |
| `PATCH` | `/auth/me` | bearer |

## Workspaces

| Method | Path | Requires | Notes |
|---|---|---|---|
| `GET` | `/workspaces` | bearer | Only the caller's own workspaces |
| `POST` | `/workspaces` | bearer | `{name, default_locale?}`; the creator becomes OWNER |
| `GET` | `/workspaces/{id}` | `read` | |
| `PATCH` | `/workspaces/{id}` | `manage_workspace` | OWNER only |
| `DELETE` | `/workspaces/{id}` | `manage_workspace` | OWNER only; cascades to tables, fields and records |

## Tables

| Method | Path | Requires | Notes |
|---|---|---|---|
| `GET` | `/tables?workspace_id=` | `read` | |
| `POST` | `/tables` | `change_structure` | `{workspace_id, name, description?, icon?}` |
| `GET` | `/tables/{id}` | `read` | Returns the table **with its `fields`** |
| `PATCH` | `/tables/{id}` | `change_structure` | The `slug` is stable and does not follow a rename |
| `DELETE` | `/tables/{id}` | `change_structure` | |

## Fields

| Method | Path | Requires | Notes |
|---|---|---|---|
| `GET` | `/field-types` | bearer | `{supported, planned}` |
| `GET` | `/fields?table_id=` | `read` | Ordered by `position` |
| `POST` | `/fields` | `change_structure` | `{table_id, label, field_type, required?, key?, position?, config?}` |
| `GET` | `/fields/{id}` | `read` | |
| `PATCH` | `/fields/{id}` | `change_structure` | `label`, `required`, `position`, `config` only |
| `DELETE` | `/fields/{id}` | `change_structure` | Also removes the key from existing records |

`key` is optional: omit it and a neutral identifier is derived from the label
(`First name` → `first_name`; `שם פרטי` → `field_1`). See DEC-011.

`single_select` requires `config.options`, either `["a", "b"]` or
`[{"value": "a", "label": "כיתה א"}]`. Only `value` is stored.

## Records

| Method | Path | Requires | Notes |
|---|---|---|---|
| `GET` | `/records?table_id=&limit=&offset=` | `read` | `{items, total, limit, offset}`, newest first |
| `POST` | `/records` | `write_records` | `{table_id, data}` |
| `GET` | `/records/{id}` | `read` | |
| `PUT` | `/records/{id}` | `write_records` | Full replacement of `data` |
| `PATCH` | `/records/{id}` | `write_records` | Merges `data`, then validates the result |
| `DELETE` | `/records/{id}` | `write_records` | |

## Record validation

`data` is checked against the table's field definitions (DEC-012):

- a key with no matching field is rejected (`unknown_field`);
- `required` fields must be present and non-empty (`required`) — a blank or
  whitespace-only string does not satisfy a required field;
- values must match their declared type (`invalid_type`), with no coercion:
  `"2024"` is not a `number` and `true` is not a `number`;
- `single_select` values must be one of the configured options (`invalid_option`);
- `date` accepts ISO `YYYY-MM-DD` and stores the canonical form;
- empty optional values are dropped rather than stored as `null`.

On `PATCH`, an explicit `null` clears a field. Required-field checks run against
the merged result, so a `PATCH` cannot empty a required field.

## Error shape

Domain errors use a single envelope:

```json
{
  "detail": {
    "code": "validation_error",
    "message": "Record validation failed.",
    "errors": [
      {"field": "entry_year", "code": "invalid_type",
       "message": "Field 'שנת כניסה' of type 'number' expects a number."}
    ]
  }
}
```

`errors[].field` is the field **key**, so a client can place each message next to
the matching input; `message` names the user-facing **label**.

Statuses: `401 unauthenticated`, `403 forbidden`, `404 not_found`,
`409 conflict`, `422 validation_error`. Request-shape errors (bad UUID, missing
body key) still use FastAPI's own 422 format.

## Health

| Method | Path | Requires | Notes |
|---|---|---|---|
| `GET` | `/api/health` | — | Liveness; process up and database answering |
| `GET` | `/api/ready` | — | Readiness; `503` while the schema is behind the build's head |

Both are outside `/api/v1` and deliberately unauthenticated — a load balancer
has no credentials. Neither returns configuration or secrets.
