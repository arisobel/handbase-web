import uuid

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.locales import SupportedLocale


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    preferred_locale: SupportedLocale | None
    is_active: bool


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    preferred_locale: SupportedLocale | None = None


class MembershipRead(BaseModel):
    """A workspace the current user belongs to, with their role in it."""

    workspace_id: uuid.UUID
    workspace_name: str
    role: str
    #: Capability names granted by ``role``; the UI uses these to hide actions
    #: the server would reject anyway.
    capabilities: list[str]


class SessionRead(BaseModel):
    """Login/refresh response.

    The refresh token is never in the body — it travels only as an HttpOnly
    cookie. The access token is returned here for the client to hold in memory.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
    memberships: list[MembershipRead]
    effective_locale: SupportedLocale


class MeRead(BaseModel):
    user: UserRead
    memberships: list[MembershipRead]
    effective_locale: SupportedLocale
