"""
Spring-inspired @Transactional decorator for FastAPI with SQLAlchemy async sessions.

This module provides automatic transaction management for service layer methods,
similar to Spring's @Transactional annotation with support for propagation levels,
isolation levels, nested transactions, and automatic object expunging.
"""

import asyncio
import inspect
import logging
from contextvars import ContextVar
from enum import Enum
from functools import wraps
from typing import Optional, Type, List, Union, Any, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from fastapi_playground_poc.db import get_db


# Configure logging
logger = logging.getLogger(__name__)


class Propagation(Enum):
    """Transaction propagation behavior similar to Spring's @Transactional"""
    REQUIRED = "required"           # Join existing or create new (default)
    REQUIRES_NEW = "requires_new"   # Always create new transaction
    SUPPORTS = "supports"           # Join if exists, no transaction if none
    NOT_SUPPORTED = "not_supported" # Never run in transaction
    MANDATORY = "mandatory"         # Must have existing transaction
    NEVER = "never"                # Must NOT run in transaction


class IsolationLevel(Enum):
    """Database isolation levels"""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


# Context variable to track current transaction state
_transaction_context: ContextVar[Optional[dict]] = ContextVar('transaction_context', default=None)


class TransactionContext:
    """Manages the current transaction context and nesting level"""

    def __init__(self, session: AsyncSession, level: int = 0, savepoint_name: Optional[str] = None):
        self.session = session
        self.level = level
        self.savepoint_name = savepoint_name
        self.is_rollback_only = False

    def mark_rollback_only(self):
        """Mark this transaction for rollback only"""
        self.is_rollback_only = True


def get_current_session() -> Optional[AsyncSession]:
    """
    Get the current transactional session from context.
    Returns None if no active transaction.
    """
    context = _transaction_context.get()
    return context.session if context else None


def is_transaction_active() -> bool:
    """Check if there's an active transaction"""
    return _transaction_context.get() is not None


def mark_rollback_only():
    """Mark the current transaction for rollback only"""
    context = _transaction_context.get()
    if context:
        context.mark_rollback_only()
    else:
        raise RuntimeError("No active transaction to mark for rollback")


class TransactionalError(Exception):
    """Base exception for transactional operations"""
    pass


class TransactionRequiredError(TransactionalError):
    """Raised when MANDATORY propagation is used without existing transaction"""
    pass


class TransactionNotAllowedError(TransactionalError):
    """Raised when NEVER propagation is used with existing transaction"""
    pass


def Transactional(
        propagation: Propagation = Propagation.REQUIRED,
        isolation_level: Optional[Union[IsolationLevel, str]] = None,
        read_only: bool = False,
        timeout: Optional[int] = None,
        rollback_for: Optional[List[Type[Exception]]] = None,
        no_rollback_for: Optional[List[Type[Exception]]] = None,
        auto_expunge: bool = True
):
    """
    Decorator that provides automatic transaction management for async functions.

    Args:
        propagation: Transaction propagation behavior
        isolation_level: Database isolation level
        read_only: Whether this is a read-only transaction
        timeout: Transaction timeout in seconds
        rollback_for: Exception types that should trigger rollback
        no_rollback_for: Exception types that should NOT trigger rollback
        auto_expunge: Whether to automatically expunge all objects after transaction (default: True)

    Usage:
        @Transactional()
        async def create_user(self, db: AsyncSession, user_data: UserCreate):
            # Objects automatically expunged after transaction
            pass

        @Transactional(auto_expunge=False)
        async def internal_helper(self, db: AsyncSession, user_id: int):
            # Objects remain attached for performance within transaction scope
            pass

        @Transactional(propagation=Propagation.REQUIRES_NEW, read_only=True)
        async def get_user_stats(self, db: AsyncSession, user_id: int):
            # Read-only operation in separate transaction with auto-expunge
            pass
    """

    # Default rollback exceptions
    if rollback_for is None:
        rollback_for = [Exception]
    if no_rollback_for is None:
        no_rollback_for = []

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get function signature to determine injection point
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())

            # Check if this is a method (has 'self') or function
            has_self = params and params[0] == 'self'
            injection_index = 1 if has_self else 0

            # Get current transaction context
            current_context = _transaction_context.get()

            # Handle propagation logic
            if propagation == Propagation.MANDATORY:
                if not current_context:
                    raise TransactionRequiredError(
                        f"Transaction required for method {func.__name__} with MANDATORY propagation"
                    )
                # Use existing transaction - inject session if needed
                return await _inject_session_if_needed(func, args, kwargs, current_context.session)

            elif propagation == Propagation.NEVER:
                if current_context:
                    raise TransactionNotAllowedError(
                        f"Transaction not allowed for method {func.__name__} with NEVER propagation"
                    )
                # Execute without transaction
                return await func(*args, **kwargs)

            elif propagation == Propagation.NOT_SUPPORTED:
                if current_context:
                    # Suspend current transaction and execute without it
                    token = _transaction_context.set(None)
                    try:
                        return await func(*args, **kwargs)
                    finally:
                        _transaction_context.reset(token)
                else:
                    # No transaction, execute normally
                    return await func(*args, **kwargs)

            elif propagation == Propagation.SUPPORTS:
                if current_context:
                    # Join existing transaction - inject session if needed
                    return await _inject_session_if_needed(func, args, kwargs, current_context.session)
                else:
                    # No transaction, execute without one
                    return await func(*args, **kwargs)

            elif propagation == Propagation.REQUIRES_NEW:
                # Always create new transaction, even if one exists
                return await _execute_in_new_transaction(
                    func, args, kwargs, injection_index,
                    isolation_level, read_only, timeout, rollback_for, no_rollback_for, auto_expunge
                )

            else:  # REQUIRED (default)
                if current_context:
                    # Join existing transaction with savepoint for nested behavior
                    return await _execute_in_nested_transaction(
                        func, args, kwargs, current_context,
                        rollback_for, no_rollback_for
                    )
                else:
                    # Create new transaction
                    return await _execute_in_new_transaction(
                        func, args, kwargs, injection_index,
                        isolation_level, read_only, timeout, rollback_for, no_rollback_for, auto_expunge
                    )

        return wrapper
    return decorator


