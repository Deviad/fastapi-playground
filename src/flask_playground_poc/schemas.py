from pydantic import BaseModel, ConfigDict
from typing import Optional


class UserInfoCreate(BaseModel):
    """Schema for creating user info"""

    address: str
    bio: Optional[str] = None


class UserInfoResponse(BaseModel):
    """Schema for user info response"""

    id: int
    address: str
    bio: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Schema for creating a new user"""

    name: str
    address: str
    bio: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user response"""

    id: int
    name: str
    user_info: Optional[UserInfoResponse] = None

    model_config = ConfigDict(from_attributes=True, extra="allow")
