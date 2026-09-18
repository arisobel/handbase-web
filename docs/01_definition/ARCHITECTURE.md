# Architecture

> **Status:** Active | **Last updated:** 2026-09-18

```text
React + TypeScript
      |
 i18n + RTL/LTR
      |
    FastAPI
      |
 Auth + workspace roles
      |
 Metadata Engine
      |
SQLAlchemy/Alembic
      |
PostgreSQL + JSONB
```

User-defined tables such as `תלמידים` or `Students` are metadata, not new physical SQL tables.
Dynamic record payloads use JSONB while stable platform relationships remain relational.

Authentication and workspace authorization sit in FastAPI dependencies in front
of the Metadata Engine, not inside it: the same service functions are called by
the bootstrap CLI, where there is no request and no token. See
`04_technical/AUTHORIZATION.md`.
