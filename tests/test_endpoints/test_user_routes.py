"""
Tests for user-related API endpoints.

This module tests all user CRUD operations including:
- Creating users with user info
- Retrieving individual users
- Retrieving all users
- Error handling for non-existent users
"""

import pytest
from fastapi.testclient import TestClient


class TestUserEndpoints:
    """Test class for user-related endpoints."""

    @pytest.mark.unit
    def test_create_user_success(self, test_client: TestClient):
        """Test successful user creation with user info."""
        user_data = {
            "name": "Alice Johnson",
            "address": "456 Oak Avenue",
            "bio": "Software engineer with 5 years experience",
        }

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
    def test_create_user_minimal_data(self, test_client: TestClient):
        """Test user creation with minimal required data."""
        user_data = {
            "name": "Bob Smith",
            "address": "789 Pine Street",
            # bio is optional
        }

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
    def test_get_user_by_id_success(self, test_client: TestClient, sample_user):
        """Test retrieving a user by ID."""
        user_id = sample_user.id

        response = test_client.get(f"/user/{user_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == user_id
        assert data["name"] == sample_user.name
        assert data["user_info"] is not None
        assert data["user_info"]["address"] == sample_user.user_info.address

    @pytest.mark.unit
    def test_get_user_by_id_not_found(self, test_client: TestClient):
        """Test retrieving a non-existent user."""
        non_existent_id = 99999

        response = test_client.get(f"/user/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_all_users_empty(self, test_client: TestClient):
        """Test retrieving all users when database is empty."""
        response = test_client.get("/users")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.unit
    def test_get_all_users_with_data(self, test_client: TestClient, multiple_users):
        """Test retrieving all users when users exist."""
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
    def test_get_all_users_single_user(self, test_client: TestClient, sample_user):
        """Test retrieving all users with a single user."""
        response = test_client.get("/users")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["id"] == sample_user.id
        assert data[0]["name"] == sample_user.name

    @pytest.mark.unit
    def test_user_creation_cascade_behavior(self, test_client: TestClient):
        """Test that user creation properly cascades to user_info."""
        user_data = {
            "name": "Cascade Test User",
            "address": "123 Cascade Street",
            "bio": "Testing cascade behavior",
        }

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
    def test_user_endpoints_data_types(self, test_client: TestClient):
        """Test that user endpoints return correct data types."""
        user_data = {
            "name": "Type Test User",
            "address": "456 Type Street",
            "bio": "Testing data types",
        }

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
    def test_user_creation_with_special_characters(self, test_client: TestClient):
        """Test user creation with special characters in data."""
        user_data = {
            "name": "José María O'Connor-Smith",
            "address": "123 Café Street, Apt #4B",
            "bio": "Bio with émojis 🚀 and special chars: @#$%^&*()",
        }

        response = test_client.post("/user", json=user_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == user_data["name"]
        assert data["user_info"]["address"] == user_data["address"]
        assert data["user_info"]["bio"] == user_data["bio"]
