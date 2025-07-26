"""
Targeted tests specifically designed to hit missing lines in course and user routes.
These tests are intentionally simple and direct to ensure we hit specific code paths.
"""

import pytest
from fastapi.testclient import TestClient


class TestTargetedCourseCoverage:
    """Tests specifically targeting missing lines in course routes."""

    @pytest.mark.unit
    def test_course_creation_refresh_lines_39_40(self, test_client: TestClient):
        """Test to specifically hit lines 39-40 (refresh and return in course creation)."""
        response = test_client.post("/course", json={
            "name": "Target Course",
            "author_name": "Target Author",
            "price": "99.99"
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        # This should hit lines 39-40 (refresh and return)

    @pytest.mark.unit
    def test_get_course_not_found_lines_51_52(self, test_client: TestClient):
        """Test to specifically hit lines 51-52 (course not found)."""
        response = test_client.get("/course/99999")
        assert response.status_code == 404
        # This should hit lines 51-52 (if course is None, raise HTTPException)

    @pytest.mark.unit
    def test_get_all_courses_lines_61_62(self, test_client: TestClient, sample_course):
        """Test to specifically hit lines 61-62 (return courses)."""
        response = test_client.get("/courses")
        assert response.status_code == 200
        # This should hit lines 61-62 (courses = result.scalars().all() and return courses)

    @pytest.mark.unit
    def test_update_course_lines_72_84(self, test_client: TestClient, sample_course):
        """Test to specifically hit lines 72-84 (update course logic)."""
        course_id = sample_course.id
        response = test_client.put(f"/course/{course_id}", json={
            "name": "Updated Course"
        })
        assert response.status_code == 200
        # This should hit lines 72-84 (update logic including refresh)

    @pytest.mark.unit
    def test_update_course_not_found_lines_74_75(self, test_client: TestClient):
        """Test to specifically hit lines 74-75 (course not found in update)."""
        response = test_client.put("/course/99999", json={"name": "Updated"})
        assert response.status_code == 404
        # This should hit lines 74-75 (if course is None in update)

    @pytest.mark.unit
    def test_delete_course_lines_92_100(self, test_client: TestClient, sample_course):
        """Test to specifically hit lines 92-100 (delete course logic)."""
        course_id = sample_course.id
        response = test_client.delete(f"/course/{course_id}")
        assert response.status_code == 200
        # This should hit lines 92-100 (delete logic)

    @pytest.mark.unit
    def test_delete_course_not_found_lines_94_95(self, test_client: TestClient):
        """Test to specifically hit lines 94-95 (course not found in delete)."""
        response = test_client.delete("/course/99999")
        assert response.status_code == 404
        # This should hit lines 94-95 (if course is None in delete)

    @pytest.mark.unit
    def test_enroll_user_not_found_lines_112_113(self, test_client: TestClient, sample_course):
        """Test to specifically hit lines 112-113 (user not found in enrollment)."""
        course_id = sample_course.id
        response = test_client.post(f"/user/99999/enroll/{course_id}")
        assert response.status_code == 404
        # This should hit lines 112-113 (if user is None)

    @pytest.mark.unit
    def test_enroll_course_not_found_lines_118_119(self, test_client: TestClient, sample_user):
        """Test to specifically hit lines 118-119 (course not found in enrollment)."""
        user_id = sample_user.id
        response = test_client.post(f"/user/{user_id}/enroll/99999")
        assert response.status_code == 404
        # This should hit lines 118-119 (if course is None)

    @pytest.mark.unit
    def test_enroll_success_lines_122_133(self, test_client: TestClient, sample_user, sample_course):
        """Test to specifically hit lines 122-133 (successful enrollment)."""
        user_id = sample_user.id
        course_id = sample_course.id
        response = test_client.post(f"/user/{user_id}/enroll/{course_id}")
        assert response.status_code == 200
        # This should hit lines 122-133 (enrollment creation and commit)

    @pytest.mark.unit
    def test_enroll_duplicate_lines_131_132(self, test_client: TestClient, sample_enrollment):
        """Test to specifically hit lines 131-132 (duplicate enrollment error)."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id
        response = test_client.post(f"/user/{user_id}/enroll/{course_id}")
        assert response.status_code == 409
        # This should hit lines 131-132 (IntegrityError handling)

    @pytest.mark.unit
    def test_unenroll_success_lines_147_156(self, test_client: TestClient, sample_enrollment):
        """Test to specifically hit lines 147-156 (successful unenrollment)."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id
        response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")
        assert response.status_code == 200
        # This should hit lines 147-156 (unenrollment logic)

    @pytest.mark.unit
    def test_unenroll_not_found_lines_149_150(self, test_client: TestClient, sample_user, sample_course):
        """Test to specifically hit lines 149-150 (enrollment not found)."""
        user_id = sample_user.id
        course_id = sample_course.id
        response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")
        assert response.status_code == 404
        # This should hit lines 149-150 (if enrollment is None)

    @pytest.mark.unit
    def test_get_user_courses_lines_166_185(self, test_client: TestClient, sample_enrollment):
        """Test to specifically hit lines 166-185 (get user courses logic)."""
        user_id = sample_enrollment.user_id
        response = test_client.get(f"/user/{user_id}/courses")
        assert response.status_code == 200
        # This should hit lines 166-185 (get user courses logic)

    @pytest.mark.unit
    def test_get_user_courses_not_found_lines_168_169(self, test_client: TestClient):
        """Test to specifically hit lines 168-169 (user not found in get courses)."""
        response = test_client.get("/user/99999/courses")
        assert response.status_code == 404
        # This should hit lines 168-169 (if user is None)

    @pytest.mark.unit
    def test_get_course_users_lines_193_214(self, test_client: TestClient, sample_enrollment):
        """Test to specifically hit lines 193-214 (get course users logic)."""
        course_id = sample_enrollment.course_id
        response = test_client.get(f"/course/{course_id}/users")
        assert response.status_code == 200
        # This should hit lines 193-214 (get course users logic)

    @pytest.mark.unit
    def test_get_course_users_not_found_lines_195_196(self, test_client: TestClient):
        """Test to specifically hit lines 195-196 (course not found in get users)."""
        response = test_client.get("/course/99999/users")
        assert response.status_code == 404
        # This should hit lines 195-196 (if course is None)


class TestTargetedUserCoverage:
    """Tests specifically targeting missing lines in user routes."""

    @pytest.mark.unit
    def test_user_creation_refresh_lines_33_40(self, test_client: TestClient):
        """Test to specifically hit lines 33-40 (refresh logic in user creation)."""
        response = test_client.post("/user", json={
            "name": "Target User",
            "address": "123 Target Street",
            "bio": "Target bio"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user_info"] is not None
        # This should hit lines 33-40 (select with selectinload and return)

    @pytest.mark.unit
    def test_get_user_not_found_lines_52_53(self, test_client: TestClient):
        """Test to specifically hit lines 52-53 (user not found)."""
        response = test_client.get("/user/99999")
        assert response.status_code == 404
        # This should hit lines 52-53 (if user is None)

    @pytest.mark.unit
    def test_get_all_users_lines_63_65(self, test_client: TestClient, sample_user):
        """Test to specifically hit lines 63-65 (return users in get all)."""
        response = test_client.get("/users")
        assert response.status_code == 200
        # This should hit lines 63-65 (users = result.scalars().all() and return users)