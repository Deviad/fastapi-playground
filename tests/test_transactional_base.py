"""
Base test functionality for @Transactional decorator tests.
Shared fixtures, utilities, and common test patterns.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from fastapi_playground_poc.transactional import (
    Transactional, Propagation, IsolationLevel,
    TransactionRequiredError, TransactionNotAllowedError,
    get_current_session, is_transaction_active, mark_rollback_only
)


class CustomException(Exception):
    """Custom exception for testing rollback rules"""
    pass


class NonRollbackException(Exception):
    """Exception that should not trigger rollback"""
    pass


async def async_generator_from_session(session):
    """Helper to create async generator from session for mocking get_db()"""
    try:
        yield session
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


def mock_get_db_factory(session):
    """Factory function that returns a fresh generator each time"""
    def mock_get_db():
        return async_generator_from_session(session)
    return mock_get_db


def assert_sql_command_executed(mock_session, expected_sql):
    """
    Helper to verify SQL commands were executed by checking their text content.
    
    This function solves the SQLAlchemy TextClause comparison issue where
    mock_session.execute.assert_any_call(text("SQL")) fails because each
    text() call creates a new object with different memory addresses.
    
    Usage Examples:
    
    # Instead of this (fails due to object comparison):
    # mock_session.execute.assert_any_call(text("SET TRANSACTION READ ONLY"))
    
    # Use this helper:
    assert_sql_command_executed(mock_session, "SET TRANSACTION READ ONLY")
    
    # Alternative standard unittest.mock approach:
    # assert mock_session.execute.called
    # call_arg = mock_session.execute.call_args[0][0]
    # assert str(call_arg.text) == "SET TRANSACTION READ ONLY"
    
    # For multiple commands:
    # call_args_list = mock_session.execute.call_args_list
    # executed_commands = [str(call[0][0].text) for call in call_args_list]
    # assert "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE" in executed_commands
    # assert "SET TRANSACTION READ ONLY" in executed_commands
    
    Args:
        mock_session: AsyncMock session with execute.call_args_list
        expected_sql: SQL command text to verify was executed
    
    Raises:
        AssertionError: If expected SQL command was not found in executed commands
    """
    executed_commands = []
    for call in mock_session.execute.call_args_list:
        if call[0]:  # Check if there are positional arguments
            command = call[0][0]
            if hasattr(command, 'text'):
                executed_commands.append(str(command.text))
            else:
                executed_commands.append(str(command))
    
    assert expected_sql in executed_commands, f"Expected '{expected_sql}' not found in executed commands: {executed_commands}"


# Test data fixtures
@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    from fastapi_playground_poc.schemas import UserCreate
    return UserCreate(name="Test User", address="123 Test St", bio="Test bio")


@pytest.fixture  
def sample_course_data():
    """Sample course data for testing"""
    from fastapi_playground_poc.schemas import CourseCreate
    return CourseCreate(name="Test Course", author_name="Test Author", price=99.99)


class TestTransactionalDecoratorBase:
    """Base test class with common test patterns"""
    
    @pytest.mark.asyncio
    async def test_basic_session_injection(self, mock_session):
        """Test basic session injection into decorated method"""
        
        @Transactional()
        async def test_func(db: AsyncSession):
            assert isinstance(db, AsyncSession)
            return "success"
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            result = await test_func()
            
            assert result == "success"
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_method_session_injection(self, mock_session):
        """Test session injection into class methods"""
        
        class TestService:
            @Transactional()
            async def test_method(self, db: AsyncSession):
                assert isinstance(db, AsyncSession)
                return "method_success"
        
        service = TestService()
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            result = await service.test_method()
            
            assert result == "method_success"
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_exception_rollback(self, mock_session):
        """Test that exceptions trigger rollback"""
        
        @Transactional()
        async def test_func(db: AsyncSession):
            raise ValueError("Test exception")
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            with pytest.raises(ValueError):
                await test_func()
            
            # Rollback should be triggered through generator.athrow()
            mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_custom_rollback_rules(self, mock_session):
        """Test custom rollback exception rules"""
        
        @Transactional(rollback_for=[CustomException], no_rollback_for=[NonRollbackException])
        async def test_func(db: AsyncSession, exception_type):
            if exception_type:
                raise exception_type("Test exception")
            return "success"
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            # Test no exception
            result = await test_func(None)
            assert result == "success"
            mock_session.commit.assert_called()
            
            # Reset mock
            mock_session.reset_mock()
            
            # Test NonRollbackException (should commit)
            with pytest.raises(NonRollbackException):
                await test_func(NonRollbackException)
            mock_session.commit.assert_called_once()
            
            # Reset mock
            mock_session.reset_mock()
            
            # Test CustomException (should rollback)
            with pytest.raises(CustomException):
                await test_func(CustomException)
            mock_session.commit.assert_not_called()


class TestPropagationBase:
    """Base tests for transaction propagation behaviors"""
    
    @pytest.mark.asyncio
    async def test_required_propagation_new_transaction(self, mock_session):
        """Test REQUIRED propagation creates new transaction when none exists"""
        
        @Transactional(propagation=Propagation.REQUIRED)
        async def test_func(db: AsyncSession):
            assert is_transaction_active()
            return "success"
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            assert not is_transaction_active()
            result = await test_func()
            assert result == "success"
            assert not is_transaction_active()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_requires_new_propagation(self, mock_session):
        """Test REQUIRES_NEW always creates new transaction"""
        
        @Transactional(propagation=Propagation.REQUIRES_NEW)
        async def inner_func(db: AsyncSession):
            return "inner_success"
        
        @Transactional()
        async def outer_func(db: AsyncSession):
            result = await inner_func()
            return f"outer_{result}"
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            result = await outer_func()
            assert result == "outer_inner_success"
    
    @pytest.mark.asyncio
    async def test_mandatory_propagation_with_transaction(self, mock_session):
        """Test MANDATORY propagation works when transaction exists"""
        
        @Transactional(propagation=Propagation.MANDATORY)
        async def inner_func(db: AsyncSession):
            assert is_transaction_active()
            return "mandatory_success"
        
        @Transactional()
        async def outer_func(db: AsyncSession):
            return await inner_func()
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            result = await outer_func()
            assert result == "mandatory_success"
    
    @pytest.mark.asyncio
    async def test_mandatory_propagation_without_transaction(self):
        """Test MANDATORY propagation fails when no transaction exists"""
        
        @Transactional(propagation=Propagation.MANDATORY)
        async def test_func(db: AsyncSession):
            return "should_not_reach"
        
        with pytest.raises(TransactionRequiredError):
            await test_func()
    
    @pytest.mark.asyncio
    async def test_never_propagation_without_transaction(self):
        """Test NEVER propagation works when no transaction exists"""
        
        @Transactional(propagation=Propagation.NEVER)
        async def test_func():
            assert not is_transaction_active()
            return "never_success"
        
        result = await test_func()
        assert result == "never_success"
    
    @pytest.mark.asyncio
    async def test_never_propagation_with_transaction(self, mock_session):
        """Test NEVER propagation fails when transaction exists"""
        
        @Transactional(propagation=Propagation.NEVER)
        async def inner_func():
            return "should_not_reach"
        
        @Transactional()
        async def outer_func(db: AsyncSession):
            return await inner_func()
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            with pytest.raises(TransactionNotAllowedError):
                await outer_func()
    
    @pytest.mark.asyncio
    async def test_supports_propagation_with_transaction(self, mock_session):
        """Test SUPPORTS propagation joins existing transaction"""
        
        @Transactional(propagation=Propagation.SUPPORTS)
        async def inner_func(db: AsyncSession):
            assert is_transaction_active()
            return "supports_with_tx"
        
        @Transactional()
        async def outer_func(db: AsyncSession):
            return await inner_func()
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            result = await outer_func()
            assert result == "supports_with_tx"
    
    @pytest.mark.asyncio
    async def test_supports_propagation_without_transaction(self):
        """Test SUPPORTS propagation works without transaction"""
        
        @Transactional(propagation=Propagation.SUPPORTS)
        async def test_func():
            assert not is_transaction_active()
            return "supports_without_tx"
        
        result = await test_func()
        assert result == "supports_without_tx"
    
    @pytest.mark.asyncio
    async def test_not_supported_propagation(self, mock_session):
        """Test NOT_SUPPORTED propagation suspends existing transaction"""
        
        @Transactional(propagation=Propagation.NOT_SUPPORTED)
        async def inner_func():
            assert not is_transaction_active()
            return "not_supported_success"
        
        @Transactional()
        async def outer_func(db: AsyncSession):
            assert is_transaction_active()
            result = await inner_func()
            assert is_transaction_active()  # Transaction should be restored
            return result
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            result = await outer_func()
            assert result == "not_supported_success"


class TestNestedTransactionBase:
    """Base tests for nested transaction behavior"""
    
    @pytest.mark.asyncio
    async def test_nested_transaction_session_injection(self, mock_session):
        """Test that nested transactions correctly inject sessions"""
        
        @Transactional()
        async def inner_service_method(db: AsyncSession):
            assert isinstance(db, AsyncSession)
            return "inner_result"
        
        @Transactional()
        async def outer_service_method(db: AsyncSession):
            assert isinstance(db, AsyncSession)
            result = await inner_service_method()
            return f"outer_{result}"
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            result = await outer_service_method()
            assert result == "outer_inner_result"
    
    @pytest.mark.asyncio
    async def test_nested_transaction_rollback_propagation(self, mock_session):
        """Test that nested transaction failures propagate to parent"""
        
        @Transactional()
        async def failing_inner_method(db: AsyncSession):
            raise ValueError("Inner method failed")
        
        @Transactional()
        async def outer_method(db: AsyncSession):
            await failing_inner_method()
            return "should_not_reach"
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            with pytest.raises(ValueError):
                await outer_method()
            
            # Should not commit due to nested failure
            mock_session.commit.assert_not_called()


class TestContextFunctionsBase:
    """Base tests for transaction context functions"""
    
    @pytest.mark.asyncio
    async def test_get_current_session(self, mock_session):
        """Test getting current session from context"""
        
        @Transactional()
        async def test_func(db: AsyncSession):
            current_session = get_current_session()
            assert current_session is not None
            assert isinstance(current_session, AsyncSession)
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            await test_func()
    
    @pytest.mark.asyncio
    async def test_get_current_session_no_transaction(self):
        """Test getting current session when no transaction active"""
        current_session = get_current_session()
        assert current_session is None
    
    @pytest.mark.asyncio
    async def test_is_transaction_active(self, mock_session):
        """Test checking if transaction is active"""
        
        @Transactional()
        async def test_func(db: AsyncSession):
            assert is_transaction_active()
        
        assert not is_transaction_active()
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            await test_func()
        
        assert not is_transaction_active()
    
    @pytest.mark.asyncio
    async def test_mark_rollback_only(self, mock_session):
        """Test marking transaction for rollback only"""
        
        @Transactional()
        async def test_func(db: AsyncSession):
            mark_rollback_only()
            return "marked_for_rollback"
        
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)
            
            result = await test_func()
            assert result == "marked_for_rollback"
            # Should rollback instead of commit
            mock_session.rollback.assert_called_once()
            mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_mark_rollback_only_no_transaction(self):
        """Test marking rollback when no transaction active"""
        with pytest.raises(RuntimeError):
            mark_rollback_only()


# Example Service Classes for Testing
class UserService:
    """Example service class demonstrating @Transactional usage patterns"""
    
    @Transactional()
    async def create_user_with_info(self, db: AsyncSession, user_data) -> object:
        """Create a user with user info in a transaction"""
        from fastapi_playground_poc.models.User import User
        from fastapi_playground_poc.models.UserInfo import UserInfo
        
        new_user = User(name=user_data.name)
        new_user_info = UserInfo(address=user_data.address, bio=user_data.bio)
        new_user.user_info = new_user_info
        
        db.add(new_user)
        
        # Call another transactional method (nested transaction)
        await self.log_user_creation(db, new_user.name)
        
        return new_user
    
    @Transactional(propagation=Propagation.REQUIRED)
    async def log_user_creation(self, db: AsyncSession, username: str):
        """Log user creation - uses same transaction as parent"""
        # In a real app, this might insert into an audit table
        # For testing, we'll just verify the session is the same
        current_session = get_current_session()
        assert current_session == db, "Session should be the same in nested transaction"
    
    @Transactional(propagation=Propagation.REQUIRES_NEW)
    async def audit_user_creation(self, db: AsyncSession, user_id: int) -> bool:
        """Audit user creation in a separate transaction"""
        from sqlalchemy import select
        from fastapi_playground_poc.models.User import User
        
        # This would run in a completely separate transaction
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return user is not None
    
    @Transactional(read_only=True)
    async def get_user_count(self, db: AsyncSession) -> int:
        """Get user count in read-only transaction"""
        from sqlalchemy import select
        from fastapi_playground_poc.models.User import User
        
        result = await db.execute(select(User))
        users = result.scalars().all()
        return len(users)
    
    @Transactional(
        rollback_for=[ValueError],
        no_rollback_for=[KeyError]
    )
    async def create_user_with_custom_rollback(self, db: AsyncSession, user_data, fail_type: str = None):
        """Create user with custom rollback rules"""
        from fastapi_playground_poc.models.User import User
        
        new_user = User(name=user_data.name)
        db.add(new_user)
        
        if fail_type == "value_error":
            raise ValueError("This should trigger rollback")
        elif fail_type == "key_error":
            raise KeyError("This should NOT trigger rollback")
        
        return new_user
    
    @Transactional()
    async def create_user_with_manual_rollback(self, db: AsyncSession, user_data):
        """Create user and manually mark for rollback"""
        from fastapi_playground_poc.models.User import User
        
        new_user = User(name=user_data.name)
        db.add(new_user)
        
        # Manually mark transaction for rollback
        mark_rollback_only()
        
        return new_user


class CourseService:
    """Example service for course management"""
    
    @Transactional()
    async def create_course_and_enroll_user(self, db: AsyncSession, course_data, user_id: int):
        """Create course and enroll a user in a single transaction"""
        from datetime import datetime
        from fastapi_playground_poc.models.Course import Course
        from fastapi_playground_poc.models.Enrollment import Enrollment
        
        # Create course
        new_course = Course(
            name=course_data.name,
            author_name=course_data.author_name,
            price=course_data.price
        )
        db.add(new_course)
        await db.flush()  # Get the course ID
        
        # Enroll user
        enrollment = Enrollment(
            user_id=user_id,
            course_id=new_course.id,
            enrollment_date=datetime.utcnow()
        )
        db.add(enrollment)
        
        return new_course
    
    @Transactional(propagation=Propagation.MANDATORY)
    async def enroll_user_mandatory(self, db: AsyncSession, user_id: int, course_id: int):
        """This method requires an existing transaction"""
        from datetime import datetime
        from fastapi_playground_poc.models.Enrollment import Enrollment
        
        enrollment = Enrollment(
            user_id=user_id,
            course_id=course_id,
            enrollment_date=datetime.utcnow()
        )
        db.add(enrollment)
    
    @Transactional(propagation=Propagation.NEVER)
    async def get_course_info_no_transaction(self, course_id: int) -> dict:
        """This method must not run in a transaction"""
        # This would typically access cached data or external APIs
        return {"course_id": course_id, "source": "cache"}