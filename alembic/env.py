from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.models import auth, metadata  # noqa: F401  (registers the mappers)

config = context.config

# A programmatic caller (the PostgreSQL integration suite) may set the URL on
# the Config it passes in; only fall back to the application settings when it
# has not, so `alembic upgrade` can be pointed at a throwaway database.
if not config.get_main_option("sqlalchemy.url", None):
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
