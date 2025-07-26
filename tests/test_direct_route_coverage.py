"""
Direct route function tests to achieve higher coverage.

This module tests route functions directly rather than through TestClient
to ensure all code paths are executed and covered.
"""

import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

# Import route functions directly
from fastapi_playground_poc.user_routes import create_user, get_user, get_all_users
from fastapi_playground_poc.courses_routes import (
    create_course, get_course, get_all_courses, update_course, delete_course,
    enroll_user_in_course, unenroll_user_from_course, get_user_courses, get_course_users
)
from fastapi_playground_poc.schemas import UserCreate, CourseCreate, CourseUpdate
from fastapi_playground_poc.models.User import User
from fastapi_playground_poc.models.UserInfo import UserInfo
from fastapi_playground_poc.models.Course import Course
from fastapi_playground_poc.models.Enrollment import Enrollment


class TestDirectUserRoutes:
    """Test user routes directly to hit missing lines."""

    @pytest.mark.asyncio
    async def test_create_user_direct_lines_38_40(self, test_db: AsyncSession):
        """Direct test of create_user to hit lines 38-40."""
        user_data = UserCreate(
            name="Direct Test User",
            address="123 Direct Street", 
            bio="Direct test execution"
        )
        
        # Call the route function directly
        result = await create_user(user_data, test_db)
        
        assert result.name == user_data.name
        assert result.user_info.address == user_data.address
        assert result.user_info.bio == user_data.bio
        # This should hit lines 38-40: scalar_one() and return user_with_info

    @pytest.mark.asyncio
    async def test_get_user_direct_success_lines_50_55(self, test_db: AsyncSession, sample_user):
        """Direct test of get_user success path to hit lines 50-55."""
        # Call the route function directly
        result = await get_user(sample_user.id, test_db)
        
        assert result.id == sample_user.id
        assert result.name == sample_user.name
        assert result.user_info is not None
        # This should hit lines 50-55: scalar_one_or_none success and return user

    @pytest.mark.asyncio
    async def test_get_user_direct_not_found_lines_52_53(self, test_db: AsyncSession):
        """Direct test of get_user not found to hit lines 52-53."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user(99999, test_db)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)
        # This should hit lines 52-53: if user is None and raise HTTPException

    @pytest.mark.asyncio
    async def test_get_all_users_direct_lines_63_65(self, test_db: AsyncSession, multiple_users):
        """Direct test of get_all_users to hit lines 63-65."""
        # Call the route function directly
        result = await get_all_users(test_db)
        
        assert isinstance(result, list)
        assert len(result) == len(multiple_users)
        
        # Verify all users have user_info loaded
        for user in result:
            assert user.user_info is not None
        # This should hit lines 63-65: scalars().all() and return users


class TestDirectCourseRoutes:
    """Test course routes directly to hit missing lines."""

    @pytest.mark.asyncio
    async def test_create_course_direct_line_40(self, test_db: AsyncSession):
        """Direct test of create_course to hit line 40."""
        course_data = CourseCreate(
            name="Direct Test Course",
            author_name="Direct Author",
            price="199.99"
        )
        
        result = await create_course(course_data, test_db)
        
        assert result.name == course_data.name
        assert result.author_name == course_data.author_name
        assert result.price == course_data.price
        # This should hit line 40: return new_course

    @pytest.mark.asyncio
    async def test_get_course_direct_success_lines_49_54(self, test_db: AsyncSession, sample_course):
        """Direct test of get_course success to hit lines 49-54."""
        result = await get_course(sample_course.id, test_db)
        
        assert result.id == sample_course.id
        assert result.name == sample_course.name
        assert hasattr(result, 'users')
        # This should hit lines 49-54: course found and return with users

    @pytest.mark.asyncio
    async def test_get_course_direct_not_found_lines_51_52(self, test_db: AsyncSession):
        """Direct test of get_course not found to hit lines 51-52."""
        with pytest.raises(HTTPException) as exc_info:
            await get_course(99999, test_db)
        
        assert exc_info.value.status_code == 404
        assert "Course not found" in str(exc_info.value.detail)
        # This should hit lines 51-52: if course is None and raise HTTPException

    @pytest.mark.asyncio
    async def test_get_all_courses_direct_lines_61_62(self, test_db: AsyncSession, multiple_courses):
        """Direct test of get_all_courses to hit lines 61-62."""
        result = await get_all_courses(test_db)
        
        assert isinstance(result, list)
        assert len(result) == len(multiple_courses)
        # This should hit lines 61-62: scalars().all() and return courses

    @pytest.mark.asyncio
    async def test_update_course_direct_success_lines_72_84(self, test_db: AsyncSession, sample_course):
        """Direct test of update_course success to hit lines 72-84."""
        update_data = CourseUpdate(
            name="Updated Direct Course",
            price="299.99"
        )
        
        result = await update_course(sample_course.id, update_data, test_db)
        
        assert result.id == sample_course.id
        assert result.name == update_data.name
        assert result.price == update_data.price
        # This should hit lines 72-84: course found, update, commit, refresh, return

    @pytest.mark.asyncio
    async def test_update_course_direct_not_found_lines_74_75(self, test_db: AsyncSession):
        """Direct test of update_course not found to hit lines 74-75."""
        update_data = CourseUpdate(name="Updated")
        
        with pytest.raises(HTTPException) as exc_info:
            await update_course(99999, update_data, test_db)
        
        assert exc_info.value.status_code == 404
        assert "Course not found" in str(exc_info.value.detail)
        # This should hit lines 74-75: if course is None and raise HTTPException

    @pytest.mark.asyncio
    async def test_delete_course_direct_success_lines_92_100(self, test_db: AsyncSession, sample_course):
        """Direct test of delete_course success to hit lines 92-100."""
        course_id = sample_course.id
        
        result = await delete_course(course_id, test_db)
        
        assert "deleted successfully" in result["message"]
        assert str(course_id) in result["message"]
        # This should hit lines 92-100: course found, delete, commit, return message

    @pytest.mark.asyncio
    async def test_delete_course_direct_not_found_lines_94_95(self, test_db: AsyncSession):
        """Direct test of delete_course not found to hit lines 94-95."""
        with pytest.raises(HTTPException) as exc_info:
            await delete_course(99999, test_db)
        
        assert exc_info.value.status_code == 404
        assert "Course not found" in str(exc_info.value.detail)
        # This should hit lines 94-95: if course is None and raise HTTPException

    @pytest.mark.asyncio
    async def test_enroll_user_direct_success_lines_111_133(self, test_db: AsyncSession, sample_user, sample_course):
        """Direct test of enroll_user_in_course success to hit lines 111-133."""
        result = await enroll_user_in_course(sample_user.id, sample_course.id, test_db)
        
        assert result.user_id == sample_user.id
        assert result.course_id == sample_course.id
        assert result.enrollment_date is not None
        # This should hit lines 111-133: user/course found, create enrollment, add, commit, refresh, return

    @pytest.mark.asyncio
    async def test_enroll_user_direct_user_not_found_lines_112_113(self, test_db: AsyncSession, sample_course):
        """Direct test of enroll_user_in_course user not found to hit lines 112-113."""
        with pytest.raises(HTTPException) as exc_info:
            await enroll_user_in_course(99999, sample_course.id, test_db)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)
        # This should hit lines 112-113: if user is None and raise HTTPException

    @pytest.mark.asyncio
    async def test_enroll_course_not_found_lines_117_119(self, test_db: AsyncSession, sample_user):
        """Direct test of enroll_user_in_course course not found to hit lines 117-119."""
        with pytest.raises(HTTPException) as exc_info:
            await enroll_user_in_course(sample_user.id, 99999, test_db)
        
        assert exc_info.value.status_code == 404
        assert "Course not found" in str(exc_info.value.detail)
        # This should hit lines 117-119: if course is None and raise HTTPException

    @pytest.mark.asyncio
    async def test_unenroll_direct_success_lines_147_156(self, test_db: AsyncSession, sample_enrollment):
        """Direct test of unenroll_user_from_course success to hit lines 147-156."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id
        
        result = await unenroll_user_from_course(user_id, course_id, test_db)
        
        assert "unenrolled" in result["message"]
        assert str(user_id) in result["message"]
        assert str(course_id) in result["message"]
        # This should hit lines 147-156: enrollment found, delete, commit, return message

    @pytest.mark.asyncio
    async def test_unenroll_direct_not_found_lines_149_150(self, test_db: AsyncSession, sample_user, sample_course):
        """Direct test of unenroll_user_from_course not found to hit lines 149-150."""
        with pytest.raises(HTTPException) as exc_info:
            await unenroll_user_from_course(sample_user.id, sample_course.id, test_db)
        
        assert exc_info.value.status_code == 404
        assert "Enrollment not found" in str(exc_info.value.detail)
        # This should hit lines 149-150: if enrollment is None and raise HTTPException

    @pytest.mark.asyncio
    async def test_get_user_courses_direct_success_lines_166_180(self, test_db: AsyncSession, sample_enrollment):
        """Direct test of get_user_courses success to hit lines 166-180."""
        user_id = sample_enrollment.user_id
        
        result = await get_user_courses(user_id, test_db)
        
        # get_user_courses returns a dict, not a model object
        assert result["id"] == user_id
        assert "courses" in result
        assert len(result["courses"]) > 0
        # This should hit lines 166-180: user found, select with joinedload, return user

    @pytest.mark.asyncio
    async def test_get_user_courses_direct_not_found_lines_168_169(self, test_db: AsyncSession):
        """Direct test of get_user_courses not found to hit lines 168-169."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_courses(99999, test_db)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)
        # This should hit lines 168-169: if user is None and raise HTTPException

    @pytest.mark.asyncio
    async def test_get_course_users_direct_success_lines_193_208(self, test_db: AsyncSession, sample_enrollment):
        """Direct test of get_course_users success to hit lines 193-208."""
        course_id = sample_enrollment.course_id
        
        result = await get_course_users(course_id, test_db)
        
        # get_course_users returns a dict, not a model object
        assert result["id"] == course_id
        assert "users" in result
        assert len(result["users"]) > 0
        # This should hit lines 193-208: course found, select with joinedload, return course

    @pytest.mark.asyncio
    async def test_get_course_users_direct_not_found_lines_195_196(self, test_db: AsyncSession):
        """Direct test of get_course_users not found to hit lines 195-196."""
        with pytest.raises(HTTPException) as exc_info:
            await get_course_users(99999, test_db)
        
        assert exc_info.value.status_code == 404
        assert "Course not found" in str(exc_info.value.detail)
        # This should hit lines 195-196: if course is None and raise HTTPException


class TestIntegrityErrorPaths:
    """Test specific error paths like duplicate enrollment."""

    @pytest.mark.asyncio
    async def test_duplicate_enrollment_lines_131_133(self, test_db: AsyncSession, sample_enrollment):
        """Test duplicate enrollment to hit lines 131-133."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id
        
        # Try to enroll the same user in the same course again
        with pytest.raises(HTTPException) as exc_info:
            await enroll_user_in_course(user_id, course_id, test_db)
        
        assert exc_info.value.status_code == 409
        assert "already enrolled" in str(exc_info.value.detail)
        # This should hit lines 131-133: IntegrityError handling