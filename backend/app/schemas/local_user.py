from pydantic import BaseModel, Field
from backend.app.core.locales import SupportedLocale
from backend.app.models.auth import WorkspaceRole


class LocalUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=200)
    role: WorkspaceRole
    preferred_locale: SupportedLocale | None = None


class LocalUserCreated(BaseModel):
    id: str
    email: str
    display_name: str
    role: WorkspaceRole
    temporary_password: str
