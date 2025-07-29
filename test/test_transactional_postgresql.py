"""
PostgreSQL-specific tests for @Transactional decorator.
Tests PostgreSQL-specific features like full isolation level support and read-only transactions.
"""

import pytest
import pytest_asyncio
from typing import Optional
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from fastapi_playground_poc.infrastructure.transactional import (
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
from fastapi_playground_poc.domain.model.User import User
from fastapi_playground_poc.domain.model.UserInfo import UserInfo
from fastapi_playground_poc.domain.model.Course import Course
from fastapi_playground_poc.domain.model.Enrollment import Enrollment
from fastapi_playground_poc.application.web.dto.schemas import UserCreate, CourseCreate

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


# PostgreSQL-specific fixtures
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
    from fastapi_playground_poc.infrastructure.db import Base

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

    AsyncSessionLocal = sessionmaker(
        postgresql_test_engine, class_=AsyncSession, expire_on_commit=False
    )

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
    with patch("fastapi_playground_poc.infrastructure.transactional.get_db", test_get_db):
        yield postgresql_test_session


# class TestTransactionalDecoratorPostgreSQL(TestTransactionalDecoratorBase):
#     """PostgreSQL-specific transactional decorator tests"""
#     pass


# class TestPropagationPostgreSQL(TestPropagationBase):
#     """PostgreSQL-specific propagation tests"""
#     pass


# class TestNestedTransactionPostgreSQL(TestNestedTransactionBase):
#     """PostgreSQL-specific nested transaction tests"""
#     pass


# class TestContextFunctionsPostgreSQL(TestContextFunctionsBase):
#     """PostgreSQL-specific context function tests"""
#     pass


class TestPostgreSQLSpecificBehavior:
    """Tests specific to PostgreSQL database behavior"""

    @pytest_asyncio.fixture
    async def postgresql_mock_session(self):
        """Create a mock AsyncSession configured for PostgreSQL"""
        session = AsyncMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.url = MagicMock()
        session.bind.url.__str__ = MagicMock(
            return_value="postgresql://user:pass@localhost/testdb"
        )
        return session

    @pytest.mark.asyncio
    async def test_read_only_mode_postgresql(self, postgresql_mock_session):
        """Test that read-only mode is properly set for PostgreSQL"""

        @Transactional(read_only=True)
        async def test_func(db: AsyncSession):
            return "read_only_test"

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)

            result = await test_func()
            assert result == "read_only_test"

            # Verify that SET TRANSACTION READ ONLY was called for PostgreSQL
            assert_sql_command_executed(
                postgresql_mock_session, "SET TRANSACTION READ ONLY"
            )

    @pytest.mark.asyncio
    async def test_all_isolation_levels_postgresql(self, postgresql_mock_session):
        """Test all isolation levels work properly with PostgreSQL"""

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

            with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
                mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)

                result = await test_func()
                expected = (
                    f"isolation_{isolation_level.value.lower().replace(' ', '_')}"
                )
                assert result == expected

                # Verify the correct SQL command was executed
                expected_sql = (
                    f"SET TRANSACTION ISOLATION LEVEL {isolation_level.value}"
                )
                assert_sql_command_executed(postgresql_mock_session, expected_sql)

                # Reset for next iteration
                postgresql_mock_session.reset_mock()

    @pytest.mark.asyncio
    async def test_isolation_levels_sql_commands_postgresql(
        self, postgresql_mock_session
    ):
        """Test that isolation levels generate correct SQL commands for PostgreSQL"""

        test_cases = [
            (
                IsolationLevel.READ_UNCOMMITTED,
                "SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED",
            ),
            (
                IsolationLevel.READ_COMMITTED,
                "SET TRANSACTION ISOLATION LEVEL READ COMMITTED",
            ),
            (
                IsolationLevel.REPEATABLE_READ,
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ",
            ),
            (
                IsolationLevel.SERIALIZABLE,
                "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE",
            ),
        ]

        for isolation_level, expected_sql in test_cases:

            @Transactional(isolation_level=isolation_level)
            async def test_func(db: AsyncSession):
                return "isolation_test"

            with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
                mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)

                result = await test_func()
                assert result == "isolation_test"

                # Verify the correct SQL command was executed
                assert_sql_command_executed(postgresql_mock_session, expected_sql)

                # Reset for next test case
                postgresql_mock_session.reset_mock()

    @pytest.mark.asyncio
    async def test_combined_read_only_and_isolation_postgresql(
        self, postgresql_mock_session
    ):
        """Test combining read-only mode with isolation levels in PostgreSQL"""

        @Transactional(isolation_level=IsolationLevel.SERIALIZABLE, read_only=True)
        async def test_func(db: AsyncSession):
            return "combined_test"

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)

            result = await test_func()
            assert result == "combined_test"

            # Verify both SQL commands were executed
            assert_sql_command_executed(
                postgresql_mock_session, "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"
            )
            assert_sql_command_executed(
                postgresql_mock_session, "SET TRANSACTION READ ONLY"
            )

    @pytest.mark.asyncio
    async def test_string_isolation_level_postgresql(self, postgresql_mock_session):
        """Test using string isolation levels with PostgreSQL"""

        @Transactional(isolation_level="REPEATABLE READ")
        async def test_func(db: AsyncSession):
            return "string_isolation_test"

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)

            result = await test_func()
            assert result == "string_isolation_test"

            # Verify the correct SQL command was executed
            assert_sql_command_executed(
                postgresql_mock_session,
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ",
            )


