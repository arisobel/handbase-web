import uuid

from pydantic import BaseModel, ConfigDict, Field


class FieldCreate(BaseModel):
    table_id: uuid.UUID
    label: str = Field(min_length=1, max_length=200)
    field_type: str = Field(max_length=50)
    #: Optional. Omit it and a neutral key is derived from the label, which is
    #: what a Hebrew-only or Portuguese label needs.
    key: str | None = Field(default=None, min_length=1, max_length=120, pattern=r"^[a-z][a-z0-9_]*$")
    required: bool = False
    position: int | None = None
    config: dict = Field(default_factory=dict)


class FieldUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=200)
    required: bool | None = None
    position: int | None = None
    config: dict | None = None


class FieldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    table_id: uuid.UUID
    key: str
    label: str
    field_type: str
    position: int
    required: bool
    config: dict


class FieldTypeCatalog(BaseModel):
    supported: list[str]
    planned: list[str]
