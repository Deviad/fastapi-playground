from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from fastapi_playground_poc.db import Base as SqlBase


class User(SqlBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))

    # One-to-one relationship with UserInfo
    # cascade="save-update" allows automatic saving but keeps user when user_info is deleted
    user_info = relationship(
        "UserInfo", back_populates="user", uselist=False, cascade="save-update"
    )

    # One-to-many relationship with Enrollment
    enrollments = relationship(
        "Enrollment", back_populates="user", cascade="all, delete-orphan"
    )

    # Many-to-many relationship with Course through Enrollment (viewonly for convenience)
    courses = relationship(
        "Course",
        secondary="enrollments",
        back_populates="users",
        viewonly=True,
        overlaps="enrollments",
    )
