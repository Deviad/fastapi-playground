"""
Debug tests to understand why coverage isn't improving.
"""

import pytest
from fastapi.testclient import TestClient


class TestCoverageDebug:
    """Debug tests to verify route execution."""

    @pytest.mark.unit
    def test_simple_user_creation_debug(self, test_client: TestClient, mock_transactional_db):
        """Simple test to verify user creation route is accessible."""
        print("=== DEBUG: Testing user creation ===")
        
        with mock_transactional_db:
            user_data = {
                "name": "Debug User",
                "address": "123 Debug Street",
                "bio": "Debug test"
            }
            
            response = test_client.post("/user", json=user_data)
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.json()}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == user_data["name"]

    @pytest.mark.unit
    def test_simple_course_creation_debug(self, test_client: TestClient, mock_transactional_db):
        """Simple test to verify course creation route is accessible."""
        print("=== DEBUG: Testing course creation ===")
        
        with mock_transactional_db:
            course_data = {
                "name": "Debug Course",
                "author_name": "Debug Author",
                "price": "99.99"
            }
            
            response = test_client.post("/course", json=course_data)
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.json()}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == course_data["name"]

    @pytest.mark.unit
    def test_get_all_users_debug(self, test_client: TestClient, mock_transactional_db):
        """Simple test to verify get all users route."""
        print("=== DEBUG: Testing get all users ===")
        
        with mock_transactional_db:
            response = test_client.get("/users")
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.json()}")
            
            assert response.status_code == 200

    @pytest.mark.unit
    def test_get_all_courses_debug(self, test_client: TestClient, mock_transactional_db):
        """Simple test to verify get all courses route."""
        print("=== DEBUG: Testing get all courses ===")
        
        with mock_transactional_db:
            response = test_client.get("/courses")
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.json()}")
            
            assert response.status_code == 200