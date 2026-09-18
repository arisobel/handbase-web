# Progress

> **Status:** Active | **Last updated:** 2026-09-18

## Implemented — foundation seed

- FastAPI skeleton.
- PostgreSQL SQLAlchemy metadata models.
- JSONB record payload.
- Initial Alembic migration.
- React/TypeScript starter UI.
- EN/HE/PT-BR switching.
- Dynamic RTL/LTR.
- Direction-safe CSS baseline.
- Docker Compose PostgreSQL.
- CapRover `captain-definition`.
- Multi-stage Dockerfile.
- PowerShell tar/deploy helpers.
- CKJ-inspired documentation tree.

## Implemented — first vertical slice (metadata engine CRUD)

End-to-end path now working: create workspace → create table → define fields →
create record → list → edit → delete.

### Backend

- Service layer under `backend/app/services/`:
  - `metadata_service.py` — workspace/table/field operations;
  - `record_service.py` — record CRUD and payload validation;
  - `field_types.py` — per-type value rules;
  - `identifiers.py` — neutral slug/key generation from any-script labels;
  - `errors.py` — domain errors mapped to HTTP by a handler in `main.py`.
- Pydantic schemas under `backend/app/schemas/`, separate from the SQLAlchemy models.
- REST API under `/api/v1/`:
  - `GET|POST /workspaces`, `GET|PATCH|DELETE /workspaces/{id}`
  - `GET /tables?workspace_id=`, `POST /tables`, `GET|PATCH|DELETE /tables/{id}`
    (`GET /tables/{id}` returns the table with its field definitions)
  - `GET /fields?table_id=`, `POST /fields`, `GET|PATCH|DELETE /fields/{id}`
  - `GET /field-types` — supported vs planned types
  - `GET /records?table_id=&limit=&offset=`, `POST /records`,
    `GET|PUT|PATCH|DELETE /records/{id}`
- Record validation against `FieldDefinition`: unknown keys rejected, `required`
  enforced, values type-checked. Supported types: `text`, `long_text`, `number`,
  `boolean`, `date`, `single_select`.
- Validation errors return `{"detail": {"code", "message", "errors": [{field, code, message}]}}`
  so the UI can place messages next to the right input.
- Deleting a field removes its key from existing records.
- Migration `20260918_02` replaces `ix_records_table_id` with the composite
  `ix_records_table_created (table_id, created_at)` used by the list endpoint.
- Models use dialect-portable column types that render as native UUID/JSONB on
  PostgreSQL (see DEC-009).

### Frontend

- React Router routes: `/`, `/workspaces/:workspaceId`, `/tables/:tableId`,
  `/tables/:tableId/settings`, `/tables/:tableId/new`, `/records/:recordId`.
- Typed API client (`src/api/`).
- Table builder: create a table, then add fields with label, type and required.
- Record editor: the form is generated entirely from `FieldDefinition` — no
  domain-specific fields are hard-coded anywhere in the UI.
- Record list: stacked rows on mobile, table on desktop, from the same markup.
- Server-side validation messages rendered per field.
- EN/HE/PT-BR strings for every new screen.
- Stylesheet contains no physical direction properties; only the two chevron
  glyphs are direction-aware.

### Tests

- `backend/tests/` — 21 pytest cases covering workspace creation, table creation,
  field creation, valid records, missing required fields, invalid types,
  undefined fields, edit (PUT and PATCH) and delete.
- Suite runs on in-memory SQLite; no PostgreSQL server needed.
- `frontend/src/vite-env.d.ts` added — `npm run build` previously failed on the
  `styles.css` side-effect import.

## Not implemented

- Authentication, users, memberships, RBAC.
- Relations between tables.
- Saved views / filter engine (`view_definitions` exists as a model only).
- Search.
- Audit log, tasks, attachments, import/export.
- Offline/PWA service worker.
- Field `key` or `field_type` changes after creation.
- Reordering fields from the UI (`position` is settable via the API only).

## Verification performed on 2026-09-18

- `pytest` — 21 passed.
- `npm run build` — TypeScript and Vite build clean.
- `alembic upgrade head --sql` — both revisions compile to PostgreSQL DDL.
- Manual HTTP smoke of `/api/health`, `/api/v1/field-types`, `/api/v1/workspaces`
  and SPA deep-route serving.
- The Docker/CapRover stack was **not** exercised: no Docker daemon available on
  the machine used for this change.
