# Locale Resolution

> **Status:** Active | **Last updated:** 2026-09-20

Supported locale identifiers are exactly `en`, `he` and `pt-BR`. Backend
validation and resolution use `backend/app/core/locales.py`; arbitrary locale
strings are rejected.

Resolution order:

1. authenticated `User.preferred_locale`, when set and supported;
2. active `Workspace.default_locale`, when relevant;
3. application `DEFAULT_LOCALE`, falling back safely to `en` if misconfigured.

The user value is a personal preference and follows the account across
workspaces and devices. The workspace value is only a fallback/default and is
never copied over members' personal preferences. `localStorage` is retained
only to bootstrap the login screen before authentication is restored.

The global language selector updates the interface immediately and persists an
authenticated change through `PATCH /api/v1/auth/me`. The workspace General
settings form changes only `Workspace.default_locale` and is OWNER-only.