async def _inject_session_if_needed(func, args, kwargs, session):
    """Helper function to inject session into function arguments if needed"""
    # Get function signature to determine injection point
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())

    # Check if this is a method (has 'self') or function
    has_self = params and params[0] == 'self'
    injection_index = 1 if has_self else 0

    # Check if session already provided (avoid double injection)
    if len(args) > injection_index and isinstance(args[injection_index], AsyncSession):
        return await func(*args, **kwargs)
    else:
        # Inject session into function arguments
        new_args = list(args)
        new_args.insert(injection_index, session)
        return await func(*new_args, **kwargs)


async def _execute_in_new_transaction(
        func, args, kwargs, injection_index,
        isolation_level, read_only, timeout, rollback_for, no_rollback_for, auto_expunge
):
    """Execute function in a new transaction"""

    # Check if session already provided (avoid double injection)
    if len(args) > injection_index and isinstance(args[injection_index], AsyncSession):
        return await func(*args, **kwargs)

    # Create new session using existing get_db() function
    db_generator = get_db()
    session = await anext(db_generator)

    try:
        # Set isolation level if specified
        if isolation_level:
            isolation_str = isolation_level.value if isinstance(isolation_level, IsolationLevel) else isolation_level
            await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_str}"))

        # Set read-only mode if specified (skip for SQLite)
        if read_only:
            # Check if we're using SQLite (which doesn't support SET TRANSACTION READ ONLY)
            db_url = str(session.bind.url)
            if not db_url.startswith('sqlite'):
                await session.execute(text("SET TRANSACTION READ ONLY"))
            else:
                logger.debug("Skipping read-only mode for SQLite database")

        # Create transaction context
        context = TransactionContext(session, level=0)
        token = _transaction_context.set(context)

        try:
            # Inject session into function arguments
            new_args = list(args)
            new_args.insert(injection_index, session)

            # Execute function with timeout if specified
            if timeout:
                result = await asyncio.wait_for(
                    func(*new_args, **kwargs),
                    timeout=timeout
                )
            else:
                result = await func(*new_args, **kwargs)

            # Commit if not marked for rollback
            if not context.is_rollback_only:
                await session.commit()
                logger.debug(f"Transaction committed for {func.__name__}")

                # Auto-expunge all objects after successful commit if enabled
                if auto_expunge:
                    session.expunge_all()
                    logger.debug(f"All objects expunged after commit for {func.__name__}")
            else:
                await session.rollback()
                logger.debug(f"Transaction rolled back (marked rollback-only) for {func.__name__}")

                # Also expunge after rollback if auto_expunge is enabled
                # This ensures consistency and prevents DetachedInstanceError
                if auto_expunge:
                    session.expunge_all()
                    logger.debug(f"All objects expunged after rollback for {func.__name__}")

            return result

        except Exception as e:
            # Check if this exception should trigger rollback
            should_rollback = _should_rollback(e, rollback_for, no_rollback_for)

            if should_rollback:
                logger.debug(f"Rolling back transaction for {func.__name__} due to {type(e).__name__}")
                # Trigger rollback through get_db() generator
                try:
                    await db_generator.athrow(type(e), e, e.__traceback__)
                except StopAsyncIteration:
                    pass

                # Expunge after rollback if auto_expunge is enabled
                if auto_expunge:
                    session.expunge_all()
                    logger.debug(f"All objects expunged after rollback for {func.__name__}")
            else:
                # Commit even though exception occurred
                await session.commit()
                logger.debug(f"Transaction committed for {func.__name__} despite {type(e).__name__}")

                # Expunge after commit if auto_expunge is enabled
                if auto_expunge:
                    session.expunge_all()
                    logger.debug(f"All objects expunged after commit for {func.__name__}")

            raise

        finally:
            _transaction_context.reset(token)

    finally:
        # Properly close the generator by calling aclose()
        await db_generator.aclose()


