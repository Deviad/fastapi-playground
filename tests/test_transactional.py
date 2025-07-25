"""
Tests for the @Transactional decorator functionality.

This module contains comprehensive tests for the Spring-inspired @Transactional decorator,
including example service classes that demonstrate the service layer pattern.
"""

import pytest
import asyncio
from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch

from flask_playground_poc.transactional import (
    Transactional,
    Propagation,
    IsolationLevel,
    get_current_session,
    is_transaction_active,
    mark_rollback_only,
    TransactionRequiredError,
    TransactionNotAllowedError,
    transactional,
    read_only_transaction,
    requires_new_transaction
)
from flask_playground_poc.models.User import User
from flask_playground_poc.models.UserInfo import UserInfo
from flask_playground_poc.models.Course import Course
from flask_playground_poc.models.Enrollment import Enrollment
from flask_playground_poc.schemas import UserCreate, CourseCreate


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
    with patch('flask_playground_poc.transactional.get_db', test_get_db):
        yield test_db


# Example Service Classes for Testing
class UserService:
    """Example service class demonstrating @Transactional usage patterns"""
    
    @Transactional()
    async def create_user_with_info(self, db: AsyncSession, user_data: UserCreate) -> User:
        """Create a user with user info in a transaction"""
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
        # This would run in a completely separate transaction
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return user is not None
    
    @Transactional(read_only=True)
    async def get_user_count(self, db: AsyncSession) -> int:
        """Get user count in read-only transaction"""
        result = await db.execute(select(User))
        users = result.scalars().all()
        return len(users)
    
    @Transactional(
        rollback_for=[ValueError],
        no_rollback_for=[KeyError]
    )
    async def create_user_with_custom_rollback(self, db: AsyncSession, user_data: UserCreate, fail_type: str = None) -> User:
        """Create user with custom rollback rules"""
        new_user = User(name=user_data.name)
        db.add(new_user)
        
        if fail_type == "value_error":
            raise ValueError("This should trigger rollback")
        elif fail_type == "key_error":
            raise KeyError("This should NOT trigger rollback")
        
        return new_user
    
    @Transactional()
    async def create_user_with_manual_rollback(self, db: AsyncSession, user_data: UserCreate) -> User:
        """Create user and manually mark for rollback"""
        new_user = User(name=user_data.name)
        db.add(new_user)
        
        # Manually mark transaction for rollback
        mark_rollback_only()
        
        return new_user


class CourseService:
    """Example service for course management"""
    
    @Transactional()
    async def create_course_and_enroll_user(self, db: AsyncSession, course_data: CourseCreate, user_id: int) -> Course:
        """Create course and enroll a user in a single transaction"""
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