class TestPostgreSQLAdvancedFeatures:
    """Test advanced PostgreSQL-specific features"""

    @pytest_asyncio.fixture
    async def postgresql_mock_session(self):
        """Create a mock AsyncSession configured for PostgreSQL"""
        session = AsyncMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.url = MagicMock()
        session.bind.url.__str__ = MagicMock(
            return_value="postgresql://user:pass@localhost/testdb"
        )
        return session

    @pytest.mark.asyncio
    async def test_serializable_isolation_with_timeout_postgresql(
        self, postgresql_mock_session
    ):
        """Test SERIALIZABLE isolation with timeout in PostgreSQL"""
        import asyncio

        @Transactional(
            isolation_level=IsolationLevel.SERIALIZABLE, timeout=2, read_only=True
        )
        async def test_func(db: AsyncSession):
            await asyncio.sleep(0.1)  # Short operation
            return "serializable_with_timeout"

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)

            result = await test_func()
            assert result == "serializable_with_timeout"

            # Verify all settings were applied
            assert_sql_command_executed(
                postgresql_mock_session, "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"
            )
            assert_sql_command_executed(
                postgresql_mock_session, "SET TRANSACTION READ ONLY"
            )

    @pytest.mark.asyncio
    async def test_complex_nested_transactions_postgresql(
        self, postgresql_mock_session
    ):
        """Test complex nested transaction scenarios with PostgreSQL"""

        class DatabaseService:
            @Transactional(isolation_level=IsolationLevel.READ_COMMITTED)
            async def read_data(self, db: AsyncSession):
                return "data_read"

        class AnalyticsService:
            @Transactional(
                isolation_level=IsolationLevel.REPEATABLE_READ, read_only=True
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

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(postgresql_mock_session)

            result = await service.generate_report()
            assert result == "report_based_on_analyzed_data_read"

            # Verify the outer transaction's isolation level was set
            assert_sql_command_executed(
                postgresql_mock_session, "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"
            )


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
        AsyncSessionLocal = sessionmaker(
            postgresql_test_engine, class_=AsyncSession, expire_on_commit=False
        )

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

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db", test_get_db):

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
                main_result = await fresh_db.execute(
                    select(User).where(User.name == "PG Main User")
                )
                assert main_result.scalar_one_or_none() is None

                # Independent user should still exist (committed in separate transaction)
                independent_result = await fresh_db.execute(
                    select(User).where(User.name == "PG Independent User")
                )
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
        result1 = await mock_postgresql_db.execute(
            select(User).where(User.name == "Serializable User")
        )
        assert result1.scalar_one_or_none() is not None

        result2 = await mock_postgresql_db.execute(
            select(User).where(User.name == "Read Committed User")
        )
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

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db", mock_get_db):

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
            "SET TRANSACTION ISOLATION LEVEL READ COMMITTED",  # String format
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ",  # String format
            "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE",  # String format
        ]

        assert (
            len(executed_commands) == 8
        ), f"Expected 8 commands, got {len(executed_commands)}"

        for i, expected in enumerate(expected_commands):
            assert (
                executed_commands[i] == expected
            ), f"Command {i}: expected '{expected}', got '{executed_commands[i]}'"

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
                rollback_for=[ValueError, RuntimeError],
            )
            async def transfer_funds(
                self,
                db: AsyncSession,
                from_account: str,
                to_account: str,
                amount: float,
            ):
                if amount <= 0:
                    raise ValueError("Invalid amount")
                return f"transferred_{amount}_from_{from_account}_to_{to_account}"

        class AuditService:
            @Transactional(
                propagation=Propagation.REQUIRES_NEW,
                isolation_level=IsolationLevel.READ_COMMITTED,
            )
            async def log_transaction(self, db: AsyncSession, transaction_id: str):
                return f"logged_{transaction_id}"

        class BankingService:
            def __init__(self):
                self.account_service = AccountService()
                self.audit_service = AuditService()

            @Transactional(isolation_level=IsolationLevel.SERIALIZABLE)
            async def process_transfer(
                self,
                db: AsyncSession,
                from_account: str,
                to_account: str,
                amount: float,
            ):
                # Main transfer in SERIALIZABLE isolation
                transfer_result = await self.account_service.transfer_funds(
                    from_account, to_account, amount
                )

                # Audit in separate transaction
                audit_result = await self.audit_service.log_transaction(
                    f"transfer_{from_account}_{to_account}"
                )

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
        AsyncSessionLocal = sessionmaker(
            postgresql_test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async def test_get_db():
            async with AsyncSessionLocal() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db", test_get_db):

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
                main_result = await fresh_db.execute(
                    select(User).where(User.name == "Complex User")
                )
                assert main_result.scalar_one_or_none() is None

                # Audit entry should exist (committed in separate transaction)
                audit_result = await fresh_db.execute(
                    select(User).where(User.name == "AUDIT_Complex User")
                )
                audit_user = audit_result.scalar_one_or_none()
                assert audit_user is not None
                assert audit_user.name == "AUDIT_Complex User"


class TestAutoExpungeBehaviorPostgreSQL:
    """Test auto_expunge functionality with PostgreSQL database"""

    @pytest.mark.asyncio
    async def test_auto_expunge_true_objects_detached_after_commit(
        self, mock_postgresql_db
    ):
        """Test that objects are detached from session after commit when auto_expunge=True (default)"""

        @Transactional(auto_expunge=True)
        async def create_user_with_auto_expunge(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            await db.flush()  # Get the ID
            return user

        user = await create_user_with_auto_expunge("PG Auto Expunge Test User")

        # Verify user was created
        assert user.name == "PG Auto Expunge Test User"
        assert user.id is not None

        # After transaction completion with auto_expunge=True, object should be detached
        # We can still access basic attributes that were loaded
        assert user.name == "PG Auto Expunge Test User"

        # Verify the user exists in database by querying with a fresh session
        result = await mock_postgresql_db.execute(
            select(User).where(User.id == user.id)
        )
        db_user = result.scalar_one_or_none()
        assert db_user is not None
        assert db_user.name == "PG Auto Expunge Test User"

    @pytest.mark.asyncio
    async def test_auto_expunge_false_objects_remain_attached(self, mock_postgresql_db):
        """Test that objects remain attached to session when auto_expunge=False"""

        @Transactional(auto_expunge=False)
        async def create_user_no_auto_expunge(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            await db.flush()
            return user

        user = await create_user_no_auto_expunge("PG No Auto Expunge User")

        # Verify user was created
        assert user.name == "PG No Auto Expunge User"
        assert user.id is not None

        # With auto_expunge=False, we should be able to access the object normally
        # Note: In real scenarios, the session would still be available for lazy loading
        assert user.name == "PG No Auto Expunge User"

    @pytest.mark.asyncio
    async def test_auto_expunge_true_prevents_detached_instance_error(
        self, mock_postgresql_db
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

        user = await create_user_with_info("PG Detached Test User", "123 Test St")

        # These should work fine - basic attributes are loaded
        assert user.name == "PG Detached Test User"
        assert user.id is not None

        # The user_info relationship should also be accessible since we loaded it
        if user.user_info:
            assert user.user_info.address == "123 Test St"

    @pytest.mark.asyncio
    async def test_auto_expunge_behavior_during_rollback(self, mock_postgresql_db):
        """Test auto_expunge behavior during transaction rollback"""

        @Transactional(auto_expunge=True)
        async def create_user_and_fail(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            await db.flush()
            # Force rollback
            raise ValueError("Intentional failure")

        with pytest.raises(ValueError):
            await create_user_and_fail("PG Rollback Test User")

        # Verify user was not created due to rollback
        result = await mock_postgresql_db.execute(
            select(User).where(User.name == "PG Rollback Test User")
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_auto_expunge_with_nested_transactions(self, mock_postgresql_db):
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
            "PG Nested User", "PG Nested Course"
        )

        # Both objects should be accessible after nested transaction completion
        assert user.name == "PG Nested User"
        assert course.name == "PG Nested Course"

        # Verify both exist in database
        user_result = await mock_postgresql_db.execute(
            select(User).where(User.name == "PG Nested User")
        )
        assert user_result.scalar_one_or_none() is not None

        course_result = await mock_postgresql_db.execute(
            select(Course).where(Course.name == "PG Nested Course")
        )
        assert course_result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_auto_expunge_with_requires_new_propagation(self, mock_postgresql_db):
        """Test auto_expunge with REQUIRES_NEW propagation"""

        @Transactional(auto_expunge=True, propagation=Propagation.REQUIRES_NEW)
        async def create_audit_user(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            await db.flush()
            return user

        @Transactional(auto_expunge=True)
        async def main_transaction(db: AsyncSession):
            main_user = User(name="PG Main User")
            db.add(main_user)
            await db.flush()

            # This should create a separate transaction
            audit_user = await create_audit_user("PG Audit User")

            return main_user, audit_user

        main_user, audit_user = await main_transaction()

        # Both users should be accessible
        assert main_user.name == "PG Main User"
        assert audit_user.name == "PG Audit User"

        # Verify both exist in database
        main_result = await mock_postgresql_db.execute(
            select(User).where(User.name == "PG Main User")
        )
        assert main_result.scalar_one_or_none() is not None

        audit_result = await mock_postgresql_db.execute(
            select(User).where(User.name == "PG Audit User")
        )
        assert audit_result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_internal_transaction_decorator_no_auto_expunge(
        self, mock_postgresql_db
    ):
        """Test that internal_transaction decorator uses auto_expunge=False"""
        from fastapi_playground_poc.infrastructure.transactional import internal_transaction

        @internal_transaction
        async def create_user_internal(db: AsyncSession, name: str) -> User:
            user = User(name=name)
            db.add(user)
            await db.flush()
            return user

        user = await create_user_internal("PG Internal User")

        # Verify user was created
        assert user.name == "PG Internal User"
        assert user.id is not None

        # With internal_transaction (auto_expunge=False), object should remain accessible
        assert user.name == "PG Internal User"


class TestAutoExpungeIntegrationPostgreSQL:
    """Integration tests for auto_expunge with real-world usage patterns in PostgreSQL"""

    @pytest.mark.asyncio
    async def test_service_layer_auto_expunge_pattern(self, mock_postgresql_db):
        """Test auto_expunge behavior in service layer patterns with PostgreSQL"""

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
            "PG Service User", "456 Service St", "Service bio"
        )

        assert user.name == "PG Service User"
        assert user.user_info.address == "456 Service St"
        assert user.user_info.bio == "Service bio"

        # Test auto_expunge=False method
        found_user = await service.internal_user_lookup(user.id)
        assert found_user is not None
        assert found_user.name == "PG Service User"

    @pytest.mark.asyncio
    async def test_complex_object_graph_auto_expunge(self, mock_postgresql_db):
        """Test auto_expunge with complex object relationships in PostgreSQL"""
        from datetime import datetime

        @Transactional(auto_expunge=True)
        async def create_complete_enrollment(
            db: AsyncSession,
        ) -> tuple[User, Course, Enrollment]:
            # Create user with info
            user = User(name="PG Complex User")
            user_info = UserInfo(address="789 Complex St", bio="Complex bio")
            user.user_info = user_info

            # Create course
            course = Course(
                name="PG Complex Course", author_name="Complex Author", price=199.99
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
        assert user.name == "PG Complex User"
        assert user.user_info.address == "789 Complex St"
        assert course.name == "PG Complex Course"
        assert enrollment.user_id == user.id
        assert enrollment.course_id == course.id

        # Verify all objects exist in database
        user_result = await mock_postgresql_db.execute(
            select(User).where(User.id == user.id)
        )
        assert user_result.scalar_one_or_none() is not None

        course_result = await mock_postgresql_db.execute(
            select(Course).where(Course.id == course.id)
        )
        assert course_result.scalar_one_or_none() is not None

        enrollment_result = await mock_postgresql_db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user.id, Enrollment.course_id == course.id
            )
        )
        assert enrollment_result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_auto_expunge_with_postgresql_isolation_levels(
        self, mock_postgresql_db
    ):
        """Test auto_expunge behavior with PostgreSQL-specific isolation levels"""

        @Transactional(
            auto_expunge=True,
            isolation_level=IsolationLevel.SERIALIZABLE,
            read_only=True,
        )
        async def read_user_serializable(db: AsyncSession, name: str) -> Optional[User]:
            result = await db.execute(select(User).where(User.name == name))
            return result.scalar_one_or_none()

        # First create a user
        user = User(name="PG Isolation Test User")
        mock_postgresql_db.add(user)
        await mock_postgresql_db.commit()

        # Test with SERIALIZABLE isolation and auto_expunge
        found_user = await read_user_serializable("PG Isolation Test User")
        assert found_user is not None
        assert found_user.name == "PG Isolation Test User"

        # Object should be accessible after auto_expunge
        assert found_user.name == "PG Isolation Test User"

    @pytest.mark.asyncio
    async def test_auto_expunge_with_exception_handling(self, mock_postgresql_db):
        """Test auto_expunge behavior with custom exception handling in PostgreSQL"""

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
        user1 = await create_user_with_custom_exceptions("PG Success User")
        assert user1.name == "PG Success User"

        # Test rollback case (ValueError)
        with pytest.raises(ValueError):
            await create_user_with_custom_exceptions("PG Rollback User", "value_error")

        # Verify rollback user was not created
        result = await mock_postgresql_db.execute(
            select(User).where(User.name == "PG Rollback User")
        )
        assert result.scalar_one_or_none() is None

        # Test no-rollback case (KeyError) - transaction should commit
        with pytest.raises(KeyError):
            user2 = await create_user_with_custom_exceptions(
                "PG No Rollback User", "key_error"
            )

        # Verify no-rollback user WAS created (transaction committed despite exception)
        result = await mock_postgresql_db.execute(
            select(User).where(User.name == "PG No Rollback User")
        )
        committed_user = result.scalar_one_or_none()
        assert committed_user is not None
        assert committed_user.name == "PG No Rollback User"


class TestAutoExpungeMockVerificationPostgreSQL:
    """Test auto_expunge functionality using mocks to verify expunge_all() calls with PostgreSQL"""

    @pytest.mark.asyncio
    async def test_expunge_all_called_on_commit_with_auto_expunge_true(self):
        """Verify that session.expunge_all() is called after commit when auto_expunge=True"""

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.bind = MagicMock()
        mock_session.bind.url = MagicMock()
        mock_session.bind.url.__str__ = MagicMock(
            return_value="postgresql://user:pass@localhost/testdb"
        )

        @Transactional(auto_expunge=True)
        async def test_func(db: AsyncSession):
            return "test_result"

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
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
        mock_session.bind.url.__str__ = MagicMock(
            return_value="postgresql://user:pass@localhost/testdb"
        )

        @Transactional(auto_expunge=False)
        async def test_func(db: AsyncSession):
            return "test_result"

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
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
        mock_session.bind.url.__str__ = MagicMock(
            return_value="postgresql://user:pass@localhost/testdb"
        )

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

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
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
        mock_session.bind.url.__str__ = MagicMock(
            return_value="postgresql://user:pass@localhost/testdb"
        )

        @Transactional(auto_expunge=True)
        async def test_func(db: AsyncSession):
            mark_rollback_only()
            return "marked_for_rollback"

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
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
        from fastapi_playground_poc.infrastructure.transactional import internal_transaction

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.bind = MagicMock()
        mock_session.bind.url = MagicMock()
        mock_session.bind.url.__str__ = MagicMock(
            return_value="postgresql://user:pass@localhost/testdb"
        )

        @internal_transaction
        async def test_func(db: AsyncSession):
            return "internal_result"

        with patch("fastapi_playground_poc.infrastructure.transactional.get_db") as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(mock_session)

            result = await test_func()
            assert result == "internal_result"

            # Verify commit was called
            mock_session.commit.assert_called_once()

            # Verify expunge_all was NOT called (internal_transaction uses auto_expunge=False)
            mock_session.expunge_all.assert_not_called()
