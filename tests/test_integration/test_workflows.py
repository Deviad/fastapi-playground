"""
Integration tests for complex workflows and cross-endpoint interactions.

This module tests complete user journeys and complex scenarios that
involve multiple endpoints working together.
"""

import pytest
from fastapi.testclient import TestClient


class TestCompleteWorkflows:
    """Test class for complete user workflows and integration scenarios."""

    @pytest.mark.integration
    def test_complete_user_journey(self, test_client: TestClient, mock_transactional_db):
        """
        Test a complete user journey from registration to course enrollment.

        Workflow:
        1. Create a user
        2. Create multiple courses
        3. Enroll user in courses
        4. Verify enrollments
        5. Update course details
        6. Unenroll from one course
        7. Verify final state
        """
        with mock_transactional_db:
            # Step 1: Create a user
            user_data = {
                "name": "Integration Test User",
                "address": "123 Integration Street",
                "bio": "Testing complete workflows",
            }
            user_response = test_client.post("/user", json=user_data)
            assert user_response.status_code == 200
            user = user_response.json()
            user_id = user["id"]

            # Step 2: Create multiple courses
            courses_data = [
                {
                    "name": "Python Fundamentals",
                    "author_name": "Dr. Python",
                    "price": "99.99",
                },
                {
                    "name": "Advanced Web Development",
                    "author_name": "Web Master",
                    "price": "199.99",
                },
                {
                    "name": "Data Science Basics",
                    "author_name": "Data Guru",
                    "price": "149.99",
                },
            ]

            created_courses = []
            for course_data in courses_data:
                course_response = test_client.post("/course", json=course_data)
                assert course_response.status_code == 200
                created_courses.append(course_response.json())

            # Step 3: Enroll user in first two courses
            for i in range(2):
                course_id = created_courses[i]["id"]
                enroll_response = test_client.post(f"/user/{user_id}/enroll/{course_id}")
                assert enroll_response.status_code == 200

            # Step 4: Verify enrollments
            user_courses_response = test_client.get(f"/user/{user_id}/courses")
            assert user_courses_response.status_code == 200
            user_with_courses = user_courses_response.json()
            assert len(user_with_courses["courses"]) == 2

            # Verify each course has the user
            for i in range(2):
                course_id = created_courses[i]["id"]
                course_users_response = test_client.get(f"/course/{course_id}/users")
                assert course_users_response.status_code == 200
                course_with_users = course_users_response.json()
                assert len(course_with_users["users"]) == 1
                assert course_with_users["users"][0]["id"] == user_id

            # Step 5: Update course details
            course_id = created_courses[0]["id"]
            update_data = {"name": "Updated Python Fundamentals", "price": "79.99"}
            update_response = test_client.put(f"/course/{course_id}", json=update_data)
            assert update_response.status_code == 200
            updated_course = update_response.json()
            assert updated_course["name"] == update_data["name"]
            assert updated_course["price"] == update_data["price"]

            # Step 6: Unenroll from one course
            unenroll_response = test_client.delete(f"/user/{user_id}/enroll/{course_id}")
            assert unenroll_response.status_code == 200

            # Step 7: Verify final state
            final_user_courses = test_client.get(f"/user/{user_id}/courses")
            assert final_user_courses.status_code == 200
            final_user_data = final_user_courses.json()
            assert len(final_user_data["courses"]) == 1
            assert final_user_data["courses"][0]["id"] == created_courses[1]["id"]

    @pytest.mark.integration
    def test_cascade_deletion_workflow(self, test_client: TestClient, mock_transactional_db):
        """
        Test cascade deletion behavior when deleting courses with enrollments.

        Workflow:
        1. Create users and courses
        2. Create enrollments
        3. Delete a course
        4. Verify enrollments are cascade deleted
        5. Verify users remain intact
        """
        with mock_transactional_db:
            # Step 1: Create users and courses
            users_data = [
                {"name": "User 1", "address": "Address 1"},
                {"name": "User 2", "address": "Address 2"},
            ]

            created_users = []
            for user_data in users_data:
                response = test_client.post("/user", json=user_data)
                assert response.status_code == 200
                created_users.append(response.json())

            course_data = {
                "name": "Course to Delete",
                "author_name": "Test Author",
                "price": "99.99",
            }
            course_response = test_client.post("/course", json=course_data)
            assert course_response.status_code == 200
            course = course_response.json()
            course_id = course["id"]

            # Step 2: Create enrollments
            for user in created_users:
                enroll_response = test_client.post(f"/user/{user['id']}/enroll/{course_id}")
                assert enroll_response.status_code == 200

            # Verify enrollments exist
            course_users_response = test_client.get(f"/course/{course_id}/users")
            assert course_users_response.status_code == 200
            assert len(course_users_response.json()["users"]) == 2

            # Step 3: Delete the course
            delete_response = test_client.delete(f"/course/{course_id}")
            assert delete_response.status_code == 200

            # Step 4: Verify course is deleted
            get_course_response = test_client.get(f"/course/{course_id}")
            assert get_course_response.status_code == 404

            # Step 5: Verify users still exist and have no courses
            for user in created_users:
                user_response = test_client.get(f"/user/{user['id']}")
                assert user_response.status_code == 200

                user_courses_response = test_client.get(f"/user/{user['id']}/courses")
                assert user_courses_response.status_code == 200
                assert len(user_courses_response.json()["courses"]) == 0

    @pytest.mark.integration
    def test_multiple_users_multiple_courses_complex(self, test_client: TestClient, mock_transactional_db):
        """
        Test complex scenario with multiple users and courses with various enrollments.

        Scenario:
        - 3 users, 3 courses
        - User 1: enrolled in courses 1 and 2
        - User 2: enrolled in courses 2 and 3
        - User 3: enrolled in course 1 only
        """
        with mock_transactional_db:
            # Create users
            users_data = [
                {"name": "Alice", "address": "Alice Street", "bio": "Alice bio"},
                {"name": "Bob", "address": "Bob Avenue", "bio": "Bob bio"},
                {"name": "Charlie", "address": "Charlie Road"},
            ]

            users = []
            for user_data in users_data:
                response = test_client.post("/user", json=user_data)
                assert response.status_code == 200
                users.append(response.json())

            # Create courses
            courses_data = [
                {"name": "Course A", "author_name": "Author A", "price": "100.00"},
                {"name": "Course B", "author_name": "Author B", "price": "200.00"},
                {"name": "Course C", "author_name": "Author C", "price": "300.00"},
            ]

            courses = []
            for course_data in courses_data:
                response = test_client.post("/course", json=course_data)
                assert response.status_code == 200
                courses.append(response.json())

            # Create enrollments according to scenario
            enrollments = [
                (0, 0),  # User 1 -> Course 1
                (0, 1),  # User 1 -> Course 2
                (1, 1),  # User 2 -> Course 2
                (1, 2),  # User 2 -> Course 3
                (2, 0),  # User 3 -> Course 1
            ]

            for user_idx, course_idx in enrollments:
                user_id = users[user_idx]["id"]
                course_id = courses[course_idx]["id"]
                response = test_client.post(f"/user/{user_id}/enroll/{course_id}")
                assert response.status_code == 200

            # Verify User 1 enrollments (courses 1 and 2)
            user1_courses = test_client.get(f"/user/{users[0]['id']}/courses")
            assert user1_courses.status_code == 200
            user1_data = user1_courses.json()
            assert len(user1_data["courses"]) == 2
            user1_course_ids = {course["id"] for course in user1_data["courses"]}
            expected_user1_courses = {courses[0]["id"], courses[1]["id"]}
            assert user1_course_ids == expected_user1_courses

            # Verify User 2 enrollments (courses 2 and 3)
            user2_courses = test_client.get(f"/user/{users[1]['id']}/courses")
            assert user2_courses.status_code == 200
            user2_data = user2_courses.json()
            assert len(user2_data["courses"]) == 2
            user2_course_ids = {course["id"] for course in user2_data["courses"]}
            expected_user2_courses = {courses[1]["id"], courses[2]["id"]}
            assert user2_course_ids == expected_user2_courses

            # Verify User 3 enrollments (course 1 only)
            user3_courses = test_client.get(f"/user/{users[2]['id']}/courses")
            assert user3_courses.status_code == 200
            user3_data = user3_courses.json()
            assert len(user3_data["courses"]) == 1
            assert user3_data["courses"][0]["id"] == courses[0]["id"]

            # Verify Course 1 users (users 1 and 3)
            course1_users = test_client.get(f"/course/{courses[0]['id']}/users")
            assert course1_users.status_code == 200
            course1_data = course1_users.json()
            assert len(course1_data["users"]) == 2
            course1_user_ids = {user["id"] for user in course1_data["users"]}
            expected_course1_users = {users[0]["id"], users[2]["id"]}
            assert course1_user_ids == expected_course1_users

            # Verify Course 2 users (users 1 and 2)
            course2_users = test_client.get(f"/course/{courses[1]['id']}/users")
            assert course2_users.status_code == 200
            course2_data = course2_users.json()
            assert len(course2_data["users"]) == 2
            course2_user_ids = {user["id"] for user in course2_data["users"]}
            expected_course2_users = {users[0]["id"], users[1]["id"]}
            assert course2_user_ids == expected_course2_users

            # Verify Course 3 users (user 2 only)
            course3_users = test_client.get(f"/course/{courses[2]['id']}/users")
            assert course3_users.status_code == 200
            course3_data = course3_users.json()
            assert len(course3_data["users"]) == 1
            assert course3_data["users"][0]["id"] == users[1]["id"]

    @pytest.mark.integration
    def test_api_consistency_across_endpoints(self, test_client: TestClient, mock_transactional_db):
        """
        Test that data remains consistent across different API endpoints.

        This test verifies that the same data is returned consistently
        whether accessed through different endpoints.
        """
        with mock_transactional_db:
            # Create test data
            user_data = {
                "name": "Consistency Test User",
                "address": "Consistency Street",
                "bio": "Testing API consistency",
            }
            user_response = test_client.post("/user", json=user_data)
            assert user_response.status_code == 200
            user = user_response.json()
            user_id = user["id"]

            course_data = {
                "name": "Consistency Test Course",
                "author_name": "Consistency Author",
                "price": "123.45",
            }
            course_response = test_client.post("/course", json=course_data)
            assert course_response.status_code == 200
            course = course_response.json()
            course_id = course["id"]

            # Enroll user in course
            enroll_response = test_client.post(f"/user/{user_id}/enroll/{course_id}")
            assert enroll_response.status_code == 200

            # Get user data from different endpoints
            user_direct = test_client.get(f"/user/{user_id}").json()
            user_from_courses = test_client.get(f"/user/{user_id}/courses").json()
            users_list = test_client.get("/users").json()
            user_from_list = next(u for u in users_list if u["id"] == user_id)

            # Verify user data consistency
            assert user_direct["id"] == user_from_courses["id"] == user_from_list["id"]
            assert (
                user_direct["name"] == user_from_courses["name"] == user_from_list["name"]
            )

            # Get course data from different endpoints
            course_direct = test_client.get(f"/course/{course_id}").json()
            course_from_users = test_client.get(f"/course/{course_id}/users").json()
            courses_list = test_client.get("/courses").json()
            course_from_list = next(c for c in courses_list if c["id"] == course_id)

            # Verify course data consistency
            assert course_direct["id"] == course_from_users["id"] == course_from_list["id"]
            assert (
                course_direct["name"]
                == course_from_users["name"]
                == course_from_list["name"]
            )
            assert (
                course_direct["author_name"]
                == course_from_users["author_name"]
                == course_from_list["author_name"]
            )
            assert (
                course_direct["price"]
                == course_from_users["price"]
                == course_from_list["price"]
            )

            # Verify enrollment consistency
            user_courses = user_from_courses["courses"]
            course_users = course_from_users["users"]

            assert len(user_courses) == 1
            assert len(course_users) == 1
            assert user_courses[0]["id"] == course_id
            assert course_users[0]["id"] == user_id

    @pytest.mark.integration
    def test_root_and_health_endpoints(self, test_client: TestClient):
        """Test the root and health check endpoints."""
        # Test root endpoint
        root_response = test_client.get("/")
        assert root_response.status_code == 200
        root_data = root_response.json()
        assert "message" in root_data
        assert isinstance(root_data["message"], str)

        # Test health endpoint
        health_response = test_client.get("/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert "status" in health_data
        assert health_data["status"] == "healthy"
