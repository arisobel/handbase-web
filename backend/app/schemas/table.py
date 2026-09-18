import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.field import FieldRead


class TableCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=50)


class TableUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=50)


class TableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    created_at: datetime | None = None


class TableDetail(TableRead):
    """A table together with the field definitions that drive its forms."""

    fields: list[FieldRead] = []
