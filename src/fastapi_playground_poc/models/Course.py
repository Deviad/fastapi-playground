from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy.orm import relationship

from fastapi_playground_poc.db import Base as SqlBase


class Course(SqlBase):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    author_name = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)

    # One-to-many relationship with Enrollment
    # cascade="all, delete-orphan" ensures that when a course is deleted,
    # all its enrollments are also deleted, but users remain intact
    enrollments = relationship(
        "Enrollment", back_populates="course", cascade="all, delete-orphan"
    )

    # Many-to-many relationship with User through Enrollment (viewonly for convenience)
    users = relationship(
        "User",
        secondary="enrollments",
        back_populates="courses",
        viewonly=True,
        overlaps="enrollments",
    )
