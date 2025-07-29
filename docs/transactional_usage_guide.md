# @Transactional Decorator Usage Guide

A comprehensive guide to using the Spring-inspired `@Transactional` decorator in your FastAPI/SQLAlchemy application.

## Table of Contents

1. [Overview](#overview)
2. [Basic Usage](#basic-usage)
3. [Propagation Levels](#propagation-levels)
4. [Advanced Configuration](#advanced-configuration)
5. [Service Layer Architecture](#service-layer-architecture)
6. [Migration Guide](#migration-guide)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

The `@Transactional` decorator provides automatic transaction management for your service layer methods, inspired by Spring's `@Transactional` annotation. It automatically handles:

- Database session injection
- Transaction lifecycle (begin, commit, rollback)
- Nested transactions with savepoints
- Multiple propagation behaviors
- Custom rollback rules
- Read-only transactions
- Isolation levels

## Basic Usage

### Simple Transaction

```python
from fastapi_playground_poc.infrastructure.transactional import Transactional
from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    @Transactional()
    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> User:
        new_user = User(name=user_data.name)
        db.add(new_user)
        # No need for manual commit - decorator handles it
        return new_user
```

### Route Integration

```python
from fastapi import APIRouter

router = APIRouter()

@router.post("/user", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    user_service = UserService()
    # No dependency injection needed - decorator handles session
    return await user_service.create_user(user_data)
```

### Convenience Decorators

```python
from fastapi_playground_poc.infrastructure.transactional import transactional, read_only_transaction


# Simple transaction with defaults
@transactional
async def create_simple_user(db: AsyncSession, name: str) -> User:
    user = User(name=name)
    db.add(user)
    return user


# Read-only transaction
@read_only_transaction
async def get_user_count(db: AsyncSession) -> int:
    result = await db.execute(select(User))
    return len(result.scalars().all())
```

## Propagation Levels

### REQUIRED (Default)
Joins existing transaction or creates new one if none exists.

```python
@Transactional()  # Default is Propagation.REQUIRED
async def update_user(self, db: AsyncSession, user_id: int, data: dict):
    # Will join parent transaction if called from another @Transactional method
    # Will create new transaction if called independently
    pass
```

### REQUIRES_NEW
Always creates a new transaction, even if one already exists.

```python
@Transactional(propagation=Propagation.REQUIRES_NEW)
async def audit_operation(self, db: AsyncSession, operation: str):
    # Always runs in separate transaction
    # Useful for logging/auditing that should succeed even if main operation fails
    audit_log = AuditLog(operation=operation, timestamp=datetime.utcnow())
    db.add(audit_log)
```

### MANDATORY
Requires an existing transaction; fails if none exists.

```python
@Transactional(propagation=Propagation.MANDATORY)
async def validate_user_data(self, db: AsyncSession, user_id: int):
    # Must be called from within another transaction
    # Useful for validation methods that should only run as part of larger operations
    pass
```

### NEVER
Must not run in a transaction; fails if one exists.

```python
@Transactional(propagation=Propagation.NEVER)
async def send_notification(self, user_id: int, message: str):
    # Calls external API - should not be in database transaction
    await external_notification_service.send(user_id, message)
```

### SUPPORTS
Joins existing transaction if available, runs without transaction if none.

```python
@Transactional(propagation=Propagation.SUPPORTS)
async def get_user_preferences(self, db: AsyncSession, user_id: int):
    # Can run with or without transaction
    # Useful for read operations that might be called in various contexts
    pass
```

### NOT_SUPPORTED
Suspends current transaction and runs without one.

```python
@Transactional(propagation=Propagation.NOT_SUPPORTED)
async def call_external_service(self, data: dict):
    # Temporarily suspends transaction to call external service
    # Useful when you need to call external APIs that shouldn't be in transaction
    pass
```

## Advanced Configuration

### Custom Rollback Rules

```python
@Transactional(
    rollback_for=[ValueError, ValidationError],    # Rollback for these exceptions
    no_rollback_for=[UserWarning, NotificationError]  # Don't rollback for these
)
async def create_user_with_notification(self, db: AsyncSession, user_data: UserCreate):
    # Create user
    user = User(name=user_data.name)
    db.add(user)
    
    # Send notification - if this fails, don't rollback user creation
    try:
        await send_welcome_email(user.email)
    except NotificationError:
        # Transaction continues, user is still created
        logger.warning(f"Failed to send welcome email to {user.email}")
```

### Read-Only Transactions

```python
@Transactional(read_only=True)
async def generate_user_report(self, db: AsyncSession, user_id: int) -> dict:
    # Database optimizations for read-only operations
    # Cannot perform writes in this transaction
    user = await db.get(User, user_id)
    enrollments = await db.execute(
        select(Enrollment).where(Enrollment.user_id == user_id)
    )
    return {
        "user": user,
        "enrollment_count": len(enrollments.scalars().all())
    }
```

### Isolation Levels

The `@Transactional` decorator supports all 4 PostgreSQL isolation levels, both as enum values and strings:

#### READ_UNCOMMITTED (Least Strict)
Allows dirty reads - can see uncommitted data from other transactions.

```python
@Transactional(isolation_level=IsolationLevel.READ_UNCOMMITTED)
async def get_approximate_stats(self, db: AsyncSession) -> dict:
    # High-performance read for analytics dashboards
    # Acceptable to see uncommitted data for approximate results
    # Use when real-time accuracy isn't critical
    result = await db.execute(select(func.count(User.id)))
    return {"approximate_user_count": result.scalar()}
```

#### READ_COMMITTED (Default)
Prevents dirty reads - only sees committed data from other transactions.

```python
@Transactional(isolation_level=IsolationLevel.READ_COMMITTED)
async def update_user_profile(self, db: AsyncSession, user_id: int, data: dict):
    # Standard isolation level for most business operations
    # Balances consistency with performance
    user = await db.get(User, user_id)
    for key, value in data.items():
        setattr(user, key, value)
    return user
```

#### REPEATABLE_READ
Prevents dirty reads and non-repeatable reads - same row read twice returns same value.

```python
@Transactional(isolation_level=IsolationLevel.REPEATABLE_READ)
async def calculate_financial_summary(self, db: AsyncSession, user_id: int) -> dict:
    # Ensures row values remain stable during calculation
    # Perfect for financial calculations requiring consistency
    user = await db.get(User, user_id)
    initial_balance = user.account_balance
    
    # Complex calculations here...
    await asyncio.sleep(0.1)  # Simulate processing time
    
    # Re-read balance - guaranteed to be same value
    user = await db.get(User, user_id)
    final_balance = user.account_balance
    
    assert initial_balance == final_balance, "Balance changed during calculation!"
    return {"balance": final_balance, "calculations": "..."}
```

#### SERIALIZABLE (Most Strict)
Prevents all isolation phenomena - transactions appear to run sequentially.

```python
@Transactional(isolation_level=IsolationLevel.SERIALIZABLE)
async def transfer_credits(self, db: AsyncSession, from_user: int, to_user: int, amount: int):
    # Highest isolation for critical financial operations
    # Prevents all concurrency issues but may cause serialization failures
    from_account = await db.get(User, from_user)
    to_account = await db.get(User, to_user)
    
    if from_account.credits < amount:
        raise ValueError("Insufficient credits")
    
    from_account.credits -= amount
    to_account.credits += amount
    
    # Transaction will either succeed completely or fail with serialization error
    return {"transferred": amount, "from": from_user, "to": to_user}
```

#### String Format Support
All isolation levels also accept string values:

```python
# All of these are equivalent
@Transactional(isolation_level=IsolationLevel.SERIALIZABLE)
@Transactional(isolation_level="SERIALIZABLE")
@Transactional(isolation_level="serializable")  # Case insensitive

# Available string values:
# "READ_UNCOMMITTED" / "READ UNCOMMITTED"
# "READ_COMMITTED" / "READ COMMITTED"
# "REPEATABLE_READ" / "REPEATABLE READ"
# "SERIALIZABLE"
```

#### Choosing the Right Isolation Level

| Level | Use Case | Performance | Consistency |
|-------|----------|-------------|-------------|
| `READ_UNCOMMITTED` | Analytics, dashboards | Highest | Lowest |
| `READ_COMMITTED` | Standard operations | High | Medium |
| `REPEATABLE_READ` | Financial calculations | Medium | High |
| `SERIALIZABLE` | Critical transactions | Lowest | Highest |

**Note**: SQLite only supports `SERIALIZABLE` behavior and ignores isolation level settings. PostgreSQL supports all levels.

### Timeout Configuration

```python
@Transactional(timeout=30)  # 30 seconds
async def long_running_operation(self, db: AsyncSession, data: dict):
    # Transaction will timeout after 30 seconds
    # Useful for operations that might hang
    pass
```

## Service Layer Architecture

### Recommended Structure

```
src/
  fastapi_playground_poc/
    services/
      __init__.py
      user_service.py
      course_service.py
      enrollment_service.py
    models/
      ...
    routes/
      user_routes.py
      course_routes.py
```

### Service Layer Example

```python
# services/user_service.py
from fastapi_playground_poc.infrastructure.transactional import Transactional, Propagation


class UserService:
    def __init__(self):
        self.notification_service = NotificationService()
        self.audit_service = AuditService()

    @Transactional()
    async def create_user_with_welcome(self, db: AsyncSession, user_data: UserCreate) -> User:
        """Create user and send welcome notification"""
        # Create user
        user = User(name=user_data.name, email=user_data.email)
        user_info = UserInfo(address=user_data.address, bio=user_data.bio)
        user.user_info = user_info

        db.add(user)
        await db.flush()  # Get user ID

        # Audit in separate transaction (succeeds even if notification fails)
        await self.audit_service.log_user_creation(user.id)

        # Send notification (failure won't rollback user creation)
        try:
            await self.notification_service.send_welcome_email(user.email)
        except NotificationError as e:
            logger.warning(f"Welcome email failed: {e}")

        return user

    @Transactional(read_only=True)
    async def get_user_statistics(self, db: AsyncSession, user_id: int) -> dict:
        """Get comprehensive user statistics"""
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        # Complex read-only queries
        enrollments = await db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.course))
            .where(Enrollment.user_id == user_id)
        )

        return {
            "user": user,
            "enrollment_count": len(enrollments.scalars().all()),
            "total_course_value": sum(e.course.price for e in enrollments.scalars())
        }


# services/audit_service.py
class AuditService:
    @Transactional(propagation=Propagation.REQUIRES_NEW)
    async def log_user_creation(self, db: AsyncSession, user_id: int):
        """Log user creation in separate transaction"""
        audit_entry = AuditLog(
            operation="USER_CREATED",
            user_id=user_id,
            timestamp=datetime.utcnow()
        )
        db.add(audit_entry)
```

### Route Layer Integration

```python
# routes/user_routes.py
from services.user_service import UserService

router = APIRouter()

@router.post("/user", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    """Create a new user with welcome process"""
    user_service = UserService()
    return await user_service.create_user_with_welcome(user_data)

@router.get("/user/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(user_id: int):
    """Get user statistics"""
    user_service = UserService()
    return await user_service.get_user_statistics(user_id)
```

## Migration Guide

### From Current Manual Transaction Management

**Before (Manual):**
```python
@router.post("/user", response_model=UserResponse)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    new_user = User(name=user_data.name)
    new_user_info = UserInfo(address=user_data.address, bio=user_data.bio)
    new_user.user_info = new_user_info
    
    db.add(new_user)
    await db.commit()  # Manual commit
    
    result = await db.execute(
        select(User).options(selectinload(User.user_info)).where(User.id == new_user.id)
    )
    return result.scalar_one()
```

**After (With @Transactional):**
```python
# Service layer
class UserService:
    @Transactional()
    async def create_user_with_info(self, db: AsyncSession, user_data: UserCreate) -> User:
        new_user = User(name=user_data.name)
        new_user_info = UserInfo(address=user_data.address, bio=user_data.bio)
        new_user.user_info = new_user_info
        
        db.add(new_user)
        # No manual commit needed
        
        return new_user

# Route layer
@router.post("/user", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    user_service = UserService()
    user = await user_service.create_user_with_info(user_data)
    
    # Load with relationships for response
    result = await get_current_session().execute(
        select(User).options(selectinload(User.user_info)).where(User.id == user.id)
    )
    return result.scalar_one()
```

### Migration Steps

1. **Create Service Layer**: Move business logic from routes to service classes
2. **Add @Transactional Decorators**: Replace manual transaction management
3. **Update Routes**: Simplify routes to call service methods
4. **Remove Database Dependencies**: Let @Transactional handle session injection
5. **Test Thoroughly**: Ensure transaction behavior is correct

## Best Practices

### 1. Service Layer Separation
- Keep business logic in services, not routes
- Use @Transactional on service methods, not route handlers
- Make services stateless and injectable

### 2. Transaction Boundaries
- Keep transactions as short as possible
- Don't include external API calls in transactions (use REQUIRES_NEW for auditing)
- Use read-only transactions for reporting/analytics

### 3. Error Handling
- Define clear rollback rules for different exception types
- Use REQUIRES_NEW for critical operations that must succeed
- Log transaction events for debugging

### 4. Nested Transactions
- Understand that nested @Transactional methods use savepoints
- Be careful with exception propagation in nested calls
- Use MANDATORY for methods that should only be called within transactions

### 5. Testing
- Test both success and failure scenarios
- Verify rollback behavior
- Test different propagation levels
- Use database assertions to verify transaction effects

## Troubleshooting

### Common Issues

#### 1. "No active transaction" Error
```python
# Problem: Calling get_current_session() outside transaction
def some_function():
    db = get_current_session()  # This will fail

# Solution: Ensure method is decorated
@Transactional()
async def some_function(db: AsyncSession):
    current_db = get_current_session()  # This works
```

#### 2. Transaction Not Rolling Back
```python
# Problem: Exception not in rollback_for list
@Transactional(rollback_for=[ValueError])  # Only ValueError triggers rollback
async def create_user(db: AsyncSession, data):
    # ...
    raise RuntimeError("This won't rollback!")

# Solution: Include all relevant exceptions or use default
@Transactional()  # Default: rollback for any Exception
async def create_user(db: AsyncSession, data):
    # ...
```

#### 3. Session Already Provided Error
```python
# Problem: Mixing @Transactional with Depends(get_db)
@router.post("/user")
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    service = UserService()
    return await service.create_user(db, user_data)  # db injected twice

# Solution: Remove Depends(get_db) when using @Transactional
@router.post("/user")
async def create_user(user_data: UserCreate):
    service = UserService()
    return await service.create_user(user_data)  # Let decorator inject db
```

#### 4. Nested Transaction Issues
```python
# Problem: Not understanding savepoint behavior
@Transactional()
async def parent_method(db: AsyncSession):
    # ... some work
    try:
        await child_method(db)  # This uses savepoint
    except ValueError:
        # Savepoint is already rolled back, but parent transaction continues
        pass

@Transactional()
async def child_method(db: AsyncSession):
    # ... work that might fail
    raise ValueError("Child failed")
```

### Debugging Tips

1. **Enable SQL Logging**: See actual transaction boundaries
```python
# In your database configuration
engine = create_async_engine(DATABASE_URL, echo=True)
```

2. **Use Transaction Context Functions**:
```python
@Transactional()
async def debug_method(db: AsyncSession):
    print(f"Transaction active: {is_transaction_active()}")
    print(f"Session ID: {id(get_current_session())}")
```

3. **Test Transaction Boundaries**:
```python
# Create test that verifies rollback behavior
@pytest.mark.asyncio
async def test_rollback():
    with pytest.raises(ValueError):
        await service.failing_method()
    
    # Verify nothing was committed
    count = await db.execute(select(func.count(User.id)))
    assert count.scalar() == 0
```

## Performance Considerations

- Use read-only transactions for reporting queries
- Keep transaction duration minimal
- Consider connection pooling settings
- Monitor long-running transactions
- Use appropriate isolation levels for your use case

## Advanced Features

### Manual Transaction Control

```python
from fastapi_playground_poc.infrastructure.transactional import mark_rollback_only


@Transactional()
async def conditional_operation(db: AsyncSession, data: dict):
    user = User(**data)
    db.add(user)

    if not await validate_user_data(user):
        mark_rollback_only()  # Force rollback
        return {"status": "validation_failed"}

    return {"status": "success", "user": user}
```

### Context Manager Support

```python
# For manual transaction control when decorator isn't suitable
from fastapi_playground_poc.infrastructure.db import get_db


async def manual_transaction_example():
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        # Manual transaction logic
        user = User(name="Manual User")
        db.add(user)
        await db.commit()
    except Exception:
        await db_gen.athrow(Exception)
        raise
    finally:
        try:
            await anext(db_gen)
        except StopAsyncIteration:
            pass
```

This concludes the comprehensive usage guide for the `@Transactional` decorator. For more examples, see the test files and example implementations in the `tests/` directory.