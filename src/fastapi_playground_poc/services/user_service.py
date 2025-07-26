"""
User service layer for business logic operations.

This service handles all user-related operations using the @Transactional decorator
for automatic database transaction management.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from fastapi_playground_poc.transactional import Transactional
from fastapi_playground_poc.models.User import User
from fastapi_playground_poc.models.UserInfo import UserInfo
from fastapi_playground_poc.schemas import UserCreate


class UserService:
    """Service class for user operations with automatic transaction management."""

    @Transactional()
    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user with user info using direct assignment pattern."""
        # Create new user instance
        new_user = User(name=user_data.name)

        # Create user info instance
        new_user_info = UserInfo(address=user_data.address, bio=user_data.bio)

        # Direct assignment - this is the pattern you asked about!
        # With cascade="save-update", both objects will be saved automatically
        new_user.user_info = new_user_info

        # Only need to add the parent object - cascade handles the rest
        db.add(new_user)
        await db.commit()

        # Load the user with the relationship properly for serialization
        result = await db.execute(
            select(User)
            .options(selectinload(User.user_info))
            .where(User.id == new_user.id)
        )
        user_with_info = result.scalar_one()

        return user_with_info

    @Transactional()
    async def get_user(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Get a user by ID with user info."""
        # Query for user by ID with user_info relationship
        result = await db.execute(
            select(User).options(selectinload(User.user_info)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return user

    @Transactional()
    async def get_all_users(self, db: AsyncSession) -> List[User]:
        """Get all users with user info."""
        # Query for all users with user_info relationship
        result = await db.execute(select(User).options(selectinload(User.user_info)))
        users = result.scalars().all()
        return list(users)