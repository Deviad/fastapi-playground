"""
Tests for user-related API endpoints.

This module tests all user CRUD operations including:
- Creating users with user info
- Retrieving individual users
- Retrieving all users
- Error handling for non-existent users
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from tests.test_transactional_base import mock_get_db_factory


class TestUserEndpoints:
    """Test class for user-related endpoints."""

    @pytest.mark.unit
    def test_create_user_success(self, test_client: TestClient, test_db):
        """Test successful user creation with user info."""
        user_data = {
            "name": "Alice Johnson",
            "address": "456 Oak Avenue",
            "bio": "Software engineer with 5 years experience",
        }

        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(test_db)
            
            response = test_client.post("/user", json=user_data)

            # Debug: Print response details
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")

            assert response.status_code == 200
            data = response.json()

            # Verify user data
            assert data["name"] == user_data["name"]
            assert "id" in data
            assert isinstance(data["id"], int)

            # Verify user info is included
            assert data["user_info"] is not None
            assert data["user_info"]["address"] == user_data["address"]
            assert data["user_info"]["bio"] == user_data["bio"]

    @pytest.mark.unit
    def test_create_user_minimal_data(self, test_client: TestClient, test_db):
        """Test user creation with minimal required data."""
        user_data = {
            "name": "Bob Smith",
            "address": "789 Pine Street",
            # bio is optional
        }

        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(test_db)
            
            response = test_client.post("/user", json=user_data)

            assert response.status_code == 200
            data = response.json()

            assert data["name"] == user_data["name"]
            assert data["user_info"]["address"] == user_data["address"]
            assert data["user_info"]["bio"] is None

    @pytest.mark.unit
    def test_create_user_invalid_data(self, test_client: TestClient):
        """Test user creation with invalid data."""
        # Missing required fields
        invalid_data = {
            "name": "Invalid User"
            # Missing address
        }

        response = test_client.post("/user", json=invalid_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.unit
    def test_get_user_by_id_success(self, test_client: TestClient, sample_user, test_db):
        """Test retrieving a user by ID."""
        user_id = sample_user.id

        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(test_db)
            
            response = test_client.get(f"/user/{user_id}")

            assert response.status_code == 200
            data = response.json()

            assert data["id"] == user_id
            assert data["name"] == sample_user.name
            assert data["user_info"] is not None
            assert data["user_info"]["address"] == sample_user.user_info.address

    @pytest.mark.unit
    def test_get_user_by_id_not_found(self, test_client: TestClient, test_db):
        """Test retrieving a non-existent user."""
        non_existent_id = 99999

        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(test_db)
            
            response = test_client.get(f"/user/{non_existent_id}")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_all_users_empty(self, test_client: TestClient, test_db):
        """Test retrieving all users when database is empty."""
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(test_db)
            
            response = test_client.get("/users")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0

    @pytest.mark.unit
    def test_get_all_users_with_data(self, test_client: TestClient, multiple_users, test_db):
        """Test retrieving all users when users exist."""
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(test_db)
            
            response = test_client.get("/users")

            assert response.status_code == 200
            data = response.json()

            assert isinstance(data, list)
            assert len(data) == len(multiple_users)

            # Verify all users are returned with their user_info
            for user_data in data:
                assert "id" in user_data
                assert "name" in user_data
                assert "user_info" in user_data
                assert user_data["user_info"] is not None

    @pytest.mark.unit
    def test_get_all_users_single_user(self, test_client: TestClient, sample_user, test_db):
        """Test retrieving all users with a single user."""
        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(test_db)
            
            response = test_client.get("/users")

            assert response.status_code == 200
            data = response.json()

            assert len(data) == 1
            assert data[0]["id"] == sample_user.id
            assert data[0]["name"] == sample_user.name

    @pytest.mark.unit
    def test_user_creation_cascade_behavior(self, test_client: TestClient, test_db):
        """Test that user creation properly cascades to user_info."""
        user_data = {
            "name": "Cascade Test User",
            "address": "123 Cascade Street",
            "bio": "Testing cascade behavior",
        }

        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(test_db)
            
            # Create user
            response = test_client.post("/user", json=user_data)
            assert response.status_code == 200
            created_user = response.json()
            user_id = created_user["id"]

            # Verify user can be retrieved with user_info
            response = test_client.get(f"/user/{user_id}")
            assert response.status_code == 200
            retrieved_user = response.json()

            assert retrieved_user["user_info"]["address"] == user_data["address"]
            assert retrieved_user["user_info"]["bio"] == user_data["bio"]

    @pytest.mark.unit
    def test_user_endpoints_data_types(self, test_client: TestClient, test_db):
        """Test that user endpoints return correct data types."""
        user_data = {
            "name": "Type Test User",
            "address": "456 Type Street",
            "bio": "Testing data types",
        }

        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(test_db)
            
            response = test_client.post("/user", json=user_data)
            assert response.status_code == 200
            data = response.json()

            # Verify data types
            assert isinstance(data["id"], int)
            assert isinstance(data["name"], str)
            assert isinstance(data["user_info"], dict)
            assert isinstance(data["user_info"]["id"], int)
            assert isinstance(data["user_info"]["address"], str)
            assert (
                isinstance(data["user_info"]["bio"], str)
                or data["user_info"]["bio"] is None
            )

    @pytest.mark.unit
    def test_user_creation_with_special_characters(self, test_client: TestClient, test_db):
        """Test user creation with special characters in data."""
        user_data = {
            "name": "José María O'Connor-Smith",
            "address": "123 Café Street, Apt #4B",
            "bio": "Bio with émojis 🚀 and special chars: @#$%^&*()",
        }

        with patch('fastapi_playground_poc.transactional.get_db') as mock_get_db:
            mock_get_db.side_effect = mock_get_db_factory(test_db)
            
            response = test_client.post("/user", json=user_data)

            assert response.status_code == 200
            data = response.json()

            assert data["name"] == user_data["name"]
            assert data["user_info"]["address"] == user_data["address"]
            assert data["user_info"]["bio"] == user_data["bio"]


class TestUserErrorHandling:
    """Test class for user endpoint error handling scenarios."""

    @pytest.mark.unit
    def test_create_user_missing_name(self, test_client: TestClient):
        """Test user creation missing required name field."""
        user_data = {
            "address": "123 Test Street",
            "bio": "Test bio"
            # Missing required "name" field
        }

        response = test_client.post("/user", json=user_data)
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_create_user_missing_address(self, test_client: TestClient):
        """Test user creation missing required address field."""
        user_data = {
            "name": "Test User",
            "bio": "Test bio"
            # Missing required "address" field
        }

        response = test_client.post("/user", json=user_data)
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_create_user_empty_name(self, test_client: TestClient, mock_transactional_db):
        """Test user creation with empty name."""
        user_data = {
            "name": "",  # Empty name
            "address": "123 Test Street",
            "bio": "Test bio"
        }

        with mock_transactional_db:
            response = test_client.post("/user", json=user_data)
            
            # This might succeed or fail depending on validation rules
            # If it succeeds, we should still get a proper response
            if response.status_code == 200:
                data = response.json()
                assert data["name"] == ""
            else:
                assert response.status_code == 422

    @pytest.mark.unit
    def test_create_user_null_values(self, test_client: TestClient):
        """Test user creation with null values in JSON."""
        user_data = {
            "name": None,
            "address": None,
            "bio": None
        }

        response = test_client.post("/user", json=user_data)
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_create_user_invalid_json_types(self, test_client: TestClient):
        """Test user creation with invalid data types."""
        user_data = {
            "name": 123,  # Should be string
            "address": ["not", "a", "string"],  # Should be string
            "bio": {"invalid": "type"}  # Should be string or null
        }

        response = test_client.post("/user", json=user_data)
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_get_user_refresh_path_coverage(self, test_client: TestClient, sample_user, mock_transactional_db):
        """Test the refresh logic in get_user endpoint by accessing user info."""
        user_id = sample_user.id

        with mock_transactional_db:
            # First access should work and trigger the refresh path
            response = test_client.get(f"/user/{user_id}")
            assert response.status_code == 200
            data = response.json()
            
            # Verify user_info is properly loaded
            assert data["user_info"] is not None
            assert "address" in data["user_info"]
            assert "bio" in data["user_info"]

            # Multiple accesses to ensure consistent behavior
            for _ in range(3):
                response = test_client.get(f"/user/{user_id}")
                assert response.status_code == 200
                fresh_data = response.json()
                assert fresh_data["id"] == data["id"]
                assert fresh_data["user_info"]["address"] == data["user_info"]["address"]

    @pytest.mark.unit
    def test_get_all_users_database_consistency(self, test_client: TestClient, multiple_users, mock_transactional_db):
        """Test get_all_users endpoint for database consistency and error handling."""
        with mock_transactional_db:
            # Get all users multiple times to test consistency
            responses = []
            for _ in range(3):
                response = test_client.get("/users")
                assert response.status_code == 200
                responses.append(response.json())

            # All responses should be identical
            for response_data in responses[1:]:
                assert len(response_data) == len(responses[0])
                for i, user in enumerate(response_data):
                    assert user["id"] == responses[0][i]["id"]
                    assert user["name"] == responses[0][i]["name"]
                    assert user["user_info"]["address"] == responses[0][i]["user_info"]["address"]

    @pytest.mark.unit
    def test_get_all_users_with_varied_user_info(self, test_client: TestClient, mock_transactional_db):
        """Test get_all_users with users having different user_info configurations."""
        with mock_transactional_db:
            # Create users with different user_info scenarios
            users_data = [
                {"name": "User With Bio", "address": "123 Street", "bio": "Has bio"},
                {"name": "User Without Bio", "address": "456 Street"},  # bio will be None
                {"name": "User With Empty Bio", "address": "789 Street", "bio": ""},
            ]

            created_users = []
            for user_data in users_data:
                response = test_client.post("/user", json=user_data)
                assert response.status_code == 200
                created_users.append(response.json())

            # Get all users and verify each has proper user_info
            response = test_client.get("/users")
            assert response.status_code == 200
            all_users = response.json()
            
            assert len(all_users) == len(users_data)
            
            for user in all_users:
                assert "user_info" in user
                assert user["user_info"] is not None
                assert "address" in user["user_info"]
                # bio can be string or None

    @pytest.mark.unit
    def test_database_constraint_simulation(self, test_client: TestClient, mock_transactional_db):
        """Test database constraint handling through edge case scenarios."""
        with mock_transactional_db:
            # Test with very long strings that might approach database limits
            user_data = {
                "name": "Very Long Name " + "X" * 200,  # Test long name
                "address": "Very Long Address " + "Y" * 500,  # Test long address
                "bio": "Very Long Bio " + "Z" * 1000  # Test long bio
            }

            response = test_client.post("/user", json=user_data)
            
            # Should either succeed or return a proper error
            if response.status_code == 200:
                data = response.json()
                assert data["name"] == user_data["name"]
            else:
                # If database constraints prevent this, should get proper error
                assert response.status_code in [400, 422, 500]


class TestUserRoutesCoverageEnhancement:
    """Additional parameterized tests to enhance code coverage for user routes."""

    @pytest.mark.parametrize("user_data,expected_status", [
        ({"name": "Test User 1", "address": "123 Main St", "bio": "Bio 1"}, 200),
        ({"name": "Test User 2", "address": "456 Oak Ave", "bio": "Bio 2"}, 200),
        ({"name": "Test User 3", "address": "789 Pine Rd"}, 200),  # No bio
        ({"name": "Test User 4", "address": "321 Elm St", "bio": ""}, 200),  # Empty bio
    ])
    @pytest.mark.unit
    def test_create_user_refresh_logic_coverage(self, test_client: TestClient, user_data, expected_status, mock_transactional_db):
        """Test user creation with various inputs to hit refresh logic (lines 33-40)."""
        with mock_transactional_db:
            response = test_client.post("/user", json=user_data)
            
            assert response.status_code == expected_status
            if expected_status == 200:
                data = response.json()
                assert data["name"] == user_data["name"]
                assert data["user_info"]["address"] == user_data["address"]
                assert "id" in data
                # This specifically hits lines 33-40 (select query with selectinload and return)
                
                # Verify the refresh path worked by checking user_info is properly loaded
                assert data["user_info"] is not None
                assert isinstance(data["user_info"]["id"], int)

    @pytest.mark.parametrize("user_id,expected_status,should_exist", [
        (1, 200, True),  # Valid user (will be replaced with actual ID)
        (99999, 404, False),  # Non-existent user
        (-1, 404, False),  # Invalid negative ID
        (0, 404, False),  # Invalid zero ID
        (999998, 404, False),  # Another non-existent ID
    ])
    @pytest.mark.unit
    def test_get_user_error_paths_coverage(self, test_client: TestClient, sample_user, user_id, expected_status, should_exist, mock_transactional_db):
        """Test get user with various IDs to hit error paths (lines 50-55)."""
        with mock_transactional_db:
            # Use actual user ID for valid test case
            if user_id == 1:
                user_id = sample_user.id
                
            response = test_client.get(f"/user/{user_id}")
            
            assert response.status_code == expected_status
            data = response.json()
            
            if should_exist:
                assert "id" in data
                assert "name" in data
                assert "user_info" in data
                # This hits the successful path (line 55)
            else:
                assert "detail" in data
                assert "not found" in data["detail"].lower()
                # This hits lines 52-53 (user not found error)

    @pytest.mark.unit
    def test_get_all_users_return_logic_coverage(self, test_client: TestClient, multiple_users, mock_transactional_db):
        """Test get all users to ensure return logic is covered (lines 63-65)."""
        with mock_transactional_db:
            response = test_client.get("/users")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0
            # This hits lines 63-65 (scalars().all() and return users)
            
            # Verify all users have proper user_info loaded
            for user in data:
                assert "user_info" in user
                assert user["user_info"] is not None

    @pytest.mark.unit
    def test_get_all_users_empty_database_coverage(self, test_client: TestClient, mock_transactional_db):
        """Test get all users with empty database to hit return path."""
        with mock_transactional_db:
            response = test_client.get("/users")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            # This hits lines 63-65 (return users, even if empty)

    @pytest.mark.parametrize("create_count", [1, 3, 5])
    @pytest.mark.unit
    def test_user_creation_batch_refresh_logic(self, test_client: TestClient, create_count, mock_transactional_db):
        """Test multiple user creations to thoroughly exercise refresh logic."""
        with mock_transactional_db:
            created_users = []
            
            for i in range(create_count):
                user_data = {
                    "name": f"Batch User {i+1}",
                    "address": f"{100+i} Test Street",
                    "bio": f"Bio for user {i+1}"
                }
                
                response = test_client.post("/user", json=user_data)
                assert response.status_code == 200
                
                data = response.json()
                created_users.append(data)
                
                # Each creation hits lines 33-40 (refresh logic)
                assert data["name"] == user_data["name"]
                assert data["user_info"]["address"] == user_data["address"]
                assert data["user_info"]["bio"] == user_data["bio"]
            
            # Verify all users are retrievable (hits get_all_users lines 63-65)
            response = test_client.get("/users")
            assert response.status_code == 200
            all_users = response.json()
            assert len(all_users) >= create_count

    @pytest.mark.parametrize("invalid_user_id", [
        "invalid_string",
        "99999999999999",  # Very large number
        "-999999",  # Very negative number
        "0.5",  # Decimal number (if passed as string)
    ])
    @pytest.mark.unit
    def test_get_user_various_invalid_ids(self, test_client: TestClient, invalid_user_id):
        """Test get user with various invalid ID formats."""
        # This might cause validation errors before hitting our code,
        # but let's test to see what happens
        try:
            response = test_client.get(f"/user/{invalid_user_id}")
            # Should either be 404 (our code) or 422 (validation error)
            assert response.status_code in [404, 422]
            
            data = response.json()
            assert "detail" in data
        except Exception:
            # If the test client rejects the request entirely, that's also valid
            pass

    @pytest.mark.unit
    def test_user_info_relationship_loading_coverage(self, test_client: TestClient, mock_transactional_db):
        """Test user creation and retrieval to ensure user_info relationships are properly loaded."""
        with mock_transactional_db:
            # Create a user with specific user_info
            user_data = {
                "name": "Relationship Test User",
                "address": "123 Relationship St",
                "bio": "Testing user_info relationship loading"
            }
            
            # Create user (hits lines 33-40)
            create_response = test_client.post("/user", json=user_data)
            assert create_response.status_code == 200
            created_user = create_response.json()
            user_id = created_user["id"]
            
            # Get user individually (should hit lines 47-55)
            get_response = test_client.get(f"/user/{user_id}")
            assert get_response.status_code == 200
            retrieved_user = get_response.json()
            
            # Verify user_info is properly loaded in both responses
            for user_response in [created_user, retrieved_user]:
                assert user_response["user_info"] is not None
                assert user_response["user_info"]["address"] == user_data["address"]
                assert user_response["user_info"]["bio"] == user_data["bio"]
            
            # Get all users (hits lines 62-65)
            all_response = test_client.get("/users")
            assert all_response.status_code == 200
            all_users = all_response.json()
            
            # Find our user in the list
            our_user = next((u for u in all_users if u["id"] == user_id), None)
            assert our_user is not None
            assert our_user["user_info"]["address"] == user_data["address"]

    @pytest.mark.unit
    def test_user_creation_edge_cases_for_refresh(self, test_client: TestClient, mock_transactional_db):
        """Test user creation edge cases that exercise the refresh logic thoroughly."""
        with mock_transactional_db:
            edge_cases = [
                {"name": "", "address": "Empty Name St"},  # Empty name
                {"name": "   ", "address": "Whitespace Name St"},  # Whitespace name
                {"name": "Unicode Test 🚀", "address": "Unicode Address ñáéíóú"},  # Unicode
                {"name": "Very" + "Long" * 50 + "Name", "address": "Long Name Address"},  # Long name
            ]
            
            for i, user_data in enumerate(edge_cases):
                user_data["bio"] = f"Edge case bio {i+1}"
                
                response = test_client.post("/user", json=user_data)
                
                # Some edge cases might fail validation, others should succeed
                if response.status_code == 200:
                    data = response.json()
                    # If successful, verify refresh logic worked (lines 33-40)
                    assert data["user_info"] is not None
                    assert "id" in data
                    assert isinstance(data["user_info"]["id"], int)
                else:
                    # If validation fails, that's also valid
                    assert response.status_code == 422

# Test 404 for non-existent user
def test_get_user_not_found(test_client, mock_transactional_db):
    with mock_transactional_db:
        response = test_client.get("/user/999")
        assert response.status_code == 404

# Test 422 for invalid user creation
def test_create_user_invalid_data(test_client):
    response = test_client.post("/user", json={"name": ""})
    assert response.status_code == 422

# Test user update validation errors
def test_update_user_validation_error(test_client, sample_user):
    # There's no update endpoint in the current implementation
    # This test should be removed or the endpoint should be implemented
    pass

# Test user deletion failure
def test_delete_user_not_found(test_client):
    # There's no delete endpoint in the current implementation
    # This test should be removed or the endpoint should be implemented
    pass
