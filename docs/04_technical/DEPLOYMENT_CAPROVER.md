# Deployment — CapRover

> **Status:** Active | **Last updated:** 2026-09-18

The `captain-definition` points to the repository `Dockerfile`.

The production image:
1. builds React;
2. installs Python dependencies;
3. copies the frontend build;
4. runs `alembic upgrade head`;
5. starts Uvicorn on port 8000.

## Recommended topology

- one CapRover app for the web/API;
- PostgreSQL as a separate persistent service or external managed database.

Do not store business data in the app container.

## Required production variables

```text
APP_ENV=production
APP_SECRET_KEY=<long-random-secret>
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
DEFAULT_LOCALE=he
CORS_ORIGINS=https://your-domain.example
```

## Tarball deploy

```powershell
.\scripts\build-tar.ps1
```

Then upload `dist/handbase-web.tar` to CapRover, or:

```powershell
.\scripts\deploy-caprover.ps1 -AppName handbase-web -Server https://captain.example.com
```

Future uploaded files should use object storage or a persistent volume.
