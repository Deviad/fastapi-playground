"""
Simple test to debug coverage measurement.
"""

import pytest
from fastapi.testclient import TestClient


class TestSimpleCoverageDebug:
    """Simple test to verify coverage measurement is working."""

    @pytest.mark.unit
    def test_simple_course_creation(self, test_client: TestClient):
        """Simple test that should definitely hit course creation lines."""
        print("Making POST request to /course")
        response = test_client.post("/course", json={
            "name": "Debug Course",
            "author_name": "Debug Author", 
            "price": "99.99"
        })
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Debug Course"

    @pytest.mark.unit
    def test_simple_course_not_found(self, test_client: TestClient):
        """Simple test that should hit course not found exception."""
        print("Making GET request to /course/99999")
        response = test_client.get("/course/99999")
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.json()}")
        assert response.status_code == 404