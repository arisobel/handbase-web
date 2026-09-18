# Bootstrapping the first owner

> **Status:** Active | **Last updated:** 2026-09-18

There is no default account anywhere in this codebase. No migration, seed or
startup hook creates a user. The first user exists only after an operator runs
the command below, and the password is never a literal in the repository.

All commands run from the repository root, or inside the container with
`docker compose exec app …`.

## Create the first owner

```bash
python -m backend.app.cli create-owner \
  --email admin@example.com \
  --workspace "Yeshiva" \
  --locale he
```

The password is prompted for twice and never appears on the command line. The
command creates the user, creates the workspace, and grants OWNER in one step.

If the user already exists it is reused and only the workspace is created, so
the command is safe to run again to add a second owned workspace.

### Non-interactive

For a provisioning script, read the password from stdin:

```bash
printf '%s' "$ADMIN_PASSWORD" | python -m backend.app.cli create-owner \
  --email admin@example.com --workspace "Yeshiva" --password-stdin
```

There is deliberately no `--password` flag: arguments land in shell history and
in the process list.

Minimum password length is 10 characters.

## Existing workspaces created before authentication

Workspaces that predate this phase have no members. Nothing was deleted and
nothing was rewritten — they are simply unreachable through the API until
somebody is made their owner, because no migration can know who that should be.

Find them:

```bash
python -m backend.app.cli list-workspaces
# 8f3c…  Yeshiva                     members=2
# a7a0…  Legacy pre-auth workspace   members=0  (no members)
```

Adopt every memberless workspace:

```bash
python -m backend.app.cli adopt-orphans --email admin@example.com
```

It lists what it is about to do and asks for confirmation; `--yes` skips the
prompt. Only memberships are added.

## Grant a role to somebody else

```bash
python -m backend.app.cli grant \
  --email teacher@example.com \
  --workspace-id 8f3c… \
  --role EDITOR
```

Roles: `OWNER`, `ADMIN`, `EDITOR`, `VIEWER` — see [AUTHORIZATION.md](AUTHORIZATION.md).
Running it again on the same pair updates the role.

The user must already exist. Until an invitation flow lands, create them with
`create-owner` (pointing at a scratch workspace of their own) or add a
`create-user` path to the CLI.

## Reset a password

```bash
python -m backend.app.cli reset-password --email admin@example.com
```

This also revokes every active session for that user, so a compromised password
ends the sessions it could have opened.

## Notes

* All commands use `DATABASE_URL` from the environment, exactly like the app.
* They talk to the service layer, not to HTTP, so they need no running server —
  only a migrated database.
