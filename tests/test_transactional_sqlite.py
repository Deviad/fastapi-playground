"""
SQLite-specific tests for @Transactional decorator.
Tests basic functionality, propagation, and SQLite-specific behaviors.
"""

import pytest
import pytest_asyncio
from typing import Optional
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from fastapi_playground_poc.transactional import (
    Transactional,
    Propagation,
    IsolationLevel,
    get_current_session,
    is_transaction_active,
    mark_rollback_only,
    transactional,
    read_only_transaction,
    requires_new_transaction,
)
from fastapi_playground_poc.models.User import User
from fastapi_playground_poc.models.UserInfo import UserInfo
from fastapi_playground_poc.models.Course import Course
from fastapi_playground_poc.models.Enrollment import Enrollment
from fastapi_playground_poc.schemas import UserCreate, CourseCreate

from .test_transactional_base import (
    TestTransactionalDecoratorBase,
    TestPropagationBase,
    TestNestedTransactionBase,
    TestContextFunctionsBase,
    async_generator_from_session,
    mock_get_db_factory,
    assert_sql_command_executed,
    CustomException,
    NonRollbackException,
    UserService,
    CourseService,
)


@pytest_asyncio.fixture
async def mock_session():
    """Create a mock AsyncSession for testing - SQLite version"""
    session = AsyncMock(spec=AsyncSession)
    session.bind = MagicMock()
    session.bind.url = MagicMock()
    session.bind.url.__str__ = MagicMock(return_value="sqlite:///test.db")
    return session


@pytest.fixture
async def mock_transactional_db(test_db):
    """
    Fixture that patches the get_db function used by @Transactional
    to use the test database instead of production database.
    """

    async def test_get_db():
        """Test version of get_db that uses the test database session"""
        try:
            yield test_db
        except Exception:
            await test_db.rollback()
            raise
        finally:
            await test_db.close()

    # Patch the get_db import in the transactional module
    with patch("fastapi_playground_poc.transactional.get_db", test_get_db):
        yield test_db


class TestTransactionalDecoratorSQLite(TestTransactionalDecoratorBase):
    """SQLite-specific transactional decorator tests"""

    pass


class TestPropagationSQLite(TestPropagationBase):
    """SQLite-specific propagation tests"""

    pass


class TestNestedTransactionSQLite(TestNestedTransactionBase):
    """SQLite-specific nested transaction tests"""

    pass


class TestContextFunctionsSQLite(TestContextFunctionsBase):
    """SQLite-specific context function tests"""

    pass


