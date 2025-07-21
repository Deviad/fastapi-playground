"""
Pytest configuration and fixtures for the test suite.

This module provides all the necessary fixtures for testing with
an in-memory SQLite database and FastAPI TestClient.
Uses original models with consistent autoincrement behavior.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from flask_playground_poc.app import app
from flask_playground_poc.db import get_db
from tests.test_config import (
    get_test_db,
    create_test_tables,
    drop_test_tables,
    TestAsyncSessionLocal,
)

# Import original models to ensure they're registered
from flask_playground_poc.models.User import User
from flask_playground_poc.models.UserInfo import UserInfo
from flask_playground_poc.models.Course import Course
from flask_playground_poc.models.Enrollment import Enrollment


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_test_database():
    """
    Session-scoped fixture to set up the test database.
    Creates tables with consistent autoincrement behavior at the start of the test session.
    """
    await create_test_tables()
    yield
    await drop_test_tables()


@pytest.fixture
async def test_db(setup_test_database):
    """
    Function-scoped fixture that provides a clean database session for each test.
    Uses original models with PostgreSQL-like autoincrement behavior.
    """
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # Ensure any pending transactions are rolled back
            await session.rollback()

            # Clean all data from tables for test isolation (order matters for foreign keys)
            await session.execute(text("DELETE FROM enrollments"))
            await session.execute(text("DELETE FROM user_info"))
            await session.execute(text("DELETE FROM courses"))
            await session.execute(text("DELETE FROM users"))
            await session.commit()
            await session.close()


@pytest.fixture
async def test_db_session():
    """
    Alternative fixture that provides a fresh database session.
    Creates and tears down tables for each test (slower but more isolated).
    """
    await create_test_tables()

    session = TestAsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
        await drop_test_tables()


@pytest.fixture
def test_client(test_db: AsyncSession):
    """
    Fixture that provides a FastAPI TestClient with the test database.
    Overrides the get_db dependency to use the test database.
    """

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    # Clean up the dependency override
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_user(test_db: AsyncSession):
    """
    Fixture that creates a sample user with user_info for testing.
    Uses original User model with consistent autoincrement behavior.
    """
    user = User(name="John Doe")
    test_db.add(user)
    await test_db.flush()  # Get the user ID

    user_info = UserInfo(
        user_id=user.id, address="123 Test Street", bio="Sample user for testing"
    )
    test_db.add(user_info)
    await test_db.commit()
    await test_db.refresh(user)
    await test_db.refresh(user_info)
    return user


@pytest.fixture
async def sample_user_with_info(test_db: AsyncSession):
    """
    Fixture that creates a sample user with user info for testing.
    """
    user = User(name="Jane Smith")
    test_db.add(user)
    await test_db.flush()  # Get the user ID

    user_info = UserInfo(
        user_id=user.id, address="456 Oak Ave", bio="Sample user for testing"
    )
    test_db.add(user_info)
    await test_db.commit()
    await test_db.refresh(user)
    await test_db.refresh(user_info)

    return user, user_info


@pytest.fixture
async def sample_course(test_db: AsyncSession):
    """
    Fixture that creates a sample course for testing.
    """
    course = Course(name="Python Programming", author_name="Dr. Python", price=99.99)
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)
    return course


@pytest.fixture
async def sample_enrollment(test_db: AsyncSession, sample_user, sample_course):
    """
    Fixture that creates a sample enrollment for testing.
    Depends on sample_user and sample_course fixtures.
    """
    from datetime import datetime

    enrollment = Enrollment(
        user_id=sample_user.id,
        course_id=sample_course.id,
        enrollment_date=datetime.now(),
    )
    test_db.add(enrollment)
    await test_db.commit()
    await test_db.refresh(enrollment)
    return enrollment


@pytest.fixture
async def sample_data(test_db: AsyncSession):
    """
    Fixture that creates a complete set of sample data for testing.
    Returns a dictionary with all created objects.
    """
    from datetime import datetime

    # Create users
    user1 = User(name="Alice Johnson")
    user2 = User(name="Bob Wilson")
    test_db.add_all([user1, user2])
    await test_db.flush()

    # Create user info
    user1_info = UserInfo(user_id=user1.id, address="123 Main St", bio="Alice's bio")
    user2_info = UserInfo(user_id=user2.id, address="789 Pine St", bio="Bob's bio")
    test_db.add_all([user1_info, user2_info])

    # Create courses
    course1 = Course(name="Python Basics", author_name="Prof. Snake", price=49.99)
    course2 = Course(name="Advanced Python", author_name="Dr. Pythonic", price=99.99)
    test_db.add_all([course1, course2])
    await test_db.flush()

    # Create enrollments
    enrollment1 = Enrollment(
        user_id=user1.id, course_id=course1.id, enrollment_date=datetime.now()
    )
    enrollment2 = Enrollment(
        user_id=user2.id, course_id=course2.id, enrollment_date=datetime.now()
    )
    test_db.add_all([enrollment1, enrollment2])

    await test_db.commit()

    # Refresh all objects
    for obj in [
        user1,
        user2,
        user1_info,
        user2_info,
        course1,
        course2,
        enrollment1,
        enrollment2,
    ]:
        await test_db.refresh(obj)

    return {
        "users": [user1, user2],
        "user_infos": [user1_info, user2_info],
        "courses": [course1, course2],
        "enrollments": [enrollment1, enrollment2],
    }


@pytest.fixture
async def multiple_users(test_db: AsyncSession):
    """
    Fixture that creates multiple users with user_info for testing.
    """
    users = [
        User(name="Alice Johnson"),
        User(name="Bob Wilson"),
        User(name="Charlie Brown"),
    ]

    test_db.add_all(users)
    await test_db.flush()  # Get user IDs

    # Create user_info for each user
    user_infos = [
        UserInfo(user_id=users[0].id, address="123 Alice St", bio="Alice's bio"),
        UserInfo(user_id=users[1].id, address="456 Bob Ave", bio="Bob's bio"),
        UserInfo(user_id=users[2].id, address="789 Charlie Rd", bio="Charlie's bio"),
    ]

    test_db.add_all(user_infos)
    await test_db.commit()

    for user in users:
        await test_db.refresh(user)

    return users


@pytest.fixture
async def multiple_courses(test_db: AsyncSession):
    """
    Fixture that creates multiple courses for testing.
    """
    courses = [
        Course(name="Python Basics", author_name="Prof. Snake", price=49.99),
        Course(name="Advanced Python", author_name="Dr. Pythonic", price=99.99),
        Course(name="Web Development", author_name="Ms. Web", price=79.99),
    ]

    test_db.add_all(courses)
    await test_db.commit()

    for course in courses:
        await test_db.refresh(course)

    return courses
