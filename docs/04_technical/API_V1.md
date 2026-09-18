# API v1 — Metadata Engine

> **Status:** Active | **Last updated:** 2026-09-18

Base path: `/api/v1`. Interactive reference: `/docs`.

No authentication exists yet. Every endpoint is open; do not expose an instance
publicly until auth lands.

## Workspaces

| Method | Path | Notes |
|---|---|---|
| `GET` | `/workspaces` | |
| `POST` | `/workspaces` | `{name, default_locale?}` |
| `GET` | `/workspaces/{id}` | |
| `PATCH` | `/workspaces/{id}` | |
| `DELETE` | `/workspaces/{id}` | Cascades to tables, fields and records |

## Tables

| Method | Path | Notes |
|---|---|---|
| `GET` | `/tables?workspace_id=` | |
| `POST` | `/tables` | `{workspace_id, name, description?, icon?}` |
| `GET` | `/tables/{id}` | Returns the table **with its `fields`** |
| `PATCH` | `/tables/{id}` | The `slug` is stable and does not follow a rename |
| `DELETE` | `/tables/{id}` | |

## Fields

| Method | Path | Notes |
|---|---|---|
| `GET` | `/field-types` | `{supported, planned}` |
| `GET` | `/fields?table_id=` | Ordered by `position` |
| `POST` | `/fields` | `{table_id, label, field_type, required?, key?, position?, config?}` |
| `GET` | `/fields/{id}` | |
| `PATCH` | `/fields/{id}` | `label`, `required`, `position`, `config` only |
| `DELETE` | `/fields/{id}` | Also removes the key from existing records |

`key` is optional: omit it and a neutral identifier is derived from the label
(`First name` → `first_name`; `שם פרטי` → `field_1`). See DEC-011.

`single_select` requires `config.options`, either `["a", "b"]` or
`[{"value": "a", "label": "כיתה א"}]`. Only `value` is stored.

## Records

| Method | Path | Notes |
|---|---|---|
| `GET` | `/records?table_id=&limit=&offset=` | `{items, total, limit, offset}`, newest first |
| `POST` | `/records` | `{table_id, data}` |
| `GET` | `/records/{id}` | |
| `PUT` | `/records/{id}` | Full replacement of `data` |
| `PATCH` | `/records/{id}` | Merges `data`, then validates the result |
| `DELETE` | `/records/{id}` | |

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

Statuses: `404 not_found`, `409 conflict`, `422 validation_error`. Request-shape
errors (bad UUID, missing body key) still use FastAPI's own 422 format.
