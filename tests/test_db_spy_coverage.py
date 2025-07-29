"""
Tests using database spying to increase coverage for service layer operations.

This module creates spy objects for service methods and database sessions to verify that
specific operations are called, ensuring service layer code paths are properly tested
with the @Transactional decorator infrastructure.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_playground_poc.models.User import User
from fastapi_playground_poc.models.UserInfo import UserInfo
from fastapi_playground_poc.models.Course import Course
from fastapi_playground_poc.models.Enrollment import Enrollment
from fastapi_playground_poc.services.course_service import CourseService
from fastapi_playground_poc.services.user_service import UserService


class TestCourseServiceWithDbSpy:
    """Test course service operations with database spying to increase coverage."""

    @pytest.mark.unit
    def test_create_course_with_db_refresh_spy(
        self, test_client: TestClient, mock_transactional_db, mocker
    ):
        """Test course creation with spy to verify db.refresh is called."""
        with mock_transactional_db:
            # Spy on the database session's refresh method
            refresh_spy = mocker.spy(AsyncSession, "refresh")

            course_data = {
                "name": "Spy Test Course",
                "author_name": "Dr. Spy",
                "price": "99.99",
            }

            response = test_client.post("/course", json=course_data)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == course_data["name"]

            # Verify that db.refresh was called at least once
            assert refresh_spy.call_count >= 1
            # This tests the db.refresh call in the course creation logic

    @pytest.mark.unit
    def test_get_course_with_db_query_spy(
        self, test_client: TestClient, sample_course, mock_transactional_db, mocker
    ):
        """Test get course with spy to verify database queries."""
        with mock_transactional_db:
            # Spy on select method to verify database queries
            execute_spy = mocker.spy(AsyncSession, "execute")

            response = test_client.get(f"/course/{sample_course.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_course.id

            # Verify that database execute method was called
            assert execute_spy.call_count >= 1
            # This tests the select query execution path

    @pytest.mark.unit
    def test_update_course_with_db_refresh_spy(
        self, test_client: TestClient, sample_course, mock_transactional_db, mocker
    ):
        """Test course update with spy to verify db.refresh is called."""
        with mock_transactional_db:
            refresh_spy = mocker.spy(AsyncSession, "refresh")
            commit_spy = mocker.spy(AsyncSession, "commit")

            update_data = {"name": "Updated Course Name via Spy"}

            response = test_client.put(f"/course/{sample_course.id}", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == update_data["name"]

            # Verify database operations were called
            assert refresh_spy.call_count >= 1
            assert commit_spy.call_count >= 1
            # This tests the update and refresh logic

    @pytest.mark.unit
    def test_delete_course_with_db_operations_spy(
        self, test_client: TestClient, sample_course, mock_transactional_db, mocker
    ):
        """Test course deletion with spy to verify database operations."""
        with mock_transactional_db:
            delete_spy = mocker.spy(AsyncSession, "delete")
            commit_spy = mocker.spy(AsyncSession, "commit")

            response = test_client.delete(f"/course/{sample_course.id}")

            assert response.status_code == 200
            data = response.json()
            assert "message" in data

            # Verify delete and commit were called
            assert delete_spy.call_count >= 1
            assert commit_spy.call_count >= 1
            # This tests the deletion logic

    @pytest.mark.unit
    def test_enroll_user_with_db_operations_spy(
        self,
        test_client: TestClient,
        sample_user,
        sample_course,
        mock_transactional_db,
        mocker,
    ):
        """Test user enrollment with comprehensive database spying."""
        with mock_transactional_db:
            add_spy = mocker.spy(AsyncSession, "add")
            commit_spy = mocker.spy(AsyncSession, "commit")
            refresh_spy = mocker.spy(AsyncSession, "refresh")
            execute_spy = mocker.spy(AsyncSession, "execute")

            response = test_client.post(
                f"/user/{sample_user.id}/enroll/{sample_course.id}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == sample_user.id
            assert data["course_id"] == sample_course.id

            # Verify all database operations
            assert add_spy.call_count >= 1  # Adding enrollment
            assert commit_spy.call_count >= 1  # Committing transaction
            assert refresh_spy.call_count >= 1  # Refreshing enrollment
            assert execute_spy.call_count >= 1  # User/course existence checks
            # This tests enrollment creation and validation logic

    @pytest.mark.unit
    def test_get_course_users_with_db_spy(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db, mocker
    ):
        """Test get course users with database spying."""
        with mock_transactional_db:
            execute_spy = mocker.spy(AsyncSession, "execute")

            response = test_client.get(f"/course/{sample_enrollment.course_id}/users")

            assert response.status_code == 200
            data = response.json()
            assert "users" in data
            assert len(data["users"]) > 0

            # Verify database queries were executed
            assert execute_spy.call_count >= 1
            # This tests the complex query for course with users

    @pytest.mark.unit
    def test_get_user_courses_with_db_spy(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db, mocker
    ):
        """Test get user courses with database spying."""
        with mock_transactional_db:
            execute_spy = mocker.spy(AsyncSession, "execute")

            response = test_client.get(f"/user/{sample_enrollment.user_id}/courses")

            assert response.status_code == 200
            data = response.json()
            assert "courses" in data
            assert len(data["courses"]) > 0

            # Verify database queries were executed
            assert execute_spy.call_count >= 1
            # This tests the complex query for user with courses


class TestUserServiceWithDbSpy:
    """Test user service operations with database spying to increase coverage."""

    @pytest.mark.unit
    def test_create_user_with_db_operations_spy(
        self, test_client: TestClient, mock_transactional_db, mocker
    ):
        """Test user creation with spy to verify database operations."""
        with mock_transactional_db:
            add_spy = mocker.spy(AsyncSession, "add")
            commit_spy = mocker.spy(AsyncSession, "commit")
            execute_spy = mocker.spy(AsyncSession, "execute")

            user_data = {
                "name": "Spy Test User",
                "address": "123 Spy Street",
                "bio": "Testing with database spy",
            }

            response = test_client.post("/user", json=user_data)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == user_data["name"]
            assert data["user_info"]["address"] == user_data["address"]

            # Verify database operations (user creation uses cascade, so only 1 add call)
            assert add_spy.call_count >= 1  # User (UserInfo saved via cascade)
            assert commit_spy.call_count >= 1  # Commit transaction
            assert (
                execute_spy.call_count >= 1
            )  # Select query to load user with user_info
            # This tests the user creation with cascade and selectinload logic

    @pytest.mark.unit
    def test_get_user_with_db_query_spy(
        self, test_client: TestClient, sample_user, mock_transactional_db, mocker
    ):
        """Test get user with spy to verify database queries."""
        with mock_transactional_db:
            execute_spy = mocker.spy(AsyncSession, "execute")

            response = test_client.get(f"/user/{sample_user.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_user.id
            assert data["user_info"] is not None

            # Verify database query was executed
            assert execute_spy.call_count >= 1
            # This tests the select query with selectinload for user_info

    @pytest.mark.unit
    def test_get_all_users_with_db_spy(
        self, test_client: TestClient, multiple_users, mock_transactional_db, mocker
    ):
        """Test get all users with database spying."""
        with mock_transactional_db:
            execute_spy = mocker.spy(AsyncSession, "execute")

            response = test_client.get("/users")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

            # Verify database query was executed
            assert execute_spy.call_count >= 1
            # This tests the select all users with user_info logic


class TestServiceTransactionSpying:
    """Test service layer transaction behavior with spying."""

    @pytest.mark.unit
    def test_enrollment_transaction_with_error_handling(
        self, test_client: TestClient, sample_user, mock_transactional_db, mocker
    ):
        """Test enrollment with non-existent course to verify error handling."""
        with mock_transactional_db:
            execute_spy = mocker.spy(AsyncSession, "execute")

            # Try to enroll in non-existent course
            response = test_client.post(f"/user/{sample_user.id}/enroll/99999")

            assert response.status_code == 404
            data = response.json()
            assert "message" in data
            assert "COURSE_NOT_FOUND" in data["error_code"]

            # Verify database operations
            assert execute_spy.call_count >= 1  # Course existence check
            # Error handling is now managed by service layer and @Transactional decorator

    @pytest.mark.unit
    def test_user_creation_database_operations_comprehensive_spy(
        self, test_client: TestClient, mock_transactional_db, mocker
    ):
        """Comprehensive test of all database operations during user creation."""
        with mock_transactional_db:
            # Spy on all relevant database methods
            add_spy = mocker.spy(AsyncSession, "add")
            commit_spy = mocker.spy(AsyncSession, "commit")
            execute_spy = mocker.spy(AsyncSession, "execute")

            user_data = {
                "name": "Comprehensive Spy User",
                "address": "456 Database Ave",
                "bio": "Testing all database operations",
            }

            response = test_client.post("/user", json=user_data)

            assert response.status_code == 200
            data = response.json()
            assert data["user_info"]["address"] == user_data["address"]

            # Verify comprehensive database operations (cascade relationship means only 1 add call)
            assert add_spy.call_count >= 1  # User object (UserInfo saved via cascade)
            assert commit_spy.call_count >= 1  # Final commit
            assert execute_spy.call_count >= 1  # Query to return user with user_info
            # This tests the complete user creation workflow with cascade

    @pytest.mark.unit
    def test_course_update_with_attribute_spying(
        self, test_client: TestClient, sample_course, mock_transactional_db, mocker
    ):
        """Test course update with spying on attribute changes."""
        with mock_transactional_db:
            commit_spy = mocker.spy(AsyncSession, "commit")
            refresh_spy = mocker.spy(AsyncSession, "refresh")

            original_name = sample_course.name
            update_data = {"name": "Spy Updated Course Name", "price": "199.99"}

            response = test_client.put(f"/course/{sample_course.id}", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == update_data["name"]
            assert data["name"] != original_name

            # Verify database operations for update
            assert commit_spy.call_count >= 1
            assert refresh_spy.call_count >= 1
            # This tests the course update and refresh logic

    @pytest.mark.unit
    def test_unenroll_with_db_operations_spy(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db, mocker
    ):
        """Test unenrollment with database operation spying."""
        with mock_transactional_db:
            delete_spy = mocker.spy(AsyncSession, "delete")
            commit_spy = mocker.spy(AsyncSession, "commit")
            execute_spy = mocker.spy(AsyncSession, "execute")

            user_id = sample_enrollment.user_id
            course_id = sample_enrollment.course_id

            response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")

            assert response.status_code == 200
            data = response.json()
            assert str(user_id) in data["message"]
            assert str(course_id) in data["message"]

            # Verify database operations
            assert execute_spy.call_count >= 1  # Query to find enrollment
            assert delete_spy.call_count >= 1  # Delete enrollment
            assert commit_spy.call_count >= 1  # Commit deletion
            # This tests the unenrollment logic

    @pytest.mark.unit
    def test_error_handling_with_db_spy(
        self, test_client: TestClient, mock_transactional_db, mocker
    ):
        """Test error handling paths with database spying."""
        with mock_transactional_db:
            execute_spy = mocker.spy(AsyncSession, "execute")

            # Test non-existent user
            response = test_client.get("/user/99999")
            assert response.status_code == 404

            # Test non-existent course
            response = test_client.get("/course/99999")
            assert response.status_code == 404

            # Verify database queries were attempted
            assert execute_spy.call_count >= 2
            # This tests error handling paths where database is queried but no results found


class TestServiceLayerCoverageTargets:
    """Tests specifically targeting service layer operations for coverage."""

    @pytest.mark.unit
    def test_course_creation_refresh_logic(
        self, test_client: TestClient, mock_transactional_db, mocker
    ):
        """Test to specifically target service layer course creation logic."""
        with mock_transactional_db:
            refresh_spy = mocker.spy(AsyncSession, "refresh")

            course_data = {
                "name": "Target Coverage Course",
                "author_name": "Coverage Author",
                "price": "149.99",
            }

            response = test_client.post("/course", json=course_data)

            assert response.status_code == 200
            data = response.json()
            assert "id" in data

            # Verify refresh was called in service layer
            assert refresh_spy.call_count >= 1
            # This tests the service layer course creation logic

    @pytest.mark.unit
    def test_user_creation_select_query_with_refresh(
        self, test_client: TestClient, mock_transactional_db, mocker
    ):
        """Test to specifically target service layer user creation logic."""
        with mock_transactional_db:
            execute_spy = mocker.spy(AsyncSession, "execute")

            user_data = {
                "name": "Select Query User",
                "address": "789 Select Street",
                "bio": "Testing select query with selectinload",
            }

            response = test_client.post("/user", json=user_data)

            assert response.status_code == 200
            data = response.json()
            assert data["user_info"] is not None

            # Verify the select query with selectinload was executed
            assert execute_spy.call_count >= 1
            # This tests the service layer user creation logic

    @pytest.mark.unit
    def test_get_all_courses_return_path(
        self, test_client: TestClient, multiple_courses, mock_transactional_db, mocker
    ):
        """Test to specifically target service layer get all courses logic."""
        with mock_transactional_db:
            execute_spy = mocker.spy(AsyncSession, "execute")

            response = test_client.get("/courses")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

            # Verify database query was executed
            assert execute_spy.call_count >= 1
            # This tests the service layer get all courses logic

    @pytest.mark.unit
    def test_get_all_users_return_path(
        self, test_client: TestClient, multiple_users, mock_transactional_db, mocker
    ):
        """Test to specifically target service layer get all users logic."""
        with mock_transactional_db:
            execute_spy = mocker.spy(AsyncSession, "execute")

            response = test_client.get("/users")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

            # Verify database query was executed
            assert execute_spy.call_count >= 1
            # This tests the service layer get all users logic
