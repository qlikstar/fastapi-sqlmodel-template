import asyncio
import urllib.parse
from logging.config import fileConfig

from alembic import context
from app.core.config import settings, DBOption
from sqlmodel import SQLModel
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import models explicitly to ensure they're registered with SQLModel.metadata
from app.models.user import User
# Import any other models here as needed

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Determine the database URL based on the DB_ENGINE setting
print(f"DB_ENGINE: {settings.DB_ENGINE}")

if settings.DB_ENGINE == DBOption.POSTGRES:
    # URL encode the password to handle special characters
    encoded_password = urllib.parse.quote_plus(settings.POSTGRES_PASSWORD)
    # Use %% to escape % in ConfigParser strings
    safe_password = encoded_password.replace('%', '%%')
    db_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{safe_password}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    print(f"Using PostgreSQL database URL: postgresql+asyncpg://{settings.POSTGRES_USER}:OBFUSCATED_PASSWORD@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
else:
    # Fallback to SQLite
    db_url = "sqlite+aiosqlite:///./sql_app.db"
    print(f"Using SQLite database URL: {db_url}")

config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
