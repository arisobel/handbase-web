# Authentication

> **Status:** Active | **Last updated:** 2026-09-18

## Token model

Two tokens with different jobs (DEC-014):

| | Access token | Refresh token |
|---|---|---|
| Format | JWT, HS256, signed with `APP_SECRET_KEY` | opaque, 48 random bytes (`secrets.token_urlsafe`) |
| Lifetime | `ACCESS_TOKEN_TTL_SECONDS`, default 15 min | `REFRESH_TOKEN_TTL_SECONDS`, default 14 days |
| Transport | `Authorization: Bearer` header | `HttpOnly` cookie, `Path=/api/v1/auth` |
| Stored where | browser memory only (a module variable) | browser cookie jar; only a SHA-256 digest in `refresh_tokens` |
| Revocable | no | yes — that is the point of the table |

Claims on the access token: `sub` (user id), `typ: "access"`, `iat`, `exp`, `jti`.
`typ` is checked on decode so a token of another kind can never be presented as
an access token.

## Why this split

* **The access token is never persisted by the client.** No `localStorage`, no
  readable cookie. An injected script can use the API while the page is open,
  but it cannot copy a credential that outlives the tab.
* **The refresh token is unreadable by page JavaScript.** `HttpOnly` means the
  long-lived credential is exactly the one XSS cannot exfiltrate.
* **Refresh tokens rotate.** Every `/auth/refresh` revokes the presented token
  and issues a new one, so a stolen refresh token works at most once before the
  legitimate client's next refresh invalidates the thief's copy — and the theft
  becomes visible as a failed refresh.
* **Short access TTL bounds the damage.** Access tokens are not revocable;
  15 minutes is the window in which a leaked one is useful.

## Tradeoffs we are accepting

* **CSRF.** A cookie is attached by the browser automatically, so `/auth/refresh`
  is reachable cross-site in principle. Mitigations in place: `SameSite=Lax`
  (browsers do not attach the cookie to cross-site `POST`s), the cookie is
  scoped to `Path=/api/v1/auth`, and refresh returns the new access token in the
  response body — which the attacker's page cannot read cross-origin. No CSRF
  token is issued. If a future endpoint ever acts on cookie authentication
  alone, that changes and a token becomes necessary.
* **`Secure` depends on environment.** The cookie is marked `Secure` when
  `APP_ENV=production`, and not otherwise, so local development works over
  plain HTTP. Deploy behind TLS; `AUTH_COOKIE_SECURE=true` forces it on.
* **No rotation-reuse alarm.** Replaying a rotated token is rejected but does
  not revoke the whole family. That is a deliberate omission for this phase.
* **Logout is unauthenticated on purpose.** It must work after the access token
  has expired. It only revokes whatever refresh token the caller presents.
* **No rate limiting on `/auth/login`.** Brute-force protection belongs at the
  reverse proxy for now; see the backlog.

## Passwords

argon2id via `argon2-cffi`, at the library's default parameters (which follow
the OWASP recommendation). No cryptography is implemented in this codebase.
`check_needs_rehash` runs on every successful login, so raising the parameters
later upgrades stored hashes transparently.

Minimum length is 10 characters (`auth_service.MIN_PASSWORD_LENGTH`). No
composition rules — length is what matters.

Failed logins return one identical response whether the address is unknown or
the password is wrong, so the form cannot be used to enumerate accounts.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | none | `{email, password}` → session + refresh cookie |
| `POST` | `/api/v1/auth/refresh` | refresh cookie | new access token, rotated cookie |
| `POST` | `/api/v1/auth/logout` | none | revoke the presented refresh token, clear the cookie |
| `GET` | `/api/v1/auth/me` | bearer | the user and their memberships |
| `PATCH` | `/api/v1/auth/me` | bearer | update own `display_name` / `preferred_locale` |

`login` and `refresh` return:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {"id": "...", "email": "...", "display_name": "...",
           "preferred_locale": "he", "is_active": true},
  "memberships": [{"workspace_id": "...", "workspace_name": "Yeshiva",
                   "role": "OWNER",
                   "capabilities": ["change_structure", "manage_workspace",
                                    "read", "write_records"]}]
}
```

`capabilities` exists so the UI can hide actions the server would reject; it is
a convenience, never the enforcement point.

## Locale

`users.preferred_locale` is the account's language. The frontend applies it on
login and on session restore, and writes changes back through `PATCH /auth/me`,
so the choice follows the account to another device rather than living in one
browser's `localStorage`.

## Frontend session lifecycle

1. On load, the app calls `/auth/refresh`. A surviving cookie restores the
   session silently; otherwise the user lands on `/login`.
2. Any API call that returns `401` triggers one refresh attempt and a replay.
   If the refresh also fails, the session is cleared and the route guard
   redirects to `/login`.
3. `/auth/*` calls are excluded from that retry so a failed login cannot loop.

## Startup guard

The application refuses to start when `APP_ENV=production` and `APP_SECRET_KEY`
is unset or still the placeholder: every session in the deployment would
otherwise be forgeable. Outside production it logs a warning instead.
