# Deployment — CapRover

> **Status:** Active | **Last updated:** 2026-09-18

HandBase Web ships as **one** CapRover application. The production image builds
the React frontend and serves it from the FastAPI process, so there is one
deployment script — not a frontend and a backend one.

`captain-definition` points to the repository `Dockerfile`, which:

1. builds React (`npm install && npm run build`);
2. installs Python dependencies;
3. copies the frontend build into the runtime image;
4. runs `alembic upgrade head`;
5. starts Uvicorn on port 8000.

## Two kinds of configuration

Keeping these apart is the point of the whole setup.

| | **Deploy-time** | **Runtime** |
|---|---|---|
| Answers | where to deploy, and what proves you may | how the running application behaves |
| Lives in | `deploy/.env` on the operator's machine | the CapRover app's environment variables |
| Variables | `CAPROVER_URL`, `CAPROVER_APP`, `CAPROVER_APP_TOKEN` | `APP_ENV`, `APP_SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `DEFAULT_LOCALE`, auth cookie settings |
| In the tarball | **never** | **never** |
| Reference | `deploy/.env.example` | [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) |

`deploy/deploy.ps1` **refuses to run** if `deploy/.env` contains anything
outside the three deploy-time keys. A `DATABASE_URL` pasted in there is a real
mistake — it means someone is treating the deployment package as a place to keep
production secrets — so it stops rather than continuing quietly.

## Topology

- one CapRover app for the web/API — **stateless**, no volumes;
- PostgreSQL as a separate CapRover one-click app with persistent storage, or an
  external managed database.

The container holds nothing durable: records live in PostgreSQL, sessions live
in the `refresh_tokens` table, and the access token lives in the user's browser
memory. Redeploying or replacing the container loses nothing and does not log
anybody out.

## Deploying

### 1. Deploy-time configuration (once per machine)

```powershell
Copy-Item deploy\.env.example deploy\.env
```

Then fill in `deploy/.env`:

| Variable | Value |
|---|---|
| `CAPROVER_URL` | your CapRover dashboard, e.g. `https://captain.example.com` |
| `CAPROVER_APP` | the app name, e.g. `handbase-web` |
| `CAPROVER_APP_TOKEN` | *Apps → your app → Deployment → App Token* |

An **app token** is scoped to that single application, so it cannot administer
the CapRover server the way the account password can. No password ever goes into
a script or a file here.

`deploy/.env` is gitignored. Every key also falls back to the environment, so CI
can export `CAPROVER_APP_TOKEN` instead of writing it to disk.

### 2. Runtime configuration (once per app, in CapRover)

In *App Configs → Environment Variables* — never in the repository:

```text
APP_ENV=production
APP_SECRET_KEY=<64+ random characters>
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@srv-captain--handbase-db:5432/handbase
CORS_ORIGINS=https://your-domain.example
DEFAULT_LOCALE=he
```

Optional settings, all with working defaults, are in
[ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md).

#### `APP_SECRET_KEY`

It signs every access token and is the only thing standing between a stranger
and a forged session. **The application refuses to start** when `APP_ENV` is
`production` and this is unset or still the placeholder.

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Changing it invalidates every outstanding access token; refresh tokens survive
because they are opaque database rows, so users recover on their next refresh.

#### TLS is not optional

With `APP_ENV=production` the refresh cookie is marked `Secure`, so the browser
will not send it over plain HTTP and sessions will silently fail to persist.
Enable HTTPS on the CapRover app before first use.

#### `CORS_ORIGINS`

Serving the SPA from the same origin as the API keeps CORS out of the request
path entirely. Keep this narrow anyway — `allow_credentials=True` is set for the
refresh cookie, and a wildcard origin plus credentials is exactly the
combination to avoid.

### 3. Run the deployment

```powershell
.\deploy\deploy.ps1
```

The flow, in order, stopping the whole run on any failure:

```text
load config -> validate layout -> pytest -> frontend build
  -> package -> inspect archive -> CapRover deploy
```

