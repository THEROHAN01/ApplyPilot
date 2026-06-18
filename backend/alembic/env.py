"""Alembic environment using app settings and model metadata."""
import sys
import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the backend package root is on sys.path when alembic runs from any cwd.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings  # noqa: E402
from database import Base  # noqa: E402
import models  # noqa: F401, E402  ensures all tables registered

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
