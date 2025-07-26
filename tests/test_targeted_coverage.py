"""
Targeted tests to ensure service layer operations through routes using common test infrastructure.
These tests are intentionally simple and direct to ensure we hit specific service layer code paths.
"""

import pytest
from fastapi.testclient import TestClient


class TestTargetedServiceCoverage:
    """Tests specifically targeting service layer operations through route handlers."""

    @pytest.mark.unit
    def test_course_creation_refresh_lines_39_40(self, test_client: TestClient, mock_transactional_db):
        """Test course creation through CourseService."""
        with mock_transactional_db:
            response = test_client.post("/course", json={
                "name": "Target Course",
                "author_name": "Target Author",
                "price": "99.99"
            })
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            # This exercises CourseService.create_course operation

    @pytest.mark.unit
    def test_get_course_not_found_lines_51_52(self, test_client: TestClient, mock_transactional_db):
        """Test course not found through CourseService."""
        with mock_transactional_db:
            response = test_client.get("/course/99999")
            assert response.status_code == 404
            # This exercises CourseService.get_course returning None

    @pytest.mark.unit
    def test_get_all_courses_lines_61_62(self, test_client: TestClient, sample_course, mock_transactional_db):
        """Test get all courses through CourseService."""
        with mock_transactional_db:
            response = test_client.get("/courses")
            assert response.status_code == 200
            # This exercises CourseService.get_all_courses operation

    @pytest.mark.unit
    def test_update_course_lines_72_84(self, test_client: TestClient, sample_course, mock_transactional_db):
        """Test course update through CourseService."""
        with mock_transactional_db:
            course_id = sample_course.id
            response = test_client.put(f"/course/{course_id}", json={
                "name": "Updated Course"
            })
            assert response.status_code == 200
            # This exercises CourseService.update_course operation

    @pytest.mark.unit
    def test_update_course_not_found_lines_74_75(self, test_client: TestClient, mock_transactional_db):
        """Test course not found in update through CourseService."""
        with mock_transactional_db:
            response = test_client.put("/course/99999", json={"name": "Updated"})
            assert response.status_code == 404
            # This exercises CourseService.update_course returning None

    @pytest.mark.unit
    def test_delete_course_lines_92_100(self, test_client: TestClient, sample_course, mock_transactional_db):
        """Test course deletion through CourseService."""
        with mock_transactional_db:
            course_id = sample_course.id
            response = test_client.delete(f"/course/{course_id}")
            assert response.status_code == 200
            # This exercises CourseService.delete_course operation

    @pytest.mark.unit
    def test_delete_course_not_found_lines_94_95(self, test_client: TestClient, mock_transactional_db):
        """Test course not found in delete through CourseService."""
        with mock_transactional_db:
            response = test_client.delete("/course/99999")
            assert response.status_code == 404
            # This exercises CourseService.delete_course returning False

    @pytest.mark.unit
    def test_enroll_user_not_found_lines_112_113(self, test_client: TestClient, sample_course, mock_transactional_db):
        """Test user not found in enrollment through CourseService."""
        with mock_transactional_db:
            course_id = sample_course.id
            response = test_client.post(f"/user/99999/enroll/{course_id}")
            assert response.status_code == 404
            # This exercises CourseService.enroll_user_in_course with user not found

    @pytest.mark.unit
    def test_enroll_course_not_found_lines_118_119(self, test_client: TestClient, sample_user, mock_transactional_db):
        """Test course not found in enrollment through CourseService."""
        with mock_transactional_db:
            user_id = sample_user.id
            response = test_client.post(f"/user/{user_id}/enroll/99999")
            assert response.status_code == 404
            # This exercises CourseService.enroll_user_in_course with course not found

    @pytest.mark.unit
    def test_enroll_success_lines_122_133(self, test_client: TestClient, sample_user, sample_course, mock_transactional_db):
        """Test successful enrollment through CourseService."""
        with mock_transactional_db:
            user_id = sample_user.id
            course_id = sample_course.id
            response = test_client.post(f"/user/{user_id}/enroll/{course_id}")
            assert response.status_code == 200
            # This exercises CourseService.enroll_user_in_course operation

    @pytest.mark.unit
    def test_enroll_duplicate_lines_131_132(self, test_client: TestClient, sample_enrollment, mock_transactional_db):
        """Test duplicate enrollment error through CourseService."""
        with mock_transactional_db:
            user_id = sample_enrollment.user_id
            course_id = sample_enrollment.course_id
            response = test_client.post(f"/user/{user_id}/enroll/{course_id}")
            assert response.status_code == 409
            # This exercises CourseService.enroll_user_in_course with IntegrityError

    @pytest.mark.unit
    def test_unenroll_success_lines_147_156(self, test_client: TestClient, sample_enrollment, mock_transactional_db):
        """Test successful unenrollment through CourseService."""
        with mock_transactional_db:
            user_id = sample_enrollment.user_id
            course_id = sample_enrollment.course_id
            response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")
            assert response.status_code == 200
            # This exercises CourseService.unenroll_user_from_course operation

    @pytest.mark.unit
    def test_unenroll_not_found_lines_149_150(self, test_client: TestClient, sample_user, sample_course, mock_transactional_db):
        """Test enrollment not found in unenrollment through CourseService."""
        with mock_transactional_db:
            user_id = sample_user.id
            course_id = sample_course.id
            response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")
            assert response.status_code == 404
            # This exercises CourseService.unenroll_user_from_course returning False

    @pytest.mark.unit
    def test_get_user_courses_lines_166_185(self, test_client: TestClient, sample_enrollment, mock_transactional_db):
        """Test get user courses through CourseService."""
        with mock_transactional_db:
            user_id = sample_enrollment.user_id
            response = test_client.get(f"/user/{user_id}/courses")
            assert response.status_code == 200
            # This exercises CourseService.get_user_courses operation

    @pytest.mark.unit
    def test_get_user_courses_not_found_lines_168_169(self, test_client: TestClient, mock_transactional_db):
        """Test user not found in get courses through CourseService."""
        with mock_transactional_db:
            response = test_client.get("/user/99999/courses")
            assert response.status_code == 404
            # This exercises CourseService.get_user_courses returning None

    @pytest.mark.unit
    def test_get_course_users_lines_193_214(self, test_client: TestClient, sample_enrollment, mock_transactional_db):
        """Test get course users through CourseService."""
        with mock_transactional_db:
            course_id = sample_enrollment.course_id
            response = test_client.get(f"/course/{course_id}/users")
            assert response.status_code == 200
            # This exercises CourseService.get_course_users operation

    @pytest.mark.unit
    def test_get_course_users_not_found_lines_195_196(self, test_client: TestClient, mock_transactional_db):
        """Test course not found in get users through CourseService."""
        with mock_transactional_db:
            response = test_client.get("/course/99999/users")
            assert response.status_code == 404
            # This exercises CourseService.get_course_users returning None


class TestTargetedUserServiceCoverage:
    """Tests specifically targeting service layer operations for user routes."""

    @pytest.mark.unit
    def test_user_creation_refresh_lines_33_40(self, test_client: TestClient, mock_transactional_db):
        """Test user creation through UserService."""
        with mock_transactional_db:
            response = test_client.post("/user", json={
                "name": "Target User",
                "address": "123 Target Street",
                "bio": "Target bio"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["user_info"] is not None
            # This exercises UserService.create_user operation

    @pytest.mark.unit
    def test_get_user_not_found_lines_52_53(self, test_client: TestClient, mock_transactional_db):
        """Test user not found through UserService."""
        with mock_transactional_db:
            response = test_client.get("/user/99999")
            assert response.status_code == 404
            # This exercises UserService.get_user returning None

    @pytest.mark.unit
    def test_get_all_users_lines_63_65(self, test_client: TestClient, sample_user, mock_transactional_db):
        """Test get all users through UserService."""
        with mock_transactional_db:
            response = test_client.get("/users")
            assert response.status_code == 200
            # This exercises UserService.get_all_users operation