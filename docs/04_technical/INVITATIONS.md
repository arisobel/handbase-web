# Invitations

> **Status:** Active | **Last updated:** 2026-09-20

Workspace invitations onboard addresses that do not yet have accounts. No email
provider is used: an authorized OWNER or ADMIN copies the link manually.

## Verification modes

`LINK_ONLY` preserves the original behaviour. `LINK_AND_PIN` additionally
requires a six-digit code before the invite page exposes account onboarding.
Only a SHA-256 PIN digest is stored; the raw PIN is returned once at creation.
Five incorrect PIN attempts revoke the invitation. PIN verification is persisted
on the still-secret token invitation and acceptance enforces that state.

## Lifecycle and security

`WorkspaceInvitation` stores a normalized email, workspace role, inviter and
lifecycle timestamps. The raw token is generated with `secrets.token_urlsafe`
and returned only by creation; the database stores only its SHA-256 digest.
Tokens are valid for `INVITATION_TTL_HOURS` (168 by default), one-time, and
reject after acceptance, revocation or expiry. A new invitation for the same
email and workspace revokes the prior pending one.

## Authorization and acceptance

OWNER may invite/revoke every role; ADMIN may manage ADMIN, EDITOR and VIEWER,
never OWNER. The server applies this boundary.

The acceptance page locks the invitation email. For a new address it atomically
creates the user, membership and acceptance record. For an existing account,
the invitee signs in first and only the matching normalized email can accept.
Personal locale selected at creation is persisted on `User.preferred_locale`;
workspace locale remains fallback only.
