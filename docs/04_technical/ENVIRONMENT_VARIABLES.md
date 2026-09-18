# Environment Variables

> **Status:** Active | **Last updated:** 2026-09-18

Read by `backend/app/core/config.py` from the environment or a local `.env`.

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

## Notes

- Never commit a production `.env`; `.env` is gitignored.
- `APP_SECRET_KEY` rotation invalidates outstanding access tokens only —
  refresh tokens are opaque database rows and survive.
- SQLite values are not supported for `DATABASE_URL` (DEC-009). It appears only
  as an in-memory test adapter, configured in code, never through this variable.