Nothing reaches CapRover unverified: there is no path that deploys a package
whose tests failed or whose archive contains a secret.

#### Options

| Switch | Effect |
|---|---|
| `-SkipDeploy` | Everything except the upload. Validates, tests, builds, packages and inspects, then stops so you can review the archive. |
| `-SkipTests` | Skips `pytest`. Must be passed explicitly and prints a warning. The frontend is still built, because `tsc -b` is its type check and the image needs the result. |
| `-EnvironmentFile <path>` | Use a config file other than `deploy/.env`. |

To prepare and review a package without deploying:

```powershell
.\deploy\deploy.ps1 -SkipDeploy
tar -tvf dist\handbase-web_<timestamp>.tar
```

## What ends up in the package

Timestamped, never overwritten: `dist/handbase-web_YYYYMMDD_HHmmss.tar`.
The five most recent are kept; older ones are deleted automatically.

The archive contains only what the Docker build reads:

```text
captain-definition   Dockerfile   .dockerignore
backend/             frontend/    alembic/   alembic.ini
```

No docs, no tests, no `node_modules`, no `frontend/dist` (the image builds it),
no local database, no `.env` of any kind.

After writing the archive the script reads it back with `tar -tf` and audits
every entry against a forbidden list — `.env*`, `.git`, virtualenvs,
`node_modules`, `__pycache__`, `*.pyc`, `*.log`, `*.sqlite*`, `*.pem`, `*.key`,
`*.token`. This is a separate list from the one used to build the archive, on
purpose: it checks the result rather than trusting the tool that produced it.
**A package that fails inspection is deleted**, so it cannot be deployed by
hand afterwards. The script also verifies that the files CapRover needs are
actually present, so a broken package fails here instead of on the server.

Deploy credentials are handled the same way: `CAPROVER_APP_TOKEN` is exported
only for the duration of the `caprover deploy` call and the previous value (or
its absence) is restored afterwards. The token is never printed.

## First deployment

1. Deploy the PostgreSQL app and note its internal hostname.
2. Set the runtime variables above and enable HTTPS.
3. Run `.\deploy\deploy.ps1`.
4. The container starts and `alembic upgrade head` runs automatically.
5. Confirm the schema: `GET /api/ready` must return `200` with
   `"status": "ready"`.
6. **Create the first user.** No account exists until you do — deployment never
   creates one:

   ```bash
   # CapRover web terminal, or docker exec on the app container
   python -m backend.app.cli create-owner \
     --email you@your-domain.example --workspace "Yeshiva" --locale he
   ```

   The password is prompted for; it is never a command-line flag. If you are
   upgrading an installation that predates authentication, use
   `adopt-orphans` instead to claim existing workspaces. Full procedure:
   [BOOTSTRAP_OWNER.md](BOOTSTRAP_OWNER.md).
7. Sign in at `/login`.

Later deployments repeat only step 3.

## Migrations on container start

The start command is `alembic upgrade head && uvicorn …` (DEC-016).

Kept because it suits the deployment model this app has — a single CapRover
instance, where the alternative (a manual migration step before every deploy) is
a step someone eventually forgets. PostgreSQL's transactional DDL means a failed
migration rolls back rather than leaving a half-applied schema, and the
container then fails to start instead of serving against a broken one.

The caveat to revisit **before scaling past one replica**: N containers starting
together run N concurrent `alembic upgrade head`. They will not corrupt the
schema, but losers of the race can fail their startup. If this app is ever
scaled out, move the migration into a pre-deploy job and drop it from the start
command.

## Health checks

| Endpoint | Meaning | Use for |
|---|---|---|
| `/api/health` | process alive, database answering | liveness |
| `/api/ready` | schema migrated to this build's head | readiness / post-deploy gate |

Both are unauthenticated — a load balancer has no credentials — and neither
returns configuration, secrets or hostnames. `/api/ready` returns `503` while
the schema is behind the build's expected revision.

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
