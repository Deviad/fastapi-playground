"""
SQLAlchemy 2.0+ One-to-One Relationship Creation Patterns
=========================================================

This file demonstrates various ways to create users with user_info using SQLAlchemy 2.0+
with proper cascade configuration for the requirements:
- User remains when user_info is deleted
- User_info is deleted when user is deleted
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from flask_playground_poc.models.User import User
from flask_playground_poc.models.UserInfo import UserInfo


# Pattern 1: Direct Assignment (RECOMMENDED)
# ==========================================
async def create_user_direct_assignment(
    session: AsyncSession, name: str, address: str, bio: str = None
):
    """
    The most intuitive pattern - exactly what the user asked about!

    With cascade="save-update", this automatically saves both objects.
    """
    # Create user instance
    user = User(name=name)

    # Create user_info instance
    user_info = UserInfo(address=address, bio=bio)

    # Direct assignment - this is the key pattern!
    user.user_info = user_info

    # Only need to add the parent - cascade handles the rest
    session.add(user)
    await session.commit()

    return user


# Pattern 2: Constructor Assignment
# =================================
async def create_user_constructor_assignment(
    session: AsyncSession, name: str, address: str, bio: str = None
):
    """
    Create user_info first, then pass it to User constructor.
    """
    user_info = UserInfo(address=address, bio=bio)
    user = User(name=name, user_info=user_info)

    session.add(user)
    await session.commit()

    return user


# Pattern 3: Factory Pattern
# ===========================
def create_user_with_info_factory(name: str, address: str, bio: str = None) -> User:
    """
    Factory function that creates a complete user with user_info.
    Returns the user object ready to be added to session.
    """
    user_info = UserInfo(address=address, bio=bio)
    user = User(name=name, user_info=user_info)
    return user


async def use_factory_pattern(
    session: AsyncSession, name: str, address: str, bio: str = None
):
    """Using the factory pattern."""
    user = create_user_with_info_factory(name, address, bio)

    session.add(user)
    await session.commit()

    return user


# Pattern 4: Bulk Creation with Context Manager
# ==============================================
async def create_multiple_users_with_transaction(
    session: AsyncSession, users_data: list
):
    """
    Create multiple users with proper transaction handling.
    """
    created_users = []

    try:
        async with session.begin():
            for user_data in users_data:
                user = User(name=user_data["name"])
                user_info = UserInfo(
                    address=user_data["address"], bio=user_data.get("bio")
                )

                # Direct assignment pattern
                user.user_info = user_info

                session.add(user)
                created_users.append(user)

            # Auto-commit on successful completion

        return created_users

    except Exception as e:
        # Auto-rollback on exception
        raise e


# Pattern 5: With Proper Loading for API Responses
# =================================================
async def create_user_for_api_response(
    session: AsyncSession, name: str, address: str, bio: str = None
):
    """
    Create user and return with properly loaded relationships for API serialization.
    This is what we implemented in the user_routes.py
    """
    # Create user instance
    user = User(name=name)

    # Create user_info instance
    user_info = UserInfo(address=address, bio=bio)

    # Direct assignment
    user.user_info = user_info

    # Save both objects
    session.add(user)
    await session.commit()

    # Load with relationship for proper serialization
    result = await session.execute(
        select(User).options(selectinload(User.user_info)).where(User.id == user.id)
    )
    user_with_info = result.scalar_one()

    return user_with_info


# Deletion Behavior Examples
# ===========================
async def demonstrate_deletion_behavior(session: AsyncSession):
    """
    Demonstrates the cascade deletion behavior:
    - Deleting user_info keeps the user (no delete-orphan cascade)
    - Deleting user deletes user_info (database CASCADE)
    """

    # Create a test user
    user = User(name="Test User")
    user_info = UserInfo(address="Test Address", bio="Test Bio")
    user.user_info = user_info

    session.add(user)
    await session.commit()

    user_id = user.id
    user_info_id = user_info.id

    # Scenario 1: Delete user_info only - user remains
    await session.delete(user_info)
    await session.commit()

    # Check that user still exists
    remaining_user = await session.get(User, user_id)
    print(f"User still exists: {remaining_user is not None}")
    print(f"User.user_info is None: {remaining_user.user_info is None}")

    # Scenario 2: Delete user - user_info also deleted (via DB cascade)
    await session.delete(remaining_user)
    await session.commit()

    # Both should be gone
    deleted_user = await session.get(User, user_id)
    deleted_user_info = await session.get(UserInfo, user_info_id)
    print(f"User deleted: {deleted_user is None}")
    print(f"UserInfo deleted: {deleted_user_info is None}")


# Best Practices Summary
# ======================
"""
1. Use cascade="save-update" for automatic persistence without orphan deletion
2. Use ondelete='CASCADE' in ForeignKey for database-level cascade deletion
3. Direct assignment (user.user_info = object) is the most intuitive pattern
4. Always use proper transaction handling with try/except or context managers
5. For API responses, ensure relationships are properly loaded with selectinload()
6. Only add the parent object to session - cascade handles related objects
"""
