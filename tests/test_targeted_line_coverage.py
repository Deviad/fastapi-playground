"""
Targeted tests to ensure comprehensive coverage of service layer operations through routes.

This module contains tests specifically designed to exercise service layer operations
through route handlers using the common test infrastructure.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestServiceLayerThroughRoutesCoverage:
    """Tests targeting service layer operations through route handlers."""

    # ===== USER SERVICE OPERATIONS THROUGH ROUTES =====
    
    @pytest.mark.unit
    def test_user_creation_service_operation(self, test_client: TestClient, mock_transactional_db):
        """Test user creation through UserService with proper relationship loading."""
        with mock_transactional_db:
            user_data = {
                "name": "Line Coverage User",
                "address": "123 Coverage Street",
                "bio": "Targeting specific lines"
            }
            
            response = test_client.post("/user", json=user_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_info"] is not None
            # This exercises UserService.create_user with proper relationship loading

    @pytest.mark.unit
    def test_get_user_success_service_operation(self, test_client: TestClient, sample_user, mock_transactional_db):
        """Test successful user retrieval through UserService."""
        with mock_transactional_db:
            response = test_client.get(f"/user/{sample_user.id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_user.id
            # This exercises UserService.get_user with successful retrieval

    @pytest.mark.unit
    def test_get_user_not_found_error_handling(self, test_client: TestClient, mock_transactional_db):
        """Test user not found error handling through service layer."""
        with mock_transactional_db:
            response = test_client.get("/user/99999")
            
            assert response.status_code == 404
            data = response.json()
            assert "User not found" in data["detail"]
            # This exercises UserService.get_user returning None and route error handling

    @pytest.mark.unit
    def test_get_all_users_service_operation(self, test_client: TestClient, multiple_users, mock_transactional_db):
        """Test get all users through UserService."""
        with mock_transactional_db:
            response = test_client.get("/users")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0
            # This exercises UserService.get_all_users operation

    # ===== COURSE SERVICE OPERATIONS THROUGH ROUTES =====
    
    @pytest.mark.unit
    def test_course_creation_service_operation(self, test_client: TestClient, mock_transactional_db, mocker):
        """Test course creation through CourseService."""
        with mock_transactional_db:
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
            # This exercises CourseService.create_course with database operations

    @pytest.mark.unit
    def test_get_course_success_service_operation(self, test_client: TestClient, sample_course, mock_transactional_db):
        """Test successful course retrieval through CourseService."""
        with mock_transactional_db:
            response = test_client.get(f"/course/{sample_course.id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_course.id
            assert "users" in data
            # This exercises CourseService.get_course with relationship loading

    @pytest.mark.unit
    def test_get_course_not_found_error_handling(self, test_client: TestClient, mock_transactional_db):
        """Test course not found error handling through service layer."""
        with mock_transactional_db:
            response = test_client.get("/course/99999")
            
            assert response.status_code == 404
            data = response.json()
            assert "Course not found" in data["detail"]
            # This exercises CourseService.get_course returning None and route error handling

    @pytest.mark.unit
    def test_get_all_courses_service_operation(self, test_client: TestClient, multiple_courses, mock_transactional_db):
        """Test get all courses through CourseService."""
        with mock_transactional_db:
            response = test_client.get("/courses")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0
            # This exercises CourseService.get_all_courses operation

    @pytest.mark.unit
    def test_update_course_success_service_operation(self, test_client: TestClient, sample_course, mock_transactional_db, mocker):
        """Test successful course update through CourseService."""
        with mock_transactional_db:
            refresh_spy = mocker.spy(AsyncSession, 'refresh')
            commit_spy = mocker.spy(AsyncSession, 'commit')
            
            update_data = {"name": "Updated Coverage Course", "price": "299.99"}
            
            response = test_client.put(f"/course/{sample_course.id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == update_data["name"]
            assert refresh_spy.call_count >= 1
            assert commit_spy.call_count >= 1
            # This exercises CourseService.update_course with database operations

    @pytest.mark.unit
    def test_update_course_not_found_error_handling(self, test_client: TestClient, mock_transactional_db):
        """Test course not found in update through service layer."""
        with mock_transactional_db:
            response = test_client.put("/course/99999", json={"name": "Updated"})
            
            assert response.status_code == 404
            data = response.json()
            assert "Course not found" in data["detail"]
            # This exercises CourseService.update_course returning None and route error handling

    @pytest.mark.unit
    def test_delete_course_success_service_operation(self, test_client: TestClient, sample_course, mock_transactional_db, mocker):
        """Test successful course deletion through CourseService."""
        with mock_transactional_db:
            delete_spy = mocker.spy(AsyncSession, 'delete')
            commit_spy = mocker.spy(AsyncSession, 'commit')
            
            response = test_client.delete(f"/course/{sample_course.id}")
            
            assert response.status_code == 200
            data = response.json()
            assert "deleted successfully" in data["message"]
            assert delete_spy.call_count >= 1
            assert commit_spy.call_count >= 1
            # This exercises CourseService.delete_course with database operations

    @pytest.mark.unit
    def test_delete_course_not_found_error_handling(self, test_client: TestClient, mock_transactional_db):
        """Test course not found in delete through service layer."""
        with mock_transactional_db:
            response = test_client.delete("/course/99999")
            
            assert response.status_code == 404
            data = response.json()
            assert "Course not found" in data["detail"]
            # This exercises CourseService.delete_course returning False and route error handling

    @pytest.mark.unit
    def test_enroll_user_success_service_operation(self, test_client: TestClient, sample_user, sample_course, mock_transactional_db, mocker):
        """Test successful user enrollment through CourseService."""
        with mock_transactional_db:
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
            # This exercises CourseService.enroll_user_in_course with database operations

    @pytest.mark.unit
    def test_enroll_user_not_found_error_handling(self, test_client: TestClient, sample_course, mock_transactional_db):
        """Test user not found in enrollment through service layer."""
        with mock_transactional_db:
            response = test_client.post(f"/user/99999/enroll/{sample_course.id}")
            
            assert response.status_code == 404
            data = response.json()
            assert "User not found" in data["detail"]
            # This exercises CourseService.enroll_user_in_course with user not found ValueError

    @pytest.mark.unit
    def test_enroll_course_not_found_error_handling(self, test_client: TestClient, sample_user, mock_transactional_db):
        """Test course not found in enrollment through service layer."""
        with mock_transactional_db:
            response = test_client.post(f"/user/{sample_user.id}/enroll/99999")
            
            assert response.status_code == 404
            data = response.json()
            assert "Course not found" in data["detail"]
            # This exercises CourseService.enroll_user_in_course with course not found ValueError

    @pytest.mark.unit
    def test_enroll_duplicate_error_handling(self, test_client: TestClient, sample_enrollment, mock_transactional_db):
        """Test duplicate enrollment error through service layer."""
        with mock_transactional_db:
            user_id = sample_enrollment.user_id
            course_id = sample_enrollment.course_id
            
            response = test_client.post(f"/user/{user_id}/enroll/{course_id}")
            
            assert response.status_code == 409
            data = response.json()
            assert "already enrolled" in data["detail"]
            # This exercises CourseService.enroll_user_in_course with IntegrityError handling

    @pytest.mark.unit
    def test_unenroll_success_service_operation(self, test_client: TestClient, sample_enrollment, mock_transactional_db, mocker):
        """Test successful unenrollment through CourseService."""
        with mock_transactional_db:
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
            # This exercises CourseService.unenroll_user_from_course with database operations

    @pytest.mark.unit
    def test_unenroll_not_found_error_handling(self, test_client: TestClient, sample_user, sample_course, mock_transactional_db):
        """Test enrollment not found in unenrollment through service layer."""
        with mock_transactional_db:
            response = test_client.delete(f"/user/{sample_user.id}/enroll/{sample_course.id}")
            
            assert response.status_code == 404
            data = response.json()
            assert "Enrollment not found" in data["detail"]
            # This exercises CourseService.unenroll_user_from_course returning False

    @pytest.mark.unit
    def test_get_user_courses_success_service_operation(self, test_client: TestClient, sample_enrollment, mock_transactional_db):
        """Test get user courses through CourseService."""
        with mock_transactional_db:
            user_id = sample_enrollment.user_id
            
            response = test_client.get(f"/user/{user_id}/courses")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == user_id
            assert "courses" in data
            assert len(data["courses"]) > 0
            # This exercises CourseService.get_user_courses with relationship loading

    @pytest.mark.unit
    def test_get_user_courses_not_found_error_handling(self, test_client: TestClient, mock_transactional_db):
        """Test user not found in get courses through service layer."""
        with mock_transactional_db:
            response = test_client.get("/user/99999/courses")
            
            assert response.status_code == 404
            data = response.json()
            assert "User not found" in data["detail"]
            # This exercises CourseService.get_user_courses returning None

    @pytest.mark.unit
    def test_get_course_users_success_service_operation(self, test_client: TestClient, sample_enrollment, mock_transactional_db):
        """Test get course users through CourseService."""
        with mock_transactional_db:
            course_id = sample_enrollment.course_id
            
            response = test_client.get(f"/course/{course_id}/users")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == course_id
            assert "users" in data
            assert len(data["users"]) > 0
            # This exercises CourseService.get_course_users with relationship loading

    @pytest.mark.unit
    def test_get_course_users_not_found_error_handling(self, test_client: TestClient, mock_transactional_db):
        """Test course not found in get users through service layer."""
        with mock_transactional_db:
            response = test_client.get("/course/99999/users")
            
            assert response.status_code == 404
            data = response.json()
            assert "Course not found" in data["detail"]
            # This exercises CourseService.get_course_users returning None


class TestServiceLayerEdgeCases:
    """Additional edge cases to ensure maximum service layer coverage."""

    @pytest.mark.unit
    def test_empty_course_update_service_operation(self, test_client: TestClient, sample_course, mock_transactional_db):
        """Test course update with empty data through CourseService."""
        with mock_transactional_db:
            response = test_client.put(f"/course/{sample_course.id}", json={})
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_course.id
            # Ensures CourseService.update_course handles empty updates correctly

    @pytest.mark.unit
    def test_partial_course_updates_service_operations(self, test_client: TestClient, sample_course, mock_transactional_db):
        """Test all combinations of partial course updates through CourseService."""
        with mock_transactional_db:
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
                # This ensures CourseService.update_course handles all attribute combinations

    @pytest.mark.unit
    def test_multiple_enrollments_same_user_service_operations(self, test_client: TestClient, sample_user, multiple_courses, mock_transactional_db):
        """Test enrolling the same user in multiple courses through CourseService."""
        with mock_transactional_db:
            for course in multiple_courses:
                response = test_client.post(f"/user/{sample_user.id}/enroll/{course.id}")
                assert response.status_code == 200
            
            # Verify user has all courses
            response = test_client.get(f"/user/{sample_user.id}/courses")
            assert response.status_code == 200
            data = response.json()
            assert len(data["courses"]) == len(multiple_courses)
            # This tests CourseService complex relationship loading scenarios