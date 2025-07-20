from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from flask_playground_poc.db import get_db
from flask_playground_poc.models.User import User
from flask_playground_poc.schemas import UserCreate, UserResponse

router = APIRouter()


@router.post("/user", response_model=UserResponse)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user"""
    # Create new user instance
    new_user = User(name=user_data.name)

    # Add to database
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get a user by ID"""
    # Query for user by ID
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(db: AsyncSession = Depends(get_db)):
    """Get all users"""
    # Query for all users
    result = await db.execute(select(User))
    users = result.scalars().all()

    return users
