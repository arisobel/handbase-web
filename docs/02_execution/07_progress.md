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
- PowerShell tar/deploy helpers (superseded by `deploy/` - see deploy hardening below).
- CKJ-inspired documentation tree.

## Implemented — phase 1, metadata engine CRUD

End-to-end path: create workspace → create table → define fields → create
record → list → edit → delete.

### Backend

- Service layer under `backend/app/services/`:
  `metadata_service`, `record_service`, `field_types`, `identifiers`, `errors`.
- Pydantic schemas under `backend/app/schemas/`, separate from the ORM models.
- REST API under `/api/v1/` for workspaces, tables, fields and records.
- Record validation against `FieldDefinition`: unknown keys rejected, `required`
  enforced, values type-checked, no coercion. Types: `text`, `long_text`,
  `number`, `boolean`, `date`, `single_select`.
- Deleting a field removes its key from existing records.
- Migration `20260918_02`: composite `ix_records_table_created`.

### Frontend

- React Router routes, typed API client, table builder, metadata-driven record
  editor, responsive record list, per-field validation messages, EN/HE/PT-BR.

## Implemented — phase 1.5, authentication and authorization

### Identity

- `User` (argon2id password hash, normalized unique email, `preferred_locale`,
  `is_active`), `WorkspaceMembership` (unique per workspace+user) and
  `RefreshToken` (SHA-256 digest, expiry, revocation) in `backend/app/models/auth.py`.
- Migration `20260918_03` — additive; no existing data is touched.

### Authentication

- `POST /api/v1/auth/login`, `POST /auth/refresh`, `POST /auth/logout`,
  `GET /auth/me`, `PATCH /auth/me`.
- Short-lived HS256 access token in the response body; opaque refresh token in
  an `HttpOnly`, `SameSite=Lax` cookie scoped to `/api/v1/auth`, rotated on every
  refresh (DEC-014). Design and tradeoffs: `04_technical/AUTHENTICATION.md`.
- Identical response for a wrong password and an unknown address, so login is
  not an account-enumeration oracle.
- Startup refuses to run with `APP_ENV=production` and a placeholder
  `APP_SECRET_KEY`.

### Authorization

- Roles OWNER / ADMIN / EDITOR / VIEWER mapped to four capabilities in one table
  (`services/authz.ROLE_CAPABILITIES`). Matrix: `04_technical/AUTHORIZATION.md`.
- Enforced by FastAPI dependencies in `backend/app/api/deps.py`, in front of the
  services; `metadata_service` and `record_service` contain no permission logic.
- The owning workspace is always resolved server-side
  (`record -> table -> workspace`); a client-supplied `workspace_id` is never
  accepted as proof (DEC-015).
- Non-members get `404`, insufficient roles get `403`.
- `GET /workspaces` returns only the caller's workspaces; creating one makes the
  creator OWNER.

### Bootstrap

- `python -m backend.app.cli` with `create-owner`, `grant`, `adopt-orphans`,
  `list-workspaces`, `reset-password`. Password is prompted, never a flag.
- No default account exists anywhere. Procedure: `04_technical/BOOTSTRAP_OWNER.md`.
- Pre-authentication workspaces are preserved and claimed explicitly (DEC-017).

### Health

- `/api/health` unchanged (liveness).
- `/api/ready` added: reports the applied vs expected Alembic revision, `503`
  while behind. Neither endpoint exposes configuration.

### Frontend

- `/login`, session restore through `/auth/refresh` on load, one automatic
  refresh-and-replay on any `401`, logout, route guard.
- Workspace selection: one membership enters directly, several show a picker;
  the list always drives the decision.
- Role-aware UI — the table builder, record actions and the editor are hidden
  or read-only per capability. The server enforces the same rules.
- Account locale: applied from `preferred_locale` on login and written back with
  `PATCH /auth/me`, so it follows the account rather than one browser.
- Emails, UUIDs and field keys wrapped in `<bdi dir="ltr">` so they stay legible
  inside Hebrew layouts.

