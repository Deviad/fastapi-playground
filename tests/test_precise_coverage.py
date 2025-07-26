"""
Tests designed to hit the exact missing lines in route handlers.
"""

import pytest
from fastapi.testclient import TestClient


class TestPreciseCoverageTargeting:
    """Tests targeting exact missing lines."""

    @pytest.mark.unit
    def test_user_creation_selectinload_lines_33_40(self, test_client: TestClient):
        """Target lines 33-40 in user_routes.py - the select query with selectinload."""
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
        
        # This should execute the select query with selectinload (lines 33-40)

    @pytest.mark.unit  
    def test_get_user_by_id_lines_47_55(self, test_client: TestClient, sample_user):
        """Target lines 47-55 in user_routes.py - the get_user function."""
        user_id = sample_user.id
        
        response = test_client.get(f"/user/{user_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == user_id
        assert data["name"] == sample_user.name
        assert data["user_info"] is not None
        
        # This should execute lines 47-55 (select query, scalar_one_or_none, return)

    @pytest.mark.unit
    def test_get_user_not_found_line_52_53(self, test_client: TestClient):
        """Target lines 52-53 in user_routes.py - HTTPException for user not found."""
        response = test_client.get("/user/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "User not found" in data["detail"]
        
        # This should execute lines 52-53 (if user is None and HTTPException)

    @pytest.mark.unit
    def test_get_all_users_lines_63_65(self, test_client: TestClient, multiple_users):
        """Target lines 63-65 in user_routes.py - scalars().all() and return."""
        response = test_client.get("/users")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == len(multiple_users)
        
        # Verify all users have user_info loaded (proves selectinload worked)
        for user_data in data:
            assert "user_info" in user_data
            assert user_data["user_info"] is not None
        
        # This should execute lines 63-65 (scalars().all() and return users)

    @pytest.mark.unit
    def test_user_creation_followed_by_retrieval(self, test_client: TestClient):
        """Test creating a user then retrieving it to hit both code paths."""
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
        
        # This should hit lines 33-40 (create_user selectinload)
        
        # Now retrieve the user
        get_response = test_client.get(f"/user/{user_id}")
        assert get_response.status_code == 200
        retrieved_user = get_response.json()
        
        assert retrieved_user["id"] == user_id
        assert retrieved_user["name"] == user_data["name"]
        assert retrieved_user["user_info"]["address"] == user_data["address"]
        
        # This should hit lines 47-55 (get_user function)

    @pytest.mark.unit
    def test_multiple_user_operations_comprehensive(self, test_client: TestClient):
        """Comprehensive test hitting all user route operations."""
        # Test get all users (empty)
        response = test_client.get("/users")
        assert response.status_code == 200
        # Should hit lines 63-65
        
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
            # Each creation should hit lines 33-40
        
        # Get each user individually
        for user_id in created_user_ids:
            get_response = test_client.get(f"/user/{user_id}")
            assert get_response.status_code == 200
            # Each get should hit lines 47-55
        
        # Get all users (should have 3 now)
        all_response = test_client.get("/users")
        assert all_response.status_code == 200
        all_users = all_response.json()
        assert len(all_users) >= 3
        # Should hit lines 63-65
        
        # Test user not found
        notfound_response = test_client.get("/user/99999")
        assert notfound_response.status_code == 404
        # Should hit lines 52-53

    @pytest.mark.unit
    def test_user_with_none_bio(self, test_client: TestClient):
        """Test user creation with None bio to ensure all code paths."""
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
        
        # This should execute the selectinload code path (lines 33-40)

    @pytest.mark.unit
    def test_user_edge_cases_for_coverage(self, test_client: TestClient):
        """Test edge cases to ensure complete coverage."""
        # Create user with very specific data to ensure code path execution
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
            
            # Immediately retrieve user to test both paths
            get_response = test_client.get(f"/user/{user_id}")
            assert get_response.status_code == 200
            
            # Get all users to test that path too
            all_response = test_client.get("/users")
            assert all_response.status_code == 200
            
        # Test invalid user ID
        invalid_response = test_client.get("/user/999999")
        assert invalid_response.status_code == 404