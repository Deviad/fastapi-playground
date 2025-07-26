"""
Targeted tests to hit specific missing lines in route handlers for 95% coverage.

This module contains tests specifically designed to execute the missing lines
identified in the coverage report to achieve the 95% coverage threshold.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestTargetedLineCoverage:
    """Tests targeting specific uncovered lines in routes."""

    # ===== USER ROUTES SPECIFIC LINE COVERAGE =====
    
    @pytest.mark.unit
    def test_user_creation_lines_33_40(self, test_client: TestClient):
        """Target lines 33-40 in user_routes.py (select with selectinload and return)."""
        user_data = {
            "name": "Line Coverage User",
            "address": "123 Coverage Street",
            "bio": "Targeting specific lines"
        }
        
        response = test_client.post("/user", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_info"] is not None
        # This executes lines 33-40 (select with selectinload and return user_with_info)

    @pytest.mark.unit
    def test_get_user_success_lines_50_55(self, test_client: TestClient, sample_user):
        """Target lines 50-55 in user_routes.py (successful user retrieval)."""
        response = test_client.get(f"/user/{sample_user.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_user.id
        # This executes lines 50, 55 (scalar_one_or_none success and return user)

    @pytest.mark.unit
    def test_get_user_not_found_lines_52_53(self, test_client: TestClient):
        """Target lines 52-53 in user_routes.py (user not found error)."""
        response = test_client.get("/user/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "User not found" in data["detail"]
        # This executes lines 52-53 (user is None check and HTTPException)

    @pytest.mark.unit
    def test_get_all_users_lines_63_65(self, test_client: TestClient, multiple_users):
        """Target lines 63-65 in user_routes.py (scalars().all() and return)."""
        response = test_client.get("/users")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # This executes lines 63-65 (scalars().all() and return users)

    # ===== COURSE ROUTES SPECIFIC LINE COVERAGE =====
    
    @pytest.mark.unit
    def test_course_creation_lines_39_40(self, test_client: TestClient, mocker):
        """Target lines 39-40 in courses_routes.py (refresh and return)."""
        refresh_spy = mocker.spy(AsyncSession, 'refresh')
        
        course_data = {
            "name": "Line Coverage Course",
            "author_name": "Coverage Author",
            "price": "199.99"
        }
        
        response = test_client.post("/course", json=course_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert refresh_spy.call_count >= 1
        # This executes lines 39-40 (db.refresh and return new_course)

    @pytest.mark.unit
    def test_get_course_success_lines_49_54(self, test_client: TestClient, sample_course):
        """Target lines 49-54 in courses_routes.py (successful course retrieval)."""
        response = test_client.get(f"/course/{sample_course.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_course.id
        assert "users" in data
        # This executes lines 49-54 (course found, selectinload, and return)

    @pytest.mark.unit
    def test_get_course_not_found_lines_51_52(self, test_client: TestClient):
        """Target lines 51-52 in courses_routes.py (course not found error)."""
        response = test_client.get("/course/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Course not found" in data["detail"]
        # This executes lines 51-52 (course is None and HTTPException)

    @pytest.mark.unit
    def test_get_all_courses_lines_61_62(self, test_client: TestClient, multiple_courses):
        """Target lines 61-62 in courses_routes.py (scalars().all() and return)."""
        response = test_client.get("/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # This executes lines 61-62 (scalars().all() and return courses)

    @pytest.mark.unit
    def test_update_course_success_lines_72_84(self, test_client: TestClient, sample_course, mocker):
        """Target lines 72-84 in courses_routes.py (update logic and refresh)."""
        refresh_spy = mocker.spy(AsyncSession, 'refresh')
        commit_spy = mocker.spy(AsyncSession, 'commit')
        
        update_data = {"name": "Updated Coverage Course", "price": "299.99"}
        
        response = test_client.put(f"/course/{sample_course.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert refresh_spy.call_count >= 1
        assert commit_spy.call_count >= 1
        # This executes lines 72-84 (course found, update attributes, commit, refresh, return)

    @pytest.mark.unit
    def test_update_course_not_found_lines_74_75(self, test_client: TestClient):
        """Target lines 74-75 in courses_routes.py (course not found in update)."""
        response = test_client.put("/course/99999", json={"name": "Updated"})
        
        assert response.status_code == 404
        data = response.json()
        assert "Course not found" in data["detail"]
        # This executes lines 74-75 (course is None and HTTPException in update)

    @pytest.mark.unit
    def test_delete_course_success_lines_92_100(self, test_client: TestClient, sample_course, mocker):
        """Target lines 92-100 in courses_routes.py (delete logic)."""
        delete_spy = mocker.spy(AsyncSession, 'delete')
        commit_spy = mocker.spy(AsyncSession, 'commit')
        
        response = test_client.delete(f"/course/{sample_course.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        assert delete_spy.call_count >= 1
        assert commit_spy.call_count >= 1
        # This executes lines 92-100 (course found, delete, commit, return message)

    @pytest.mark.unit
    def test_delete_course_not_found_lines_94_95(self, test_client: TestClient):
        """Target lines 94-95 in courses_routes.py (course not found in delete)."""
        response = test_client.delete("/course/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Course not found" in data["detail"]
        # This executes lines 94-95 (course is None and HTTPException in delete)

    @pytest.mark.unit
    def test_enroll_user_success_lines_111_133(self, test_client: TestClient, sample_user, sample_course, mocker):
        """Target lines 111-133 in courses_routes.py (enrollment logic)."""
        add_spy = mocker.spy(AsyncSession, 'add')
        commit_spy = mocker.spy(AsyncSession, 'commit')
        refresh_spy = mocker.spy(AsyncSession, 'refresh')
        
        response = test_client.post(f"/user/{sample_user.id}/enroll/{sample_course.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == sample_user.id
        assert data["course_id"] == sample_course.id
        assert add_spy.call_count >= 1
        assert commit_spy.call_count >= 1
        assert refresh_spy.call_count >= 1
        # This executes lines 111-133 (user/course found, create enrollment, add, commit, refresh, return)

    @pytest.mark.unit
    def test_enroll_user_not_found_lines_112_113(self, test_client: TestClient, sample_course):
        """Target lines 112-113 in courses_routes.py (user not found in enrollment)."""
        response = test_client.post(f"/user/99999/enroll/{sample_course.id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "User not found" in data["detail"]
        # This executes lines 112-113 (user is None and HTTPException)

    @pytest.mark.unit
    def test_enroll_course_not_found_lines_118_119(self, test_client: TestClient, sample_user):
        """Target lines 118-119 in courses_routes.py (course not found in enrollment)."""
        response = test_client.post(f"/user/{sample_user.id}/enroll/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Course not found" in data["detail"]
        # This executes lines 118-119 (course is None and HTTPException)

    @pytest.mark.unit
    def test_enroll_duplicate_lines_131_132(self, test_client: TestClient, sample_enrollment):
        """Target lines 131-132 in courses_routes.py (duplicate enrollment error)."""
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id
        
        response = test_client.post(f"/user/{user_id}/enroll/{course_id}")
        
        assert response.status_code == 409
        data = response.json()
        assert "already enrolled" in data["detail"]
        # This executes lines 131-132 (IntegrityError and HTTPException)

    @pytest.mark.unit
    def test_unenroll_success_lines_147_156(self, test_client: TestClient, sample_enrollment, mocker):
        """Target lines 147-156 in courses_routes.py (unenrollment logic)."""
        delete_spy = mocker.spy(AsyncSession, 'delete')
        commit_spy = mocker.spy(AsyncSession, 'commit')
        
        user_id = sample_enrollment.user_id
        course_id = sample_enrollment.course_id
        
        response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert str(user_id) in data["message"]
        assert str(course_id) in data["message"]
        assert delete_spy.call_count >= 1
        assert commit_spy.call_count >= 1
        # This executes lines 147-156 (enrollment found, delete, commit, return message)

    @pytest.mark.unit
    def test_unenroll_not_found_lines_149_150(self, test_client: TestClient, sample_user, sample_course):
        """Target lines 149-150 in courses_routes.py (enrollment not found)."""
        response = test_client.delete(f"/user/{sample_user.id}/enroll/{sample_course.id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "Enrollment not found" in data["detail"]
        # This executes lines 149-150 (enrollment is None and HTTPException)

    @pytest.mark.unit
    def test_get_user_courses_success_lines_166_180(self, test_client: TestClient, sample_enrollment):
        """Target lines 166-180 in courses_routes.py (get user courses logic)."""
        user_id = sample_enrollment.user_id
        
        response = test_client.get(f"/user/{user_id}/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert "courses" in data
        assert len(data["courses"]) > 0
        # This executes lines 166-180 (user found, select with joinedload, return user)

    @pytest.mark.unit
    def test_get_user_courses_not_found_lines_168_169(self, test_client: TestClient):
        """Target lines 168-169 in courses_routes.py (user not found in get courses)."""
        response = test_client.get("/user/99999/courses")
        
        assert response.status_code == 404
        data = response.json()
        assert "User not found" in data["detail"]
        # This executes lines 168-169 (user is None and HTTPException)

    @pytest.mark.unit
    def test_get_course_users_success_lines_193_208(self, test_client: TestClient, sample_enrollment):
        """Target lines 193-208 in courses_routes.py (get course users logic)."""
        course_id = sample_enrollment.course_id
        
        response = test_client.get(f"/course/{course_id}/users")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == course_id
        assert "users" in data
        assert len(data["users"]) > 0
        # This executes lines 193-208 (course found, select with joinedload, return course)

    @pytest.mark.unit
    def test_get_course_users_not_found_lines_195_196(self, test_client: TestClient):
        """Target lines 195-196 in courses_routes.py (course not found in get users)."""
        response = test_client.get("/course/99999/users")
        
        assert response.status_code == 404
        data = response.json()
        assert "Course not found" in data["detail"]
        # This executes lines 195-196 (course is None and HTTPException)


class TestEdgeCasesForCoverage:
    """Additional edge cases to ensure maximum coverage."""

    @pytest.mark.unit
    def test_empty_course_update(self, test_client: TestClient, sample_course):
        """Test course update with empty data to ensure all update paths are covered."""
        response = test_client.put(f"/course/{sample_course.id}", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_course.id
        # Ensures update logic handles empty updates correctly

    @pytest.mark.unit
    def test_partial_course_updates(self, test_client: TestClient, sample_course):
        """Test all combinations of partial course updates."""
        test_cases = [
            {"name": "Updated Name Only"},
            {"author_name": "Updated Author Only"},
            {"price": "199.99"},
            {"name": "Updated Name", "price": "299.99"},
            {"author_name": "Updated Author", "price": "399.99"},
            {"name": "Full Update", "author_name": "Full Author", "price": "499.99"}
        ]
        
        for i, update_data in enumerate(test_cases):
            # Create a new course for each test to avoid conflicts
            course_data = {
                "name": f"Test Course {i}",
                "author_name": f"Test Author {i}",
                "price": "99.99"
            }
            create_response = test_client.post("/course", json=course_data)
            assert create_response.status_code == 200
            course_id = create_response.json()["id"]
            
            # Test the update
            response = test_client.put(f"/course/{course_id}", json=update_data)
            assert response.status_code == 200
            # This ensures all update attribute assignment paths are covered

    @pytest.mark.unit
    def test_multiple_enrollments_same_user(self, test_client: TestClient, sample_user, multiple_courses):
        """Test enrolling the same user in multiple courses."""
        for course in multiple_courses:
            response = test_client.post(f"/user/{sample_user.id}/enroll/{course.id}")
            assert response.status_code == 200
        
        # Verify user has all courses
        response = test_client.get(f"/user/{sample_user.id}/courses")
        assert response.status_code == 200
        data = response.json()
        assert len(data["courses"]) == len(multiple_courses)
        # This tests complex relationship loading scenarios