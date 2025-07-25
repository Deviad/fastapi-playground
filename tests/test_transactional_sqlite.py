"""
SQLite-specific tests for @Transactional decorator.
Tests basic functionality, propagation, and SQLite-specific behaviors.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from fastapi_playground_poc.transactional import (
    Transactional, Propagation, IsolationLevel,
    get_current_session, is_transaction_active, mark_rollback_only,
    transactional, read_only_transaction, requires_new_transaction
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
    CourseService
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
    with patch('fastapi_playground_poc.transactional.get_db', test_get_db):
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
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(sqlite_mock_session)
            
            result = await test_func()
            assert result == "read_only_test"
            
            # Verify that SET TRANSACTION READ ONLY was not called for SQLite
            executed_commands = [call[0][0] for call in sqlite_mock_session.execute.call_args_list if call[0]]
            read_only_commands = [cmd for cmd in executed_commands if hasattr(cmd, 'text') and 'READ ONLY' in str(cmd.text)]
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
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
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
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(sqlite_mock_session)
            
            result = await test_func()
            assert result == "isolation_test"
            
            # Verify the correct SQL command was executed
            assert_sql_command_executed(sqlite_mock_session, "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
    
    @pytest.mark.asyncio
    async def test_all_isolation_levels_sqlite(self, sqlite_mock_session):
        """Test all isolation levels work with SQLite"""
        
        isolation_levels = [
            IsolationLevel.READ_UNCOMMITTED,
            IsolationLevel.READ_COMMITTED,
            IsolationLevel.REPEATABLE_READ,
            IsolationLevel.SERIALIZABLE
        ]
        
        for isolation_level in isolation_levels:
            @Transactional(isolation_level=isolation_level)
            async def test_func(db: AsyncSession):
                return f"isolation_{isolation_level.value.lower().replace(' ', '_')}"
            
            with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
                mock_get_db.side_effect = mock_get_db_factory(sqlite_mock_session)
                
                result = await test_func()
                expected = f"isolation_{isolation_level.value.lower().replace(' ', '_')}"
                assert result == expected
                
                # Verify the correct SQL command was executed
                expected_sql = f"SET TRANSACTION ISOLATION LEVEL {isolation_level.value}"
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
        result = await mock_transactional_db.execute(select(User).where(User.id == user.id))
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
            await user_service.create_user_with_custom_rollback(user_data, fail_type="value_error")
        
        # Verify no user was created
        result = await mock_transactional_db.execute(select(User).where(User.name == "Test User"))
        users = result.scalars().all()
        assert len(users) == 0
    
    @pytest.mark.asyncio
    async def test_no_rollback_for_specific_exceptions(self, mock_transactional_db):
        """Test that specific exceptions don't trigger rollback"""
        user_service = UserService()
        user_data = UserCreate(name="Test User No Rollback", address="123 Test St", bio="Test bio")
        
        # Test KeyError does NOT trigger rollback
        with pytest.raises(KeyError):
            await user_service.create_user_with_custom_rollback(user_data, fail_type="key_error")
        
        # Verify user WAS created (transaction committed despite exception)
        result = await mock_transactional_db.execute(select(User).where(User.name == "Test User No Rollback"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.name == "Test User No Rollback"
    
    @pytest.mark.asyncio
    async def test_manual_rollback_only(self, mock_transactional_db):
        """Test manually marking transaction for rollback"""
        user_service = UserService()
        user_data = UserCreate(name="Manual Rollback User", address="123 Test St", bio="Test bio")
        
        user = await user_service.create_user_with_manual_rollback(user_data)
        
        # User object should exist in memory
        assert user.name == "Manual Rollback User"
        
        # But should not exist in database due to rollback
        result = await mock_transactional_db.execute(select(User).where(User.name == "Manual Rollback User"))
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
        user_data = UserCreate(name="Audit Test User", address="123 Test St", bio="Test bio")
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
        user_data = UserCreate(name="Integration Test User", address="123 Test St", bio="Test bio")
        user = await user_service.create_user_with_info(user_data)
        
        # Create course and enroll user
        course_data = CourseCreate(name="Integration Course", author_name="Test Author", price=199.99)
        course = await course_service.create_course_and_enroll_user(course_data, user.id)
        
        # Verify everything was created
        assert user.name == "Integration Test User"
        assert course.name == "Integration Course"
        
        # Verify enrollment exists
        result = await mock_transactional_db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user.id,
                Enrollment.course_id == course.id
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
    async def test_requires_new_transaction_decorator_sqlite(self, mock_transactional_db):
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
            async def create_user_and_course(self, db: AsyncSession, user_name: str, course_name: str):
                sessions_used.append(('main', id(db)))
                
                # Create user
                user = User(name=user_name)
                db.add(user)
                await db.flush()
                
                # Call nested transactional method
                course = await self.create_course_for_user(db, course_name, user.id)
                
                return user, course
            
            @Transactional(propagation=Propagation.REQUIRED)
            async def create_course_for_user(self, db: AsyncSession, course_name: str, user_id: int):
                sessions_used.append(('nested', id(db)))
                
                # This should receive the same session as the parent transaction
                current_session = get_current_session()
                assert current_session == db, "Nested transaction should have same session"
                
                course = Course(name=course_name, author_name="Test Author", price=99.99)
                db.add(course)
                await db.flush()
                
                # Create enrollment
                enrollment = Enrollment(
                    user_id=user_id,
                    course_id=course.id,
                    enrollment_date=datetime.utcnow()
                )
                db.add(enrollment)
                
                return course
        
        service = TestService()
        user, course = await service.create_user_and_course("Nested Test User", "Nested Test Course")
        
        # Verify objects were created
        assert user.name == "Nested Test User"
        assert course.name == "Nested Test Course"
        
        # Verify sessions were tracked
        assert len(sessions_used) == 2
        assert sessions_used[0][0] == 'main'
        assert sessions_used[1][0] == 'nested'
        # In REQUIRED propagation, sessions should be the same
        assert sessions_used[0][1] == sessions_used[1][1]
        
        # Verify database state
        user_result = await mock_transactional_db.execute(select(User).where(User.name == "Nested Test User"))
        assert user_result.scalar_one_or_none() is not None
        
        course_result = await mock_transactional_db.execute(select(Course).where(Course.name == "Nested Test Course"))
        assert course_result.scalar_one_or_none() is not None