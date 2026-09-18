# Environment Variables

> **Status:** Active | **Last updated:** 2026-09-18

**Runtime** configuration, read by `backend/app/core/config.py` from the
environment or a local `.env`. In production these live in the CapRover
application's own environment variables.

Deploy-time configuration is a separate, much smaller set that never reaches the
running application — see [Deploy-time](#deploy-time) at the bottom and
`deploy/.env.example`.

## Application

| Variable | Required | Default | Purpose |
|---|:---:|---|---|
| `APP_NAME` | no | `HandBase Web` | Display name |
| `APP_ENV` | prod | `development` | `production` enables the secret-key guard and `Secure` cookies |
| `APP_SECRET_KEY` | **prod** | `change-me` | Signs access tokens. Startup fails in production if unset or placeholder |
| `DATABASE_URL` | yes | `postgresql+psycopg://handbase:handbase@db:5432/handbase` | PostgreSQL URL |
| `DEFAULT_LOCALE` | no | `en` | Locale given to a user created without one |
| `CORS_ORIGINS` | prod | `http://localhost:5173,http://localhost:8000` | Comma-separated trusted origins |
| `APP_BUILD_REVISION` | no | `unknown` | Build identifier reported by `/api/health` |

## Authentication

| Variable | Required | Default | Purpose |
|---|:---:|---|---|
| `ACCESS_TOKEN_TTL_SECONDS` | no | `900` | Access-token lifetime. Not revocable — keep it short |
| `REFRESH_TOKEN_TTL_SECONDS` | no | `1209600` | Refresh-token lifetime (14 days) |
| `AUTH_COOKIE_NAME` | no | `handbase_refresh` | Refresh cookie name |
| `AUTH_COOKIE_SECURE` | no | *(unset)* | Unset means `true` in production, `false` elsewhere. Set `true` to force |
| `AUTH_COOKIE_SAMESITE` | no | `lax` | `lax` blocks the cookie on cross-site POSTs — the CSRF mitigation |

## Testing

| Variable | Required | Default | Purpose |
|---|:---:|---|---|
| `TEST_DATABASE_URL` | no | `postgresql+psycopg://handbase:handbase@localhost:5433/handbase_test` | Target of `pytest -m postgres`. Its schema is **dropped** each run |

## Deploy-time

Read by `deploy/deploy.ps1` from `deploy/.env` or the environment. These say
where to deploy and what proves you may; the running application never sees them.

| Variable | Required | Purpose |
|---|:---:|---|
| `CAPROVER_URL` | yes | CapRover dashboard URL |
| `CAPROVER_APP` | yes | Target application name |
| `CAPROVER_APP_TOKEN` | yes | App-scoped deploy token (not the account password) |

`deploy/deploy.ps1` rejects any other key in `deploy/.env`, so a runtime secret
pasted there is caught instead of being shipped inside the deployment package.

## Notes

- Never commit a production `.env`; both `.env` and `deploy/.env` are gitignored.
- `APP_SECRET_KEY` rotation invalidates outstanding access tokens only —
  refresh tokens are opaque database rows and survive.
- SQLite values are not supported for `DATABASE_URL` (DEC-009). It appears only
  as an in-memory test adapter, configured in code, never through this variable.
