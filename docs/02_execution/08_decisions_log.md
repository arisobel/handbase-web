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
