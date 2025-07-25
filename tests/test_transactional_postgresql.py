"""
PostgreSQL-specific tests for @Transactional decorator.
Tests PostgreSQL-specific features like full isolation level support and read-only transactions.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from flask_playground_poc.transactional import (
    Transactional, Propagation, IsolationLevel,
    get_current_session, is_transaction_active,
    transactional, read_only_transaction, requires_new_transaction
)
from flask_playground_poc.models.User import User
from flask_playground_poc.models.UserInfo import UserInfo
from flask_playground_poc.models.Course import Course
from flask_playground_poc.models.Enrollment import Enrollment
from flask_playground_poc.schemas import UserCreate, CourseCreate

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
    """Create a mock AsyncSession for testing - PostgreSQL version"""
    session = AsyncMock(spec=AsyncSession)
    session.bind = MagicMock()
    session.bind.url = MagicMock()
    session.bind.url.__str__ = MagicMock(return_value="postgresql://user:pass@localhost/testdb")
    return session


# PostgreSQL-specific fixtures
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


class TestTransactionalDecoratorPostgreSQL(TestTransactionalDecoratorBase):
    """PostgreSQL-specific transactional decorator tests"""
    pass


class TestPropagationPostgreSQL(TestPropagationBase):
    """PostgreSQL-specific propagation tests"""
    pass


class TestNestedTransactionPostgreSQL(TestNestedTransactionBase):
    """PostgreSQL-specific nested transaction tests"""
    pass


class TestContextFunctionsPostgreSQL(TestContextFunctionsBase):
    """PostgreSQL-specific context function tests"""
    pass


class TestPostgreSQLSpecificBehavior:
    """Tests specific to PostgreSQL database behavior"""
    
    @pytest_asyncio.fixture
    async def postgresql_mock_session(self):
        """Create a mock AsyncSession configured for PostgreSQL"""
        session = AsyncMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.url = MagicMock()
        session.bind.url.__str__ = MagicMock(return_value="postgresql://user:pass@localhost/testdb")
        return session
    
    @pytest.mark.asyncio
    async def test_read_only_mode_postgresql(self, postgresql_mock_session):
        """Test that read-only mode is properly set for PostgreSQL"""
        
        @Transactional(read_only=True)
        async def test_func(db: AsyncSession):
            return "read_only_test"
        
        with patch('flask_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)
            
            result = await test_func()
            assert result == "read_only_test"
            
            # Verify that SET TRANSACTION READ ONLY was called for PostgreSQL
            assert_sql_command_executed(postgresql_mock_session, "SET TRANSACTION READ ONLY")
    
    @pytest.mark.asyncio
    async def test_all_isolation_levels_postgresql(self, postgresql_mock_session):
        """Test all isolation levels work properly with PostgreSQL"""
        
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
            
            with patch('flask_playground_poc.transactional.get_db') as mock_get_db:
                mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)
                
                result = await test_func()
                expected = f"isolation_{isolation_level.value.lower().replace(' ', '_')}"
                assert result == expected
                
                # Verify the correct SQL command was executed
                expected_sql = f"SET TRANSACTION ISOLATION LEVEL {isolation_level.value}"
                assert_sql_command_executed(postgresql_mock_session, expected_sql)
                
                # Reset for next iteration
                postgresql_mock_session.reset_mock()
    
    @pytest.mark.asyncio
    async def test_isolation_levels_sql_commands_postgresql(self, postgresql_mock_session):
        """Test that isolation levels generate correct SQL commands for PostgreSQL"""
        
        test_cases = [
            (IsolationLevel.READ_UNCOMMITTED, "SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"),
            (IsolationLevel.READ_COMMITTED, "SET TRANSACTION ISOLATION LEVEL READ COMMITTED"),
            (IsolationLevel.REPEATABLE_READ, "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"),
            (IsolationLevel.SERIALIZABLE, "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"),
        ]
        
        for isolation_level, expected_sql in test_cases:
            @Transactional(isolation_level=isolation_level)
            async def test_func(db: AsyncSession):
                return "isolation_test"
            
            with patch('flask_playground_poc.transactional.get_db') as mock_get_db:
                mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)
                
                result = await test_func()
                assert result == "isolation_test"
                
                # Verify the correct SQL command was executed
                assert_sql_command_executed(postgresql_mock_session, expected_sql)
                
                # Reset for next test case
                postgresql_mock_session.reset_mock()
    
    @pytest.mark.asyncio
    async def test_combined_read_only_and_isolation_postgresql(self, postgresql_mock_session):
        """Test combining read-only mode with isolation levels in PostgreSQL"""
        
        @Transactional(
            isolation_level=IsolationLevel.SERIALIZABLE,
            read_only=True
        )
        async def test_func(db: AsyncSession):
            return "combined_test"
        
        with patch('flask_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)
            
            result = await test_func()
            assert result == "combined_test"
            
            # Verify both SQL commands were executed
            assert_sql_command_executed(postgresql_mock_session, "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            assert_sql_command_executed(postgresql_mock_session, "SET TRANSACTION READ ONLY")
    
    @pytest.mark.asyncio
    async def test_string_isolation_level_postgresql(self, postgresql_mock_session):
        """Test using string isolation levels with PostgreSQL"""
        
        @Transactional(isolation_level="REPEATABLE READ")
        async def test_func(db: AsyncSession):
            return "string_isolation_test"
        
        with patch('flask_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)
            
            result = await test_func()
            assert result == "string_isolation_test"
            
            # Verify the correct SQL command was executed
            assert_sql_command_executed(postgresql_mock_session, "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")


class TestPostgreSQLAdvancedFeatures:
    """Test advanced PostgreSQL-specific features"""
    
    @pytest_asyncio.fixture
    async def postgresql_mock_session(self):
        """Create a mock AsyncSession configured for PostgreSQL"""
        session = AsyncMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.url = MagicMock()
        session.bind.url.__str__ = MagicMock(return_value="postgresql://user:pass@localhost/testdb")
        return session
    
    @pytest.mark.asyncio
    async def test_serializable_isolation_with_timeout_postgresql(self, postgresql_mock_session):
        """Test SERIALIZABLE isolation with timeout in PostgreSQL"""
        import asyncio
        
        @Transactional(
            isolation_level=IsolationLevel.SERIALIZABLE,
            timeout=2,
            read_only=True
        )
        async def test_func(db: AsyncSession):
            await asyncio.sleep(0.1)  # Short operation
            return "serializable_with_timeout"
        
        with patch('flask_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)
            
            result = await test_func()
            assert result == "serializable_with_timeout"
            
            # Verify all settings were applied
            assert_sql_command_executed(postgresql_mock_session, "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            assert_sql_command_executed(postgresql_mock_session, "SET TRANSACTION READ ONLY")
    
    @pytest.mark.asyncio
    async def test_complex_nested_transactions_postgresql(self, postgresql_mock_session):
        """Test complex nested transaction scenarios with PostgreSQL"""
        
        class DatabaseService:
            @Transactional(isolation_level=IsolationLevel.READ_COMMITTED)
            async def read_data(self, db: AsyncSession):
                return "data_read"
        
        class AnalyticsService:
            @Transactional(
                isolation_level=IsolationLevel.REPEATABLE_READ,
                read_only=True
            )
            async def analyze_data(self, db: AsyncSession, data: str):
                return f"analyzed_{data}"
        
        class ReportService:
            def __init__(self):
                self.db_service = DatabaseService()
                self.analytics_service = AnalyticsService()
            
            @Transactional(isolation_level=IsolationLevel.SERIALIZABLE)
            async def generate_report(self, db: AsyncSession):
                # This creates a complex nested transaction scenario
                data = await self.db_service.read_data()
                analysis = await self.analytics_service.analyze_data(data)
                return f"report_based_on_{analysis}"
        
        service = ReportService()
        
        with patch('flask_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)
            
            result = await service.generate_report()
            assert result == "report_based_on_analyzed_data_read"
            
            # Verify the outer transaction's isolation level was set
            assert_sql_command_executed(postgresql_mock_session, "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")


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


class TestServiceLayerIntegrationPostgreSQL:
    """Test service layer integration patterns with PostgreSQL advanced features"""
    
    @pytest.mark.asyncio
    async def test_financial_transaction_pattern_postgresql(self, mock_postgresql_db):
        """Test a financial transaction pattern using PostgreSQL SERIALIZABLE isolation"""
        
        class AccountService:
            @Transactional(
                isolation_level=IsolationLevel.SERIALIZABLE,
                timeout=30,
                rollback_for=[ValueError, RuntimeError]
            )
            async def transfer_funds(self, db: AsyncSession, from_account: str, to_account: str, amount: float):
                if amount <= 0:
                    raise ValueError("Invalid amount")
                return f"transferred_{amount}_from_{from_account}_to_{to_account}"
        
        class AuditService:
            @Transactional(
                propagation=Propagation.REQUIRES_NEW,
                isolation_level=IsolationLevel.READ_COMMITTED
            )
            async def log_transaction(self, db: AsyncSession, transaction_id: str):
                return f"logged_{transaction_id}"
        
        class BankingService:
            def __init__(self):
                self.account_service = AccountService()
                self.audit_service = AuditService()
            
            @Transactional(isolation_level=IsolationLevel.SERIALIZABLE)
            async def process_transfer(self, db: AsyncSession, from_account: str, to_account: str, amount: float):
                # Main transfer in SERIALIZABLE isolation
                transfer_result = await self.account_service.transfer_funds(from_account, to_account, amount)
                
                # Audit in separate transaction
                audit_result = await self.audit_service.log_transaction(f"transfer_{from_account}_{to_account}")
                
                return f"{transfer_result}_and_{audit_result}"
        
        service = BankingService()
        
        result = await service.process_transfer("acc1", "acc2", 100.0)
        expected = "transferred_100.0_from_acc1_to_acc2_and_logged_transfer_acc1_acc2"
        assert result == expected
    
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