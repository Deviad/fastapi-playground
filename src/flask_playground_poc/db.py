from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
# Create the declarative base
Base = declarative_base()

# Database URL - this should match your alembic.ini configuration
DATABASE_URL = "postgresql+asyncpg://dev-user:password@localhost:5432/dev_db"

# Create async engine
engine = create_async_engine(
            DATABASE_URL,
            poolclass=pool.NullPool,
            connect_args={"server_settings": {"search_path": "test_app"}},
        )

# Create async session factory
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """Dependency to get database session with automatic rollback on exceptions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            # Automatic rollback on any exception during the request
            await session.rollback()
            raise  # Re-raise the original exception to preserve error context
        finally:
            await session.close()