### Tests

- 67 fast tests (SQLite): the 21 phase-1 tests unchanged, plus authentication,
  session lifecycle, role capabilities and cross-workspace isolation.
- 10 PostgreSQL integration tests under `backend/tests/integration/`, marked
  `postgres` and excluded from the default run:
  `04_technical`/`03_validation/POSTGRES_INTEGRATION.md`.

## Implemented - deploy hardening

- `deploy/deploy.ps1` replaces `scripts/build-tar.ps1` and
  `scripts/deploy-caprover.ps1`, which were removed. One script, because the app
  is one CapRover image.
- Fixed order, each step fatal: load config -> validate layout -> `pytest` ->
  `npm run build` -> package -> audit archive -> deploy.
- `deploy/.env` (gitignored) holds only `CAPROVER_URL`, `CAPROVER_APP` and
  `CAPROVER_APP_TOKEN`; any other key is a hard error. Every key falls back to
  the environment. `deploy/.env.example` is committed.
- App-scoped deploy token instead of the CapRover account password; exported
  only for the duration of the CLI call and restored afterwards, never printed.
- Timestamped packages `dist/handbase-web_YYYYMMDD_HHmmss.tar`; the five most
  recent are kept and older ones deleted.
- Archive contents limited to what the Docker build reads; the finished archive
  is read back with `tar -tf` and audited against a forbidden list. A package
  that fails inspection, or that is missing a file CapRover needs, is deleted.
- `-SkipDeploy` (package and inspect only) and `-SkipTests` (explicit, warns).
- `.dockerignore` tightened: tests, docs, compose files, secrets and build
  output are out of the image context.
- See DEC-019 and `04_technical/DEPLOYMENT_CAPROVER.md`.

## Not implemented

- Invitations or a membership-management API — roles are granted with the CLI.
- Field-level and record-level permissions, custom roles.
- Rate limiting on `/auth/login`.
- Password reset by email; self-service registration.
- Relations between tables.
- Saved views / filter engine (`view_definitions` is still a model only).
- Search, audit log, tasks, attachments, import/export.
- Offline/PWA service worker.
- Field `key` / `field_type` changes after creation (DEC-013).

## Verification performed on 2026-09-18

Executed, with results:

- `pytest` — 67 passed (SQLite).
- `pytest -m postgres` — 10 passed against PostgreSQL 17 in Docker, schema built
  by `alembic upgrade head` from an empty database.
- `npm run build` — TypeScript and Vite build clean.
- `docker compose build` and `docker compose up` — stack healthy; migrations
  `20260918_01 → 02 → 03` applied on container start; `/api/health` 200;
  `/api/ready` 200 `"ready"`; SPA served.
- In the running container: bootstrap owner created via CLI, login, refresh
  cookie issued with `HttpOnly`/`Path=/api/v1/auth`, `/auth/me`, refresh,
  authenticated CRUD, VIEWER blocked from writing (403), non-member blocked from
  a record id (404), Hebrew round-trip through JSONB intact.

Deploy tooling, verified on 2026-09-18:

- `deploy/deploy.ps1 -SkipDeploy` - full flow green: 67 tests, frontend build,
  package `dist/handbase-web_20260918_110250.tar` (0.28 MB, 76 files), archive
  audit clean, retention applied.
- The extracted package alone builds the production image
  (`docker build` from a clean directory), and the resulting image contains the
  compiled frontend and no test code.
- Failure paths exercised: runtime secrets in `deploy/.env` rejected by name;
  missing/incomplete deploy config stops before any work; with the tar excludes
  deliberately disabled the auditor caught an 80.78 MB archive containing
  `node_modules` and `__pycache__` and deleted it; retention trimmed 7 packages
  to 5.

Not executed:

- CapRover itself. The image, `captain-definition`, start command and packaging
  were exercised locally, but no deploy to a CapRover server took place - no
  server or app token was available, and none was requested.
- The frontend was verified only by TypeScript build and by driving the same API
  it calls; no browser session or RTL screenshot was captured.