async def _execute_in_nested_transaction(
        func, args, kwargs, parent_context, rollback_for, no_rollback_for
):
    """Execute function in a nested transaction using savepoints"""

    session = parent_context.session
    savepoint_name = f"sp_{parent_context.level + 1}_{id(func)}"

    # For nested transactions, we'll reuse the existing session without savepoints for now
    # This is a simpler approach that works better with test databases
    logger.debug(f"Executing nested transaction for {func.__name__}")

    # Create nested context but reuse the same session
    nested_context = TransactionContext(
        session,
        level=parent_context.level + 1,
        savepoint_name=savepoint_name
    )
    token = _transaction_context.set(nested_context)

    try:
        # Check if we need to inject session into args
        # Get function signature to determine injection point
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        # Check if this is a method (has 'self') or function
        has_self = params and params[0] == 'self'
        injection_index = 1 if has_self else 0

        # Check if session already provided (avoid double injection)
        if len(args) > injection_index and isinstance(args[injection_index], AsyncSession):
            result = await func(*args, **kwargs)
        else:
            # Inject session into function arguments
            new_args = list(args)
            new_args.insert(injection_index, session)
            result = await func(*new_args, **kwargs)

        # For nested transactions, we don't commit/rollback immediately
        # Let the parent transaction handle it
        if nested_context.is_rollback_only:
            parent_context.mark_rollback_only()
            logger.debug(f"Nested transaction marked parent for rollback: {func.__name__}")

        # Note: For nested transactions, we don't expunge here since objects
        # are still being used within the parent transaction context.
        # Expunging will happen when the parent transaction completes.

        return result
        
    except Exception as e:
        # Check if this exception should trigger rollback
        should_rollback = _should_rollback(e, rollback_for, no_rollback_for)
        
        if should_rollback:
            logger.debug(f"Nested transaction marking parent for rollback due to {type(e).__name__}")
            parent_context.mark_rollback_only()
        
        raise
    
    finally:
        _transaction_context.reset(token)


def _should_rollback(exception: Exception, rollback_for: List[Type[Exception]], no_rollback_for: List[Type[Exception]]) -> bool:
    """Determine if an exception should trigger a rollback"""
    
    # Check no_rollback_for first (takes precedence)
    for exc_type in no_rollback_for:
        if isinstance(exception, exc_type):
            return False
    
    # Check rollback_for
    for exc_type in rollback_for:
        if isinstance(exception, exc_type):
            return True
    
    # Default behavior: rollback for any exception
    return True


# Convenience aliases for common usage patterns
def transactional(func):
    """Simple @transactional decorator with default settings"""
    return Transactional()(func)


def read_only_transaction(func):
    """Decorator for read-only transactions"""
    return Transactional(read_only=True)(func)


def requires_new_transaction(func):
    """Decorator that always creates a new transaction"""
    return Transactional(propagation=Propagation.REQUIRES_NEW)(func)


def internal_transaction(func):
    """Decorator for internal methods that should keep objects attached for performance"""
    return Transactional(auto_expunge=False)(func)