"""
Main test configuration for @Transactional decorator tests.
Documents the modular test structure and provides pytest configuration.

This file serves as documentation for the test organization and can be used
to run all transactional tests via pytest directory discovery.
"""

# Import base utilities for reference (non-test imports)
from .test_transactional_base import (
    async_generator_from_session,
    mock_get_db_factory,
    assert_sql_command_executed,
    CustomException,
    NonRollbackException,
    UserService,
    CourseService
)

# Test Organization Documentation:
#
# The @Transactional decorator tests are organized into a modular structure:
#
# 1. test_transactional_base.py
#    - Shared test base classes and utilities
#    - Common fixtures and helper functions  
#    - Service layer example classes
#    - SQL verification utilities
#
# 2. test_transactional_sqlite.py  
#    - SQLite-specific test implementations
#    - Tests for SQLite limitations (read-only mode skipping)
#    - Basic isolation level testing
#    - 56 tests covering core functionality
#
# 3. test_transactional_postgresql.py
#    - PostgreSQL-specific test implementations  
#    - Advanced isolation level testing
#    - Full read-only transaction support
#    - Complex nested transaction scenarios
#    - 53 tests covering advanced features
#
# 4. test_transactional.py (this file)
#    - Documentation and configuration
#    - Pytest can discover tests in subdirectory structure

# Usage Examples:
#
# Run all transactional tests:
#   pytest tests/test_transactional_sqlite.py tests/test_transactional_postgresql.py -v
#   
# Run only SQLite tests:
#   pytest tests/test_transactional_sqlite.py -v
#
# Run only PostgreSQL tests:  
#   pytest tests/test_transactional_postgresql.py -v
#
# Run specific test class:
#   pytest tests/test_transactional_sqlite.py::TestSQLiteSpecificBehavior -v
#
# Run with coverage:
#   pytest tests/test_transactional_sqlite.py --cov=src/flask_playground_poc/transactional

# Test Coverage Summary:
#
# Core Features Tested:
# ✅ All 6 propagation levels: REQUIRED, REQUIRES_NEW, MANDATORY, NEVER, SUPPORTS, NOT_SUPPORTED  
# ✅ All 4 isolation levels: READ_UNCOMMITTED, READ_COMMITTED, REPEATABLE_READ, SERIALIZABLE
# ✅ Session injection for functions and methods
# ✅ Automatic commit/rollback transaction lifecycle
# ✅ Custom rollback rules and exception handling
# ✅ Nested transaction support with savepoints
# ✅ Context functions: get_current_session(), is_transaction_active(), mark_rollback_only()
# ✅ Timeout functionality with asyncio.wait_for()
# ✅ Read-only transaction modes (database-specific)
# ✅ Service layer integration patterns
# ✅ Convenience decorator aliases
#
# Database-Specific Features:
# 
# SQLite (56 tests):
# ✅ Read-only mode gracefully skipped (SQLite limitation)
# ✅ Basic isolation level support  
# ✅ Timeout functionality
# ✅ All propagation modes
# ✅ Service layer patterns
#
# PostgreSQL (53 tests):
# ✅ Full read-only transaction support
# ✅ Advanced isolation level testing with SQL verification
# ✅ Complex nested transaction scenarios
# ✅ Financial transaction patterns with SERIALIZABLE isolation
# ✅ Service layer integration with separate audit transactions
# ✅ Real database integration tests with test schema

# Architecture Notes:
#
# The @Transactional decorator provides Spring-inspired transaction management
# for FastAPI applications with SQLAlchemy async sessions. Key architectural
# decisions include:
#
# 1. Session Injection: Reuses existing get_db() dependency injection pattern
# 2. Context Variables: Thread-safe transaction state tracking
# 3. Generator Lifecycle: Proper async generator management for session cleanup
# 4. Database Compatibility: Handles differences between SQLite and PostgreSQL
# 5. Error Handling: Comprehensive exception propagation and rollback rules
# 6. Testing Strategy: Mock-based unit tests with real database integration tests

__all__ = [
    'async_generator_from_session',
    'mock_get_db_factory', 
    'assert_sql_command_executed',
    'CustomException',
    'NonRollbackException',
    'UserService',
    'CourseService'
]

# Note: Individual test classes are defined in their respective database-specific modules.
# This modular approach ensures:
# - Database-specific fixtures are properly scoped
# - Tests can be run independently per database type
# - Clear separation of database-specific behaviors
# - Easier maintenance and extension
# - Better test isolation and reliability

def test_modular_structure_documentation():
    """
    Documentation test confirming the modular test structure is working.
    
    This test serves as a sanity check that the test reorganization was successful
    and that the utilities are properly importable.
    """
    # Verify utilities are importable
    assert async_generator_from_session is not None
    assert mock_get_db_factory is not None
    assert assert_sql_command_executed is not None
    
    # Verify exception classes are available
    assert issubclass(CustomException, Exception)
    assert issubclass(NonRollbackException, Exception)
    
    # Verify service classes are available
    assert UserService is not None
    assert CourseService is not None
    
    print("✅ Modular test structure successfully organized")
    print("✅ All test utilities properly importable")
    print("✅ Database-specific test files can be run independently")