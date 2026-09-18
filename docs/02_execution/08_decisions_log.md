# Decisions Log

> **Status:** Active | **Last updated:** 2026-09-18

- **DEC-001** Generic metadata engine: user tables are metadata, not physical SQL tables.
- **DEC-002** PostgreSQL is the primary relational database.
- **DEC-003** Relational platform entities + JSONB dynamic record payload.
- **DEC-004** Internationalization is architectural from the first release.
- **DEC-005** Hebrew RTL is first-class, not a later retrofit.
- **DEC-006** Mobile-first web/PWA direction.
- **DEC-007** Docker/CapRover compatibility from the start.
- **DEC-008** Core remains domain-neutral; school/yeshiva is the first use case only.
- **DEC-009** Model column types are declared through dialect variants
  (`backend/app/db/types.py`): native `UUID`/`JSONB` on PostgreSQL, portable
  equivalents elsewhere. PostgreSQL remains the only supported production
  database (DEC-002); the variants exist so the test suite can run in-memory on
  SQLite without a database server. Verified: the migrated PostgreSQL DDL is
  unchanged.
- **DEC-010** The service layer (`backend/app/services/`) owns all metadata and
  record logic; routers only translate HTTP. Domain errors are raised by services
  and mapped to HTTP responses by a single handler, which keeps authorization
  addable as a separate layer in front of the services rather than inside them.
- **DEC-011** Internal `key` and `slug` identifiers are ASCII-neutral and derived
  from user labels; a label with no Latin characters (e.g. `שם פרטי`) falls back
  to a generated `field_N` / `table-N` identifier. Labels stay in the user's
  language; identifiers stay safe for URLs, JSON keys and future exports.
- **DEC-012** Record values are validated strictly, with no silent coercion
  (`"2024"` is not a number, `true` is not a number). A JSONB payload has no
  database-level type enforcement, so the API boundary is the only place where
  type integrity can be established.
- **DEC-013** `field_definitions.key` and `field_type` are immutable after
  creation. Changing either would require rewriting every stored record payload,
  which belongs in a dedicated schema-change feature rather than in a PATCH.
- **DEC-014** Split token model: a short-lived HS256 JWT access token held only
  in browser memory, plus an opaque refresh token in an `HttpOnly`, `SameSite=Lax`
  cookie scoped to `/api/v1/auth`, rotated on every use and stored as a SHA-256
  digest in `refresh_tokens`. The long-lived credential is therefore the one XSS
  cannot read, and the revocable one is the one that lives in the database.
  Accepted tradeoffs (no CSRF token, no rotation-reuse alarm, no login rate
  limiting) are written down in `04_technical/AUTHENTICATION.md`.
- **DEC-015** Authorization is resolved server-side from the object being
  touched (`record -> table -> workspace`), never from a `workspace_id` supplied
  by the client, and lives in FastAPI dependencies in front of the services so
  `metadata_service`/`record_service` stay free of permission logic (DEC-010).
  A caller who is not a member gets `404` rather than `403`, because `403` would
  confirm that an id exists in somebody else's workspace.
- **DEC-016** The container start command keeps `alembic upgrade head && uvicorn`.
  It matches the single-instance CapRover deployment this app has, and
  PostgreSQL's transactional DDL means a failed migration rolls back and the
  container fails to start rather than serving a half-migrated schema. Revisit
  before running more than one replica: concurrent starts race. `/api/ready`
  exists as the readiness signal.
- **DEC-017** Workspaces that predate authentication are left intact and become
  unreachable until an operator claims them with
  `python -m backend.app.cli adopt-orphans`. Ownership is not inferred by a
  migration: no migration can know who should own data created before there were
  users, and guessing would be worse than an explicit step.
- **DEC-018** Passwords use argon2id via `argon2-cffi` at library defaults, with
  `check_needs_rehash` on every login so parameters can be raised later without a
  reset. No cryptographic primitive is implemented in this repository.
