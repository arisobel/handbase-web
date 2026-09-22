import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.core.locales import SupportedLocale
from backend.app.models import WorkspaceRole


class MemberCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: WorkspaceRole = WorkspaceRole.VIEWER


class MemberUpdate(BaseModel):
    role: WorkspaceRole


class TemporaryPasswordReset(BaseModel):
    """Clear-text temporary credential returned only by the reset operation."""

    user_id: uuid.UUID
    email: str
    temporary_password: str


class MemberRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: WorkspaceRole
    preferred_locale: SupportedLocale | None
    is_active: bool
    created_at: datetime | None = None
