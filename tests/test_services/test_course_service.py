"""
Tests for CourseService class.

This module tests all CourseService methods to ensure they work correctly
with the @Transactional decorator and maintain the same functionality
as the original route implementations.
"""

import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_playground_poc.services.course_service import CourseService
from fastapi_playground_poc.schemas import CourseCreate, CourseUpdate


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
    async def test_get_all_courses_with_data(self, multiple_courses, mock_transactional_db):
        """Test get_all_courses method with existing courses."""
        with mock_transactional_db:
            result = await self.course_service.get_all_courses()
        
        assert isinstance(result, list)
        assert len(result) == len(multiple_courses)
        
        # Verify all courses have proper data
        for course in result:
            assert hasattr(course, 'name')
            assert hasattr(course, 'author_name')
            assert hasattr(course, 'price')

    @pytest.mark.unit
    async def test_create_course_success(self, mock_transactional_db):
        """Test create_course method with valid data."""
        course_data = CourseCreate(
            name="Test Course",
            author_name="Test Author",
            price=Decimal("99.99")
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
        update_data = CourseUpdate(
            name="Updated Course Name",
            price=Decimal("199.99")
        )
        
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
            result = await self.course_service.update_course(non_existent_id, update_data)
        
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
    async def test_enroll_user_in_course_success(self, sample_user, sample_course, mock_transactional_db):
        """Test enroll_user_in_course method with valid user and course."""
        user_id = sample_user.id
        course_id = sample_course.id
        
        with mock_transactional_db:
            result = await self.course_service.enroll_user_in_course(user_id, course_id)
        
        assert result is not None
        assert result.user_id == user_id
        assert result.course_id == course_id
        assert hasattr(result, 'enrollment_date')

    @pytest.mark.unit
    async def test_enroll_user_not_found(self, sample_course, mock_transactional_db):
        """Test enroll_user_in_course method with non-existent user."""
        non_existent_user_id = 99999
        course_id = sample_course.id
        
        with mock_transactional_db:
            with pytest.raises(ValueError, match="User not found"):
                await self.course_service.enroll_user_in_course(non_existent_user_id, course_id)

    @pytest.mark.unit
    async def test_enroll_course_not_found(self, sample_user, mock_transactional_db):
        """Test enroll_user_in_course method with non-existent course."""
        user_id = sample_user.id
        non_existent_course_id = 99999
        
        with mock_transactional_db:
            with pytest.raises(ValueError, match="Course not found"):
                await self.course_service.enroll_user_in_course(user_id, non_existent_course_id)

    @pytest.mark.unit
    async def test_enroll_duplicate_enrollment(self, sample_enrollment, mock_transactional_db):
        """Test enroll_user_in_course method with duplicate enrollment."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id
        
        with mock_transactional_db:
            with pytest.raises(ValueError, match="User is already enrolled in the course"):
                await self.course_service.enroll_user_in_course(user_id, course_id)

    @pytest.mark.unit
    async def test_unenroll_user_from_course_success(self, sample_enrollment, mock_transactional_db):
        """Test unenroll_user_from_course method with existing enrollment."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id
        
        with mock_transactional_db:
            result = await self.course_service.unenroll_user_from_course(user_id, course_id)
        
        assert result is True

    @pytest.mark.unit
    async def test_unenroll_enrollment_not_found(self, sample_user, sample_course, mock_transactional_db):
        """Test unenroll_user_from_course method with non-existent enrollment."""
        user_id = sample_user.id
        course_id = sample_course.id
        
        with mock_transactional_db:
            result = await self.course_service.unenroll_user_from_course(user_id, course_id)
        
        assert result is False

    @pytest.mark.unit
    async def test_get_user_courses_success(self, sample_enrollment, mock_transactional_db):
        """Test get_user_courses method with user who has enrollments."""
        user_id = sample_enrollment.user_id
        
        with mock_transactional_db:
            result = await self.course_service.get_user_courses(user_id)
        
        assert result is not None
        assert result["id"] == user_id
        assert "name" in result
        assert "user_info" in result
        assert "courses" in result
        assert isinstance(result["courses"], list)
        assert len(result["courses"]) >= 1

    @pytest.mark.unit
    async def test_get_user_courses_user_not_found(self, mock_transactional_db):
        """Test get_user_courses method with non-existent user."""
        non_existent_user_id = 99999
        
        with mock_transactional_db:
            result = await self.course_service.get_user_courses(non_existent_user_id)
        
        assert result is None

    @pytest.mark.unit
    async def test_get_course_users_success(self, sample_enrollment, mock_transactional_db):
        """Test get_course_users method with course that has enrollments."""
        course_id = sample_enrollment.course_id
        
        with mock_transactional_db:
            result = await self.course_service.get_course_users(course_id)
        
        assert result is not None
        assert result["id"] == course_id
        assert "name" in result
        assert "author_name" in result
        assert "price" in result
        assert "users" in result
        assert isinstance(result["users"], list)
        assert len(result["users"]) >= 1

    @pytest.mark.unit
    async def test_get_course_users_course_not_found(self, mock_transactional_db):
        """Test get_course_users method with non-existent course."""
        non_existent_course_id = 99999
        
        with mock_transactional_db:
            result = await self.course_service.get_course_users(non_existent_course_id)
        
        assert result is None