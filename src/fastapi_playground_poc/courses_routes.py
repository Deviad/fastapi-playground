from typing import List
from fastapi import APIRouter, Depends, HTTPException

from fastapi_playground_poc.services.course_service import CourseService
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
async def create_course(course_data: CourseCreate, course_service: CourseService = Depends()):
    """Create a new course"""
    return await course_service.create_course(course_data)


@router.get("/course/{course_id}", response_model=CourseResponseWithUsers)
async def get_course(course_id: int, course_service: CourseService = Depends()):
    """Get a course by ID with enrolled users"""
    course = await course_service.get_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.get("/courses", response_model=List[CourseResponse])
async def get_all_courses(course_service: CourseService = Depends()):
    """Get all courses"""
    return await course_service.get_all_courses()


@router.put("/course/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int, course_data: CourseUpdate, course_service: CourseService = Depends()
):
    """Update a course"""
    course = await course_service.update_course(course_id, course_data)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.delete("/course/{course_id}")
async def delete_course(course_id: int, course_service: CourseService = Depends()):
    """Delete a course (and all its enrollments due to cascade)"""
    deleted = await course_service.delete_course(course_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"message": f"Course {course_id} deleted successfully"}


# Enrollment Management
@router.post("/user/{user_id}/enroll/{course_id}", response_model=EnrollmentResponse)
async def enroll_user_in_course(
    user_id: int, course_id: int, course_service: CourseService = Depends()
):
    """Enroll a user in a course"""
    try:
        enrollment = await course_service.enroll_user_in_course(user_id, course_id)
        if enrollment is None:
            raise HTTPException(status_code=404, detail="User or course not found")
        return enrollment
    except ValueError as e:
        error_message = str(e).lower()
        if "user not found" in error_message:
            raise HTTPException(status_code=404, detail="User not found")
        elif "course not found" in error_message:
            raise HTTPException(status_code=404, detail="Course not found")
        elif "already enrolled" in error_message:
            raise HTTPException(status_code=409, detail="User is already enrolled in the course")
        else:
            raise HTTPException(status_code=400, detail=str(e))


@router.delete("/user/{user_id}/enroll/{course_id}")
async def unenroll_user_from_course(
    user_id: int, course_id: int, course_service: CourseService = Depends()
):
    """Unenroll a user from a course"""
    success = await course_service.unenroll_user_from_course(user_id, course_id)
    if not success:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return {"message": f"User {user_id} unenrolled from course {course_id}"}


@router.get("/user/{user_id}/courses", response_model=UserResponseWithCourses)
async def get_user_courses(user_id: int, course_service: CourseService = Depends()):
    """Get a user with all their enrolled courses"""
    user_with_courses = await course_service.get_user_courses(user_id)
    if user_with_courses is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user_with_courses


@router.get("/course/{course_id}/users", response_model=CourseResponseWithUsers)
async def get_course_users(course_id: int, course_service: CourseService = Depends()):
    """Get a course with all enrolled users"""
    course_with_users = await course_service.get_course_users(course_id)
    if course_with_users is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course_with_users
