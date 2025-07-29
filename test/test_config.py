"""
Test database configuration for in-memory SQLite.

This module provides the database configuration and utilities
specifically for testing with an in-memory SQLite database.
Includes DDL Event Listener for consistent autoincrement behavior.
"""

from sqlalchemy import pool, event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import the original Base from the main application
from fastapi_playground_poc.infrastructure.db import Base

# In-memory SQLite database URL for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create async engine for testing
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=pool.StaticPool,
    connect_args={
        "check_same_thread": False,
    },
    echo=False,  # Set to True for SQL debugging
)

# Create async session factory for testing
TestAsyncSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


# DDL Event Listener for consistent autoincrement behavior
def add_sqlite_autoincrement(target, connection, **kw):
    """
    Modify SQLite tables to use AUTOINCREMENT for PostgreSQL-like behavior.
    This ensures that deleted IDs are never reused, providing consistent
    autoincrement behavior between SQLite (tests) and PostgreSQL (production).
    """
    if connection.dialect.name == "sqlite":
        table_name = target.name

        # Get current table structure
        result = connection.execute(text(f"PRAGMA table_info({table_name})"))
        columns = result.fetchall()

        # Find the primary key column
        pk_column = None
        for col in columns:
            if col[5]:  # col[5] is the pk flag
                pk_column = col
                break

        if pk_column and pk_column[2].upper() == "INTEGER":  # col[2] is the type
            # Rebuild table with AUTOINCREMENT
            temp_table = f"{table_name}_temp"

            # Rename original table
            connection.execute(text(f"ALTER TABLE {table_name} RENAME TO {temp_table}"))

            # Create new table with AUTOINCREMENT and constraints
            if table_name == "enrollments":
                # Special handling for enrollments table with unique constraint
                create_sql = f"""
                    CREATE TABLE {table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        course_id INTEGER NOT NULL,
                        enrollment_date DATETIME NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
                        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE ON UPDATE CASCADE,
                        CONSTRAINT unique_user_course_enrollment UNIQUE (user_id, course_id)
                    )
                """
            elif table_name == "user_info":
                # Special handling for user_info table with unique constraint
                create_sql = f"""
                    CREATE TABLE {table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL UNIQUE,
                        address VARCHAR(255) NOT NULL,
                        bio TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE
                    )
                """
            else:
                # Generic table creation
                create_sql = f"""
                    CREATE TABLE {table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT
                """

                # Add other columns
                for col in columns:
                    if col[1] != "id":  # col[1] is the column name
                        col_name = col[1]
                        col_type = col[2]
                        not_null = "NOT NULL" if col[3] else ""
                        create_sql += f",\n                        {col_name} {col_type} {not_null}"

                create_sql += "\n                    )"

            connection.execute(text(create_sql))

            # Copy data from temp table
            connection.execute(
                text(f"INSERT INTO {table_name} SELECT * FROM {temp_table}")
            )

            # Drop temp table
            connection.execute(text(f"DROP TABLE {temp_table}"))


async def get_test_db():
    """Dependency to get test database session"""
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_test_tables():
    """Create all test tables in the in-memory database using original models"""
    # Import original models to ensure they're registered
    from fastapi_playground_poc.domain.model.User import User
    from fastapi_playground_poc.domain.model.UserInfo import UserInfo
    from fastapi_playground_poc.domain.model.Course import Course
    from fastapi_playground_poc.domain.model.Enrollment import Enrollment

    # Register DDL event listeners for consistent autoincrement behavior
    for model in [User, UserInfo, Course, Enrollment]:
        event.listen(model.__table__, "after_create", add_sqlite_autoincrement)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_test_tables():
    """Drop all test tables from the in-memory database"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
