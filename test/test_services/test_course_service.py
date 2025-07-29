"""
Tests for CourseService class.

This module tests all CourseService methods to ensure they work correctly
with the @Transactional decorator and maintain the same functionality
as the original route implementations.
"""

import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from fastapi_playground_poc.application.web.service.course_service import CourseService
from fastapi_playground_poc.application.web.dto.schemas import CourseCreate, CourseUpdate


class TestCourseService:
    """Test class for CourseService operations."""

    def setup_method(self):
        """Set up CourseService instance for each test."""
        self.course_service = CourseService()

    @pytest.mark.unit
    async def test_get_course_success(self, sample_course, mock_transactional_db):
        """Test get_course method with existing course."""
        course_id = sample_course.id

        with mock_transactional_db:
            result = await self.course_service.get_course(course_id)

        assert result is not None
        assert result.id == course_id
        assert result.name == sample_course.name
        assert result.author_name == sample_course.author_name
        assert result.price == sample_course.price

    @pytest.mark.unit
    async def test_get_course_not_found(self, mock_transactional_db):
        """Test get_course method with non-existent course."""
        non_existent_id = 99999

        with mock_transactional_db:
            result = await self.course_service.get_course(non_existent_id)

        assert result is None

    @pytest.mark.unit
    async def test_get_all_courses_empty(self, mock_transactional_db):
        """Test get_all_courses method with empty database."""
        with mock_transactional_db:
            result = await self.course_service.get_all_courses()

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    async def test_get_all_courses_with_data(
        self, multiple_courses, mock_transactional_db
    ):
        """Test get_all_courses method with existing courses."""
        with mock_transactional_db:
            result = await self.course_service.get_all_courses()

        assert isinstance(result, list)
        assert len(result) == len(multiple_courses)

        # Verify all courses have proper data
        for course in result:
            assert hasattr(course, "name")
            assert hasattr(course, "author_name")
            assert hasattr(course, "price")

    @pytest.mark.unit
    async def test_create_course_success(self, mock_transactional_db):
        """Test create_course method with valid data."""
        course_data = CourseCreate(
            name="Test Course", author_name="Test Author", price=Decimal("99.99")
        )

        with mock_transactional_db:
            result = await self.course_service.create_course(course_data)

        assert result is not None
        assert result.name == course_data.name
        assert result.author_name == course_data.author_name
        assert result.price == course_data.price
        assert isinstance(result.id, int)

    @pytest.mark.unit
    async def test_update_course_success(self, sample_course, mock_transactional_db):
        """Test update_course method with valid data."""
        course_id = sample_course.id
        update_data = CourseUpdate(name="Updated Course Name", price=Decimal("199.99"))

        with mock_transactional_db:
            result = await self.course_service.update_course(course_id, update_data)

        assert result is not None
        assert result.id == course_id
        assert result.name == update_data.name
        assert result.price == update_data.price
        assert result.author_name == sample_course.author_name  # Unchanged

    @pytest.mark.unit
    async def test_update_course_not_found(self, mock_transactional_db):
        """Test update_course method with non-existent course."""
        non_existent_id = 99999
        update_data = CourseUpdate(name="Updated Course")

        with mock_transactional_db:
            result = await self.course_service.update_course(
                non_existent_id, update_data
            )

        assert result is None

    @pytest.mark.unit
    async def test_delete_course_success(self, sample_course, mock_transactional_db):
        """Test delete_course method with existing course."""
        course_id = sample_course.id

        with mock_transactional_db:
            result = await self.course_service.delete_course(course_id)

        assert result is True

    @pytest.mark.unit
    async def test_delete_course_not_found(self, mock_transactional_db):
        """Test delete_course method with non-existent course."""
        non_existent_id = 99999

        with mock_transactional_db:
            result = await self.course_service.delete_course(non_existent_id)

        assert result is False

    @pytest.mark.unit
    async def test_enroll_user_in_course_success(
        self, sample_user, sample_course, mock_transactional_db
    ):
        """Test enroll_user_in_course method with valid user and course."""
        user_id = sample_user.id
        course_id = sample_course.id

        with mock_transactional_db:
            result = await self.course_service.enroll_user_in_course(user_id, course_id)

        assert result is not None
        assert result.user_id == user_id
        assert result.course_id == course_id
        assert hasattr(result, "enrollment_date")

    @pytest.mark.unit
    async def test_enroll_user_not_found(self, sample_course, mock_transactional_db):
        """Test enroll_user_in_course method with non-existent user."""
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        non_existent_user_id = 99999
        course_id = sample_course.id

        with mock_transactional_db:
            with pytest.raises(DomainException) as exc_info:
                await self.course_service.enroll_user_in_course(
                    non_existent_user_id, course_id
                )

            assert exc_info.value.domain_error == DomainError.USER_NOT_FOUND
            assert "User with id 99999 does not exist" in str(exc_info.value)

    @pytest.mark.unit
    async def test_enroll_course_not_found(self, sample_user, mock_transactional_db):
        """Test enroll_user_in_course method with non-existent course."""
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        user_id = sample_user.id
        non_existent_course_id = 99999

        with mock_transactional_db:
            with pytest.raises(DomainException) as exc_info:
                await self.course_service.enroll_user_in_course(
                    user_id, non_existent_course_id
                )

            assert exc_info.value.domain_error == DomainError.COURSE_NOT_FOUND
            assert "Course with id 99999 does not exist" in str(exc_info.value)

    @pytest.mark.unit
    async def test_enroll_duplicate_enrollment(
        self, sample_enrollment, mock_transactional_db
    ):
        """Test enroll_user_in_course method with duplicate enrollment."""
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            with pytest.raises(DomainException) as exc_info:
                await self.course_service.enroll_user_in_course(user_id, course_id)

            assert (
                exc_info.value.domain_error == DomainError.DUPLICATE_ENROLLMENT_ATTEMPT
            )
            assert "User is already enrolled in the course" in str(exc_info.value)

    @pytest.mark.unit
    async def test_unenroll_user_from_course_success(
        self, sample_enrollment, mock_transactional_db
    ):
        """Test unenroll_user_from_course method with existing enrollment."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            result = await self.course_service.unenroll_user_from_course(
                user_id, course_id
            )

        assert result is True

    @pytest.mark.unit
    async def test_unenroll_enrollment_not_found(
        self, sample_user, sample_course, mock_transactional_db
    ):
        """Test unenroll_user_from_course method with non-existent enrollment."""
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        user_id = sample_user.id
        course_id = sample_course.id

        with mock_transactional_db:
            with pytest.raises(DomainException) as exc_info:
                await self.course_service.unenroll_user_from_course(user_id, course_id)

            assert exc_info.value.domain_error == DomainError.ENROLLMENT_NOTFOUND
            assert "Enrollment not found" in str(exc_info.value)

    @pytest.mark.unit
    async def test_get_user_courses_success(
        self, sample_enrollment, mock_transactional_db
    ):
        """Test get_user_courses method with user who has enrollments."""
        user_id = sample_enrollment.user_id

        with mock_transactional_db:
            result = await self.course_service.get_user_courses(user_id)

        assert result is not None
        assert result.id == user_id
        assert hasattr(result, "name")
        assert len(result.name) > 0
        assert hasattr(result, "user_info")
        assert hasattr(result, "courses")
        assert isinstance(result.courses, list)
        assert len(result.courses) >= 1

    @pytest.mark.unit
    async def test_get_user_courses_user_not_found(self, mock_transactional_db):
        """Test get_user_courses method with non-existent user."""
        non_existent_user_id = 99999

        with mock_transactional_db:
            result = await self.course_service.get_user_courses(non_existent_user_id)

        assert result is None

    # Direct route function tests for additional coverage
    @pytest.mark.asyncio
    async def test_create_course_direct_route_function(
        self, test_db: AsyncSession, mock_transactional_db
    ):
        """Direct test of create_course route function."""
        from fastapi_playground_poc.application.web.controller.courses_routes import create_course

        with mock_transactional_db:
            course_data = CourseCreate(
                name="Direct Test Course", author_name="Direct Author", price="199.99"
            )

            result = await create_course(course_data, self.course_service)

            assert result.name == course_data.name
            assert result.author_name == course_data.author_name
            assert result.price == course_data.price

    @pytest.mark.asyncio
    async def test_get_course_direct_route_success(
        self, test_db: AsyncSession, sample_course, mock_transactional_db
    ):
        """Direct test of get_course route function success."""
        from fastapi_playground_poc.application.web.controller.courses_routes import get_course

        with mock_transactional_db:
            result = await get_course(sample_course.id, self.course_service)

            assert result.id == sample_course.id
            assert result.name == sample_course.name
            assert hasattr(result, "users")

    @pytest.mark.asyncio
    async def test_get_course_direct_route_not_found(
        self, test_db: AsyncSession, mock_transactional_db
    ):
        """Direct test of get_course route function not found."""
        from fastapi_playground_poc.application.web.controller.courses_routes import get_course

        with mock_transactional_db:
            with pytest.raises(HTTPException) as exc_info:
                await get_course(99999, self.course_service)

            assert exc_info.value.status_code == 404
            assert "Course not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_all_courses_direct_route(
        self, test_db: AsyncSession, multiple_courses, mock_transactional_db
    ):
        """Direct test of get_all_courses route function."""
        from fastapi_playground_poc.application.web.controller.courses_routes import get_all_courses

        with mock_transactional_db:
            result = await get_all_courses(self.course_service)

            assert isinstance(result, list)
            assert len(result) == len(multiple_courses)

    @pytest.mark.asyncio
    async def test_update_course_direct_route_success(
        self, test_db: AsyncSession, sample_course, mock_transactional_db
    ):
        """Direct test of update_course route function success."""
        from fastapi_playground_poc.application.web.controller.courses_routes import update_course

        with mock_transactional_db:
            update_data = CourseUpdate(name="Updated Direct Course", price="299.99")

            result = await update_course(
                sample_course.id, update_data, self.course_service
            )

            assert result.id == sample_course.id
            assert result.name == update_data.name
            assert result.price == update_data.price

    @pytest.mark.asyncio
    async def test_update_course_direct_route_not_found(
        self, test_db: AsyncSession, mock_transactional_db
    ):
        """Direct test of update_course route function not found."""
        from fastapi_playground_poc.application.web.controller.courses_routes import update_course

        with mock_transactional_db:
            update_data = CourseUpdate(name="Updated")

            with pytest.raises(HTTPException) as exc_info:
                await update_course(99999, update_data, self.course_service)

            assert exc_info.value.status_code == 404
            assert "Course not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_course_direct_route_success(
        self, test_db: AsyncSession, sample_course, mock_transactional_db
    ):
        """Direct test of delete_course route function success."""

        with mock_transactional_db:
            course_id = sample_course.id

            result = await self.course_service.delete_course(course_id)

            assert result == True

    @pytest.mark.asyncio
    async def test_delete_course_direct_route_not_found(
        self, test_db: AsyncSession, mock_transactional_db
    ):
        """Direct test of delete_course route function not found."""

        with mock_transactional_db:
            result = await self.course_service.delete_course(99999)

        assert result == False

    @pytest.mark.asyncio
    async def test_enroll_user_direct_route_success(
        self, test_db: AsyncSession, sample_user, sample_course, mock_transactional_db
    ):
        """Direct test of enroll_user_in_course route function success."""
        from fastapi_playground_poc.application.web.controller.courses_routes import enroll_user_in_course

        with mock_transactional_db:
            result = await self.course_service.enroll_user_in_course(
                sample_user.id, sample_course.id
            )

            assert result.user_id == sample_user.id
            assert result.course_id == sample_course.id
            assert result.enrollment_date is not None

    @pytest.mark.asyncio
    async def test_enroll_user_direct_route_user_not_found(
        self, test_db: AsyncSession, sample_course, mock_transactional_db
    ):
        """Direct test of enroll_user_in_course route function user not found."""
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        with mock_transactional_db:
            with pytest.raises(DomainException) as exc_info:
                await self.course_service.enroll_user_in_course(99999, sample_course.id)

            assert exc_info.value.domain_error == DomainError.USER_NOT_FOUND

    @pytest.mark.asyncio
    async def test_enroll_course_direct_route_not_found(
        self, test_db: AsyncSession, sample_user, mock_transactional_db
    ):
        """Direct test of enroll_user_in_course route function course not found."""
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        with mock_transactional_db:
            with pytest.raises(DomainException) as exc_info:
                await self.course_service.enroll_user_in_course(sample_user.id, 99999)

            assert exc_info.value.domain_error == DomainError.COURSE_NOT_FOUND

    @pytest.mark.asyncio
    async def test_unenroll_direct_route_success(
        self, test_db: AsyncSession, sample_enrollment, mock_transactional_db
    ):
        """Direct test of unenroll_user_from_course route function success."""
        from fastapi_playground_poc.application.web.controller.courses_routes import unenroll_user_from_course

        with mock_transactional_db:
            user_id = sample_enrollment.user_id
            course_id = sample_enrollment.course_id

            result = await unenroll_user_from_course(
                user_id, course_id, self.course_service
            )

            assert "unenrolled" in result["message"]
            assert str(user_id) in result["message"]
            assert str(course_id) in result["message"]

    @pytest.mark.asyncio
    async def test_unenroll_direct_route_not_found(
        self, test_db: AsyncSession, sample_user, sample_course, mock_transactional_db
    ):
        """Direct test of unenroll_user_from_course route function not found."""
        from fastapi_playground_poc.application.web.controller.courses_routes import unenroll_user_from_course
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        with mock_transactional_db:
            with pytest.raises(DomainException) as exc_info:
                await unenroll_user_from_course(
                    sample_user.id, sample_course.id, self.course_service
                )

            assert exc_info.value.domain_error == DomainError.ENROLLMENT_NOTFOUND
            assert "Enrollment not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_courses_direct_route_success(
        self, test_db: AsyncSession, sample_enrollment, mock_transactional_db
    ):
        """Direct test of get_user_courses route function success."""
        from fastapi_playground_poc.application.web.controller.courses_routes import get_user_courses

        with mock_transactional_db:
            user_id = sample_enrollment.user_id

            result = await get_user_courses(user_id, self.course_service)

            assert result.id == user_id
            assert hasattr(result, "courses")
            assert len(result.courses) > 0

    @pytest.mark.asyncio
    async def test_get_user_courses_direct_route_not_found(
        self, test_db: AsyncSession, mock_transactional_db
    ):
        """Direct test of get_user_courses route function not found."""
        from fastapi_playground_poc.application.web.controller.courses_routes import get_user_courses

        with mock_transactional_db:
            with pytest.raises(HTTPException) as exc_info:
                await get_user_courses(99999, self.course_service)

            assert exc_info.value.status_code == 404
            assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_course_users_direct_route_success(
        self, test_db: AsyncSession, sample_enrollment, mock_transactional_db
    ):
        """Direct test of get_course_users route function success."""
        from fastapi_playground_poc.application.web.controller.courses_routes import get_course_users

        with mock_transactional_db:
            course_id = sample_enrollment.course_id

            result = await get_course_users(course_id, self.course_service)

            assert result.id == course_id
            assert hasattr(result, "users")
            assert len(result.users) > 0

    @pytest.mark.asyncio
    async def test_get_course_users_direct_route_not_found(
        self, test_db: AsyncSession, mock_transactional_db
    ):
        """Direct test of get_course_users route function not found."""
        from fastapi_playground_poc.application.web.controller.courses_routes import get_course_users

        with mock_transactional_db:
            with pytest.raises(HTTPException) as exc_info:
                await get_course_users(99999, self.course_service)

            assert exc_info.value.status_code == 404
            assert "Course not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_duplicate_enrollment_direct_route(
        self, test_db: AsyncSession, sample_enrollment, mock_transactional_db
    ):
        """Direct test of duplicate enrollment through route function."""
        from fastapi_playground_poc.application.web.controller.courses_routes import enroll_user_in_course
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        with mock_transactional_db:
            user_id = sample_enrollment.user_id
            course_id = sample_enrollment.course_id

            with pytest.raises(DomainException) as exc_info:
                await enroll_user_in_course(user_id, course_id, self.course_service)

            assert (
                exc_info.value.domain_error == DomainError.DUPLICATE_ENROLLMENT_ATTEMPT
            )
            assert "already enrolled" in str(exc_info.value)

    @pytest.mark.unit
    async def test_get_course_users_success(
        self, sample_enrollment, mock_transactional_db
    ):
        """Test get_course_users method with course that has enrollments."""
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            result = await self.course_service.get_course_users(course_id)

        assert result is not None
        assert result.id == course_id
        assert hasattr(result, "name")
        assert hasattr(result, "author_name")
        assert hasattr(result, "users")
        assert hasattr(result, "price")
        assert isinstance(result.users, list)
        assert len(result.users) >= 1

    @pytest.mark.unit
    async def test_get_course_users_course_not_found(self, mock_transactional_db):
        """Test get_course_users method with non-existent course."""
        non_existent_course_id = 99999

        with mock_transactional_db:
            result = await self.course_service.get_course_users(non_existent_course_id)

        assert result is None
