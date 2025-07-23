from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from flask_playground_poc.db import get_db
from flask_playground_poc.models.User import User
from flask_playground_poc.models.UserInfo import UserInfo
from flask_playground_poc.schemas import UserCreate, UserResponse

router = APIRouter()


@router.post("/user", response_model=UserResponse)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user with user info using direct assignment pattern"""
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


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get a user by ID with user info"""
    # Query for user by ID with user_info relationship
    result = await db.execute(
        select(User).options(selectinload(User.user_info)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(db: AsyncSession = Depends(get_db)):
    """Get all users with user info"""
    # Query for all users with user_info relationship
    result = await db.execute(select(User).options(selectinload(User.user_info)))
    users = result.scalars().all()

    return users
