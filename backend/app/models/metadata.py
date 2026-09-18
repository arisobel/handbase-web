import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.db.types import UUIDType, jsonb


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    default_locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tables: Mapped[list["TableDefinition"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
        order_by="TableDefinition.created_at",
    )


class TableDefinition(Base):
    __tablename__ = "table_definitions"
    __table_args__ = (UniqueConstraint("workspace_id", "slug", name="uq_table_workspace_slug"),)
    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    workspace: Mapped["Workspace"] = relationship(back_populates="tables")
    fields: Mapped[list["FieldDefinition"]] = relationship(
        back_populates="table",
        cascade="all, delete-orphan",
        order_by="FieldDefinition.position",
    )
    records: Mapped[list["Record"]] = relationship(back_populates="table", cascade="all, delete-orphan")
    views: Mapped[list["ViewDefinition"]] = relationship(back_populates="table", cascade="all, delete-orphan")


class FieldDefinition(Base):
    __tablename__ = "field_definitions"
    __table_args__ = (UniqueConstraint("table_id", "key", name="uq_field_table_key"),)
    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    table_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("table_definitions.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    field_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config: Mapped[dict] = mapped_column(jsonb(), nullable=False, default=dict)
    table: Mapped["TableDefinition"] = relationship(back_populates="fields")


class Record(Base):
    __tablename__ = "records"
    __table_args__ = (Index("ix_records_table_created", "table_id", "created_at"),)
    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    table_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("table_definitions.id", ondelete="CASCADE"))
    data: Mapped[dict] = mapped_column(jsonb(), nullable=False, default=dict)
    # Populated once authentication lands; unused by the metadata engine itself.
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUIDType, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUIDType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    table: Mapped["TableDefinition"] = relationship(back_populates="records")


class ViewDefinition(Base):
    __tablename__ = "view_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    table_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("table_definitions.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    view_type: Mapped[str] = mapped_column(String(30), nullable=False, default="grid")
    definition: Mapped[dict] = mapped_column(jsonb(), nullable=False, default=dict)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    table: Mapped["TableDefinition"] = relationship(back_populates="views")
