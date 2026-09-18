# HandBase Web Seed

Working-name seed for a mobile-first, multilingual, metadata-driven database application inspired by the interaction model of HanDBase/Palm-era personal databases.

## Core principles

- User-defined tables, fields, records and saved views.
- PostgreSQL as the primary database.
- FastAPI + SQLAlchemy + Alembic backend.
- React + TypeScript + Vite frontend.
- Hebrew/English/Portuguese internationalization.
- First-class RTL/LTR layout switching.
- RBAC-ready architecture.
- Docker and CapRover deployment from day one.
- Documentation as operational memory under `docs/`.

## Quick start

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Open:
   - App: http://localhost:8000
   - API health: http://localhost:8000/api/health
   - Swagger: http://localhost:8000/docs

## CapRover

Includes `captain-definition`, a production `Dockerfile`, and PowerShell scripts under `scripts/`.

See `docs/04_technical/DEPLOYMENT_CAPROVER.md`.

## Local development

Backend tests (no PostgreSQL server needed — the suite runs on in-memory SQLite):

```
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements-dev.txt
.venv/Scripts/python -m pytest
```

Frontend:

```
cd frontend
npm install
npm run build   # or: npm run dev
```

## Status

The first vertical slice is implemented: workspace → user-defined table →
field definitions → JSONB records, with create, list, edit and delete working
end to end in EN/HE/PT-BR and RTL/LTR.

Saved views, authentication, RBAC and relations are **not** implemented.

See `docs/02_execution/07_progress.md` for exactly what exists today.
