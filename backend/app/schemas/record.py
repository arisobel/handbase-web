import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RecordCreate(BaseModel):
    table_id: uuid.UUID
    #: Free-form by design: the real contract is the table's field definitions,
    #: enforced in the service layer.
    data: dict = Field(default_factory=dict)


class RecordWrite(BaseModel):
    data: dict = Field(default_factory=dict)


class RecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    table_id: uuid.UUID
    data: dict
    relation_display: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RecordPage(BaseModel):
    items: list[RecordRead]
    total: int
    limit: int
    offset: int
