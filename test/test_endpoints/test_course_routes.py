from unittest.mock import patch

"""
Tests for course-related API endpoints.

This module tests all course CRUD operations including:
- Creating courses
- Retrieving individual courses with enrolled users
- Retrieving all courses
- Updating courses
- Deleting courses
- Error handling for non-existent courses
"""

from fastapi import HTTPException
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_playground_poc.application.web.dto.schemas import CourseCreate, CourseUpdate


class TestCourseEndpoints:
    """Test class for course-related endpoints."""

    @pytest.mark.unit
    def test_create_course_success(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test successful course creation."""
        course_data = {
            "name": "Advanced Python Programming",
            "author_name": "Dr. Sarah Wilson",
            "price": "199.99",
        }

        with mock_transactional_db:
            response = test_client.post("/course", json=course_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == course_data["name"]
        assert data["author_name"] == course_data["author_name"]
        assert float(data["price"]) == float(course_data["price"])
        assert "id" in data
        assert isinstance(data["id"], int)

    @pytest.mark.unit
    def test_create_course_invalid_data(self, test_client: TestClient):
        """Test course creation with invalid data."""
        # Missing required fields
        invalid_data = {
            "name": "Incomplete Course"
            # Missing author_name and price
        }

        response = test_client.post("/course", json=invalid_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.unit
    def test_create_course_invalid_price(self, test_client: TestClient):
        """Test course creation with invalid price format."""
        invalid_data = {
            "name": "Test Course",
            "author_name": "Test Author",
            "price": "invalid_price",
        }

        response = test_client.post("/course", json=invalid_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.unit
    def test_get_course_by_id_success(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test retrieving a course by ID."""
        course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.get(f"/course/{course_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == course_id
        assert data["name"] == sample_course.name
        assert data["author_name"] == sample_course.author_name
        assert float(data["price"]) == float(sample_course.price)
        assert "users" in data
        assert isinstance(data["users"], list)

    @pytest.mark.unit
    def test_get_course_by_id_not_found(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test retrieving a non-existent course."""
        non_existent_id = 99999

        with mock_transactional_db:
            response = test_client.get(f"/course/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_all_courses_empty(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test retrieving all courses when database is empty."""
        with mock_transactional_db:
            response = test_client.get("/courses")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.unit
    def test_get_all_courses_with_data(
        self, test_client: TestClient, multiple_courses, mock_transactional_db
    ):
        """Test retrieving all courses when courses exist."""
        with mock_transactional_db:
            response = test_client.get("/courses")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == len(multiple_courses)

        # Verify all courses are returned
        for course_data in data:
            assert "id" in course_data
            assert "name" in course_data
            assert "author_name" in course_data
            assert "price" in course_data

    @pytest.mark.unit
    def test_update_course_success(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test successful course update."""
        course_id = sample_course.id
        update_data = {
            "name": "Updated Course Name",
            "price": "299.99",
            # author_name not updated
        }

        with mock_transactional_db:
            response = test_client.put(f"/course/{course_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == course_id
        assert data["name"] == update_data["name"]
        assert float(data["price"]) == float(update_data["price"])
        assert data["author_name"] == sample_course.author_name  # Unchanged

    @pytest.mark.unit
    def test_update_course_partial(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test partial course update (only one field)."""
        course_id = sample_course.id
        update_data = {"price": "149.99"}

        with mock_transactional_db:
            response = test_client.put(f"/course/{course_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == course_id
        assert float(data["price"]) == float(update_data["price"])
        assert data["name"] == sample_course.name  # Unchanged
        assert data["author_name"] == sample_course.author_name  # Unchanged

    @pytest.mark.unit
    def test_update_course_not_found(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test updating a non-existent course."""
        non_existent_id = 99999
        update_data = {"name": "Updated Course"}

        with mock_transactional_db:
            response = test_client.put(f"/course/{non_existent_id}", json=update_data)

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_delete_course_success(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test successful course deletion."""
        course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.delete(f"/course/{course_id}")

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert str(course_id) in data["message"]

            # Verify course is actually deleted
            get_response = test_client.get(f"/course/{course_id}")
            assert get_response.status_code == 404

    @pytest.mark.unit
    def test_delete_course_not_found(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test deleting a non-existent course."""
        non_existent_id = 99999

        with mock_transactional_db:
            response = test_client.delete(f"/course/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_course_price_precision(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test that course prices maintain proper decimal precision."""
        course_data = {
            "name": "Precision Test Course",
            "author_name": "Test Author",
            "price": "123.45",
        }

        with mock_transactional_db:
            response = test_client.post("/course", json=course_data)

        assert response.status_code == 200
        data = response.json()

        # Verify price precision is maintained
        assert data["price"] == "123.45"

    @pytest.mark.unit
    def test_course_data_types(self, test_client: TestClient, mock_transactional_db):
        """Test that course endpoints return correct data types."""
        course_data = {
            "name": "Data Types Test",
            "author_name": "Type Tester",
            "price": "99.99",
        }

        with mock_transactional_db:
            response = test_client.post("/course", json=course_data)

        assert response.status_code == 200
        data = response.json()

        # Verify data types
        assert isinstance(data["id"], int)
        assert isinstance(data["name"], str)
        assert isinstance(data["author_name"], str)
        assert isinstance(data["price"], str)  # Decimal is serialized as string

    @pytest.mark.unit
    def test_course_with_special_characters(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test course creation with special characters."""
        course_data = {
            "name": "Français & Español Programming 🚀",
            "author_name": "José María O'Connor-Smith",
            "price": "199.99",
        }

        with mock_transactional_db:
            response = test_client.post("/course", json=course_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == course_data["name"]
        assert data["author_name"] == course_data["author_name"]

    @pytest.mark.unit
    def test_course_update_empty_data(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test course update with empty data (should not change anything)."""
        course_id = sample_course.id
        original_name = sample_course.name
        original_author = sample_course.author_name
        original_price = sample_course.price

        with mock_transactional_db:
            response = test_client.put(f"/course/{course_id}", json={})

        assert response.status_code == 200
        data = response.json()

        # Verify nothing changed
        assert data["name"] == original_name
        assert data["author_name"] == original_author
        assert float(data["price"]) == float(original_price)


class TestEnrollmentEndpoints:
    """Test class for enrollment/unenrollment endpoints."""

    @pytest.mark.unit
    def test_enroll_user_in_course_success(
        self, test_client: TestClient, sample_user, sample_course, mock_transactional_db
    ):
        """Test successful user enrollment in course."""
        user_id = sample_user.id
        course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.post(f"/user/{user_id}/enroll/{course_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == user_id
        assert data["course_id"] == course_id
        assert "enrollment_date" in data
        assert "id" in data

    @pytest.mark.unit
    def test_enroll_user_not_found(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test enrollment with non-existent user."""
        non_existent_user_id = 99999
        course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.post(
                f"/user/{non_existent_user_id}/enroll/{course_id}"
            )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "message" in data
        assert "USER_NOT_FOUND" in data["error_code"]
        assert "does not exist" in data["detail"].lower()

    @pytest.mark.unit
    def test_enroll_course_not_found(
        self, test_client: TestClient, sample_user, mock_transactional_db
    ):
        """Test enrollment with non-existent course."""
        user_id = sample_user.id
        non_existent_course_id = 99999

        with mock_transactional_db:
            response = test_client.post(
                f"/user/{user_id}/enroll/{non_existent_course_id}"
            )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "message" in data
        assert "COURSE_NOT_FOUND" in data["error_code"]
        assert "does not exist" in data["detail"].lower()

    @pytest.mark.unit
    def test_enroll_duplicate_enrollment(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test duplicate enrollment (should return 409 Conflict)."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        # Try to enroll the same user in the same course again
        with mock_transactional_db:
            response = test_client.post(f"/user/{user_id}/enroll/{course_id}")

        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert "message" in data
        assert "DUPLICATE_ENROLLMENT_ATTEMPT" in data["error_code"]
        assert "already enrolled" in data["detail"].lower()

    @pytest.mark.unit
    def test_unenroll_user_from_course_success(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test successful user unenrollment from course."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert str(user_id) in data["message"]
            assert str(course_id) in data["message"]

            # Verify enrollment is actually deleted by trying to unenroll again
            response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")
            assert response.status_code == 404

    @pytest.mark.unit
    def test_unenroll_enrollment_not_found(
        self, test_client: TestClient, sample_user, sample_course, mock_transactional_db
    ):
        """Test unenrollment when enrollment doesn't exist."""
        user_id = sample_user.id
        course_id = sample_course.id

        # Try to unenroll when no enrollment exists
        with mock_transactional_db:
            response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "message" in data
        assert "ENROLLMENT_NOTFOUND" in data["error_code"]
        assert "enrollment not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_unenroll_nonexistent_user(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test unenrollment with non-existent user (should still check enrollment)."""
        non_existent_user_id = 99999
        course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.delete(
                f"/user/{non_existent_user_id}/enroll/{course_id}"
            )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "enrollment not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_unenroll_nonexistent_course(
        self, test_client: TestClient, sample_user, mock_transactional_db
    ):
        """Test unenrollment with non-existent course (should still check enrollment)."""
        user_id = sample_user.id
        non_existent_course_id = 99999

        with mock_transactional_db:
            response = test_client.delete(
                f"/user/{user_id}/enroll/{non_existent_course_id}"
            )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "enrollment not found" in data["detail"].lower()


class TestCourseUserRelationshipEndpoints:
    """Test class for course-user relationship endpoints."""

    @pytest.mark.unit
    def test_get_user_courses_success(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test retrieving user with enrolled courses."""
        user_id = sample_enrollment.user_id

        with mock_transactional_db:
            response = test_client.get(f"/user/{user_id}/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == user_id
        assert "name" in data
        assert "user_info" in data
        assert "courses" in data
        assert isinstance(data["courses"], list)
        assert len(data["courses"]) == 1
        assert data["courses"][0]["id"] == sample_enrollment.course_id

    @pytest.mark.unit
    def test_get_user_courses_no_enrollments(
        self, test_client: TestClient, sample_user, mock_transactional_db
    ):
        """Test retrieving user with no enrolled courses."""
        user_id = sample_user.id

        with mock_transactional_db:
            response = test_client.get(f"/user/{user_id}/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == user_id
        assert "courses" in data
        assert isinstance(data["courses"], list)
        assert len(data["courses"]) == 0

    @pytest.mark.unit
    def test_get_user_courses_user_not_found(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test retrieving courses for non-existent user."""
        non_existent_user_id = 99999

        with mock_transactional_db:
            response = test_client.get(f"/user/{non_existent_user_id}/courses")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_course_users_success(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test retrieving course with enrolled users."""
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            response = test_client.get(f"/course/{course_id}/users")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == course_id
        assert "name" in data
        assert "author_name" in data
        assert "price" in data
        assert "users" in data
        assert isinstance(data["users"], list)
        assert len(data["users"]) == 1
        assert data["users"][0]["id"] == sample_enrollment.user_id

    @pytest.mark.unit
    def test_get_course_users_no_enrollments(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test retrieving course with no enrolled users."""
        course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.get(f"/course/{course_id}/users")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == course_id
        assert "users" in data
        assert isinstance(data["users"], list)
        assert len(data["users"]) == 0

    @pytest.mark.unit
    def test_get_course_users_course_not_found(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test retrieving users for non-existent course."""
        non_existent_course_id = 99999

        with mock_transactional_db:
            response = test_client.get(f"/course/{non_existent_course_id}/users")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_multiple_enrollments_workflow(
        self, test_client: TestClient, sample_data, mock_transactional_db
    ):
        """Test workflow with multiple users and courses."""
        users = sample_data["users"]
        courses = sample_data["courses"]

        user1_id = users[0].id
        user2_id = users[1].id
        course1_id = courses[0].id
        course2_id = courses[1].id

        with mock_transactional_db:
            # Enroll user1 in course2 (user1 already enrolled in course1 via sample_data)
            response = test_client.post(f"/user/{user1_id}/enroll/{course2_id}")
            assert response.status_code == 200

            # Check user1 courses (should have both courses)
            response = test_client.get(f"/user/{user1_id}/courses")
            assert response.status_code == 200
            data = response.json()
            assert len(data["courses"]) == 2

            # Check course1 users (should have user1 only)
            response = test_client.get(f"/course/{course1_id}/users")
            assert response.status_code == 200
            data = response.json()
            assert len(data["users"]) == 1
            assert data["users"][0]["id"] == user1_id

            # Check course2 users (should have user1 and user2)
            response = test_client.get(f"/course/{course2_id}/users")
            assert response.status_code == 200
            data = response.json()
            assert len(data["users"]) == 2
            user_ids = [user["id"] for user in data["users"]]
            assert user1_id in user_ids
            assert user2_id in user_ids


class TestCourseRoutesCoverageEnhancement:
    """Additional parameterized tests to enhance code coverage for course routes."""

    @pytest.mark.parametrize(
        "course_data,expected_status",
        [
            (
                {"name": "Test Course", "author_name": "Test Author", "price": "99.99"},
                200,
            ),
            (
                {
                    "name": "Course with Special Price",
                    "author_name": "Author",
                    "price": "0.01",
                },
                200,
            ),
            (
                {
                    "name": "High Price Course",
                    "author_name": "Premium Author",
                    "price": "999.99",
                },
                200,
            ),
        ],
    )
    @pytest.mark.unit
    def test_create_course_parameterized(
        self,
        test_client: TestClient,
        course_data,
        expected_status,
        mock_transactional_db,
    ):
        """Test course creation with various valid inputs to hit refresh logic."""
        with mock_transactional_db:
            response = test_client.post("/course", json=course_data)

        assert response.status_code == expected_status
        if expected_status == 200:
            data = response.json()
            assert data["name"] == course_data["name"]
            assert data["author_name"] == course_data["author_name"]
            assert data["price"] == course_data["price"]
            assert "id" in data
            # This hits lines 39-40 (refresh and return)

    @pytest.mark.parametrize(
        "course_id,expected_status,should_have_data",
        [
            (1, 200, True),  # Valid course (assuming sample_course has id=1)
            (99999, 404, False),  # Non-existent course
            (-1, 404, False),  # Invalid negative ID
            (0, 404, False),  # Invalid zero ID
        ],
    )
    @pytest.mark.unit
    def test_get_course_parameterized(
        self,
        test_client: TestClient,
        sample_course,
        course_id,
        expected_status,
        should_have_data,
        mock_transactional_db,
    ):
        """Test get course with various IDs to hit all error paths."""
        # Use actual course ID for valid test case
        if course_id == 1:
            course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.get(f"/course/{course_id}")

        assert response.status_code == expected_status
        data = response.json()

        if should_have_data:
            assert "id" in data
            assert "name" in data
            assert "users" in data
            # This hits lines 49-54 (successful path)
        else:
            assert "detail" in data
            # This hits lines 51-52 (error path)

    @pytest.mark.unit
    def test_get_all_courses_coverage(
        self, test_client: TestClient, multiple_courses, mock_transactional_db
    ):
        """Test get all courses to ensure return logic is covered."""
        with mock_transactional_db:
            response = test_client.get("/courses")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # This hits lines 61-62 (return courses)

    @pytest.mark.parametrize(
        "update_data,expected_status",
        [
            ({"name": "Updated Name"}, 200),
            ({"author_name": "Updated Author"}, 200),
            ({"price": "199.99"}, 200),
            ({"name": "New Name", "price": "299.99"}, 200),
            ({}, 200),  # Empty update should succeed
        ],
    )
    @pytest.mark.unit
    def test_update_course_parameterized(
        self,
        test_client: TestClient,
        sample_course,
        update_data,
        expected_status,
        mock_transactional_db,
    ):
        """Test course updates with various data to hit update logic."""
        course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.put(f"/course/{course_id}", json=update_data)

        assert response.status_code == expected_status
        data = response.json()
        assert data["id"] == course_id
        # This hits lines 72-84 (update logic with refresh)

    @pytest.mark.unit
    def test_update_nonexistent_course_coverage(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test updating non-existent course to hit error path."""
        with mock_transactional_db:
            response = test_client.put("/course/99999", json={"name": "Updated"})

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
        # This hits lines 74-75 (course not found error)

    @pytest.mark.unit
    def test_delete_course_coverage(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test course deletion to hit deletion logic."""
        course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.delete(f"/course/{course_id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert str(course_id) in data["message"]
        # This hits lines 92-100 (delete logic)

    @pytest.mark.unit
    def test_delete_nonexistent_course_coverage(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test deleting non-existent course to hit error path."""
        with mock_transactional_db:
            response = test_client.delete("/course/99999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        # This hits lines 94-95 (course not found in delete)

    @pytest.mark.parametrize(
        "user_exists,course_exists,expect_user_error,expect_course_error",
        [
            (True, True, False, False),  # Both exist - success
            (False, True, True, False),  # User doesn't exist
            (True, False, False, True),  # Course doesn't exist
            (False, False, True, False),  # Neither exists (user checked first)
        ],
    )
    @pytest.mark.unit
    def test_enroll_user_validation_paths(
        self,
        test_client: TestClient,
        sample_user,
        sample_course,
        user_exists,
        course_exists,
        expect_user_error,
        expect_course_error,
        mock_transactional_db,
    ):
        """Test enrollment with various user/course existence scenarios."""
        user_id = sample_user.id if user_exists else 99999
        course_id = sample_course.id if course_exists else 99998

        with mock_transactional_db:
            response = test_client.post(f"/user/{user_id}/enroll/{course_id}")

        if expect_user_error:
            assert response.status_code == 404
            data = response.json()
            assert "does not exist" in data["detail"].lower()
            # This hits lines 112-113 (user not found)
        elif expect_course_error:
            assert response.status_code == 404
            data = response.json()
            assert "does not exist" in data["detail"].lower()
            # This hits lines 118-119 (course not found)
        else:
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == user_id
            assert data["course_id"] == course_id
            # This hits lines 122-133 (successful enrollment)

    @pytest.mark.unit
    def test_enroll_duplicate_integrity_error(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test duplicate enrollment to hit IntegrityError path."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            response = test_client.post(f"/user/{user_id}/enroll/{course_id}")

        assert response.status_code == 409
        data = response.json()
        assert "already enrolled" in data["detail"].lower()
        # This hits lines 131-132 (IntegrityError handling)

    @pytest.mark.unit
    def test_unenroll_user_coverage(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test unenrollment to hit unenroll logic."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert str(user_id) in data["message"]
        assert str(course_id) in data["message"]
        # This hits lines 147-156 (successful unenrollment)

    @pytest.mark.unit
    def test_unenroll_nonexistent_enrollment(
        self, test_client: TestClient, sample_user, sample_course, mock_transactional_db
    ):
        """Test unenrolling when enrollment doesn't exist."""
        user_id = sample_user.id
        course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")

        assert response.status_code == 404
        data = response.json()
        assert "enrollment not found" in data["detail"].lower()
        # This hits lines 149-150 (enrollment not found)

    @pytest.mark.unit
    def test_get_user_courses_coverage(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test get user courses to hit user courses logic."""
        user_id = sample_enrollment.user_id

        with mock_transactional_db:
            response = test_client.get(f"/user/{user_id}/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert "courses" in data
        assert len(data["courses"]) > 0
        # This hits lines 166-185 (get user courses logic)

    @pytest.mark.unit
    def test_get_user_courses_user_not_found(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test get user courses with non-existent user."""
        with mock_transactional_db:
            response = test_client.get("/user/99999/courses")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
        # This hits lines 168-169 (user not found in get courses)

    @pytest.mark.unit
    def test_get_course_users_coverage(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test get course users to hit course users logic."""
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            response = test_client.get(f"/course/{course_id}/users")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == course_id
        assert "users" in data
        assert len(data["users"]) > 0
        # This hits lines 193-214 (get course users logic)

    @pytest.mark.unit
    def test_get_course_users_course_not_found(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test get course users with non-existent course."""
        with mock_transactional_db:
            response = test_client.get("/course/99999/users")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
        # This hits lines 195-196 (course not found in get users)

    @pytest.mark.unit
    def test_get_course_not_found(self, test_client, mock_transactional_db):
        with mock_transactional_db:
            response = test_client.get("/course/999")
        assert response.status_code == 404

    @pytest.mark.unit
    def test_create_course_invalid_data(self, test_client, mock_transactional_db):
        with mock_transactional_db:
            response = test_client.post("/course", json={"title": ""})
        assert response.status_code == 422

    @pytest.mark.unit
    def test_enroll_duplicate(
        self, test_client, sample_course, sample_user, mock_transactional_db
    ):
        # Verify user and course exist first
        with mock_transactional_db:
            user_response = test_client.get(f"/user/{sample_user.id}")
            assert user_response.status_code == 200

            course_response = test_client.get(f"/course/{sample_course.id}")
            assert course_response.status_code == 200

            # First enrollment (should succeed)
            response = test_client.post(
                f"/user/{sample_user.id}/enroll/{sample_course.id}", json={}
            )
            assert response.status_code == 200

            # Second enrollment (should fail with 409)
            response = test_client.post(
                f"/user/{sample_user.id}/enroll/{sample_course.id}", json={}
            )
        assert response.status_code == 409

    @pytest.mark.unit
    def test_enroll_transaction_rollback(
        self, test_client, sample_course, sample_user, mock_transactional_db
    ):
        # This test verifies that error handling works by testing error responses
        # Test enrollment with non-existent user (simulates transaction failure scenario)
        with mock_transactional_db:
            response = test_client.post(
                f"/user/99999/enroll/{sample_course.id}", json={}
            )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "does not exist" in data["detail"].lower()

    @pytest.mark.unit
    async def test_get_course_success(
        self, test_client, sample_course, mock_transactional_db
    ):
        """Test get_course method with existing course."""
        course_id = sample_course.id

        with mock_transactional_db:
            result = test_client.get(f"/course/{sample_course.id}")
        data = result.json()
        assert data is not None
        assert data["id"] == course_id
        assert data["name"] == sample_course.name
        assert data["author_name"] == sample_course.author_name
        assert data["price"] == str(sample_course.price)

    @pytest.mark.unit
    def test_get_all_courses_empty_alt(self, test_client, mock_transactional_db):
        """Test get_all_courses endpoint with empty database."""
        with mock_transactional_db:
            result = test_client.get("/courses")

        assert result.status_code == 200
        data = result.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.unit
    def test_get_all_courses_with_data_alt(
        self, test_client, multiple_courses, mock_transactional_db
    ):
        """Test get_all_courses endpoint with existing courses."""
        with mock_transactional_db:
            result = test_client.get("/courses")

        assert result.status_code == 200
        data = result.json()
        assert isinstance(data, list)
        assert len(data) == len(multiple_courses)

        # Verify all courses have proper data
        for course in data:
            assert "name" in course
            assert "author_name" in course
            assert "price" in course

    @pytest.mark.unit
    def test_create_course_success_alt(self, test_client, mock_transactional_db):
        """Test create_course endpoint with valid data."""
        course_data = {
            "name": "Test Course",
            "author_name": "Test Author",
            "price": "99.99",
        }

        with mock_transactional_db:
            result = test_client.post("/course", json=course_data)

        assert result.status_code == 200
        data = result.json()
        assert data is not None
        assert data["name"] == course_data["name"]
        assert data["author_name"] == course_data["author_name"]
        assert data["price"] == course_data["price"]
        assert "id" in data

    @pytest.mark.unit
    def test_update_course_success_alt(
        self, test_client, sample_course, mock_transactional_db
    ):
        """Test update_course endpoint with valid data."""
        course_id = sample_course.id
        update_data = {"name": "Updated Course Name", "price": "199.99"}

        with mock_transactional_db:
            result = test_client.put(f"/course/{course_id}", json=update_data)

        assert result.status_code == 200
        data = result.json()
        assert data is not None
        assert data["id"] == course_id
        assert data["name"] == update_data["name"]
        assert data["price"] == update_data["price"]
        assert data["author_name"] == sample_course.author_name  # Unchanged

    @pytest.mark.unit
    def test_update_course_not_found_alt(self, test_client, mock_transactional_db):
        """Test update_course endpoint with non-existent course."""
        non_existent_id = 99999
        update_data = {"name": "Updated Course"}

        with mock_transactional_db:
            result = test_client.put(f"/course/{non_existent_id}", json=update_data)

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_delete_course_success_alt(
        self, test_client, sample_course, mock_transactional_db
    ):
        """Test delete_course endpoint with existing course."""
        course_id = sample_course.id

        with mock_transactional_db:
            result = test_client.delete(f"/course/{course_id}")

        assert result.status_code == 200
        data = result.json()
        assert "message" in data

    @pytest.mark.unit
    def test_delete_course_not_found_alt(self, test_client, mock_transactional_db):
        """Test delete_course endpoint with non-existent course."""
        non_existent_id = 99999

        with mock_transactional_db:
            result = test_client.delete(f"/course/{non_existent_id}")

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_enroll_user_in_course_success_alt(
        self, test_client, sample_user, sample_course, mock_transactional_db
    ):
        """Test enroll_user_in_course endpoint with valid user and course."""
        user_id = sample_user.id
        course_id = sample_course.id

        with mock_transactional_db:
            result = test_client.post(f"/user/{user_id}/enroll/{course_id}")

        assert result.status_code == 200
        data = result.json()
        assert data is not None
        assert data["user_id"] == user_id
        assert data["course_id"] == course_id
        assert "enrollment_date" in data

    @pytest.mark.unit
    def test_enroll_user_not_found_alt(
        self, test_client, sample_course, mock_transactional_db
    ):
        """Test enroll_user_in_course endpoint with non-existent user."""
        non_existent_user_id = 99999
        course_id = sample_course.id

        with mock_transactional_db:
            result = test_client.post(
                f"/user/{non_existent_user_id}/enroll/{course_id}"
            )

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data
        assert "does not exist" in data["detail"].lower()

    @pytest.mark.unit
    def test_enroll_course_not_found_alt(
        self, test_client, sample_user, mock_transactional_db
    ):
        """Test enroll_user_in_course endpoint with non-existent course."""
        user_id = sample_user.id
        non_existent_course_id = 99999

        with mock_transactional_db:
            result = test_client.post(
                f"/user/{user_id}/enroll/{non_existent_course_id}"
            )

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data
        assert "does not exist" in data["detail"].lower()

    @pytest.mark.unit
    def test_enroll_duplicate_enrollment_alt(
        self, test_client, sample_enrollment, mock_transactional_db
    ):
        """Test enroll_user_in_course endpoint with duplicate enrollment."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            result = test_client.post(f"/user/{user_id}/enroll/{course_id}")

        assert result.status_code == 409
        data = result.json()
        assert "detail" in data
        assert "already enrolled" in data["detail"].lower()

    @pytest.mark.unit
    def test_unenroll_user_from_course_success_alt(
        self, test_client, sample_enrollment, mock_transactional_db
    ):
        """Test unenroll_user_from_course endpoint with existing enrollment."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            result = test_client.delete(f"/user/{user_id}/enroll/{course_id}")

        assert result.status_code == 200
        data = result.json()
        assert "message" in data

    @pytest.mark.unit
    def test_unenroll_enrollment_not_found_alt(
        self, test_client, sample_user, sample_course, mock_transactional_db
    ):
        """Test unenroll_user_from_course endpoint with non-existent enrollment."""
        user_id = sample_user.id
        course_id = sample_course.id

        with mock_transactional_db:
            result = test_client.delete(f"/user/{user_id}/enroll/{course_id}")

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_get_user_courses_success_alt(
        self, test_client, sample_enrollment, mock_transactional_db
    ):
        """Test get_user_courses endpoint with user who has enrollments."""
        user_id = sample_enrollment.user_id

        with mock_transactional_db:
            result = test_client.get(f"/user/{user_id}/courses")

        assert result.status_code == 200
        data = result.json()
        assert data is not None
        assert data["id"] == user_id
        assert "name" in data
        assert "user_info" in data
        assert "courses" in data
        assert isinstance(data["courses"], list)
        assert len(data["courses"]) >= 1

    @pytest.mark.unit
    def test_get_user_courses_user_not_found_alt(
        self, test_client, mock_transactional_db
    ):
        """Test get_user_courses endpoint with non-existent user."""
        non_existent_user_id = 99999

        with mock_transactional_db:
            result = test_client.get(f"/user/{non_existent_user_id}/courses")

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data

    # Direct route function tests for additional coverage
    @pytest.mark.unit
    def test_create_course_direct_route_function(
        self, test_client, mock_transactional_db
    ):
        """Direct test of create_course route function."""
        course_data = {
            "name": "Direct Test Course",
            "author_name": "Direct Author",
            "price": "199.99",
        }

        with mock_transactional_db:
            result = test_client.post("/course", json=course_data)

        assert result.status_code == 200
        data = result.json()
        assert data["name"] == course_data["name"]
        assert data["author_name"] == course_data["author_name"]
        assert data["price"] == course_data["price"]

    @pytest.mark.unit
    def test_get_course_direct_route_success(
        self, test_client, sample_course, mock_transactional_db
    ):
        """Direct test of get_course route function success."""
        with mock_transactional_db:
            result = test_client.get(f"/course/{sample_course.id}")

        assert result.status_code == 200
        data = result.json()
        assert data["id"] == sample_course.id
        assert data["name"] == sample_course.name
        assert "users" in data

    @pytest.mark.unit
    def test_get_course_direct_route_not_found(
        self, test_client, mock_transactional_db
    ):
        """Direct test of get_course route function not found."""
        with mock_transactional_db:
            result = test_client.get("/course/99999")

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_all_courses_direct_route(
        self, test_client, multiple_courses, mock_transactional_db
    ):
        """Direct test of get_all_courses route function."""
        with mock_transactional_db:
            result = test_client.get("/courses")

        assert result.status_code == 200
        data = result.json()
        assert isinstance(data, list)
        assert len(data) == len(multiple_courses)

    @pytest.mark.unit
    def test_update_course_direct_route_success(
        self, test_client, sample_course, mock_transactional_db
    ):
        """Direct test of update_course route function success."""
        update_data = {"name": "Updated Direct Course", "price": "299.99"}

        with mock_transactional_db:
            result = test_client.put(f"/course/{sample_course.id}", json=update_data)

        assert result.status_code == 200
        data = result.json()
        assert data["id"] == sample_course.id
        assert data["name"] == update_data["name"]
        assert data["price"] == update_data["price"]

    @pytest.mark.unit
    def test_update_course_direct_route_not_found(
        self, test_client, mock_transactional_db
    ):
        """Direct test of update_course route function not found."""
        update_data = {"name": "Updated"}

        with mock_transactional_db:
            result = test_client.put("/course/99999", json=update_data)

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_delete_course_direct_route_success(
        self, test_client, sample_course, mock_transactional_db
    ):
        """Direct test of delete_course route function success."""
        course_id = sample_course.id

        with mock_transactional_db:
            result = test_client.delete(f"/course/{course_id}")

        assert result.status_code == 200
        data = result.json()
        assert "message" in data
        assert str(course_id) in data["message"]

    @pytest.mark.unit
    def test_delete_course_direct_route_not_found(
        self, test_client, mock_transactional_db
    ):
        """Direct test of delete_course route function not found."""
        with mock_transactional_db:
            result = test_client.delete("/course/99999")

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_enroll_user_direct_route_success(
        self, test_client, sample_user, sample_course, mock_transactional_db
    ):
        """Direct test of enroll_user_in_course route function success."""
        with mock_transactional_db:
            result = test_client.post(
                f"/user/{sample_user.id}/enroll/{sample_course.id}"
            )

        assert result.status_code == 200
        data = result.json()
        assert data["user_id"] == sample_user.id
        assert data["course_id"] == sample_course.id
        assert "enrollment_date" in data

    @pytest.mark.unit
    def test_enroll_user_direct_route_user_not_found(
        self, test_client, sample_course, mock_transactional_db
    ):
        """Direct test of enroll_user_in_course route function user not found."""
        with mock_transactional_db:
            result = test_client.post(f"/user/99999/enroll/{sample_course.id}")

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data
        assert "does not exist" in data["detail"].lower()

    @pytest.mark.unit
    def test_enroll_course_direct_route_not_found(
        self, test_client, sample_user, mock_transactional_db
    ):
        """Direct test of enroll_user_in_course route function course not found."""
        with mock_transactional_db:
            result = test_client.post(f"/user/{sample_user.id}/enroll/99999")

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data
        assert "does not exist" in data["detail"].lower()

    @pytest.mark.unit
    def test_unenroll_direct_route_success(
        self, test_client, sample_enrollment, mock_transactional_db
    ):
        """Direct test of unenroll_user_from_course route function success."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            result = test_client.delete(f"/user/{user_id}/enroll/{course_id}")

        assert result.status_code == 200
        data = result.json()
        assert "message" in data
        assert str(user_id) in data["message"]
        assert str(course_id) in data["message"]

    @pytest.mark.unit
    def test_unenroll_direct_route_not_found(
        self, test_client, sample_user, sample_course, mock_transactional_db
    ):
        """Direct test of unenroll_user_from_course route function not found."""
        with mock_transactional_db:
            result = test_client.delete(
                f"/user/{sample_user.id}/enroll/{sample_course.id}"
            )

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data
        assert "enrollment not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_user_courses_direct_route_success(
        self, test_client, sample_enrollment, mock_transactional_db
    ):
        """Direct test of get_user_courses route function success."""
        user_id = sample_enrollment.user_id

        with mock_transactional_db:
            result = test_client.get(f"/user/{user_id}/courses")

        assert result.status_code == 200
        data = result.json()
        assert data["id"] == user_id
        assert "courses" in data
        assert len(data["courses"]) > 0

    @pytest.mark.unit
    def test_get_user_courses_direct_route_not_found(
        self, test_client, mock_transactional_db
    ):
        """Direct test of get_user_courses route function not found."""
        with mock_transactional_db:
            result = test_client.get("/user/99999/courses")

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_course_users_direct_route_success(
        self, test_client, sample_enrollment, mock_transactional_db
    ):
        """Direct test of get_course_users route function success."""
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            result = test_client.get(f"/course/{course_id}/users")

        assert result.status_code == 200
        data = result.json()
        assert data["id"] == course_id
        assert "users" in data
        assert len(data["users"]) > 0

    @pytest.mark.unit
    def test_get_course_users_direct_route_not_found(
        self, test_client, mock_transactional_db
    ):
        """Direct test of get_course_users route function not found."""
        with mock_transactional_db:
            result = test_client.get("/course/99999/users")

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_duplicate_enrollment_direct_route(
        self, test_client, sample_enrollment, mock_transactional_db
    ):
        """Direct test of duplicate enrollment through route function."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            result = test_client.post(f"/user/{user_id}/enroll/{course_id}")

        assert result.status_code == 409
        data = result.json()
        assert "detail" in data
        assert "already enrolled" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_course_users_success_endpoint(
        self, test_client, sample_enrollment, mock_transactional_db
    ):
        """Test get_course_users endpoint with course that has enrollments."""
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            result = test_client.get(f"/course/{course_id}/users")

        assert result.status_code == 200
        data = result.json()
        assert data is not None
        assert data["id"] == course_id
        assert "name" in data
        assert "author_name" in data
        assert "price" in data
        assert "users" in data
        assert isinstance(data["users"], list)
        assert len(data["users"]) >= 1

    @pytest.mark.unit
    def test_get_course_users_course_not_found_endpoint(
        self, test_client, mock_transactional_db
    ):
        """Test get_course_users endpoint with non-existent course."""
        non_existent_course_id = 99999

        with mock_transactional_db:
            result = test_client.get(f"/course/{non_existent_course_id}/users")

        assert result.status_code == 404
        data = result.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_delete_course_not_found_error_handling(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test error handling in delete_course when course is not found."""
        with mock_transactional_db:
            response = test_client.delete("/course/99999")
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "Course not found" in data["detail"]

    @pytest.mark.unit
    def test_enroll_user_in_course_none_enrollment(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test error handling when enrollment is None."""
        # Mock the service to return None
        with patch(
            "fastapi_playground_poc.application.web.service.course_service.CourseService.enroll_user_in_course"
        ) as mock_service:
            mock_service.return_value = None

            with mock_transactional_db:
                response = test_client.post(f"/user/1/enroll/{sample_course.id}")
                assert response.status_code == 404
                data = response.json()
                assert "detail" in data
                assert "User or course not found" in data["detail"]

    @pytest.mark.unit
    def test_enroll_user_in_course_user_not_found_error(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test error handling for user not found ValueError."""
        # Mock the service to raise DomainException with "user not found" message
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        with patch(
            "fastapi_playground_poc.application.web.service.course_service.CourseService.enroll_user_in_course"
        ) as mock_service:
            mock_service.side_effect = DomainException(
                DomainError.USER_NOT_FOUND, "User with id 1 does not exist"
            )

            with mock_transactional_db:
                response = test_client.post(f"/user/1/enroll/{sample_course.id}")
                assert response.status_code == 404
                data = response.json()
                assert "detail" in data
                assert "does not exist" in data["detail"].lower()

    @pytest.mark.unit
    def test_enroll_user_in_course_course_not_found_error(
        self, test_client: TestClient, sample_user, mock_transactional_db
    ):
        """Test error handling for course not found ValueError."""
        # Mock the service to raise DomainException with "course not found" message
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        with patch(
            "fastapi_playground_poc.application.web.service.course_service.CourseService.enroll_user_in_course"
        ) as mock_service:
            mock_service.side_effect = DomainException(
                DomainError.COURSE_NOT_FOUND, "Course with id 99999 does not exist"
            )

            with mock_transactional_db:
                response = test_client.post(f"/user/{sample_user.id}/enroll/99999")
                assert response.status_code == 404
                data = response.json()
                assert "detail" in data
                assert "does not exist" in data["detail"].lower()

    @pytest.mark.unit
    def test_enroll_user_in_course_already_enrolled_error(
        self, test_client: TestClient, sample_user, sample_course, mock_transactional_db
    ):
        """Test error handling for already enrolled ValueError."""
        # Mock the service to raise DomainException with "already enrolled" message
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        with patch(
            "fastapi_playground_poc.application.web.service.course_service.CourseService.enroll_user_in_course"
        ) as mock_service:
            mock_service.side_effect = DomainException(
                DomainError.DUPLICATE_ENROLLMENT_ATTEMPT,
                "User is already enrolled in the course",
            )

            with mock_transactional_db:
                response = test_client.post(
                    f"/user/{sample_user.id}/enroll/{sample_course.id}"
                )
                assert response.status_code == 409
                data = response.json()
                assert "detail" in data
                assert "already enrolled" in data["detail"].lower()

    @pytest.mark.unit
    def test_enroll_user_in_course_other_value_error(
        self, test_client: TestClient, sample_user, sample_course, mock_transactional_db
    ):
        """Test error handling for other ValueError cases."""
        # Mock the service to raise DomainException with a validation error
        from fastapi_playground_poc.domain.exceptions import (
            DomainException,
            DomainError,
        )

        with patch(
            "fastapi_playground_poc.application.web.service.course_service.CourseService.enroll_user_in_course"
        ) as mock_service:
            mock_service.side_effect = DomainException(
                DomainError.INVALID_ARGUMENT, "Some validation error"
            )

            with mock_transactional_db:
                response = test_client.post(
                    f"/user/{sample_user.id}/enroll/{sample_course.id}"
                )
                assert response.status_code == 400
                data = response.json()
                assert "detail" in data
                assert "validation error" in data["detail"].lower()
