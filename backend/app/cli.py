"""Operator commands.

    python -m backend.app.cli create-owner --email admin@example.com --workspace "My Workspace"
    python -m backend.app.cli grant --email user@example.com --workspace-id <uuid> --role EDITOR
    python -m backend.app.cli adopt-orphans --email admin@example.com
    python -m backend.app.cli list-workspaces
    python -m backend.app.cli reset-password --email admin@example.com

The password is read interactively by default. ``--password-stdin`` exists for
automation; there is deliberately no ``--password`` flag, because passwords on a
command line land in shell history and process listings.

No default account is created anywhere in this codebase. The first user exists
only once an operator runs ``create-owner``.
"""
import argparse
import getpass
import sys
import uuid

from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models import WorkspaceRole
from backend.app.services import auth_service
from backend.app.services.errors import DomainError

MIN_PASSWORD_LENGTH = auth_service.MIN_PASSWORD_LENGTH


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        password = sys.stdin.readline().rstrip("\n")
        if not password:
            raise SystemExit("No password received on stdin.")
        return password

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    return password


def _resolve_user(db: Session, email: str):
    user = auth_service.find_user_by_email(db, email)
    if user is None:
        raise SystemExit(f"No user with email {auth_service.normalize_email(email)}.")
    return user


def cmd_create_owner(db: Session, args: argparse.Namespace) -> None:
    """Create the first (or any) user and give them a workspace they own."""
    existing = auth_service.find_user_by_email(db, args.email)
    if existing is not None:
        user = existing
        print(f"User {user.email} already exists; reusing it.")
    else:
        password = _read_password(args.password_stdin)
        user = auth_service.create_user(
            db,
            email=args.email,
            password=password,
            display_name=args.display_name,
            preferred_locale=args.locale,
        )
        print(f"Created user {user.email} ({user.id}).")

    workspace = auth_service.create_workspace_with_owner(
        db, user=user, name=args.workspace, default_locale=args.locale
    )
    print(f"Created workspace '{workspace.name}' ({workspace.id}) owned by {user.email}.")


def cmd_grant(db: Session, args: argparse.Namespace) -> None:
    """Give an existing user a role in an existing workspace."""
    user = _resolve_user(db, args.email)
    membership = auth_service.grant_membership(
        db,
        workspace_id=uuid.UUID(args.workspace_id),
        user_id=user.id,
        role=WorkspaceRole(args.role.upper()),
    )
    print(f"{user.email} is now {membership.role} in workspace {membership.workspace_id}.")


def cmd_adopt_orphans(db: Session, args: argparse.Namespace) -> None:
    """Assign OWNER on every workspace that currently has no members.

    This is the documented path for workspaces created before authentication
    existed. Nothing is deleted or rewritten — only memberships are added.
    """
    user = _resolve_user(db, args.email)
    orphans = auth_service.list_orphan_workspaces(db)
    if not orphans:
        print("No memberless workspaces found.")
        return

    print(f"{len(orphans)} memberless workspace(s) will be assigned to {user.email}:")
    for workspace in orphans:
        print(f"  - {workspace.name} ({workspace.id})")
    if not args.yes:
        answer = input("Proceed? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            raise SystemExit("Aborted.")

    adopted = auth_service.adopt_orphan_workspaces(db, user)
    print(f"Assigned OWNER on {len(adopted)} workspace(s).")


def cmd_list_workspaces(db: Session, args: argparse.Namespace) -> None:
    """List every workspace with its member count — including orphans."""
    from sqlalchemy import func, select

    from backend.app.models import Workspace, WorkspaceMembership

    statement = (
        select(Workspace, func.count(WorkspaceMembership.id))
        .outerjoin(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .group_by(Workspace.id)
        .order_by(Workspace.created_at)
    )
    rows = list(db.execute(statement))
    if not rows:
        print("No workspaces.")
        return
    for workspace, members in rows:
        flag = "  (no members)" if members == 0 else ""
        print(f"{workspace.id}  {workspace.name}  members={members}{flag}")


def cmd_reset_password(db: Session, args: argparse.Namespace) -> None:
    """Set a new password and end every existing session for that user."""
    user = _resolve_user(db, args.email)
    password = _read_password(args.password_stdin)
    auth_service.set_password(db, user, password)
    revoked = auth_service.revoke_all_sessions(db, user.id)
    print(f"Password updated for {user.email}; {revoked} active session(s) revoked.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m backend.app.cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-owner", help="Create a user and a workspace they own")
    create.add_argument("--email", required=True)
    create.add_argument("--workspace", required=True, help="Name of the workspace to create")
    create.add_argument("--display-name", default=None)
    create.add_argument("--locale", default=None, help="Preferred locale, e.g. he")
    create.add_argument("--password-stdin", action="store_true", help="Read the password from stdin")
    create.set_defaults(handler=cmd_create_owner)

    grant = sub.add_parser("grant", help="Set a user's role in an existing workspace")
    grant.add_argument("--email", required=True)
    grant.add_argument("--workspace-id", required=True)
    grant.add_argument(
        "--role", required=True, choices=[role.value for role in WorkspaceRole]
    )
    grant.set_defaults(handler=cmd_grant)

    adopt = sub.add_parser("adopt-orphans", help="Own every workspace that has no members")
    adopt.add_argument("--email", required=True)
    adopt.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    adopt.set_defaults(handler=cmd_adopt_orphans)

    listing = sub.add_parser("list-workspaces", help="List workspaces and their member counts")
    listing.set_defaults(handler=cmd_list_workspaces)

    reset = sub.add_parser("reset-password", help="Set a new password and revoke sessions")
    reset.add_argument("--email", required=True)
    reset.add_argument("--password-stdin", action="store_true")
    reset.set_defaults(handler=cmd_reset_password)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db = SessionLocal()
    try:
        args.handler(db, args)
    except DomainError as exc:
        print(f"Error: {exc.message}", file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
