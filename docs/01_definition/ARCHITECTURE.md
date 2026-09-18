# Architecture

> **Status:** Active | **Last updated:** 2026-09-18

```text
React + TypeScript
      |
 i18n + RTL/LTR
      |
    FastAPI
      |
 Auth/RBAC (planned)
      |
 Metadata Engine
      |
SQLAlchemy/Alembic
      |
PostgreSQL + JSONB
```

User-defined tables such as `תלמידים` or `Students` are metadata, not new physical SQL tables.
Dynamic record payloads use JSONB while stable platform relationships remain relational.
