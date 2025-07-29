"""
Tests for enrollment-related API endpoints.

This module tests all enrollment operations including:
- Enrolling users in courses
- Unenrolling users from courses
- Retrieving user courses
- Retrieving course users
- Error handling for enrollment edge cases
- Duplicate enrollment prevention
"""

import pytest
from fastapi.testclient import TestClient


class TestEnrollmentEndpoints:
    """Test class for enrollment-related endpoints."""

    @pytest.mark.unit
    def test_enroll_user_in_course_success(
        self, test_client: TestClient, sample_user, sample_course, mock_transactional_db
    ):
        """Test successful user enrollment in a course."""
        user_id = sample_user.id
        course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.post(f"/user/{user_id}/enroll/{course_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == user_id
        assert data["course_id"] == course_id
        assert "id" in data
        assert "enrollment_date" in data
        assert isinstance(data["id"], int)

    @pytest.mark.unit
    def test_enroll_user_nonexistent_user(
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
        assert "message" in data
        assert "USER_NOT_FOUND" in data["error_code"]
        assert "does not exist" in data["detail"].lower()

    @pytest.mark.unit
    def test_enroll_user_nonexistent_course(
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
        assert "message" in data
        assert "COURSE_NOT_FOUND" in data["error_code"]
        assert "does not exist" in data["detail"].lower()

    @pytest.mark.unit
    def test_enroll_user_duplicate_enrollment(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test duplicate enrollment prevention."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        # Try to enroll the same user in the same course again
        with mock_transactional_db:
            response = test_client.post(f"/user/{user_id}/enroll/{course_id}")

        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "message" in data
        assert "DUPLICATE_ENROLLMENT_ATTEMPT" in data["error_code"]
        assert "already enrolled" in data["detail"].lower()

    @pytest.mark.unit
    def test_unenroll_user_from_course_success(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test successful user unenrollment from a course."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert str(user_id) in data["message"]
        assert str(course_id) in data["message"]

    @pytest.mark.unit
    def test_unenroll_user_nonexistent_enrollment(
        self, test_client: TestClient, sample_user, sample_course, mock_transactional_db
    ):
        """Test unenrollment when enrollment doesn't exist."""
        user_id = sample_user.id
        course_id = sample_course.id

        # Try to unenroll without existing enrollment
        with mock_transactional_db:
            response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")

        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert "ENROLLMENT_NOTFOUND" in data["error_code"]
        assert "enrollment not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_user_courses_no_enrollments(
        self, test_client: TestClient, sample_user, mock_transactional_db
    ):
        """Test retrieving user courses when user has no enrollments."""
        user_id = sample_user.id

        with mock_transactional_db:
            response = test_client.get(f"/user/{user_id}/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == user_id
        assert data["name"] == sample_user.name
        assert "courses" in data
        assert isinstance(data["courses"], list)
        assert len(data["courses"]) == 0

    @pytest.mark.unit
    def test_get_user_courses_with_enrollments(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test retrieving user courses when user has enrollments."""
        user_id = sample_enrollment.user_id

        with mock_transactional_db:
            response = test_client.get(f"/user/{user_id}/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == user_id
        assert "courses" in data
        assert isinstance(data["courses"], list)
        assert len(data["courses"]) == 1

        # Verify course data
        course = data["courses"][0]
        assert course["id"] == sample_enrollment.course_id
        assert "name" in course
        assert "author_name" in course
        assert "price" in course

    @pytest.mark.unit
    def test_get_user_courses_nonexistent_user(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test retrieving courses for non-existent user."""
        non_existent_user_id = 99999

        with mock_transactional_db:
            response = test_client.get(f"/user/{non_existent_user_id}/courses")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "user not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_course_users_no_enrollments(
        self, test_client: TestClient, sample_course, mock_transactional_db
    ):
        """Test retrieving course users when course has no enrollments."""
        course_id = sample_course.id

        with mock_transactional_db:
            response = test_client.get(f"/course/{course_id}/users")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == course_id
        assert data["name"] == sample_course.name
        assert "users" in data
        assert isinstance(data["users"], list)
        assert len(data["users"]) == 0

    @pytest.mark.unit
    def test_get_course_users_with_enrollments(
        self, test_client: TestClient, sample_enrollment, mock_transactional_db
    ):
        """Test retrieving course users when course has enrollments."""
        course_id = sample_enrollment.course_id

        with mock_transactional_db:
            response = test_client.get(f"/course/{course_id}/users")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == course_id
        assert "users" in data
        assert isinstance(data["users"], list)
        assert len(data["users"]) == 1

        # Verify user data
        user = data["users"][0]
        assert user["id"] == sample_enrollment.user_id
        assert "name" in user
        assert "user_info" in user

    @pytest.mark.unit
    def test_get_course_users_nonexistent_course(
        self, test_client: TestClient, mock_transactional_db
    ):
        """Test retrieving users for non-existent course."""
        non_existent_course_id = 99999

        with mock_transactional_db:
            response = test_client.get(f"/course/{non_existent_course_id}/users")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "course not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_enrollment_workflow_complete(
        self, test_client: TestClient, sample_user, sample_course, mock_transactional_db
    ):
        """Test complete enrollment workflow: enroll -> verify -> unenroll -> verify."""
        user_id = sample_user.id
        course_id = sample_course.id

        with mock_transactional_db:
            # Step 1: Enroll user in course
            enroll_response = test_client.post(f"/user/{user_id}/enroll/{course_id}")
            assert enroll_response.status_code == 200

            # Step 2: Verify enrollment exists in user courses
            user_courses_response = test_client.get(f"/user/{user_id}/courses")
            assert user_courses_response.status_code == 200
            user_data = user_courses_response.json()
            assert len(user_data["courses"]) == 1
            assert user_data["courses"][0]["id"] == course_id

            # Step 3: Verify enrollment exists in course users
            course_users_response = test_client.get(f"/course/{course_id}/users")
            assert course_users_response.status_code == 200
            course_data = course_users_response.json()
            assert len(course_data["users"]) == 1
            assert course_data["users"][0]["id"] == user_id

            # Step 4: Unenroll user from course
            unenroll_response = test_client.delete(
                f"/user/{user_id}/enroll/{course_id}"
            )
            assert unenroll_response.status_code == 200

            # Step 5: Verify enrollment no longer exists
            user_courses_response = test_client.get(f"/user/{user_id}/courses")
            assert user_courses_response.status_code == 200
            user_data = user_courses_response.json()
            assert len(user_data["courses"]) == 0

            course_users_response = test_client.get(f"/course/{course_id}/users")
            assert course_users_response.status_code == 200
            course_data = course_users_response.json()
            assert len(course_data["users"]) == 0

    @pytest.mark.unit
    def test_multiple_enrollments_same_user(
        self,
        test_client: TestClient,
        sample_user,
        multiple_courses,
        mock_transactional_db,
    ):
        """Test enrolling the same user in multiple courses."""
        user_id = sample_user.id

        with mock_transactional_db:
            # Enroll user in all courses
            for course in multiple_courses:
                response = test_client.post(f"/user/{user_id}/enroll/{course.id}")
                assert response.status_code == 200

            # Verify user has all courses
            response = test_client.get(f"/user/{user_id}/courses")
            assert response.status_code == 200
            data = response.json()

            assert len(data["courses"]) == len(multiple_courses)
            enrolled_course_ids = {course["id"] for course in data["courses"]}
            expected_course_ids = {course.id for course in multiple_courses}
            assert enrolled_course_ids == expected_course_ids

    @pytest.mark.unit
    def test_multiple_enrollments_same_course(
        self,
        test_client: TestClient,
        multiple_users,
        sample_course,
        mock_transactional_db,
    ):
        """Test enrolling multiple users in the same course."""
        course_id = sample_course.id

        with mock_transactional_db:
            # Enroll all users in the course
            for user in multiple_users:
                response = test_client.post(f"/user/{user.id}/enroll/{course_id}")
                assert response.status_code == 200

            # Verify course has all users
            response = test_client.get(f"/course/{course_id}/users")
            assert response.status_code == 200
            data = response.json()

            assert len(data["users"]) == len(multiple_users)
            enrolled_user_ids = {user["id"] for user in data["users"]}
            expected_user_ids = {user.id for user in multiple_users}
            assert enrolled_user_ids == expected_user_ids
