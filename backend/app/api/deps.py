"""FastAPI dependencies for authentication and workspace authorization.

This is the only place where HTTP meets authorization. Routers declare which
capability an endpoint needs; everything else — resolving the owning workspace
from whatever id the client named, looking up the membership, and deciding —
happens here, in front of the services (DEC-010).

**Not-found vs forbidden.** A caller who is not a member of the resolved
workspace gets ``404``, not ``403``: answering "forbidden" would confirm that a
given table or record id exists in somebody else's workspace. Once membership is
established the workspace is known to exist, so an insufficient role gets a
truthful ``403``.
"""
import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Path, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.security import InvalidTokenError, decode_access_token
from backend.app.db.session import get_db
from backend.app.models import User, WorkspaceMembership
from backend.app.services import auth_service, authz
from backend.app.services.authz import AuthorizationError, Capability
from backend.app.services.errors import DomainError, NotFoundError

_bearer = HTTPBearer(auto_error=False)


class UnauthenticatedError(DomainError):
    status_code = 401
    code = "unauthenticated"


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    db: Session = Depends(get_db),
) -> User:
    """Resolve the bearer access token into an active user."""
    if credentials is None or not credentials.credentials:
        raise UnauthenticatedError("Authentication required.")
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise UnauthenticatedError("Invalid or expired access token.") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthenticatedError("Invalid or expired access token.")
    request.state.user = user
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve a bearer when present, but keep public invitation onboarding public."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise UnauthenticatedError("Invalid or expired access token.") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthenticatedError("Invalid or expired access token.")
    return user


def authorize_workspace(
    db: Session,
    user: User,
    workspace_id: uuid.UUID,
    capability: Capability,
) -> WorkspaceMembership:
    """Authorize ``user`` for ``capability`` on an already-resolved workspace.

    Call this directly from the few routes whose target is named in the request
    body (creating a table, a field or a record); everything else goes through
    the dependency factories below.
    """
    if user.must_change_password:
        raise AuthorizationError("Password change is required before accessing the application.")
    membership = auth_service.get_membership(db, workspace_id, user.id)
    if membership is None:
        raise NotFoundError("Workspace not found.")
    if not authz.has_capability(membership, capability):
        raise AuthorizationError(
            f"Role {membership.role} cannot perform this action in this workspace."
        )
    return membership


# Each factory below is written out with the parameter name the route actually
# uses, so FastAPI binds it from the path or query string without aliasing.


def require_workspace(capability: Capability) -> Callable[..., WorkspaceMembership]:
    """Authorize against a ``{workspace_id}`` path parameter."""

    def dependency(
        user: CurrentUser,
        workspace_id: uuid.UUID = Path(),
        db: Session = Depends(get_db),
    ) -> WorkspaceMembership:
        return authorize_workspace(db, user, workspace_id, capability)

    return dependency


def require_table(capability: Capability) -> Callable[..., WorkspaceMembership]:
    """Authorize against a ``{table_id}`` path parameter (table -> workspace)."""

    def dependency(
        user: CurrentUser,
        table_id: uuid.UUID = Path(),
        db: Session = Depends(get_db),
    ) -> WorkspaceMembership:
        return authorize_workspace(db, user, authz.workspace_of_table(db, table_id), capability)

    return dependency


def require_field(capability: Capability) -> Callable[..., WorkspaceMembership]:
    """Authorize against a ``{field_id}`` path parameter (field -> table -> workspace)."""

    def dependency(
        user: CurrentUser,
        field_id: uuid.UUID = Path(),
        db: Session = Depends(get_db),
    ) -> WorkspaceMembership:
        return authorize_workspace(db, user, authz.workspace_of_field(db, field_id), capability)

    return dependency


def require_record(capability: Capability) -> Callable[..., WorkspaceMembership]:
    """Authorize against a ``{record_id}`` path parameter (record -> table -> workspace)."""

    def dependency(
        user: CurrentUser,
        record_id: uuid.UUID = Path(),
        db: Session = Depends(get_db),
    ) -> WorkspaceMembership:
        return authorize_workspace(db, user, authz.workspace_of_record(db, record_id), capability)

    return dependency


def require_table_query(capability: Capability) -> Callable[..., WorkspaceMembership]:
    """Same as :func:`require_table` for endpoints that take ``?table_id=``."""

    def dependency(
        user: CurrentUser,
        table_id: uuid.UUID = Query(),
        db: Session = Depends(get_db),
    ) -> WorkspaceMembership:
        return authorize_workspace(db, user, authz.workspace_of_table(db, table_id), capability)

    return dependency


def require_workspace_query(capability: Capability) -> Callable[..., WorkspaceMembership]:
    """Same as :func:`require_workspace` for endpoints that take ``?workspace_id=``."""

    def dependency(
        user: CurrentUser,
        workspace_id: uuid.UUID = Query(),
        db: Session = Depends(get_db),
    ) -> WorkspaceMembership:
        return authorize_workspace(db, user, workspace_id, capability)

    return dependency
