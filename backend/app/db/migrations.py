"""Alembic introspection used by the readiness endpoint and the CLI.

Reads the migration scripts and the ``alembic_version`` table; it never runs a
migration. Applying migrations stays an explicit operation (container start-up
or an operator command), not something an HTTP request can trigger.
"""
from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

#: Repository root: backend/app/db/migrations.py -> up four levels.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


@lru_cache
def expected_head() -> str | None:
    """The single head revision of the bundled migration scripts."""
    if not ALEMBIC_INI.exists():
        return None
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    heads = ScriptDirectory.from_config(config).get_heads()
    return heads[0] if len(heads) == 1 else None


def current_revisions(db: Session) -> set[str]:
    """Revisions recorded in ``alembic_version``; empty if the table is absent."""
    if not inspect(db.get_bind()).has_table("alembic_version"):
        return set()
    return {row[0] for row in db.execute(text("SELECT version_num FROM alembic_version"))}
