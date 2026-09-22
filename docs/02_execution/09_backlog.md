# Backlog

> **Status:** Active | **Last updated:** 2026-09-20

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
- Workspace administration: existing-user membership API/UI, `manage_members`,
  last-owner safety and workspace/personal locale settings (DEC-020/021).

See `07_progress.md` for exactly what each of these covers.

## P0

- Validate a real CapRover deploy. The packaging path is now proven locally
  (the tarball builds a working image); the remaining unknown is the server.
- Rate limiting / lockout on `/api/v1/auth/login`.
- CRUD API for `view_definitions` (the model exists; no endpoints yet).
- Run the fast and PostgreSQL suites in CI, and fail the build when the
  PostgreSQL suite skips.
- Browser verification of the login and workspace screens in `he`/RTL.

## P1

- Self-service password reset (email delivery).
- Optional invitation email delivery (SMTP/provider integration). Copyable
  invitation links and onboarding are implemented; no email is sent by design.
- Filter expressions and saved views.
- Relation follow-ups: target search/autocomplete, multi-relation, configurable
  deletion policies and explicit display-field editing for legacy tables.
- Saved Board/Kanban Views: ViewDefinition CRUD, `view_type=board`,
  `group_by_field`, relation/single-select grouping, drag/drop source updates,
  column ordering, mobile horizontal navigation and RTL ordering.
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
