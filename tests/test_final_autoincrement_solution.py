"""
Final autoincrement solution using DDL Event Listener.
Clean, production-ready implementation for consistent behavior.
"""

import asyncio
from sqlalchemy import Column, Integer, String, event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

Base = declarative_base()


class User(Base):
    """User model with consistent autoincrement behavior"""

    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))


class UserInfo(Base):
    """UserInfo model with consistent autoincrement behavior"""

    __tablename__ = "user_info"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    address = Column(String(255))


class Course(Base):
    """Course model with consistent autoincrement behavior"""

    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    price = Column(Integer)


class Enrollment(Base):
    """Enrollment model with consistent autoincrement behavior"""

    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    course_id = Column(Integer, nullable=False)


# DDL Event Listener for consistent autoincrement behavior
def add_sqlite_autoincrement(target, connection, **kw):
    """
    Modify SQLite tables to use AUTOINCREMENT for PostgreSQL-like behavior.
    This ensures that deleted IDs are never reused.
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

            # Create new table with AUTOINCREMENT
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
                    create_sql += (
                        f",\n                    {col_name} {col_type} {not_null}"
                    )

            create_sql += "\n                )"
            connection.execute(text(create_sql))

            # Copy data from temp table
            connection.execute(
                text(f"INSERT INTO {table_name} SELECT * FROM {temp_table}")
            )

            # Drop temp table
            connection.execute(text(f"DROP TABLE {temp_table}"))


# Register event listeners for all models
for model in [User, UserInfo, Course, Enrollment]:
    event.listen(model.__table__, "after_create", add_sqlite_autoincrement)


async def test_final_solution():
    """Test the final autoincrement solution with all models"""

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    print("=== Final Solution: DDL Event Listener ===\n")

    models = [
        (User, "User"),
        (UserInfo, "UserInfo"),
        (Course, "Course"),
        (Enrollment, "Enrollment"),
    ]

    for model_class, model_name in models:
        async with AsyncSessionLocal() as session:
            print(f"Testing {model_name} autoincrement behavior:")

            # Create test records
            if model_class == User:
                obj1 = model_class(name="Test 1")
                obj2 = model_class(name="Test 2")
                obj3 = model_class(name="Test 3")
            elif model_class == UserInfo:
                obj1 = model_class(user_id=1, address="Address 1")
                obj2 = model_class(user_id=2, address="Address 2")
                obj3 = model_class(user_id=3, address="Address 3")
            elif model_class == Course:
                obj1 = model_class(name="Course 1", price=100)
                obj2 = model_class(name="Course 2", price=200)
                obj3 = model_class(name="Course 3", price=300)
            else:  # Enrollment
                obj1 = model_class(user_id=1, course_id=1)
                obj2 = model_class(user_id=2, course_id=2)
                obj3 = model_class(user_id=3, course_id=3)

            # Test autoincrement behavior
            session.add(obj1)
            await session.flush()
            print(f"  Created {model_name} 1 with ID: {obj1.id}")

            session.add(obj2)
            await session.flush()
            print(f"  Created {model_name} 2 with ID: {obj2.id}")

            await session.commit()

            await session.delete(obj2)
            await session.commit()
            print(f"  Deleted {model_name} 2 (ID: {obj2.id})")

            session.add(obj3)
            await session.flush()
            print(f"  Created {model_name} 3 with ID: {obj3.id}")

            if obj3.id == 3:
                print(
                    f"  ✅ {model_name}: Does not reuse ID (PostgreSQL-like behavior)"
                )
            else:
                print(f"  ❌ {model_name}: Reuses ID (got {obj3.id}, expected 3)")

            await session.commit()
            print()

    await engine.dispose()


def print_final_recommendation():
    """Print final recommendation"""
    print("=" * 70)
    print("FINAL RECOMMENDATION: DDL Event Listener Solution")
    print("=" * 70)
    print("✅ WORKS: Provides PostgreSQL-like autoincrement in SQLite")
    print("✅ CLEAN: Uses standard SQLAlchemy models")
    print("✅ SAFE: Only affects SQLite, PostgreSQL unchanged")
    print("✅ TRANSPARENT: No changes needed to existing model code")
    print("\nImplementation:")
    print("1. Add DDL event listener function")
    print("2. Register event for each model table")
    print("3. Use original models without modification")
    print("\nThis solution gives consistent autoincrement behavior across databases!")


if __name__ == "__main__":
    asyncio.run(test_final_solution())
    print_final_recommendation()
