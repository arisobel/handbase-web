# HandBase Web Seed

Working-name seed for a mobile-first, multilingual, metadata-driven database application inspired by the interaction model of HanDBase/Palm-era personal databases.

## Core principles

- User-defined tables, fields, records and saved views.
- PostgreSQL as the primary database.
- FastAPI + SQLAlchemy + Alembic backend.
- React + TypeScript + Vite frontend.
- Hebrew/English/Portuguese internationalization.
- First-class RTL/LTR layout switching.
- Per-workspace roles (owner/admin/editor/viewer).
- Docker and CapRover deployment from day one.
- Documentation as operational memory under `docs/`.

## Quick start

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Create the first user — nothing exists until you do:

   ```
   docker compose exec app python -m backend.app.cli create-owner \
     --email you@example.com --workspace "My Workspace"
   ```

4. Open:
   - App: http://localhost:8000
   - API health: http://localhost:8000/api/health
   - Readiness: http://localhost:8000/api/ready
   - Swagger: http://localhost:8000/docs

There is no default account and no seeded password. See
`docs/04_technical/BOOTSTRAP_OWNER.md`.

## CapRover

Includes `captain-definition`, a production `Dockerfile`, and PowerShell scripts under `scripts/`.

See `docs/04_technical/DEPLOYMENT_CAPROVER.md`.

## Local development

Fast backend tests (no PostgreSQL server needed — in-memory SQLite):

```
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements-dev.txt
.venv/Scripts/python -m pytest
```

PostgreSQL integration tests — SQLite is only a test adapter, PostgreSQL is the
supported database:

```
docker compose -f docker-compose.test.yml up -d
.venv/Scripts/python -m pytest -m postgres
docker compose -f docker-compose.test.yml down -v
```

Frontend:

```
cd frontend
npm install
npm run build   # or: npm run dev
```

## Status

Implemented end to end in EN/HE/PT-BR and RTL/LTR: workspace → user-defined
table → field definitions → JSONB records, with create, list, edit and delete;
plus authentication and per-workspace roles.

Saved views, relations, invitations and field-level permissions are **not**
implemented. Roles are granted with the CLI.

See `docs/02_execution/07_progress.md` for exactly what exists today.
