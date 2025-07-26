from typing import List
from fastapi import APIRouter, Depends, HTTPException

from fastapi_playground_poc.services.user_service import UserService
from fastapi_playground_poc.schemas import UserCreate, UserResponse

router = APIRouter()


@router.post("/user", response_model=UserResponse)
async def create_user(user_data: UserCreate, user_service: UserService = Depends()):
    """Create a new user with user info using direct assignment pattern"""
    return await user_service.create_user(user_data)


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, user_service: UserService = Depends()):
    """Get a user by ID with user info"""
    user = await user_service.get_user(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(user_service: UserService = Depends()):
    """Get all users with user info"""
    users = await user_service.get_all_users()
    return users
