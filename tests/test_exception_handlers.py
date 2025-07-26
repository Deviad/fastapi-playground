"""
Tests for global exception handlers.

This module tests all exception handling scenarios including:
- ValidationError handling (Pydantic validation errors)
- IntegrityError handling (SQLAlchemy constraint violations)
- HTTPException handling (FastAPI HTTP exceptions)
- General exception handling (unexpected errors)
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import Request, HTTPException, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from fastapi_playground_poc.exception_handlers import (
    validation_exception_handler,
    integrity_error_handler,
    http_exception_handler,
    general_exception_handler,
    register_exception_handlers,
)


class TestValidationExceptionHandler:
    """Test class for ValidationError exception handler."""

    @pytest.mark.unit
    async def test_validation_exception_handler_basic(self):
        """Test basic ValidationError handling."""
        # Create a mock request
        request = Mock(spec=Request)
        request.url = "http://test.com/api/user"

        # Create a mock ValidationError
        validation_error = Mock(spec=ValidationError)
        validation_error.errors.return_value = [
            {"loc": ["name"], "msg": "field required", "type": "value_error.missing"}
        ]

        # Test the handler
        with patch('fastapi_playground_poc.exception_handlers.logger') as mock_logger:
            response = await validation_exception_handler(request, validation_error)

        # Verify response
        assert response.status_code == 400
        response_data = response.body.decode()
        assert "Validation Error" in response_data
        assert "Invalid input data" in response_data

        # Verify logging
        mock_logger.warning.assert_called_once()

    @pytest.mark.unit
    async def test_validation_exception_handler_multiple_errors(self):
        """Test ValidationError handling with multiple validation errors."""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/course"

        validation_error = Mock(spec=ValidationError)
        validation_error.errors.return_value = [
            {"loc": ["name"], "msg": "field required", "type": "value_error.missing"},
            {"loc": ["price"], "msg": "not a valid decimal", "type": "type_error.decimal"}
        ]

        response = await validation_exception_handler(request, validation_error)

        assert response.status_code == 400
        response_data = response.body.decode()
        assert "Validation Error" in response_data
        assert "Invalid input data" in response_data


class TestIntegrityErrorHandler:
    """Test class for IntegrityError exception handler."""

    @pytest.mark.unit
    async def test_integrity_error_handler_duplicate_key(self):
        """Test IntegrityError handling for duplicate key violations."""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/enrollment"

        # Mock IntegrityError with duplicate key message
        integrity_error = Mock(spec=IntegrityError)
        integrity_error.orig = Mock()
        integrity_error.orig.__str__ = Mock(return_value="UNIQUE constraint failed: enrollments.user_id_course_id")

        with patch('fastapi_playground_poc.exception_handlers.logger') as mock_logger:
            response = await integrity_error_handler(request, integrity_error)

        assert response.status_code == 409
        response_data = response.body.decode()
        assert "Conflict" in response_data
        assert "Resource already exists" in response_data

        mock_logger.warning.assert_called_once()

    @pytest.mark.unit
    async def test_integrity_error_handler_unique_constraint(self):
        """Test IntegrityError handling for unique constraint violations."""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/user"

        integrity_error = Mock(spec=IntegrityError)
        integrity_error.orig = Mock()
        integrity_error.orig.__str__ = Mock(return_value="duplicate key value violates unique constraint")

        response = await integrity_error_handler(request, integrity_error)

        assert response.status_code == 409
        response_data = response.body.decode()
        assert "Conflict" in response_data
        assert "Resource already exists" in response_data

    @pytest.mark.unit
    async def test_integrity_error_handler_general_constraint(self):
        """Test IntegrityError handling for general constraint violations."""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/user"

        integrity_error = Mock(spec=IntegrityError)
        integrity_error.orig = Mock()
        integrity_error.orig.__str__ = Mock(return_value="foreign key constraint failed")

        response = await integrity_error_handler(request, integrity_error)

        assert response.status_code == 409
        response_data = response.body.decode()
        assert "Conflict" in response_data
        assert "Data integrity constraint violation" in response_data

    @pytest.mark.unit
    async def test_integrity_error_handler_no_orig(self):
        """Test IntegrityError handling when orig is None."""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/course"

        integrity_error = Mock(spec=IntegrityError)
        integrity_error.orig = None
        integrity_error.__str__ = Mock(return_value="Some generic integrity error")

        response = await integrity_error_handler(request, integrity_error)

        assert response.status_code == 409
        response_data = response.body.decode()
        assert "Conflict" in response_data
        assert "Data integrity constraint violation" in response_data


class TestHttpExceptionHandler:
    """Test class for HTTPException handler."""

    @pytest.mark.unit
    async def test_http_exception_handler_404(self):
        """Test HTTPException handling for 404 Not Found."""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/user/999"

        http_exception = HTTPException(status_code=404, detail="User not found")

        with patch('fastapi_playground_poc.exception_handlers.logger') as mock_logger:
            response = await http_exception_handler(request, http_exception)

        assert response.status_code == 404
        response_data = response.body.decode()
        assert "HTTP Error" in response_data
        assert "User not found" in response_data

        mock_logger.info.assert_called_once()

    @pytest.mark.unit
    async def test_http_exception_handler_400(self):
        """Test HTTPException handling for 400 Bad Request."""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/course"

        http_exception = HTTPException(status_code=400, detail="Invalid course data")

        response = await http_exception_handler(request, http_exception)

        assert response.status_code == 400
        response_data = response.body.decode()
        assert "HTTP Error" in response_data
        assert "Invalid course data" in response_data

    @pytest.mark.unit
    async def test_http_exception_handler_409(self):
        """Test HTTPException handling for 409 Conflict."""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/enrollment"

        http_exception = HTTPException(status_code=409, detail="User is already enrolled in the course")

        response = await http_exception_handler(request, http_exception)

        assert response.status_code == 409
        response_data = response.body.decode()
        assert "HTTP Error" in response_data
        assert "User is already enrolled in the course" in response_data


class TestGeneralExceptionHandler:
    """Test class for general exception handler."""

    @pytest.mark.unit
    async def test_general_exception_handler_runtime_error(self):
        """Test general exception handling for RuntimeError."""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/user"

        runtime_error = RuntimeError("Unexpected runtime error")

        with patch('fastapi_playground_poc.exception_handlers.logger') as mock_logger:
            response = await general_exception_handler(request, runtime_error)

        assert response.status_code == 500
        response_data = response.body.decode()
        assert "Internal Server Error" in response_data
        assert "An unexpected error occurred" in response_data

        mock_logger.error.assert_called_once()

    @pytest.mark.unit
    async def test_general_exception_handler_value_error(self):
        """Test general exception handling for ValueError."""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/course"

        value_error = ValueError("Invalid value provided")

        with patch('fastapi_playground_poc.exception_handlers.logger') as mock_logger:
            response = await general_exception_handler(request, value_error)

        assert response.status_code == 500
        response_data = response.body.decode()
        assert "Internal Server Error" in response_data
        assert "An unexpected error occurred" in response_data

        mock_logger.error.assert_called_once()

    @pytest.mark.unit
    async def test_general_exception_handler_type_error(self):
        """Test general exception handling for TypeError."""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/enrollment"

        type_error = TypeError("'NoneType' object is not callable")

        with patch('fastapi_playground_poc.exception_handlers.logger') as mock_logger:
            response = await general_exception_handler(request, type_error)

        assert response.status_code == 500
        response_data = response.body.decode()
        assert "Internal Server Error" in response_data
        assert "An unexpected error occurred" in response_data

        mock_logger.error.assert_called_once()


class TestRegisterExceptionHandlers:
    """Test class for exception handler registration."""

    @pytest.mark.unit
    def test_register_exception_handlers(self):
        """Test that all exception handlers are properly registered."""
        # Create a mock FastAPI app
        mock_app = Mock(spec=FastAPI)

        with patch('fastapi_playground_poc.exception_handlers.logger') as mock_logger:
            register_exception_handlers(mock_app)

        # Verify all handlers were registered
        assert mock_app.add_exception_handler.call_count == 4

        # Verify the calls included the right exception types and handlers
        calls = mock_app.add_exception_handler.call_args_list
        
        # Check that ValidationError, IntegrityError, HTTPException, and Exception were registered
        exception_types = [call[0][0] for call in calls]
        assert ValidationError in exception_types
        assert IntegrityError in exception_types
        assert HTTPException in exception_types
        assert Exception in exception_types

        # Verify logging
        mock_logger.info.assert_called_once_with("Global exception handlers registered successfully")

    @pytest.mark.unit
    def test_register_exception_handlers_multiple_calls(self):
        """Test that register_exception_handlers can be called multiple times."""
        mock_app = Mock(spec=FastAPI)

        # Register handlers twice
        register_exception_handlers(mock_app)
        register_exception_handlers(mock_app)

        # Should have been called 8 times total (4 handlers × 2 calls)
        assert mock_app.add_exception_handler.call_count == 8


class TestExceptionHandlersIntegration:
    """Integration tests for exception handlers with FastAPI."""

    @pytest.mark.unit
    def test_exception_handlers_integration_validation_error(self, test_client: TestClient):
        """Test ValidationError handling through FastAPI integration."""
        # Try to create a user with invalid data to trigger ValidationError
        invalid_data = {
            "name": 123,  # Should be string
            "address": ["not", "a", "string"],  # Should be string
        }

        response = test_client.post("/user", json=invalid_data)
        
        assert response.status_code == 422  # FastAPI's default for validation errors
        data = response.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_exception_handlers_integration_http_exception(self, test_client: TestClient, mock_transactional_db):
        """Test HTTPException handling through FastAPI integration."""
        with mock_transactional_db:
            # Try to get a non-existent user to trigger HTTPException
            response = test_client.get("/user/99999")
            
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_exception_handlers_integration_integrity_error(self, test_client: TestClient, sample_enrollment, mock_transactional_db):
        """Test IntegrityError handling through FastAPI integration."""
        with mock_transactional_db:
            # Try to create a duplicate enrollment to trigger IntegrityError
            user_id = sample_enrollment.user_id
            course_id = sample_enrollment.course_id

            response = test_client.post(f"/user/{user_id}/enroll/{course_id}")
            
            assert response.status_code == 409  # Should be handled as conflict
            data = response.json()
            assert "detail" in data
            assert "already enrolled" in data["detail"].lower()