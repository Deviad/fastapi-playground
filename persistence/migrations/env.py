from logging.config import fileConfig
import logging
import asyncio
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import your models and Base
from flask_playground_poc.db import Base
from flask_playground_poc.models.User import User  # Import your models

# Add diagnostic logging
logger = logging.getLogger("alembic.env")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

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


def do_run_migrations(connection):
    """Helper function to run migrations with a connection."""
    # Create schema if it doesn't exist
    logger.info("Ensuring test_app schema exists...")
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS test_app"))
    logger.info("Schema test_app ensured")

    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Run migrations in async mode."""
    logger.info("Starting async migrations")

    # Get database URL and handle schema configuration for asyncpg
    db_url = config.get_main_option("sqlalchemy.url")
    logger.info(f"Original Database URL: {db_url}")

    # For asyncpg, we need to handle server_settings differently
    # Remove server_settings from URL and pass as connect_args
    if "server_settings=" in db_url:
        # Extract the base URL without server_settings
        base_url = db_url.split("?")[0]
        logger.info(f"Base Database URL: {base_url}")

        # Create async engine with server_settings as connect_args
        connectable = create_async_engine(
            base_url,
            poolclass=pool.NullPool,
            connect_args={"server_settings": {"search_path": "test_app"}},
        )
    else:
        connectable = create_async_engine(
            db_url,
            poolclass=pool.NullPool,
        )

    logger.info(f"Target metadata: {target_metadata}")
    logger.info(f"Async engine created successfully: {connectable}")

    try:
        async with connectable.connect() as connection:
            logger.info("Async database connection established successfully")

            # Run migrations in sync context within async connection
            await connection.run_sync(do_run_migrations)

    except Exception as e:
        logger.error(f"Error during async database connection: {e}")
        logger.error(f"Error type: {type(e)}")
        raise
    finally:
        # Dispose of the engine
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async support.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    logger.info("Starting run_migrations_online() with async support")

    # Run async migrations
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
