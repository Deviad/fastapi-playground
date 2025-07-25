from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from fastapi_playground_poc.db import get_db
from fastapi_playground_poc.models.Course import Course
from fastapi_playground_poc.models.User import User
from fastapi_playground_poc.models.Enrollment import Enrollment
from fastapi_playground_poc.schemas import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseResponseWithUsers,
    UserResponseWithCourses,
    EnrollmentResponse,
)

router = APIRouter()


# Course CRUD Operations
@router.post("/course", response_model=CourseResponse)
async def create_course(course_data: CourseCreate, db: AsyncSession = Depends(get_db)):
    """Create a new course"""
    new_course = Course(
        name=course_data.name,
        author_name=course_data.author_name,
        price=course_data.price,
    )

    db.add(new_course)
    await db.commit()

    # Reload the course to get the ID
    await db.refresh(new_course)
    return new_course


@router.get("/course/{course_id}", response_model=CourseResponseWithUsers)
async def get_course(course_id: int, db: AsyncSession = Depends(get_db)):
    """Get a course by ID with enrolled users"""
    result = await db.execute(
        select(Course).options(selectinload(Course.users)).where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()

    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    return course


@router.get("/courses", response_model=List[CourseResponse])
async def get_all_courses(db: AsyncSession = Depends(get_db)):
    """Get all courses"""
    result = await db.execute(select(Course))
    courses = result.scalars().all()
    return courses


@router.put("/course/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int, course_data: CourseUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a course"""
    # Get the existing course
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()

    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    # Update only provided fields
    update_data = course_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)

    await db.commit()
    await db.refresh(course)
    return course


@router.delete("/course/{course_id}")
async def delete_course(course_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a course (and all its enrollments due to cascade)"""
    # Get the existing course
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()

    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    await db.delete(course)
    await db.commit()

    return {"message": f"Course {course_id} deleted successfully"}


# Enrollment Management
@router.post("/user/{user_id}/enroll/{course_id}", response_model=EnrollmentResponse)
async def enroll_user_in_course(
    user_id: int, course_id: int, db: AsyncSession = Depends(get_db)
):
    """Enroll a user in a course"""
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if course exists
    course_result = await db.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

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
    except IntegrityError:
         raise HTTPException(status_code=409, detail="User is already enrolled in the course")
    return new_enrollment


@router.delete("/user/{user_id}/enroll/{course_id}")
async def unenroll_user_from_course(
    user_id: int, course_id: int, db: AsyncSession = Depends(get_db)
):
    """Unenroll a user from a course"""
    # Find the enrollment
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == user_id, Enrollment.course_id == course_id
        )
    )
    enrollment = result.scalar_one_or_none()

    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    # Delete the enrollment
    await db.delete(enrollment)
    await db.commit()

    return {"message": f"User {user_id} unenrolled from course {course_id}"}


@router.get("/user/{user_id}/courses", response_model=UserResponseWithCourses)
async def get_user_courses(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get a user with all their enrolled courses"""
    # Get user first (without loading enrollments to avoid cache)
    user_result = await db.execute(
        select(User).options(selectinload(User.user_info)).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Get courses through a fresh enrollment query (bypasses any cached relationships)
    courses_result = await db.execute(
        select(Course)
        .join(Enrollment, Course.id == Enrollment.course_id)
        .where(Enrollment.user_id == user_id)
    )
    courses = courses_result.scalars().all()

    # Create response dict manually to include the courses
    return {
        "id": user.id,
        "name": user.name,
        "user_info": user.user_info,
        "courses": courses,
    }


@router.get("/course/{course_id}/users", response_model=CourseResponseWithUsers)
async def get_course_users(course_id: int, db: AsyncSession = Depends(get_db)):
    """Get a course with all enrolled users"""
    # Get course first (without loading enrollments to avoid cache)
    course_result = await db.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()

    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get users through a fresh enrollment query (bypasses any cached relationships)
    users_result = await db.execute(
        select(User)
        .options(selectinload(User.user_info))
        .join(Enrollment, User.id == Enrollment.user_id)
        .where(Enrollment.course_id == course_id)
    )
    users = users_result.scalars().all()

    # Create response dict manually to include the users
    return {
        "id": course.id,
        "name": course.name,
        "author_name": course.author_name,
        "price": course.price,
        "users": users,
    }
