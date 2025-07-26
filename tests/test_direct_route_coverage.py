"""
Direct route function tests to ensure service layer operations work correctly.

This module tests route functions directly rather than through TestClient
to ensure all code paths through the service layer are executed and covered.
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
from fastapi_playground_poc.services.user_service import UserService
from fastapi_playground_poc.services.course_service import CourseService


class TestDirectUserServiceRoutes:
    """Test user routes directly to exercise service layer operations."""

    @pytest.mark.asyncio
    async def test_create_user_direct_lines_38_40(self, test_db: AsyncSession, mock_transactional_db):
        """Direct test of create_user through UserService."""
        with mock_transactional_db:
            user_data = UserCreate(
                name="Direct Test User",
                address="123 Direct Street",
                bio="Direct test execution"
            )
            
            # Create UserService instance for direct route call
            user_service = UserService()
            result = await create_user(user_data, user_service)
            
            assert result.name == user_data.name
            assert result.user_info.address == user_data.address
            assert result.user_info.bio == user_data.bio
            # This exercises UserService.create_user through direct route call

    @pytest.mark.asyncio
    async def test_get_user_direct_success_lines_50_55(self, test_db: AsyncSession, sample_user, mock_transactional_db):
        """Direct test of get_user success path through UserService."""
        with mock_transactional_db:
            # Create UserService instance for direct route call
            user_service = UserService()
            result = await get_user(sample_user.id, user_service)
            
            assert result.id == sample_user.id
            assert result.name == sample_user.name
            assert result.user_info is not None
            # This exercises UserService.get_user through direct route call

    @pytest.mark.asyncio
    async def test_get_user_direct_not_found_lines_52_53(self, test_db: AsyncSession, mock_transactional_db):
        """Direct test of get_user not found through UserService."""
        with mock_transactional_db:
            # Create UserService instance for direct route call
            user_service = UserService()
            with pytest.raises(HTTPException) as exc_info:
                await get_user(99999, user_service)
            
            assert exc_info.value.status_code == 404
            assert "User not found" in str(exc_info.value.detail)
            # This exercises UserService.get_user returning None through direct route call

    @pytest.mark.asyncio
    async def test_get_all_users_direct_lines_63_65(self, test_db: AsyncSession, multiple_users, mock_transactional_db):
        """Direct test of get_all_users through UserService."""
        with mock_transactional_db:
            # Create UserService instance for direct route call
            user_service = UserService()
            result = await get_all_users(user_service)
            
            assert isinstance(result, list)
            assert len(result) == len(multiple_users)
            
            # Verify all users have user_info loaded
            for user in result:
                assert user.user_info is not None
            # This exercises UserService.get_all_users through direct route call


class TestDirectCourseServiceRoutes:
    """Test course routes directly to exercise service layer operations."""

    @pytest.mark.asyncio
    async def test_create_course_direct_line_40(self, test_db: AsyncSession, mock_transactional_db):
        """Direct test of create_course through CourseService."""
        with mock_transactional_db:
            course_data = CourseCreate(
                name="Direct Test Course",
                author_name="Direct Author",
                price="199.99"
            )
            
            # Create CourseService instance for direct route call
            course_service = CourseService()
            result = await create_course(course_data, course_service)
            
            assert result.name == course_data.name
            assert result.author_name == course_data.author_name
            assert result.price == course_data.price
            # This exercises CourseService.create_course through direct route call

    @pytest.mark.asyncio
    async def test_get_course_direct_success_lines_49_54(self, test_db: AsyncSession, sample_course, mock_transactional_db):
        """Direct test of get_course success through CourseService."""
        with mock_transactional_db:
            # Create CourseService instance for direct route call
            course_service = CourseService()
            result = await get_course(sample_course.id, course_service)
            
            assert result.id == sample_course.id
            assert result.name == sample_course.name
            assert hasattr(result, 'users')
            # This exercises CourseService.get_course through direct route call

    @pytest.mark.asyncio
    async def test_get_course_direct_not_found_lines_51_52(self, test_db: AsyncSession, mock_transactional_db):
        """Direct test of get_course not found through CourseService."""
        with mock_transactional_db:
            # Create CourseService instance for direct route call
            course_service = CourseService()
            with pytest.raises(HTTPException) as exc_info:
                await get_course(99999, course_service)
            
            assert exc_info.value.status_code == 404
            assert "Course not found" in str(exc_info.value.detail)
            # This exercises CourseService.get_course returning None through direct route call

    @pytest.mark.asyncio
    async def test_get_all_courses_direct_lines_61_62(self, test_db: AsyncSession, multiple_courses, mock_transactional_db):
        """Direct test of get_all_courses through CourseService."""
        with mock_transactional_db:
            # Create CourseService instance for direct route call
            course_service = CourseService()
            result = await get_all_courses(course_service)
            
            assert isinstance(result, list)
            assert len(result) == len(multiple_courses)
            # This exercises CourseService.get_all_courses through direct route call

    @pytest.mark.asyncio
    async def test_update_course_direct_success_lines_72_84(self, test_db: AsyncSession, sample_course, mock_transactional_db):
        """Direct test of update_course success through CourseService."""
        with mock_transactional_db:
            update_data = CourseUpdate(
                name="Updated Direct Course",
                price="299.99"
            )
            
            # Create CourseService instance for direct route call
            course_service = CourseService()
            result = await update_course(sample_course.id, update_data, course_service)
            
            assert result.id == sample_course.id
            assert result.name == update_data.name
            assert result.price == update_data.price
            # This exercises CourseService.update_course through direct route call

    @pytest.mark.asyncio
    async def test_update_course_direct_not_found_lines_74_75(self, test_db: AsyncSession, mock_transactional_db):
        """Direct test of update_course not found through CourseService."""
        with mock_transactional_db:
            update_data = CourseUpdate(name="Updated")
            
            # Create CourseService instance for direct route call
            course_service = CourseService()
            with pytest.raises(HTTPException) as exc_info:
                await update_course(99999, update_data, course_service)
            
            assert exc_info.value.status_code == 404
            assert "Course not found" in str(exc_info.value.detail)
            # This exercises CourseService.update_course returning None through direct route call

    @pytest.mark.asyncio
    async def test_delete_course_direct_success_lines_92_100(self, test_db: AsyncSession, sample_course, mock_transactional_db):
        """Direct test of delete_course success through CourseService."""
        with mock_transactional_db:
            course_id = sample_course.id
            
            # Create CourseService instance for direct route call
            course_service = CourseService()
            result = await delete_course(course_id, course_service)
            
            assert "deleted successfully" in result["message"]
            assert str(course_id) in result["message"]
            # This exercises CourseService.delete_course through direct route call

    @pytest.mark.asyncio
    async def test_delete_course_direct_not_found_lines_94_95(self, test_db: AsyncSession, mock_transactional_db):
        """Direct test of delete_course not found through CourseService."""
        with mock_transactional_db:
            # Create CourseService instance for direct route call
            course_service = CourseService()
            with pytest.raises(HTTPException) as exc_info:
                await delete_course(99999, course_service)
            
            assert exc_info.value.status_code == 404
            assert "Course not found" in str(exc_info.value.detail)
            # This exercises CourseService.delete_course returning False through direct route call

    @pytest.mark.asyncio
    async def test_enroll_user_direct_success_lines_111_133(self, test_db: AsyncSession, sample_user, sample_course, mock_transactional_db):
        """Direct test of enroll_user_in_course success through CourseService."""
        with mock_transactional_db:
            # Create CourseService instance for direct route call
            course_service = CourseService()
            result = await enroll_user_in_course(sample_user.id, sample_course.id, course_service)
            
            assert result.user_id == sample_user.id
            assert result.course_id == sample_course.id
            assert result.enrollment_date is not None
            # This exercises CourseService.enroll_user_in_course through direct route call

    @pytest.mark.asyncio
    async def test_enroll_user_direct_user_not_found_lines_112_113(self, test_db: AsyncSession, sample_course, mock_transactional_db):
        """Direct test of enroll_user_in_course user not found through CourseService."""
        with mock_transactional_db:
            # Create CourseService instance for direct route call
            course_service = CourseService()
            with pytest.raises(HTTPException) as exc_info:
                await enroll_user_in_course(99999, sample_course.id, course_service)
            
            assert exc_info.value.status_code == 404
            assert "User not found" in str(exc_info.value.detail)
            # This exercises CourseService.enroll_user_in_course with user not found through direct route call

    @pytest.mark.asyncio
    async def test_enroll_course_not_found_lines_117_119(self, test_db: AsyncSession, sample_user, mock_transactional_db):
        """Direct test of enroll_user_in_course course not found through CourseService."""
        with mock_transactional_db:
            # Create CourseService instance for direct route call
            course_service = CourseService()
            with pytest.raises(HTTPException) as exc_info:
                await enroll_user_in_course(sample_user.id, 99999, course_service)
            
            assert exc_info.value.status_code == 404
            assert "Course not found" in str(exc_info.value.detail)
            # This exercises CourseService.enroll_user_in_course with course not found through direct route call

    @pytest.mark.asyncio
    async def test_unenroll_direct_success_lines_147_156(self, test_db: AsyncSession, sample_enrollment, mock_transactional_db):
        """Direct test of unenroll_user_from_course success through CourseService."""
        with mock_transactional_db:
            user_id = sample_enrollment.user_id
            course_id = sample_enrollment.course_id
            
            # Create CourseService instance for direct route call
            course_service = CourseService()
            result = await unenroll_user_from_course(user_id, course_id, course_service)
            
            assert "unenrolled" in result["message"]
            assert str(user_id) in result["message"]
            assert str(course_id) in result["message"]
            # This exercises CourseService.unenroll_user_from_course through direct route call

    @pytest.mark.asyncio
    async def test_unenroll_direct_not_found_lines_149_150(self, test_db: AsyncSession, sample_user, sample_course, mock_transactional_db):
        """Direct test of unenroll_user_from_course not found through CourseService."""
        with mock_transactional_db:
            # Create CourseService instance for direct route call
            course_service = CourseService()
            with pytest.raises(HTTPException) as exc_info:
                await unenroll_user_from_course(sample_user.id, sample_course.id, course_service)
            
            assert exc_info.value.status_code == 404
            assert "Enrollment not found" in str(exc_info.value.detail)
            # This exercises CourseService.unenroll_user_from_course returning False through direct route call

    @pytest.mark.asyncio
    async def test_get_user_courses_direct_success_lines_166_180(self, test_db: AsyncSession, sample_enrollment, mock_transactional_db):
        """Direct test of get_user_courses success through CourseService."""
        with mock_transactional_db:
            user_id = sample_enrollment.user_id
            
            # Create CourseService instance for direct route call
            course_service = CourseService()
            result = await get_user_courses(user_id, course_service)
            
            # get_user_courses returns a dict, not a model object
            assert result["id"] == user_id
            assert "courses" in result
            assert len(result["courses"]) > 0
            # This exercises CourseService.get_user_courses through direct route call

    @pytest.mark.asyncio
    async def test_get_user_courses_direct_not_found_lines_168_169(self, test_db: AsyncSession, mock_transactional_db):
        """Direct test of get_user_courses not found through CourseService."""
        with mock_transactional_db:
            # Create CourseService instance for direct route call
            course_service = CourseService()
            with pytest.raises(HTTPException) as exc_info:
                await get_user_courses(99999, course_service)
            
            assert exc_info.value.status_code == 404
            assert "User not found" in str(exc_info.value.detail)
            # This exercises CourseService.get_user_courses returning None through direct route call

    @pytest.mark.asyncio
    async def test_get_course_users_direct_success_lines_193_208(self, test_db: AsyncSession, sample_enrollment, mock_transactional_db):
        """Direct test of get_course_users success through CourseService."""
        with mock_transactional_db:
            course_id = sample_enrollment.course_id
            
            # Create CourseService instance for direct route call
            course_service = CourseService()
            result = await get_course_users(course_id, course_service)
            
            # get_course_users returns a dict, not a model object
            assert result["id"] == course_id
            assert "users" in result
            assert len(result["users"]) > 0
            # This exercises CourseService.get_course_users through direct route call

    @pytest.mark.asyncio
    async def test_get_course_users_direct_not_found_lines_195_196(self, test_db: AsyncSession, mock_transactional_db):
        """Direct test of get_course_users not found through CourseService."""
        with mock_transactional_db:
            # Create CourseService instance for direct route call
            course_service = CourseService()
            with pytest.raises(HTTPException) as exc_info:
                await get_course_users(99999, course_service)
            
            assert exc_info.value.status_code == 404
            assert "Course not found" in str(exc_info.value.detail)
            # This exercises CourseService.get_course_users returning None through direct route call


class TestIntegrityErrorServicePaths:
    """Test specific error paths like duplicate enrollment through service layer."""

    @pytest.mark.asyncio
    async def test_duplicate_enrollment_lines_131_133(self, test_db: AsyncSession, sample_enrollment, mock_transactional_db):
        """Test duplicate enrollment through CourseService."""
        with mock_transactional_db:
            user_id = sample_enrollment.user_id
            course_id = sample_enrollment.course_id
            
            # Create CourseService instance for direct route call
            course_service = CourseService()
            # Try to enroll the same user in the same course again
            with pytest.raises(HTTPException) as exc_info:
                await enroll_user_in_course(user_id, course_id, course_service)
            
            assert exc_info.value.status_code == 409
            assert "already enrolled" in str(exc_info.value.detail)
            # This exercises CourseService.enroll_user_in_course IntegrityError handling through direct route call