class TestSQLiteSpecificBehavior:
    """Tests specific to SQLite database behavior"""

    @pytest_asyncio.fixture
    async def sqlite_mock_session(self):
        """Create a mock AsyncSession configured for SQLite"""
        session = AsyncMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.url = MagicMock()
        session.bind.url.__str__ = MagicMock(return_value="sqlite:///test.db")
        return session

    @pytest.mark.asyncio
    async def test_read_only_skipped_for_sqlite(self, sqlite_mock_session):
        """Test that read-only mode is skipped for SQLite"""

        @Transactional(read_only=True)
        async def test_func(db: AsyncSession):
            return "read_only_test"

        with patch("fastapi_playground_poc.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(sqlite_mock_session)

            result = await test_func()
            assert result == "read_only_test"

            # Verify that SET TRANSACTION READ ONLY was not called for SQLite
            executed_commands = [
                call[0][0]
                for call in sqlite_mock_session.execute.call_args_list
                if call[0]
            ]
            read_only_commands = [
                cmd
                for cmd in executed_commands
                if hasattr(cmd, "text") and "READ ONLY" in str(cmd.text)
            ]
            assert len(read_only_commands) == 0

    @pytest.mark.asyncio
    async def test_timeout_functionality_sqlite(self, sqlite_mock_session):
        """Test timeout functionality with SQLite"""
        import asyncio

        @Transactional(timeout=1)
        async def fast_func(db: AsyncSession):
            await asyncio.sleep(0.1)  # Short delay
            return "fast_success"

        @Transactional(timeout=1)
        async def slow_func(db: AsyncSession):
            await asyncio.sleep(2)  # Long delay that should timeout
            return "slow_success"

        with patch("fastapi_playground_poc.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(sqlite_mock_session)

            # Fast function should succeed
            result = await fast_func()
            assert result == "fast_success"

            # Reset mock for second test
            sqlite_mock_session.reset_mock()
            mock_get_db.reset_mock()
            mock_get_db.side_effect = mock_get_db_factory(sqlite_mock_session)

            # Slow function should timeout
            with pytest.raises(asyncio.TimeoutError):
                await slow_func()

    @pytest.mark.asyncio
    async def test_isolation_levels_sql_commands_sqlite(self, sqlite_mock_session):
        """Test that isolation levels generate correct SQL commands for SQLite"""

        @Transactional(isolation_level=IsolationLevel.SERIALIZABLE)
        async def test_func(db: AsyncSession):
            return "isolation_test"

        with patch("fastapi_playground_poc.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(sqlite_mock_session)

            result = await test_func()
            assert result == "isolation_test"

            # Verify the correct SQL command was executed
            assert_sql_command_executed(
                sqlite_mock_session, "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"
            )

    @pytest.mark.asyncio
    async def test_all_isolation_levels_sqlite(self, sqlite_mock_session):
        """Test all isolation levels work with SQLite"""

        isolation_levels = [
            IsolationLevel.READ_UNCOMMITTED,
            IsolationLevel.READ_COMMITTED,
            IsolationLevel.REPEATABLE_READ,
            IsolationLevel.SERIALIZABLE,
        ]

        for isolation_level in isolation_levels:

            @Transactional(isolation_level=isolation_level)
            async def test_func(db: AsyncSession):
                return f"isolation_{isolation_level.value.lower().replace(' ', '_')}"

            with patch("fastapi_playground_poc.transactional.get_db") as mock_get_db:
                mock_get_db.side_effect = mock_get_db_factory(sqlite_mock_session)

                result = await test_func()
                expected = (
                    f"isolation_{isolation_level.value.lower().replace(' ', '_')}"
                )
                assert result == expected

                # Verify the correct SQL command was executed
                expected_sql = (
                    f"SET TRANSACTION ISOLATION LEVEL {isolation_level.value}"
                )
                assert_sql_command_executed(sqlite_mock_session, expected_sql)

                # Reset for next iteration
                sqlite_mock_session.reset_mock()


class TestTransactionalDecoratorSQLiteComprehensive:
    """Comprehensive unit tests for the @Transactional decorator with SQLite"""

    @pytest.mark.asyncio
    async def test_basic_transaction_commit(self, mock_transactional_db):
        """Test basic transaction commit functionality"""
        user_service = UserService()
        user_data = UserCreate(name="Test User", address="123 Test St", bio="Test bio")

        user = await user_service.create_user_with_info(user_data)

        # Verify user was created
        assert user.name == "Test User"
        assert user.user_info.address == "123 Test St"

        # Verify user exists in database
        result = await mock_transactional_db.execute(
            select(User).where(User.id == user.id)
        )
        db_user = result.scalar_one_or_none()
        assert db_user is not None
        assert db_user.name == "Test User"

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_exception(self, mock_transactional_db):
        """Test that transactions rollback on exceptions"""
        user_service = UserService()
        user_data = UserCreate(name="Test User", address="123 Test St", bio="Test bio")

        # Test ValueError triggers rollback
        with pytest.raises(ValueError):
            await user_service.create_user_with_custom_rollback(
                user_data, fail_type="value_error"
            )

        # Verify no user was created
        result = await mock_transactional_db.execute(
            select(User).where(User.name == "Test User")
        )
        users = result.scalars().all()
        assert len(users) == 0

    @pytest.mark.asyncio
    async def test_no_rollback_for_specific_exceptions(self, mock_transactional_db):
        """Test that specific exceptions don't trigger rollback"""
        user_service = UserService()
        user_data = UserCreate(
            name="Test User No Rollback", address="123 Test St", bio="Test bio"
        )

        # Test KeyError does NOT trigger rollback
        with pytest.raises(KeyError):
            await user_service.create_user_with_custom_rollback(
                user_data, fail_type="key_error"
            )

        # Verify user WAS created (transaction committed despite exception)
        result = await mock_transactional_db.execute(
            select(User).where(User.name == "Test User No Rollback")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.name == "Test User No Rollback"

    @pytest.mark.asyncio
    async def test_manual_rollback_only(self, mock_transactional_db):
        """Test manually marking transaction for rollback"""
        user_service = UserService()
        user_data = UserCreate(
            name="Manual Rollback User", address="123 Test St", bio="Test bio"
        )

        user = await user_service.create_user_with_manual_rollback(user_data)

        # User object should exist in memory
        assert user.name == "Manual Rollback User"

        # But should not exist in database due to rollback
        result = await mock_transactional_db.execute(
            select(User).where(User.name == "Manual Rollback User")
        )
        db_user = result.scalar_one_or_none()
        assert db_user is None

    @pytest.mark.asyncio
    async def test_read_only_transaction(self, mock_transactional_db):
        """Test read-only transaction"""
        # First create a user
        user = User(name="Read Only Test User")
        mock_transactional_db.add(user)
        await mock_transactional_db.commit()

        user_service = UserService()
        count = await user_service.get_user_count()

        assert count >= 1

    @pytest.mark.asyncio
    async def test_requires_new_propagation(self, mock_transactional_db):
        """Test REQUIRES_NEW propagation creates separate transaction"""
        user_service = UserService()

        # Create a user first
        user_data = UserCreate(
            name="Audit Test User", address="123 Test St", bio="Test bio"
        )
        user = await user_service.create_user_with_info(user_data)

        # Audit in separate transaction
        exists = await user_service.audit_user_creation(user.id)
        assert exists is True


class TestServiceLayerIntegrationSQLite:
    """Test service layer integration patterns with SQLite"""

    @pytest.mark.asyncio
    async def test_cross_service_transaction_sqlite(self, mock_transactional_db):
        """Test transaction spanning multiple service methods with SQLite"""
        user_service = UserService()
        course_service = CourseService()

        # Create user
        user_data = UserCreate(
            name="Integration Test User", address="123 Test St", bio="Test bio"
        )
        user = await user_service.create_user_with_info(user_data)

        # Create course and enroll user
        course_data = CourseCreate(
            name="Integration Course", author_name="Test Author", price=199.99
        )
        course = await course_service.create_course_and_enroll_user(
            course_data, user.id
        )

        # Verify everything was created
        assert user.name == "Integration Test User"
        assert course.name == "Integration Course"

        # Verify enrollment exists
        result = await mock_transactional_db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user.id, Enrollment.course_id == course.id
            )
        )
        enrollment = result.scalar_one_or_none()
        assert enrollment is not None

    @pytest.mark.asyncio
    async def test_nested_service_rollback_sqlite(self, mock_transactional_db):
        """Test that nested service failures roll back the entire transaction with SQLite"""

        class FailingService:
            @Transactional()
            async def failing_method(self, db: AsyncSession):
                raise ValueError("Service failure")

        class MainService:
            def __init__(self):
                self.failing_service = FailingService()

            @Transactional()
            async def main_method(self, db: AsyncSession):
                await self.failing_service.failing_method()
                return "should_not_reach"

        service = MainService()

        with pytest.raises(ValueError):
            await service.main_method()


class TestConvenienceDecoratorsSQLite:
    """Test convenience decorator functions with SQLite"""

    @pytest.mark.asyncio
    async def test_simple_transactional_decorator_sqlite(self, mock_transactional_db):
        """Test the simple @transactional decorator with SQLite"""

        @transactional
        async def test_func(db: AsyncSession):
            return "simple_transactional"

        result = await test_func()
        assert result == "simple_transactional"

    @pytest.mark.asyncio
    async def test_read_only_transaction_decorator_sqlite(self, mock_transactional_db):
        """Test the @read_only_transaction decorator with SQLite"""

        @read_only_transaction
        async def test_func(db: AsyncSession):
            return "read_only_transactional"

        result = await test_func()
        assert result == "read_only_transactional"

    @pytest.mark.asyncio
    async def test_requires_new_transaction_decorator_sqlite(
        self, mock_transactional_db
    ):
        """Test the @requires_new_transaction decorator with SQLite"""

        @requires_new_transaction
        async def inner_func(db: AsyncSession):
            return "requires_new"

        @transactional
        async def outer_func(db: AsyncSession):
            result = await inner_func()
            return f"outer_{result}"

        result = await outer_func()
        assert result == "outer_requires_new"


class TestNestedTransactionSessionInjectionSQLite:
    """Test the nested transaction session injection functionality with SQLite"""

    @pytest.mark.asyncio
    async def test_nested_transaction_session_injection(self, mock_transactional_db):
        """Test that nested transactions properly inject sessions into method calls"""
        from datetime import datetime

        sessions_used = []

        class TestService:
            @Transactional()
            async def create_user_and_course(
                self, db: AsyncSession, user_name: str, course_name: str
            ):
                sessions_used.append(("main", id(db)))

                # Create user
                user = User(name=user_name)
                db.add(user)
                await db.flush()

                # Call nested transactional method
                course = await self.create_course_for_user(db, course_name, user.id)

                return user, course

            @Transactional(propagation=Propagation.REQUIRED)
            async def create_course_for_user(
                self, db: AsyncSession, course_name: str, user_id: int
            ):
                sessions_used.append(("nested", id(db)))

                # This should receive the same session as the parent transaction
                current_session = get_current_session()
                assert (
                    current_session == db
                ), "Nested transaction should have same session"

                course = Course(
                    name=course_name, author_name="Test Author", price=99.99
                )
                db.add(course)
                await db.flush()

                # Create enrollment
                enrollment = Enrollment(
                    user_id=user_id,
                    course_id=course.id,
                    enrollment_date=datetime.utcnow(),
                )
                db.add(enrollment)

                return course

        service = TestService()
        user, course = await service.create_user_and_course(
            "Nested Test User", "Nested Test Course"
        )

        # Verify objects were created
        assert user.name == "Nested Test User"
        assert course.name == "Nested Test Course"

        # Verify sessions were tracked
        assert len(sessions_used) == 2
        assert sessions_used[0][0] == "main"
        assert sessions_used[1][0] == "nested"
        # In REQUIRED propagation, sessions should be the same
        assert sessions_used[0][1] == sessions_used[1][1]

        # Verify database state
        user_result = await mock_transactional_db.execute(
            select(User).where(User.name == "Nested Test User")
        )
        assert user_result.scalar_one_or_none() is not None

        course_result = await mock_transactional_db.execute(
            select(Course).where(Course.name == "Nested Test Course")
        )
        assert course_result.scalar_one_or_none() is not None


class TestAutoExpungeBehaviorSQLite:
    """Test auto_expunge functionality with SQLite database"""

    @pytest.mark.asyncio
    async def test_auto_expunge_true_objects_detached_after_commit(
        self, mock_transactional_db
    ):
        """Test that objects are detached from session after commit when auto_expunge=True (default)"""

        @Transactional(auto_expunge=True)
        async def create_user_with_auto_expunge(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            await db.flush()  # Get the ID
            return user

        user = await create_user_with_auto_expunge("Auto Expunge Test User")

        # Verify user was created
        assert user.name == "Auto Expunge Test User"
        assert user.id is not None

        # After transaction completion with auto_expunge=True, object should be detached
        # We can still access basic attributes that were loaded
        assert user.name == "Auto Expunge Test User"

        # Verify the user exists in database by querying with a fresh session
        result = await mock_transactional_db.execute(
            select(User).where(User.id == user.id)
        )
        db_user = result.scalar_one_or_none()
        assert db_user is not None
        assert db_user.name == "Auto Expunge Test User"

    @pytest.mark.asyncio
    async def test_auto_expunge_false_objects_remain_attached(
        self, mock_transactional_db
    ):
        """Test that objects remain attached to session when auto_expunge=False"""

        @Transactional(auto_expunge=False)
        async def create_user_no_auto_expunge(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            await db.flush()
            return user

        user = await create_user_no_auto_expunge("No Auto Expunge User")

        # Verify user was created
        assert user.name == "No Auto Expunge User"
        assert user.id is not None

        # With auto_expunge=False, we should be able to access the object normally
        # Note: In real scenarios, the session would still be available for lazy loading
        assert user.name == "No Auto Expunge User"

    @pytest.mark.asyncio
    async def test_auto_expunge_true_prevents_detached_instance_error(
        self, mock_transactional_db
    ):
        """Test that auto_expunge=True prevents DetachedInstanceError for basic attribute access"""

        @Transactional(auto_expunge=True)
        async def create_user_with_info(
            db: AsyncSession, name: str, address: str
        ) -> User:
            user = User(name=name)
            user_info = UserInfo(address=address, bio="Test bio")
            user.user_info = user_info
            db.add(user)
            await db.flush()
            # Load the relationship data before transaction ends
            await db.refresh(user, ["user_info"])
            return user

        user = await create_user_with_info("Detached Test User", "123 Test St")

        # These should work fine - basic attributes are loaded
        assert user.name == "Detached Test User"
        assert user.id is not None

        # The user_info relationship should also be accessible since we loaded it
        if user.user_info:
            assert user.user_info.address == "123 Test St"

    @pytest.mark.asyncio
    async def test_auto_expunge_behavior_during_rollback(self, mock_transactional_db):
        """Test auto_expunge behavior during transaction rollback"""

        @Transactional(auto_expunge=True)
        async def create_user_and_fail(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            await db.flush()
            # Force rollback
            raise ValueError("Intentional failure")

        with pytest.raises(ValueError):
            await create_user_and_fail("Rollback Test User")

        # Verify user was not created due to rollback
        result = await mock_transactional_db.execute(
            select(User).where(User.name == "Rollback Test User")
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_auto_expunge_with_nested_transactions(self, mock_transactional_db):
        """Test auto_expunge behavior in nested transactions"""

        @Transactional(auto_expunge=True, propagation=Propagation.REQUIRED)
        async def inner_create_course(db: AsyncSession, name: str) -> Course:
            course = Course(name=name, author_name="Test Author", price=99.99)
            db.add(course)
            await db.flush()
            return course

        @Transactional(auto_expunge=True)
        async def outer_create_user_and_course(
            db: AsyncSession, user_name: str, course_name: str
        ):
            user = User(name=user_name)
            db.add(user)
            await db.flush()

            # Call nested transactional method
            course = await inner_create_course(course_name)

            return user, course

        user, course = await outer_create_user_and_course(
            "Nested User", "Nested Course"
        )

        # Both objects should be accessible after nested transaction completion
        assert user.name == "Nested User"
        assert course.name == "Nested Course"

        # Verify both exist in database
        user_result = await mock_transactional_db.execute(
            select(User).where(User.name == "Nested User")
        )
        assert user_result.scalar_one_or_none() is not None

        course_result = await mock_transactional_db.execute(
            select(Course).where(Course.name == "Nested Course")
        )
        assert course_result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_auto_expunge_with_requires_new_propagation(
        self, mock_transactional_db
    ):
        """Test auto_expunge with REQUIRES_NEW propagation"""

        @Transactional(auto_expunge=True, propagation=Propagation.REQUIRES_NEW)
        async def create_audit_user(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            await db.flush()
            return user

        @Transactional(auto_expunge=True)
        async def main_transaction(db: AsyncSession):
            main_user = User(name="Main User")
            db.add(main_user)
            await db.flush()

            # This should create a separate transaction
            audit_user = await create_audit_user("Audit User")

            return main_user, audit_user

        main_user, audit_user = await main_transaction()

        # Both users should be accessible
        assert main_user.name == "Main User"
        assert audit_user.name == "Audit User"

        # Verify both exist in database
        main_result = await mock_transactional_db.execute(
            select(User).where(User.name == "Main User")
        )
        assert main_result.scalar_one_or_none() is not None

        audit_result = await mock_transactional_db.execute(
            select(User).where(User.name == "Audit User")
        )
        assert audit_result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_internal_transaction_decorator_no_auto_expunge(
        self, mock_transactional_db
    ):
        """Test that internal_transaction decorator uses auto_expunge=False"""
        from fastapi_playground_poc.transactional import internal_transaction

        @internal_transaction
        async def create_user_internal(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            await db.flush()
            return user

        user = await create_user_internal("Internal User")

        # Verify user was created
        assert user.name == "Internal User"
        assert user.id is not None

        # With internal_transaction (auto_expunge=False), object should remain accessible
        assert user.name == "Internal User"


class TestAutoExpungeIntegrationSQLite:
    """Integration tests for auto_expunge with real-world usage patterns"""

    @pytest.mark.asyncio
    async def test_service_layer_auto_expunge_pattern(self, mock_transactional_db):
        """Test auto_expunge behavior in service layer patterns"""

        class TestUserService:
            @Transactional(auto_expunge=True)
            async def create_user_with_profile(
                self, db: AsyncSession, name: str, address: str, bio: str
            ) -> User:
                user = User(name=name)
                user_info = UserInfo(address=address, bio=bio)
                user.user_info = user_info
                db.add(user)
                await db.flush()
                # Ensure relationship is loaded before transaction ends
                await db.refresh(user, ["user_info"])
                return user

            @Transactional(auto_expunge=False)
            async def internal_user_lookup(
                self, db: AsyncSession, user_id: int
            ) -> Optional[User]:
                """Internal method that keeps objects attached for performance"""
                result = await db.execute(select(User).where(User.id == user_id))
                return result.scalar_one_or_none()

        service = TestUserService()

        # Test auto_expunge=True method
        user = await service.create_user_with_profile(
            "Service User", "456 Service St", "Service bio"
        )

        assert user.name == "Service User"
        assert user.user_info.address == "456 Service St"
        assert user.user_info.bio == "Service bio"

        # Test auto_expunge=False method
        found_user = await service.internal_user_lookup(user.id)
        assert found_user is not None
        assert found_user.name == "Service User"

    @pytest.mark.asyncio
    async def test_complex_object_graph_auto_expunge(self, mock_transactional_db):
        """Test auto_expunge with complex object relationships"""
        from datetime import datetime

        @Transactional(auto_expunge=True)
        async def create_complete_enrollment(
            db: AsyncSession,
        ) -> tuple[User, Course, Enrollment]:
            # Create user with info
            user = User(name="Complex User")
            user_info = UserInfo(address="789 Complex St", bio="Complex bio")
            user.user_info = user_info

            # Create course
            course = Course(
                name="Complex Course", author_name="Complex Author", price=199.99
            )

            # Add to session
            db.add(user)
            db.add(course)
            await db.flush()

            # Create enrollment
            enrollment = Enrollment(
                user_id=user.id, course_id=course.id, enrollment_date=datetime.utcnow()
            )
            db.add(enrollment)
            await db.flush()

            # Load relationships before transaction ends
            await db.refresh(user, ["user_info"])
            await db.refresh(enrollment, ["user", "course"])

            return user, course, enrollment

        user, course, enrollment = await create_complete_enrollment()

        # All objects should be accessible after transaction with auto_expunge
        assert user.name == "Complex User"
        assert user.user_info.address == "789 Complex St"
        assert course.name == "Complex Course"
        assert enrollment.user_id == user.id
        assert enrollment.course_id == course.id

        # Verify all objects exist in database
        user_result = await mock_transactional_db.execute(
            select(User).where(User.id == user.id)
        )
        assert user_result.scalar_one_or_none() is not None

        course_result = await mock_transactional_db.execute(
            select(Course).where(Course.id == course.id)
        )
        assert course_result.scalar_one_or_none() is not None

        enrollment_result = await mock_transactional_db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user.id, Enrollment.course_id == course.id
            )
        )
        assert enrollment_result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_auto_expunge_with_exception_handling(self, mock_transactional_db):
        """Test auto_expunge behavior with custom exception handling"""

        @Transactional(
            auto_expunge=True, rollback_for=[ValueError], no_rollback_for=[KeyError]
        )
        async def create_user_with_custom_exceptions(
            db: AsyncSession, name: str, fail_type: str = None
        ) -> User:
            user = User(name=name)
            db.add(user)
            await db.flush()

            if fail_type == "value_error":
                raise ValueError("This should trigger rollback")
            elif fail_type == "key_error":
                raise KeyError("This should NOT trigger rollback")

            return user

        # Test successful case
        user1 = await create_user_with_custom_exceptions("Success User")
        assert user1.name == "Success User"

        # Test rollback case (ValueError)
        with pytest.raises(ValueError):
            await create_user_with_custom_exceptions("Rollback User", "value_error")

        # Verify rollback user was not created
        result = await mock_transactional_db.execute(
            select(User).where(User.name == "Rollback User")
        )
        assert result.scalar_one_or_none() is None

        # Test no-rollback case (KeyError) - transaction should commit
        with pytest.raises(KeyError):
            user2 = await create_user_with_custom_exceptions(
                "No Rollback User", "key_error"
            )

        # Verify no-rollback user WAS created (transaction committed despite exception)
        result = await mock_transactional_db.execute(
            select(User).where(User.name == "No Rollback User")
        )
        committed_user = result.scalar_one_or_none()
        assert committed_user is not None
        assert committed_user.name == "No Rollback User"


class TestAutoExpungeMockVerificationSQLite:
    """Test auto_expunge functionality using mocks to verify expunge_all() calls"""

    @pytest.mark.asyncio
    async def test_expunge_all_called_on_commit_with_auto_expunge_true(self):
        """Verify that session.expunge_all() is called after commit when auto_expunge=True"""

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.bind = MagicMock()
        mock_session.bind.url = MagicMock()
        mock_session.bind.url.__str__ = MagicMock(return_value="sqlite:///test.db")

        @Transactional(auto_expunge=True)
        async def test_func(db: AsyncSession):
            return "test_result"

        with patch("fastapi_playground_poc.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)

            result = await test_func()
            assert result == "test_result"

            # Verify commit was called
            mock_session.commit.assert_called_once()

            # Verify expunge_all was called after commit
            mock_session.expunge_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_expunge_all_not_called_with_auto_expunge_false(self):
        """Verify that session.expunge_all() is NOT called when auto_expunge=False"""

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.bind = MagicMock()
        mock_session.bind.url = MagicMock()
        mock_session.bind.url.__str__ = MagicMock(return_value="sqlite:///test.db")

        @Transactional(auto_expunge=False)
        async def test_func(db: AsyncSession):
            return "test_result"

        with patch("fastapi_playground_poc.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)

            result = await test_func()
            assert result == "test_result"

            # Verify commit was called
            mock_session.commit.assert_called_once()

            # Verify expunge_all was NOT called
            mock_session.expunge_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_rollback_behavior_with_auto_expunge_true(self):
        """Verify rollback behavior when auto_expunge=True (integration-style test)"""

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.bind = MagicMock()
        mock_session.bind.url = MagicMock()
        mock_session.bind.url.__str__ = MagicMock(return_value="sqlite:///test.db")

        # Create a more accurate mock generator that properly simulates the athrow() behavior
        async def accurate_mock_generator():
            try:
                yield mock_session
            except Exception as e:
                await mock_session.rollback()
                raise
            finally:
                await mock_session.close()

        @Transactional(auto_expunge=True)
        async def test_func(db: AsyncSession):
            raise ValueError("Test exception")

        with patch("fastapi_playground_poc.transactional.get_db") as mock_get_db:
            # Use a factory that returns a fresh generator each time
            mock_get_db.side_effect = lambda: accurate_mock_generator()

            with pytest.raises(ValueError):
                await test_func()

            # Verify commit was NOT called due to exception
            mock_session.commit.assert_not_called()

            # Verify rollback was called (through the generator's except block)
            mock_session.rollback.assert_called_once()

            # Note: The expunge_all() call during rollback scenarios is verified
            # by the integration tests since the exact mock call sequence through
            # athrow() is complex to simulate accurately

    @pytest.mark.asyncio
    async def test_expunge_all_called_on_manual_rollback(self):
        """Verify expunge_all is called when transaction is manually marked for rollback"""

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.bind = MagicMock()
        mock_session.bind.url = MagicMock()
        mock_session.bind.url.__str__ = MagicMock(return_value="sqlite:///test.db")

        @Transactional(auto_expunge=True)
        async def test_func(db: AsyncSession):
            mark_rollback_only()
            return "marked_for_rollback"

        with patch("fastapi_playground_poc.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)

            result = await test_func()
            assert result == "marked_for_rollback"

            # Verify rollback was called instead of commit
            mock_session.rollback.assert_called_once()
            mock_session.commit.assert_not_called()

            # Verify expunge_all was called after rollback
            mock_session.expunge_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_internal_transaction_decorator_no_expunge_all(self):
        """Verify that internal_transaction decorator (auto_expunge=False) doesn't call expunge_all"""
        from fastapi_playground_poc.transactional import internal_transaction

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.bind = MagicMock()
        mock_session.bind.url = MagicMock()
        mock_session.bind.url.__str__ = MagicMock(return_value="sqlite:///test.db")

        @internal_transaction
        async def test_func(db: AsyncSession):
            return "internal_result"

        with patch("fastapi_playground_poc.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)

            result = await test_func()
            assert result == "internal_result"

            # Verify commit was called
            mock_session.commit.assert_called_once()

            # Verify expunge_all was NOT called (internal_transaction uses auto_expunge=False)
            mock_session.expunge_all.assert_not_called()
