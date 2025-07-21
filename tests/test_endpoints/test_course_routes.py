"""
Tests for course-related API endpoints.

This module tests all course CRUD operations including:
- Creating courses
- Retrieving individual courses with enrolled users
- Retrieving all courses
- Updating courses
- Deleting courses
- Error handling for non-existent courses
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient


class TestCourseEndpoints:
    """Test class for course-related endpoints."""

    @pytest.mark.unit
    def test_create_course_success(self, test_client: TestClient):
        """Test successful course creation."""
        course_data = {
            "name": "Advanced Python Programming",
            "author_name": "Dr. Sarah Wilson",
            "price": "199.99",
        }

        response = test_client.post("/course", json=course_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == course_data["name"]
        assert data["author_name"] == course_data["author_name"]
        assert float(data["price"]) == float(course_data["price"])
        assert "id" in data
        assert isinstance(data["id"], int)

    @pytest.mark.unit
    def test_create_course_invalid_data(self, test_client: TestClient):
        """Test course creation with invalid data."""
        # Missing required fields
        invalid_data = {
            "name": "Incomplete Course"
            # Missing author_name and price
        }

        response = test_client.post("/course", json=invalid_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.unit
    def test_create_course_invalid_price(self, test_client: TestClient):
        """Test course creation with invalid price format."""
        invalid_data = {
            "name": "Test Course",
            "author_name": "Test Author",
            "price": "invalid_price",
        }

        response = test_client.post("/course", json=invalid_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.unit
    def test_get_course_by_id_success(self, test_client: TestClient, sample_course):
        """Test retrieving a course by ID."""
        course_id = sample_course.id

        response = test_client.get(f"/course/{course_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == course_id
        assert data["name"] == sample_course.name
        assert data["author_name"] == sample_course.author_name
        assert float(data["price"]) == float(sample_course.price)
        assert "users" in data
        assert isinstance(data["users"], list)

    @pytest.mark.unit
    def test_get_course_by_id_not_found(self, test_client: TestClient):
        """Test retrieving a non-existent course."""
        non_existent_id = 99999

        response = test_client.get(f"/course/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_all_courses_empty(self, test_client: TestClient):
        """Test retrieving all courses when database is empty."""
        response = test_client.get("/courses")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.unit
    def test_get_all_courses_with_data(self, test_client: TestClient, multiple_courses):
        """Test retrieving all courses when courses exist."""
        response = test_client.get("/courses")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == len(multiple_courses)

        # Verify all courses are returned
        for course_data in data:
            assert "id" in course_data
            assert "name" in course_data
            assert "author_name" in course_data
            assert "price" in course_data

    @pytest.mark.unit
    def test_update_course_success(self, test_client: TestClient, sample_course):
        """Test successful course update."""
        course_id = sample_course.id
        update_data = {
            "name": "Updated Course Name",
            "price": "299.99",
            # author_name not updated
        }

        response = test_client.put(f"/course/{course_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == course_id
        assert data["name"] == update_data["name"]
        assert float(data["price"]) == float(update_data["price"])
        assert data["author_name"] == sample_course.author_name  # Unchanged

    @pytest.mark.unit
    def test_update_course_partial(self, test_client: TestClient, sample_course):
        """Test partial course update (only one field)."""
        course_id = sample_course.id
        update_data = {"price": "149.99"}

        response = test_client.put(f"/course/{course_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == course_id
        assert float(data["price"]) == float(update_data["price"])
        assert data["name"] == sample_course.name  # Unchanged
        assert data["author_name"] == sample_course.author_name  # Unchanged

    @pytest.mark.unit
    def test_update_course_not_found(self, test_client: TestClient):
        """Test updating a non-existent course."""
        non_existent_id = 99999
        update_data = {"name": "Updated Course"}

        response = test_client.put(f"/course/{non_existent_id}", json=update_data)

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_delete_course_success(self, test_client: TestClient, sample_course):
        """Test successful course deletion."""
        course_id = sample_course.id

        response = test_client.delete(f"/course/{course_id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert str(course_id) in data["message"]

        # Verify course is actually deleted
        get_response = test_client.get(f"/course/{course_id}")
        assert get_response.status_code == 404

    @pytest.mark.unit
    def test_delete_course_not_found(self, test_client: TestClient):
        """Test deleting a non-existent course."""
        non_existent_id = 99999

        response = test_client.delete(f"/course/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_course_price_precision(self, test_client: TestClient):
        """Test that course prices maintain proper decimal precision."""
        course_data = {
            "name": "Precision Test Course",
            "author_name": "Test Author",
            "price": "123.45",
        }

        response = test_client.post("/course", json=course_data)

        assert response.status_code == 200
        data = response.json()

        # Verify price precision is maintained
        assert data["price"] == "123.45"

    @pytest.mark.unit
    def test_course_data_types(self, test_client: TestClient):
        """Test that course endpoints return correct data types."""
        course_data = {
            "name": "Data Types Test",
            "author_name": "Type Tester",
            "price": "99.99",
        }

        response = test_client.post("/course", json=course_data)
        assert response.status_code == 200
        data = response.json()

        # Verify data types
        assert isinstance(data["id"], int)
        assert isinstance(data["name"], str)
        assert isinstance(data["author_name"], str)
        assert isinstance(data["price"], str)  # Decimal is serialized as string

    @pytest.mark.unit
    def test_course_with_special_characters(self, test_client: TestClient):
        """Test course creation with special characters."""
        course_data = {
            "name": "Français & Español Programming 🚀",
            "author_name": "José María O'Connor-Smith",
            "price": "199.99",
        }

        response = test_client.post("/course", json=course_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == course_data["name"]
        assert data["author_name"] == course_data["author_name"]

    @pytest.mark.unit
    def test_course_update_empty_data(self, test_client: TestClient, sample_course):
        """Test course update with empty data (should not change anything)."""
        course_id = sample_course.id
        original_name = sample_course.name
        original_author = sample_course.author_name
        original_price = sample_course.price

        response = test_client.put(f"/course/{course_id}", json={})

        assert response.status_code == 200
        data = response.json()

        # Verify nothing changed
        assert data["name"] == original_name
        assert data["author_name"] == original_author
        assert float(data["price"]) == float(original_price)
