# Flexible user onboarding

Workspace administrators can add an existing account, issue an invitation, or
create a platform account locally. A local user is still a global `User` plus a
separate `WorkspaceMembership`; it is never a workspace-only login.

Local creation generates a server-side temporary password, returns it once to
the authorized administrator, stores only its argon2id hash, and sets
`must_change_password`. Workspace access is server-blocked until the user
changes that password through `/api/v1/auth/change-password`.

OWNER may create every role; ADMIN may create ADMIN, EDITOR or VIEWER, never
OWNER. Existing email creation is rejected and never overwrites a password.

Invitation modes are `LINK_ONLY` and `LINK_AND_PIN`. The PIN is a separate
six-digit factor, stored only as SHA-256 digest. Five failed PIN submissions
revoke the invitation deterministically; a replacement invitation is required.
Successful verification is persisted on the invitation, so acceptance cannot
skip it. No password change currently revokes existing refresh sessions.
