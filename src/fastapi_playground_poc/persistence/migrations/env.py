from logging.config import fileConfig
import logging
import asyncio
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import your models and Base
from fastapi_playground_poc.db import Base
from fastapi_playground_poc.models.User import User  # Import your models

# Add diagnostic logging
logger = logging.getLogger("alembic.env")

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def get_config():
    """Get the alembic configuration when context is available."""
    return context.config


def setup_logging():
    """Setup logging configuration when context is available."""
    config = get_config()
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)

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
    config = get_config()  # Get config when function is called
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

    # Create alembic_version table in test_app schema if it doesn't exist
    # logger.info("Ensuring alembic_version table exists in test_app schema...")
    # connection.execute(
    #     text(
    #         """
    #     CREATE TABLE IF NOT EXISTS test_app.alembic_version (
    #         version_num VARCHAR(32) NOT NULL,
    #         CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
    #     )
    # """
    #     )
    # )
    connection.commit()
    # logger.info("alembic_version table ensured in test_app schema")
    # Verify schema exists
    schema_check = connection.execute(
        text(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'test_app'"
        )
    )
    schema_exists = schema_check.fetchone() is not None
    logger.info(f"Schema test_app exists: {schema_exists}")
    # Add diagnostic logging
    logger.info(f"Target metadata tables: {list(target_metadata.tables.keys())}")
    logger.info(f"Base metadata tables: {list(Base.metadata.tables.keys())}")

    # Log the User model table name
    from fastapi_playground_poc.models.User import User

    logger.info(f"User model tablename: {User.__tablename__}")

    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        logger.info("Starting migration transaction...")
        context.run_migrations()
        logger.info("Migration transaction completed")
        # Explicitly commit the transaction
        context.get_context().execute("COMMIT")


async def run_async_migrations():
    """Run migrations in async mode."""
    logger.info("Starting async migrations")

    # Get database URL and handle schema configuration for asyncpg
    config = get_config()  # Get config when function is called
    db_url = config.get_main_option("sqlalchemy.url")
    logger.info(f"Original Database URL: {db_url}")

    # For asyncpg, we need to handle server_settings differently
    # Remove server_settings from URL and pass as connect_args
    if "server_settings=" in db_url:
        # Extract the base URL without server_settings
        # base_url = db_url.split("?")[0]
        base_url = db_url
        logger.info(f"Base Database URL: {base_url}")

        # Create async engine with server_settings as connect_args
        connectable = create_async_engine(
            base_url,
            poolclass=pool.NullPool,
            connect_args={"server_settings": {"search_path": "test_app"}},
        )
    else:
        base_url = db_url
        connectable = create_async_engine(
            base_url,
            poolclass=pool.NullPool,
            connect_args={"server_settings": {"search_path": "test_app"}},
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
    # Setup logging configuration when we have a valid context
    setup_logging()
    run_migrations_online()
