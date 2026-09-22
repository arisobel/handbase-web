# Decisions Log

> **Status:** Active | **Last updated:** 2026-09-20

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
- **DEC-019** CapRover deployment packages use application-scoped tokens and
  validated, timestamped tarballs; deployment credentials are distinct from
  application runtime secrets. `deploy/deploy.ps1` is the single entry point
  (one app, one script), it refuses any key in `deploy/.env` outside
  `CAPROVER_URL` / `CAPROVER_APP` / `CAPROVER_APP_TOKEN`, and it audits the
  finished archive against a forbidden list independent of the one used to build
  it — deleting any package that fails. Tests and the frontend build run before
  packaging, so no unverified artifact can reach the server.
- **DEC-020** Membership administration remains workspace-scoped and introduces
  `manage_members` for OWNER and ADMIN. ADMIN cannot cross the OWNER boundary;
  only OWNER can create/change/remove an OWNER, and the last OWNER is protected
  by a server-side transactional invariant. Global user enumeration remains
  forbidden; this phase adds existing accounts by exact email only.
- **DEC-021** Personal language remains nullable `User.preferred_locale` and is
  authoritative when present. `Workspace.default_locale` is fallback/default,
  never an override; `DEFAULT_LOCALE` is last. Persisted/API values are limited
  to `en`, `he` and `pt-BR` by the shared backend locale module.
- **DEC-022** Workspace invitations are one-time opaque tokens: only a SHA-256
  digest is stored, tokens expire after configurable `INVITATION_TTL_HOURS`
  (seven days by default), and a new invitation for the same email/workspace
  revokes its prior pending invitation. Acceptance is transactional; existing
  accounts must authenticate as the invited email, while new accounts are
  created from the locked invitation email.
- **DEC-023** A relation is a single-valued metadata-level foreign-key analogue:
  UUID in JSONB, target table in field configuration, same workspace only, and
  referenced-record deletion is RESTRICT. No physical per-user FK column is created.
- **DEC-024** `TableDefinition.display_field_key` is the explicit human-readable
  record identity, initialized from the first suitable text field for new tables.
- **DEC-025** Structure Mode is browser-local UI state, never authorization;
  the server's `change_structure` capability remains authoritative.
- **DEC-026** Board/Kanban is a ViewDefinition concern, not a field type;
  a future card move changes the source grouping field.
- **DEC-027** Flexible onboarding retains one global User and membership model:
  local creation returns a generated password once and forces a server-enforced
  first-login password change; PIN invitations use digest-only six-digit PINs
  and revoke deterministically after five failures.
