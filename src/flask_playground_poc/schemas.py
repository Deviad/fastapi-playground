from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    """Schema for creating a new user"""

    name: str


class UserResponse(BaseModel):
    """Schema for user response"""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True, extra='allow')

