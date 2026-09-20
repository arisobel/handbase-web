import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.locales import SupportedLocale


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    default_locale: SupportedLocale | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    default_locale: SupportedLocale | None = None


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    default_locale: SupportedLocale
    created_at: datetime | None = None
