# Deployment — CapRover

> **Status:** Active | **Last updated:** 2026-09-18

The `captain-definition` points to the repository `Dockerfile`.

The production image:
1. builds React;
2. installs Python dependencies;
3. copies the frontend build;
4. runs `alembic upgrade head`;
5. starts Uvicorn on port 8000.

## Topology

- one CapRover app for the web/API — **stateless**, no volumes;
- PostgreSQL as a separate CapRover one-click app with persistent storage, or an
  external managed database.

The container holds nothing durable: records live in PostgreSQL, sessions live
in the `refresh_tokens` table, and the access token lives in the user's browser
memory. Redeploying or replacing the container loses nothing and does not log
anybody out.

## Required environment variables

Set these in the CapRover app's *App Configs → Environment Variables*. Never
commit them.

```text
APP_ENV=production
APP_SECRET_KEY=<64+ random characters>
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@srv-captain--handbase-db:5432/handbase
CORS_ORIGINS=https://your-domain.example
DEFAULT_LOCALE=he
```

Optional, all with working defaults — see [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md):

```text
ACCESS_TOKEN_TTL_SECONDS=900
REFRESH_TOKEN_TTL_SECONDS=1209600
AUTH_COOKIE_NAME=handbase_refresh
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
APP_BUILD_REVISION=<git sha>
```

### `APP_SECRET_KEY`

It signs every access token and is the only thing standing between a stranger
and a forged session. **The application refuses to start** when `APP_ENV` is
`production` and this is unset or still the placeholder.

Generate one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Changing it invalidates every outstanding access token; refresh tokens survive
because they are opaque database rows, so users recover on their next refresh.

### TLS is not optional

With `APP_ENV=production` the refresh cookie is marked `Secure`, so the browser
will not send it over plain HTTP and sessions will silently fail to persist.
Enable HTTPS on the CapRover app before first use.

### `CORS_ORIGINS`

Serving the SPA from the same origin as the API means CORS is not in the request
path at all. Keep this narrow anyway — `allow_credentials=True` is set for the
refresh cookie, and a wildcard origin plus credentials is exactly the
combination to avoid.

## First deployment

1. Deploy the PostgreSQL app and note its internal hostname.
2. Deploy this app with the variables above and enable HTTPS.
3. Confirm the schema: `GET /api/ready` must return `200` with
   `"status": "ready"`.
4. Create the first user — nothing exists until you do:

   ```bash
   # from CapRover's web terminal, or `docker exec` on the app container
   python -m backend.app.cli create-owner \
     --email you@your-domain.example --workspace "Yeshiva" --locale he
   ```

   Full procedure: [BOOTSTRAP_OWNER.md](BOOTSTRAP_OWNER.md).
5. Sign in at `/login`.

## Migrations on container start

The start command is unchanged: `alembic upgrade head && uvicorn …`
(DEC-016).

Kept because it suits the deployment model this app actually has — a single
CapRover instance, where the alternative (a manual migration step before every
deploy) is a step someone eventually forgets. PostgreSQL's transactional DDL
means a failed migration rolls back rather than leaving a half-applied schema,
and the container then fails to start instead of serving against a broken one.

The caveat to revisit **before scaling past one replica**: N containers starting
together run N concurrent `alembic upgrade head`. They will not corrupt the
schema, but losers of the race can fail their startup. If this app is ever
scaled out, move the migration into a pre-deploy job and drop it from the start
command.

`/api/ready` returns `503` while the schema is behind the build's expected
revision, which is the signal to hold traffic back.

## Health checks

| Endpoint | Meaning | Use for |
|---|---|---|
| `/api/health` | process alive, database answering | liveness |
| `/api/ready` | schema migrated to this build's head | readiness / post-deploy gate |

Both are unauthenticated — a load balancer has no credentials — and neither
returns configuration, secrets or hostnames.

## Tarball deploy

```powershell
.\scripts\build-tar.ps1
```

Then upload `dist/handbase-web.tar` to CapRover, or:

```powershell
.\scripts\deploy-caprover.ps1 -AppName handbase-web -Server https://captain.example.com
```

## Backups

PostgreSQL holds everything. Back up the database, not the container:

```bash
pg_dump --format=custom "$DATABASE_URL" > handbase-$(date +%F).dump
```

## Still missing before a wide rollout

- rate limiting on `/api/v1/auth/login` (do it at the reverse proxy for now);
- an invitation flow — roles are granted with the CLI;
- log aggregation and an error tracker;
- a restore drill, not just a backup.
