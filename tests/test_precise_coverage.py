"""
Tests designed to ensure comprehensive coverage of service layer operations through route handlers.
"""

import pytest
from fastapi.testclient import TestClient


class TestServiceLayerCoverageThroughRoutes:
    """Tests targeting service layer operations through route handlers."""

    @pytest.mark.unit
    def test_user_creation_service_operation(self, test_client: TestClient, mock_transactional_db):
        """Test user creation through service layer with proper relationship loading."""
        with mock_transactional_db:
            user_data = {
                "name": "SelectInLoad Test User",
                "address": "123 SelectInLoad Street",
                "bio": "Testing selectinload query execution"
            }
            
            response = test_client.post("/user", json=user_data)
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify the selectinload worked by checking user_info is loaded
            assert data["user_info"] is not None
            assert data["user_info"]["address"] == user_data["address"]
            assert data["user_info"]["bio"] == user_data["bio"]
            
            # This tests the UserService.create_user method with proper relationship loading

    @pytest.mark.unit
    def test_get_user_by_id_service_operation(self, test_client: TestClient, sample_user, mock_transactional_db):
        """Test get user by ID through service layer."""
        with mock_transactional_db:
            user_id = sample_user.id
            
            response = test_client.get(f"/user/{user_id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == user_id
            assert data["name"] == sample_user.name
            assert data["user_info"] is not None
            
            # This tests the UserService.get_user method

    @pytest.mark.unit
    def test_get_user_not_found_error_handling(self, test_client: TestClient, mock_transactional_db):
        """Test user not found error handling through service layer."""
        with mock_transactional_db:
            response = test_client.get("/user/99999")
            
            assert response.status_code == 404
            data = response.json()
            assert "User not found" in data["detail"]
            
            # This tests the service layer returning None and route error handling

    @pytest.mark.unit
    def test_get_all_users_service_operation(self, test_client: TestClient, multiple_users, mock_transactional_db):
        """Test get all users through service layer."""
        with mock_transactional_db:
            response = test_client.get("/users")
            
            assert response.status_code == 200
            data = response.json()
            
            assert isinstance(data, list)
            assert len(data) == len(multiple_users)
            
            # Verify all users have user_info loaded (proves selectinload worked)
            for user_data in data:
                assert "user_info" in user_data
                assert user_data["user_info"] is not None
            
            # This tests the UserService.get_all_users method

    @pytest.mark.unit
    def test_user_creation_followed_by_retrieval(self, test_client: TestClient, mock_transactional_db):
        """Test creating a user then retrieving it to test service layer workflow."""
        with mock_transactional_db:
            # Create user
            user_data = {
                "name": "Create Then Retrieve User",
                "address": "456 Retrieve Street",
                "bio": "Testing creation and retrieval flow"
            }
            
            create_response = test_client.post("/user", json=user_data)
            assert create_response.status_code == 200
            created_user = create_response.json()
            user_id = created_user["id"]
            
            # This tests UserService.create_user
            
            # Now retrieve the user
            get_response = test_client.get(f"/user/{user_id}")
            assert get_response.status_code == 200
            retrieved_user = get_response.json()
            
            assert retrieved_user["id"] == user_id
            assert retrieved_user["name"] == user_data["name"]
            assert retrieved_user["user_info"]["address"] == user_data["address"]
            
            # This tests UserService.get_user

    @pytest.mark.unit
    def test_multiple_user_operations_comprehensive(self, test_client: TestClient, mock_transactional_db):
        """Comprehensive test of all user service operations through routes."""
        with mock_transactional_db:
            # Test get all users (initially empty)
            response = test_client.get("/users")
            assert response.status_code == 200
            # Tests UserService.get_all_users
            
            # Create multiple users
            users_to_create = [
                {"name": "User 1", "address": "Address 1", "bio": "Bio 1"},
                {"name": "User 2", "address": "Address 2", "bio": "Bio 2"},
                {"name": "User 3", "address": "Address 3", "bio": "Bio 3"}
            ]
            
            created_user_ids = []
            for user_data in users_to_create:
                create_response = test_client.post("/user", json=user_data)
                assert create_response.status_code == 200
                created_user_ids.append(create_response.json()["id"])
                # Each creation tests UserService.create_user
            
            # Get each user individually
            for user_id in created_user_ids:
                get_response = test_client.get(f"/user/{user_id}")
                assert get_response.status_code == 200
                # Each get tests UserService.get_user
            
            # Get all users (should have 3 now)
            all_response = test_client.get("/users")
            assert all_response.status_code == 200
            all_users = all_response.json()
            assert len(all_users) >= 3
            # Tests UserService.get_all_users with data
            
            # Test user not found
            notfound_response = test_client.get("/user/99999")
            assert notfound_response.status_code == 404
            # Tests service layer error handling

    @pytest.mark.unit
    def test_user_with_none_bio(self, test_client: TestClient, mock_transactional_db):
        """Test user creation with None bio through service layer."""
        with mock_transactional_db:
            user_data = {
                "name": "None Bio User",
                "address": "789 None Bio Street"
                # bio is optional and will be None
            }
            
            response = test_client.post("/user", json=user_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["name"] == user_data["name"]
            assert data["user_info"]["address"] == user_data["address"]
            assert data["user_info"]["bio"] is None
            
            # This tests UserService.create_user with optional bio field

    @pytest.mark.unit
    def test_user_edge_cases_for_coverage(self, test_client: TestClient, mock_transactional_db):
        """Test edge cases to ensure complete service layer coverage."""
        with mock_transactional_db:
            # Create user with very specific data to ensure service layer execution
            edge_cases = [
                {"name": "Edge1", "address": "Addr1", "bio": "Bio1"},
                {"name": "Edge2", "address": "Addr2", "bio": ""},  # Empty bio
                {"name": "Edge3", "address": "Addr3"},  # No bio field
            ]
            
            for i, user_data in enumerate(edge_cases):
                # Create user
                create_response = test_client.post("/user", json=user_data)
                assert create_response.status_code == 200
                user_id = create_response.json()["id"]
                
                # Immediately retrieve user to test service layer
                get_response = test_client.get(f"/user/{user_id}")
                assert get_response.status_code == 200
                
                # Get all users to test that service method too
                all_response = test_client.get("/users")
                assert all_response.status_code == 200
                
            # Test invalid user ID
            invalid_response = test_client.get("/user/999999")
            assert invalid_response.status_code == 404