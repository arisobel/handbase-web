# Environment Variables

> **Status:** Active | **Last updated:** 2026-09-18

| Variable | Required | Purpose |
|---|---:|---|
| `APP_NAME` | no | App name |
| `APP_ENV` | prod | Environment |
| `APP_SECRET_KEY` | prod | Signing secret |
| `DATABASE_URL` | yes | PostgreSQL URL |
| `DEFAULT_LOCALE` | no | Default locale |
| `CORS_ORIGINS` | prod | Trusted origins |
| `APP_BUILD_REVISION` | no | Build identifier |

Never commit production `.env` files.
