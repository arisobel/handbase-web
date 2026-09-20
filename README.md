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

One CapRover application: the image builds React and serves it from FastAPI.

```powershell
Copy-Item deploy\.env.example deploy\.env   # CAPROVER_URL / APP / APP_TOKEN
.\deploy\deploy.ps1                         # test -> build -> package -> inspect -> deploy
.\deploy\deploy.ps1 -SkipDeploy             # prepare and review a package only
```

Deploy-time credentials live in `deploy/.env` (gitignored). Runtime settings —
`APP_SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS` — belong in the CapRover app's
environment and never enter the package.

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

Workspace settings and existing-user membership management are available in the
application. Saved views, relations, invitation links/email delivery and
field-level permissions are **not** implemented. Roles can also be granted with
the operator CLI.

See `docs/02_execution/07_progress.md` for exactly what exists today.
