from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from flask_playground_poc.db import Base as SqlBase


class Enrollment(SqlBase):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    enrollment_date = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

    # Ensure a user can only enroll in a course once
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="unique_user_course_enrollment"),
    )
