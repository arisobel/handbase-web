# Membership Management

> **Status:** Active | **Last updated:** 2026-09-20

Membership administration is workspace-scoped. There is no global user list or
global administrator. Exact-email lookup happens only after the caller is
authorized for `manage_members` in the named workspace.

## Roles and authority

- OWNER and ADMIN can list members.
- OWNER can add, change or remove any membership, subject to last-owner safety.
- ADMIN can add/change/remove ADMIN, EDITOR and VIEWER memberships.
- ADMIN cannot create, change or remove an OWNER.
- EDITOR and VIEWER cannot access membership administration.
- Workspace rename/default-language changes and deletion remain OWNER-only.

## Safety invariants

The service locks the workspace's membership rows on PostgreSQL before an owner
demotion/removal. A workspace must retain at least one OWNER. Duplicate
workspace/user pairs are rejected by both service checks and the existing
database unique constraint.

Non-members receive `404`, preserving cross-workspace concealment; members that
lack `manage_members` receive `403`.

## Adding people

The current complete flow adds an existing account by exact normalized email.
Unknown addresses are reported as not found. No email is sent and no invitation
token is created. Invitation links, token digests, expiration and acceptance
remain a separate backlog item.

The UI is at `/workspaces/{workspace_id}/settings`, under **Members**.
