import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.locales import SupportedLocale
from backend.app.models.auth import WorkspaceRole


class InvitationCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: WorkspaceRole


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    role: WorkspaceRole
    invited_by_user_id: uuid.UUID
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime | None


class InvitationCreatedRead(InvitationRead):
    invitation_url: str


class InvitationPublicRead(BaseModel):
    workspace_name: str
    workspace_default_locale: SupportedLocale
    email: str
    role: WorkspaceRole
    expires_at: datetime
    account_exists: bool


class InvitationAccept(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    password: str | None = Field(default=None, min_length=1, max_length=1024)
    preferred_locale: SupportedLocale | None = None
