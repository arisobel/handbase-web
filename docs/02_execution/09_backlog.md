# Backlog

> **Status:** Active | **Last updated:** 2026-09-18

## Done

- CRUD API for workspace/table/field/record.
- Record validation against field definitions.
- Table builder UI.
- Record editor UI.
- Automated tests for the metadata engine.
- Authentication (login / refresh / logout / me).
- Baseline RBAC: `User`, `WorkspaceMembership`, four roles, capability checks.
- PostgreSQL integration test path (`pytest -m postgres`).
- Bootstrap-owner CLI and orphan-workspace adoption.
- Docker Compose stack validated end to end.
- Hardened CapRover packaging: single validated deploy script, app-scoped token,
  timestamped and audited tarballs (DEC-019).

See `07_progress.md` for exactly what each of these covers.

## P0

- Validate a real CapRover deploy. The packaging path is now proven locally
  (the tarball builds a working image); the remaining unknown is the server.
- Rate limiting / lockout on `/api/v1/auth/login`.
- Membership management over the API: invite a user, change a role, remove a
  member. Today this is CLI-only.
- CRUD API for `view_definitions` (the model exists; no endpoints yet).
- Run the fast and PostgreSQL suites in CI, and fail the build when the
  PostgreSQL suite skips.
- Browser verification of the login and workspace screens in `he`/RTL.

## P1

- Self-service password reset (email delivery).
- Filter expressions and saved views.
- Relations.
- Global search.
- Audit log — who changed which record, now that there is a "who".
- Private/shared notes.
- Field reordering and safe field-type changes from the UI.
- Remaining field types: `datetime`, `multi_select`, `email`, `phone`.
- Refresh-token reuse detection (revoke the family on replay).

## P2

- Field-level and record-level permissions; custom roles.
- Tasks/follow-up.
- Import/export.
- PWA/offline.
- Attachments.
