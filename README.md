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

## Status

Foundation seed only. The first vertical slice is intentionally small:
workspace → user-defined table → field definitions → JSONB records → saved views.