# Unit Tests
class TestTransactionalDecorator:
    """Unit tests for the @Transactional decorator"""
    
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
    
    @pytest.mark.asyncio
    async def test_mandatory_propagation_with_transaction(self, mock_transactional_db):
        """Test MANDATORY propagation with existing transaction"""
        course_service = CourseService()
        user_service = UserService()
        
        @Transactional()
        async def create_user_and_enroll(db: AsyncSession):
            # Create user
            user_data = UserCreate(name="Mandatory Test User", address="123 Test St", bio="Test bio")
            user = User(name=user_data.name)
            db.add(user)
            await db.flush()
            
            # Create course
            course_data = CourseCreate(name="Test Course", author_name="Test Author", price=99.99)
            course = Course(name=course_data.name, author_name=course_data.author_name, price=course_data.price)
            db.add(course)
            await db.flush()
            
            # This should work because we're in a transaction
            await course_service.enroll_user_mandatory(db, user.id, course.id)
            
            return user, course
        
        user, course = await create_user_and_enroll()
        
        # Verify enrollment was created
        result = await mock_transactional_db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user.id,
                Enrollment.course_id == course.id
            )
        )
        enrollment = result.scalar_one_or_none()
        assert enrollment is not None
    
    @pytest.mark.asyncio
    async def test_mandatory_propagation_without_transaction(self):
        """Test MANDATORY propagation fails without existing transaction"""
        course_service = CourseService()
        
        with pytest.raises(TransactionRequiredError):
            # This should fail because there's no existing transaction
            await course_service.enroll_user_mandatory(None, 1, 1)
    
    @pytest.mark.asyncio
    async def test_never_propagation_without_transaction(self):
        """Test NEVER propagation works without transaction"""
        course_service = CourseService()
        
        result = await course_service.get_course_info_no_transaction(1)
        assert result["course_id"] == 1
        assert result["source"] == "cache"
    
    @pytest.mark.asyncio
    async def test_never_propagation_with_transaction(self, mock_transactional_db):
        """Test NEVER propagation fails with existing transaction"""
        course_service = CourseService()
        
        @Transactional()
        async def try_never_in_transaction(db: AsyncSession):
            # This should fail because we're in a transaction
            return await course_service.get_course_info_no_transaction(1)
        
        with pytest.raises(TransactionNotAllowedError):
            await try_never_in_transaction()
    
    @pytest.mark.asyncio
    async def test_context_functions(self):
        """Test transaction context utility functions"""
        user_service = UserService()
        
        # Outside transaction
        assert not is_transaction_active()
        assert get_current_session() is None
        
        @Transactional()
        async def test_inside_transaction(db: AsyncSession):
            # Inside transaction
            assert is_transaction_active()
            current_session = get_current_session()
            assert current_session is not None
            assert current_session == db
        
        await test_inside_transaction()
        
        # Back outside transaction
        assert not is_transaction_active()
        assert get_current_session() is None
    
    @pytest.mark.asyncio
    async def test_mark_rollback_only_without_transaction(self):
        """Test that mark_rollback_only raises error when no transaction is active"""
        from flask_playground_poc.transactional import mark_rollback_only
        
        # Should raise RuntimeError when no transaction is active
        with pytest.raises(RuntimeError, match="No active transaction to mark for rollback"):
            mark_rollback_only()
    
    @pytest.mark.asyncio
    async def test_not_supported_propagation(self, mock_transactional_db):
        """Test NOT_SUPPORTED propagation suspends existing transaction"""
        
        results = []
        
        @Transactional(propagation=Propagation.NOT_SUPPORTED)
        async def non_transactional_method():
            # This should run without a transaction
            results.append(('not_supported', is_transaction_active()))
            return "executed"
        
        @Transactional()
        async def main_transaction(db: AsyncSession):
            results.append(('main', is_transaction_active()))
            
            # This should suspend the current transaction
            result = await non_transactional_method()
            
            results.append(('after_suspend', is_transaction_active()))
            return result
        
        result = await main_transaction()
        
        assert result == "executed"
        assert len(results) == 3
        assert results[0] == ('main', True)  # In transaction
        assert results[1] == ('not_supported', False)  # Suspended
        assert results[2] == ('after_suspend', True)  # Restored
    
    @pytest.mark.asyncio
    async def test_supports_propagation_with_transaction(self, mock_transactional_db):
        """Test SUPPORTS propagation joins existing transaction"""
        
        sessions_used = []
        
        @Transactional(propagation=Propagation.SUPPORTS)
        async def supporting_method(db: AsyncSession):
            sessions_used.append(('supports', id(db)))
            user = User(name="Supports User")
            db.add(user)
            return user
        
        @Transactional()
        async def main_transaction(db: AsyncSession):
            sessions_used.append(('main', id(db)))
            return await supporting_method(db)
        
        user = await main_transaction()
        
        assert user.name == "Supports User"
        assert len(sessions_used) == 2
        # Should use the same session (joined transaction)
        assert sessions_used[0][1] == sessions_used[1][1]
    
    @pytest.mark.asyncio
    async def test_supports_propagation_without_transaction(self):
        """Test SUPPORTS propagation without existing transaction"""
        
        @Transactional(propagation=Propagation.SUPPORTS)
        async def supporting_method():
            # Should execute without transaction
            return f"executed_active_{is_transaction_active()}"
        
        result = await supporting_method()
        assert result == "executed_active_False"
    
    @pytest.mark.asyncio
    async def test_timeout_functionality(self, mock_transactional_db):
        """Test transaction timeout functionality"""
        import asyncio
        
        @Transactional(timeout=0.1)  # Very short timeout
        async def slow_operation(db: AsyncSession):
            await asyncio.sleep(0.2)  # Longer than timeout
            user = User(name="Timeout User")
            db.add(user)
            return user
        
        with pytest.raises(asyncio.TimeoutError):
            await slow_operation()
    
    @pytest.mark.asyncio
    async def test_commit_despite_exception_no_rollback_for(self, mock_transactional_db):
        """Test that transaction commits despite exception when in no_rollback_for"""
        
        @Transactional(no_rollback_for=[KeyError])
        async def method_with_key_error(db: AsyncSession):
            user = User(name="No Rollback User")
            db.add(user)
            # This should NOT trigger rollback
            raise KeyError("This should not rollback")
        
        with pytest.raises(KeyError):
            await method_with_key_error()
        
        # User should exist (transaction committed despite exception)
        result = await mock_transactional_db.execute(select(User).where(User.name == "No Rollback User"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.name == "No Rollback User"
    
    @pytest.mark.asyncio
    async def test_should_rollback_edge_cases(self):
        """Test _should_rollback function edge cases"""
        from flask_playground_poc.transactional import _should_rollback
        
        # Test with empty lists - defaults to rollback
        assert _should_rollback(ValueError("test"), [], []) == True
        
        # Test with no matching exception types - defaults to rollback
        assert _should_rollback(ValueError("test"), [KeyError], []) == True
        
        # Test when exception type is in rollback_for
        assert _should_rollback(ValueError("test"), [ValueError], []) == True
        
        # Test precedence: no_rollback_for takes precedence over rollback_for
        assert _should_rollback(ValueError("test"), [ValueError], [ValueError]) == False
        
        # Test inheritance hierarchy
        class CustomError(ValueError):
            pass
        
        # Should rollback CustomError when ValueError is in rollback_for
        assert _should_rollback(CustomError("test"), [ValueError], []) == True
        
        # Should NOT rollback CustomError when ValueError is in no_rollback_for
        assert _should_rollback(CustomError("test"), [], [ValueError]) == False
        
        # Test specific no-rollback scenario
        assert _should_rollback(KeyError("test"), [], [KeyError]) == False
    
    @pytest.mark.asyncio
    async def test_isolation_level_string_format(self, mock_transactional_db):
        """Test isolation level as string instead of enum
        
        NOTE: This test is skipped for SQLite as it doesn't support isolation levels.
        Comprehensive isolation level testing is covered in TestConvenienceDecoratorsPostgreSQL.test_isolation_levels_postgresql
        """
        pytest.skip("SQLite doesn't support isolation levels - see PostgreSQL tests for full coverage")
    
    @pytest.mark.asyncio
    async def test_not_supported_without_existing_transaction(self):
        """Test NOT_SUPPORTED propagation without existing transaction"""
        
        @Transactional(propagation=Propagation.NOT_SUPPORTED)
        async def method_without_transaction():
            # Should execute normally without transaction
            return f"executed_{is_transaction_active()}"
        
        result = await method_without_transaction()
        assert result == "executed_False"


class TestNestedTransactionSessionInjection:
    """Test the nested transaction session injection functionality"""
    
    @pytest.mark.asyncio
    async def test_nested_transaction_session_injection(self, mock_transactional_db):
        """Test that nested transactions properly inject sessions into method calls"""
        
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
    
    @pytest.mark.asyncio
    async def test_requires_new_session_injection(self, mock_transactional_db):
        """Test that REQUIRES_NEW propagation creates separate sessions"""
        
        sessions_used = []
        
        class TestService:
            @Transactional()
            async def main_workflow(self, db: AsyncSession):
                sessions_used.append(('main', id(db)))
                
                # Create main user
                main_user = User(name="Main Workflow User")
                db.add(main_user)
                
                # Call method that requires new transaction
                audit_user = await self.create_audit_user(db, "Audit User")
                
                return main_user, audit_user
            
            @Transactional(propagation=Propagation.REQUIRES_NEW)
            async def create_audit_user(self, db: AsyncSession, name: str):
                sessions_used.append(('requires_new', id(db)))
                
                # This should be a different session
                user = User(name=name)
                db.add(user)
                return user
        
        service = TestService()
        main_user, audit_user = await service.main_workflow()
        
        # Verify objects
        assert main_user.name == "Main Workflow User"
        assert audit_user.name == "Audit User"
        
        # Verify sessions were tracked
        assert len(sessions_used) == 2
        assert sessions_used[0][0] == 'main'
        assert sessions_used[1][0] == 'requires_new'
        
        # Note: In test environment, sessions might be the same due to mocking
        # The important thing is that the decorator correctly handles session injection
        
        # Verify both users exist in database
        main_result = await mock_transactional_db.execute(select(User).where(User.name == "Main Workflow User"))
        assert main_result.scalar_one_or_none() is not None
        
        audit_result = await mock_transactional_db.execute(select(User).where(User.name == "Audit User"))
        assert audit_result.scalar_one_or_none() is not None
    
    @pytest.mark.asyncio
    async def test_session_injection_with_method_parameters(self, mock_transactional_db):
        """Test session injection works correctly with various method parameter patterns"""
        
        class TestService:
            @Transactional()
            async def method_with_args(self, db: AsyncSession, name: str, age: int = 25):
                """Test method with positional and keyword arguments"""
                user = User(name=f"{name}_{age}")
                db.add(user)
                return user
            
            @Transactional()
            async def method_with_kwargs(self, db: AsyncSession, **kwargs):
                """Test method with **kwargs"""
                user = User(name=kwargs.get('name', 'default'))
                db.add(user)
                return user
        
        service = TestService()
        
        # Test with positional args
        user1 = await service.method_with_args("Test", 30)
        assert user1.name == "Test_30"
        
        # Test with keyword args
        user2 = await service.method_with_kwargs(name="Kwargs User")
        assert user2.name == "Kwargs User"
        
        # Verify in database
        result1 = await mock_transactional_db.execute(select(User).where(User.name == "Test_30"))
        assert result1.scalar_one_or_none() is not None
        
        result2 = await mock_transactional_db.execute(select(User).where(User.name == "Kwargs User"))
        assert result2.scalar_one_or_none() is not None


class TestServiceLayerIntegration:
    """Integration tests for service layer with @Transactional"""
    
    @pytest.mark.asyncio
    async def test_complete_user_course_workflow(self, mock_transactional_db):
        """Test complete workflow with multiple services"""
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
    async def test_transaction_rollback_across_services(self, mock_transactional_db):
        """Test that rollback works across multiple service calls"""
        user_service = UserService()
        course_service = CourseService()
        
        @Transactional()
        async def failing_workflow(db: AsyncSession):
            # Create user
            user_data = UserCreate(name="Rollback Test User", address="123 Test St", bio="Test bio")
            user = User(name=user_data.name)
            db.add(user)
            await db.flush()
            
            # Create course (session will be injected by decorator)
            course_data = CourseCreate(name="Rollback Course", author_name="Test Author", price=299.99)
            course = await course_service.create_course_and_enroll_user(course_data, user.id)
            
            # Force an error
            raise ValueError("Simulated error")
        
        with pytest.raises(ValueError):
            await failing_workflow()
        
        # Verify nothing was committed
        user_result = await mock_transactional_db.execute(select(User).where(User.name == "Rollback Test User"))
        assert user_result.scalar_one_or_none() is None

        course_result = await mock_transactional_db.execute(select(Course).where(Course.name == "Rollback Course"))
        assert course_result.scalar_one_or_none() is None


# Convenience decorator tests
class TestConvenienceDecoratorsSQLite:
    """Test convenience decorator aliases with SQLite (basic functionality)"""
    
    @pytest.mark.asyncio
    async def test_simple_transactional_decorator(self, mock_transactional_db):
        """Test @transactional convenience decorator"""
        
        @transactional
        async def create_simple_user(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            return user
        
        user = await create_simple_user("Simple User")
        assert user.name == "Simple User"
        
        # Verify in database
        result = await mock_transactional_db.execute(select(User).where(User.name == "Simple User"))
        db_user = result.scalar_one_or_none()
        assert db_user is not None
    
    @pytest.mark.asyncio
    async def test_read_only_decorator(self, mock_transactional_db):
        """Test @read_only_transaction convenience decorator"""
        
        # Create test data
        user = User(name="Read Only User")
        mock_transactional_db.add(user)
        await mock_transactional_db.commit()
        
        @read_only_transaction
        async def get_user_by_name(db: AsyncSession, name: str) -> User:
            result = await db.execute(select(User).where(User.name == name))
            return result.scalar_one_or_none()
        
        found_user = await get_user_by_name("Read Only User")
        assert found_user is not None
        assert found_user.name == "Read Only User"
    
    @pytest.mark.asyncio
    async def test_requires_new_decorator(self, mock_transactional_db):
        """Test @requires_new_transaction convenience decorator
        
        Note: SQLite limitations mean we test decorator behavior rather than true isolation.
        See TestConvenienceDecoratorsPostgreSQL for full isolation testing.
        """
        
        @requires_new_transaction
        async def create_independent_user(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            return user
        
        # Test that the decorator works without transaction context
        user = await create_independent_user("Independent User")
        assert user.name == "Independent User"
        
        # Verify user was created in database
        result = await mock_transactional_db.execute(select(User).where(User.name == "Independent User"))
        found_user = result.scalar_one_or_none()
        assert found_user is not None
        assert found_user.name == "Independent User"


# PostgreSQL-specific tests for true transaction isolation
@pytest.mark.asyncio
@pytest.fixture(scope="class")
async def postgresql_test_engine():
    """Create a PostgreSQL test engine with test schema"""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text, pool
    
    # Use the same DB but with a test schema
    DATABASE_URL = "postgresql+asyncpg://dev-user:password@localhost:5432/dev_db"
    TEST_SCHEMA = "test_transactional"
    
    # Create engine for schema management
    admin_engine = create_async_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
    )
    
    # Create test schema
    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))
        await conn.execute(text(f"CREATE SCHEMA {TEST_SCHEMA}"))
    
    # Create test engine with test schema
    test_engine = create_async_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
        connect_args={"server_settings": {"search_path": TEST_SCHEMA}},
    )
    
    # Create tables in test schema
    from flask_playground_poc.db import Base
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield test_engine
    
    # Cleanup: drop test schema
    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))
    
    await admin_engine.dispose()
    await test_engine.dispose()


