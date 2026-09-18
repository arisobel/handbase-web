"""Dialect-portable column types.

PostgreSQL stays the production database (DEC-002). These aliases render as
native ``UUID``/``JSONB`` on PostgreSQL and degrade to portable types on other
dialects so the test suite can run without a PostgreSQL server.
"""
from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB

# Renders as native UUID on PostgreSQL, CHAR(32) elsewhere.
UUIDType = Uuid(as_uuid=True)


def jsonb() -> JSON:
    """JSONB on PostgreSQL, generic JSON elsewhere."""
    return JSON().with_variant(JSONB(), "postgresql")
