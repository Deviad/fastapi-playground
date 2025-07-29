"""
Course service layer for business logic operations.

This service handles all course-related operations including enrollment management
using the @Transactional decorator for automatic database transaction management.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from fastapi_playground_poc.domain.exceptions import DomainException, DomainError
from fastapi_playground_poc.infrastructure.transactional import Transactional
from fastapi_playground_poc.domain.model.Course import Course
from fastapi_playground_poc.domain.model.User import User
from fastapi_playground_poc.domain.model.Enrollment import Enrollment
from fastapi_playground_poc.application.web.dto.schemas import (
    CourseCreate,
    CourseResponseWithUsers,
    CourseUpdate,
    UserInfoResponse,
    UserResponseWithCourses,
)


class CourseService:
    """Service class for course and enrollment operations with automatic transaction management."""

    # Course CRUD Operations

    @Transactional(auto_expunge=True)
    async def create_course(
        self, db: AsyncSession, course_data: CourseCreate
    ) -> Course:
        """Create a new course."""
        new_course = Course(
            name=course_data.name,
            author_name=course_data.author_name,
            price=course_data.price,
        )

        db.add(new_course)
        await db.commit()

        # Reload the course to get the ID
        await db.refresh(new_course)
        # db.expunge(new_course) Not needed with auto_expunge
        return new_course

    @Transactional()
    async def get_course(self, db: AsyncSession, course_id: int) -> Optional[Course]:
        """Get a course by ID with enrolled users."""
        result = await db.execute(
            select(Course)
            .options(selectinload(Course.users).selectinload(User.user_info))
            .where(Course.id == course_id)
        )
        course = result.scalar_one_or_none()

        if course is None:
            return None

        # Not needed with auto_expunge
        # # Expunge from session to avoid DetachedInstanceError while keeping data
        # db.expunge(course)
        # for user in course.users:
        #     db.expunge(user)
        #     if user.user_info:
        #         db.expunge(user.user_info)

        return course

    @Transactional(auto_expunge=True)
    async def get_all_courses(self, db: AsyncSession) -> List[Course]:
        """Get all courses."""
        result = await db.execute(select(Course))
        courses = result.scalars().all()
        # db.expunge(courses) Not needed with auto_expunge
        return list(courses)

    @Transactional(auto_expunge=True)
    async def update_course(
        self, db: AsyncSession, course_id: int, course_data: CourseUpdate
    ) -> Optional[Course]:
        """Update a course."""
        # Get the existing course
        result = await db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()

        if course is None:
            return None

        # Update only provided fields
        update_data = course_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(course, field, value)

        await db.commit()
        await db.refresh(course)
        # db.expunge(courses) Not needed with auto_expunge
        return course

    @Transactional(auto_expunge=True)
    async def delete_course(self, db: AsyncSession, course_id: int) -> bool:
        """Delete a course (and all its enrollments due to cascade)."""
        # Get the existing course
        result = await db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()

        if course is None:
            return False

        await db.delete(course)
        await db.commit()
        return True

    # Enrollment Management

    @Transactional(auto_expunge=True)
    async def enroll_user_in_course(
        self, db: AsyncSession, user_id: int, course_id: int
    ) -> Optional[Enrollment]:
        """Enroll a user in a course."""
        import logging

        logger = logging.getLogger(__name__)

        logger.debug(f"Starting enrollment: user_id={user_id}, course_id={course_id}")

        # Check if user exists
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            logger.error(f"User not found: user_id={user_id}")
            raise DomainException(
                DomainError.USER_NOT_FOUND, f"User with id {user_id} does not exist"
            )

        # Check if course exists
        course_result = await db.execute(select(Course).where(Course.id == course_id))
        course = course_result.scalar_one_or_none()
        if course is None:
            logger.error(f"Course not found: course_id={course_id}")
            raise DomainException(
                DomainError.COURSE_NOT_FOUND,
                f"Course with id {course_id} does not exist",
            )

        logger.debug(f"Both user and course found, creating enrollment")

        # Create enrollment
        new_enrollment = Enrollment(
            user_id=user_id,
            course_id=course_id,
            enrollment_date=datetime.utcnow(),
        )

        try:
            db.add(new_enrollment)
            await db.commit()
            await db.refresh(new_enrollment)
            logger.debug(
                f"Enrollment created successfully: enrollment_id={new_enrollment.id}"
            )
            return new_enrollment
        except IntegrityError as e:
            logger.error(f"IntegrityError during enrollment: {str(e)}")
            # Let the @Transactional decorator handle the rollback automatically
            # Don't manually commit/rollback here as it interferes with the decorator
            raise DomainException(
                DomainError.DUPLICATE_ENROLLMENT_ATTEMPT,
                "User is already enrolled in the course",
                context={
                    "course_id": course_id,
                    "user_id": user_id,
                    "original_error": str(e),
                },
            )

    @Transactional(auto_expunge=True)
    async def unenroll_user_from_course(
        self, db: AsyncSession, user_id: int, course_id: int
    ) -> bool:
        """Unenroll a user from a course."""
        # Find the enrollment
        result = await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id, Enrollment.course_id == course_id
            )
        )
        enrollment = result.scalar_one_or_none()

        if enrollment is None:
            raise DomainException(
                DomainError.ENROLLMENT_NOTFOUND,
                "Enrollment not found for this user and course",
                context={
                    "course_id": course_id,
                    "user_id": user_id,
                },
            )

        # Delete the enrollment
        await db.delete(enrollment)
        await db.commit()
        return True

    @Transactional(auto_expunge=True)
    async def get_user_courses(
        self, db: AsyncSession, user_id: int
    ) -> Optional[UserResponseWithCourses]:
        """Get a user with all their enrolled courses."""
        # Get user first (without loading enrollments to avoid cache)
        user_result = await db.execute(
            select(User).options(selectinload(User.user_info)).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            return None

        # Get courses through a fresh enrollment query (bypasses any cached relationships)
        courses_result = await db.execute(
            select(Course)
            .join(Enrollment, Course.id == Enrollment.course_id)
            .where(Enrollment.user_id == user_id)
        )
        courses = courses_result.scalars().all()
        # Convert courses to dictionaries to avoid DetachedInstanceError
        # courses_data = []
        # for course in courses:
        #     courses_data.append({
        #         "id": course.id,
        #         "name": course.name,
        #         "author_name": course.author_name,
        #         "price": course.price,
        #     })

        # Create response dict manually to include the courses
        return UserResponseWithCourses(
            id=user.id,
            name=user.name,
            user_info=(
                UserInfoResponse(
                    id=user.user_info.id,
                    address=user.user_info.address,
                    bio=user.user_info.bio,
                )
                if user.user_info
                else None
            ),
            courses=courses,
        )
        # return {
        #     "id": user.id,
        #     "name": user.name,
        #     "user_info": {
        #         "id": user.user_info.id,
        #         "address": user.user_info.address,
        #         "bio": user.user_info.bio,
        #     } if user.user_info else None,
        #     "courses": courses_data,
        # }

    @Transactional(auto_expunge=True)
    async def get_course_users(
        self, db: AsyncSession, course_id: int
    ) -> CourseResponseWithUsers:
        """Get a course with all enrolled users."""
        # Get course first (without loading enrollments to avoid cache)
        course_result = await db.execute(select(Course).where(Course.id == course_id))
        course = course_result.scalar_one_or_none()

        if course is None:
            return None

        # Get users through a fresh enrollment query (bypasses any cached relationships)
        users_result = await db.execute(
            select(User)
            .options(selectinload(User.user_info))
            .join(Enrollment, User.id == Enrollment.user_id)
            .where(Enrollment.course_id == course_id)
        )
        users = users_result.scalars().all()

        # Convert users to dictionaries to avoid DetachedInstanceError
        # users_data = []
        # for user in users:
        #     users_data.append({
        #         "id": user.id,
        #         "name": user.name,
        #         "user_info": {
        #             "id": user.user_info.id,
        #             "address": user.user_info.address,
        #             "bio": user.user_info.bio,
        #         } if user.user_info else None,
        #     })

        return CourseResponseWithUsers(
            id=course.id,
            name=course.name,
            author_name=course.author_name,
            price=course.price,
            users=users,
        )

        # Create response dict manually to include the users
        # return {
        #     "id": course.id,
        #     "name": course.name,
        #     "author_name": course.author_name,
        #     "price": course.price,
        #     "users": users_data,
        # }