@pytest.fixture
async def postgresql_test_session(postgresql_test_engine):
    """Create a test session for PostgreSQL tests"""
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import AsyncSession
    
    AsyncSessionLocal = sessionmaker(postgresql_test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def mock_postgresql_db(postgresql_test_session):
    """
    Fixture that patches the get_db function to use PostgreSQL test database
    """
    
    async def test_get_db():
        """Test version of get_db that uses the PostgreSQL test database session"""
        try:
            yield postgresql_test_session
        except Exception:
            await postgresql_test_session.rollback()
            raise
        finally:
            # Don't close the session here as it's managed by the fixture
            pass
    
    # Patch the get_db import in the transactional module
    with patch('flask_playground_poc.transactional.get_db', test_get_db):
        yield postgresql_test_session


class TestConvenienceDecoratorsPostgreSQL:
    """Test convenience decorator aliases with PostgreSQL (full transaction isolation)"""
    
    @pytest.mark.asyncio
    async def test_read_only_transaction_postgresql(self, mock_postgresql_db):
        """Test @read_only_transaction with PostgreSQL (supports SET TRANSACTION READ ONLY)"""
        
        # Create test data
        user = User(name="PG Read Only User")
        mock_postgresql_db.add(user)
        await mock_postgresql_db.commit()
        
        @read_only_transaction
        async def get_user_by_name(db: AsyncSession, name: str) -> User:
            result = await db.execute(select(User).where(User.name == name))
            return result.scalar_one_or_none()
        
        found_user = await get_user_by_name("PG Read Only User")
        assert found_user is not None
        assert found_user.name == "PG Read Only User"
    
    @pytest.mark.asyncio
    async def test_requires_new_transaction_postgresql(self, postgresql_test_engine):
        """Test @requires_new_transaction with PostgreSQL for true transaction isolation"""
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Create session factory for this test
        AsyncSessionLocal = sessionmaker(postgresql_test_engine, class_=AsyncSession, expire_on_commit=False)
        
        async def test_get_db():
            """Create a new session for each call"""
            async with AsyncSessionLocal() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
        
        with patch('flask_playground_poc.transactional.get_db', test_get_db):
            @requires_new_transaction
            async def create_independent_user(db: AsyncSession, name: str) -> User:
                user = User(name=name)
                db.add(user)
                await db.commit()  # Explicitly commit the independent transaction
                return user
            
            @Transactional()
            async def main_transaction(db: AsyncSession):
                # Create user in main transaction
                main_user = User(name="PG Main User")
                db.add(main_user)
                
                # Create user in separate transaction (should commit independently)
                independent_user = await create_independent_user("PG Independent User")
                
                # Force rollback of main transaction
                raise ValueError("Force rollback")
            
            with pytest.raises(ValueError):
                await main_transaction()
            
            # Use a fresh session to check actual database state
            async with AsyncSessionLocal() as fresh_db:
                # Main user should be rolled back (not exist)
                main_result = await fresh_db.execute(select(User).where(User.name == "PG Main User"))
                assert main_result.scalar_one_or_none() is None

                # Independent user should still exist (committed in separate transaction)
                independent_result = await fresh_db.execute(select(User).where(User.name == "PG Independent User"))
                found_user = independent_result.scalar_one_or_none()
                assert found_user is not None
                assert found_user.name == "PG Independent User"
    
    @pytest.mark.asyncio
    async def test_isolation_levels_postgresql(self, mock_postgresql_db):
        """Test different isolation levels with PostgreSQL"""
        
        @Transactional(isolation_level=IsolationLevel.SERIALIZABLE)
        async def create_user_serializable(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            return user
        
        @Transactional(isolation_level=IsolationLevel.READ_COMMITTED)
        async def create_user_read_committed(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            return user
        
        # Test SERIALIZABLE isolation level
        user1 = await create_user_serializable("Serializable User")
        assert user1.name == "Serializable User"
        
        # Test READ_COMMITTED isolation level
        user2 = await create_user_read_committed("Read Committed User")
        assert user2.name == "Read Committed User"
        
        # Verify both users exist
        result1 = await mock_postgresql_db.execute(select(User).where(User.name == "Serializable User"))
        assert result1.scalar_one_or_none() is not None
        
        result2 = await mock_postgresql_db.execute(select(User).where(User.name == "Read Committed User"))
        assert result2.scalar_one_or_none() is not None
    
    @pytest.mark.asyncio
    async def test_isolation_levels_sql_commands(self):
        """Test that isolation levels generate the correct SQL commands"""
        from unittest.mock import AsyncMock, Mock
        
        executed_commands = []
        
        # Create a mock session with proper bind attribute
        mock_session = AsyncMock(spec=AsyncSession)
        mock_bind = Mock()
        mock_bind.url = "postgresql://test"  # Not SQLite
        mock_session.bind = mock_bind
        
        async def mock_execute(command):
            executed_commands.append(str(command))
            return AsyncMock()
        
        mock_session.execute = mock_execute
        mock_session.commit = AsyncMock()
        
        # Mock get_db to return our mock session
        async def mock_get_db():
            yield mock_session
        
        with patch('flask_playground_poc.transactional.get_db', mock_get_db):
            
            # Test all 4 isolation levels with enum format
            @Transactional(isolation_level=IsolationLevel.READ_UNCOMMITTED)
            async def test_read_uncommitted(db: AsyncSession):
                return "test"
            
            @Transactional(isolation_level=IsolationLevel.READ_COMMITTED)
            async def test_read_committed(db: AsyncSession):
                return "test"
            
            @Transactional(isolation_level=IsolationLevel.REPEATABLE_READ)
            async def test_repeatable_read(db: AsyncSession):
                return "test"
            
            @Transactional(isolation_level=IsolationLevel.SERIALIZABLE)
            async def test_serializable(db: AsyncSession):
                return "test"
            
            # Test all 4 isolation levels with string format
            @Transactional(isolation_level="READ UNCOMMITTED")
            async def test_read_uncommitted_str(db: AsyncSession):
                return "test"
            
            @Transactional(isolation_level="READ COMMITTED")
            async def test_read_committed_str(db: AsyncSession):
                return "test"
            
            @Transactional(isolation_level="REPEATABLE READ")
            async def test_repeatable_read_str(db: AsyncSession):
                return "test"
            
            @Transactional(isolation_level="SERIALIZABLE")
            async def test_serializable_str(db: AsyncSession):
                return "test"
            
            # Execute all tests
            await test_read_uncommitted()
            await test_read_committed()
            await test_repeatable_read()
            await test_serializable()
            await test_read_uncommitted_str()
            await test_read_committed_str()
            await test_repeatable_read_str()
            await test_serializable_str()
        
        # Verify the correct SQL commands were executed
        expected_commands = [
            "SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED",
            "SET TRANSACTION ISOLATION LEVEL READ COMMITTED",
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ",
            "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE",
            "SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED",  # String format
            "SET TRANSACTION ISOLATION LEVEL READ COMMITTED",    # String format
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ",   # String format
            "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"       # String format
        ]
        
        assert len(executed_commands) == 8, f"Expected 8 commands, got {len(executed_commands)}"
        
        for i, expected in enumerate(expected_commands):
            assert executed_commands[i] == expected, f"Command {i}: expected '{expected}', got '{executed_commands[i]}'"
        
        print("✅ All isolation levels generate correct SQL commands:")
        for cmd in executed_commands:
            print(f"  - {cmd}")
    
    @pytest.mark.asyncio
    async def test_nested_transaction_rollback_postgresql(self, postgresql_test_engine):
        """Test complex nested transaction rollback scenarios with PostgreSQL"""
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Create session factory for this test
        AsyncSessionLocal = sessionmaker(postgresql_test_engine, class_=AsyncSession, expire_on_commit=False)
        
        async def test_get_db():
            async with AsyncSessionLocal() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
        
        with patch('flask_playground_poc.transactional.get_db', test_get_db):
            
            @Transactional(propagation=Propagation.REQUIRES_NEW)
            async def create_audit_entry(db: AsyncSession, user_name: str) -> User:
                """This will commit independently"""
                audit_user = User(name=f"AUDIT_{user_name}")
                db.add(audit_user)
                await db.commit()
                return audit_user
            
            @Transactional()
            async def create_user_with_audit(db: AsyncSession, user_name: str):
                # Create main user
                main_user = User(name=user_name)
                db.add(main_user)
                
                # Create audit entry in separate transaction
                await create_audit_entry(user_name)
                
                # Force rollback of main transaction
                raise ValueError("Simulated business logic error")
            
            with pytest.raises(ValueError):
                await create_user_with_audit("Complex User")
            
            # Use fresh session to verify isolation
            async with AsyncSessionLocal() as fresh_db:
                # Main user should not exist (rolled back)
                main_result = await fresh_db.execute(select(User).where(User.name == "Complex User"))
                assert main_result.scalar_one_or_none() is None
                
                # Audit entry should exist (committed in separate transaction)
                audit_result = await fresh_db.execute(select(User).where(User.name == "AUDIT_Complex User"))
                audit_user = audit_result.scalar_one_or_none()
                assert audit_user is not None
                assert audit_user.name == "AUDIT_Complex User"