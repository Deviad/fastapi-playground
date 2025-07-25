from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


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


# Course Schemas
class CourseCreate(BaseModel):
    """Schema for creating a new course"""

    name: str
    author_name: str
    price: Decimal


class CourseUpdate(BaseModel):
    """Schema for updating a course"""

    name: Optional[str] = None
    author_name: Optional[str] = None
    price: Optional[Decimal] = None


class CourseResponse(BaseModel):
    """Schema for course response"""

    id: int
    name: str
    author_name: str
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


# Enrollment Schemas
class EnrollmentCreate(BaseModel):
    """Schema for creating an enrollment"""

    user_id: int
    course_id: int


class EnrollmentResponse(BaseModel):
    """Schema for enrollment response"""

    id: int
    user_id: int
    course_id: int
    enrollment_date: datetime

    model_config = ConfigDict(from_attributes=True)


# Enhanced User Response with Courses
class UserResponseWithCourses(BaseModel):
    """Schema for user response including enrolled courses"""

    id: int
    name: str
    user_info: Optional[UserInfoResponse] = None
    courses: List[CourseResponse] = []

    model_config = ConfigDict(from_attributes=True)


# Enhanced Course Response with Users
class CourseResponseWithUsers(BaseModel):
    """Schema for course response including enrolled users"""

    id: int
    name: str
    author_name: str
    price: Decimal
    users: List[UserResponse] = []

    model_config = ConfigDict(from_attributes=True)
