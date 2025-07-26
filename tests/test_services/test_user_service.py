"""
Tests for UserService class.

This module tests all UserService methods to ensure they work correctly
with the @Transactional decorator and maintain the same functionality
as the original route implementations.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_playground_poc.services.user_service import UserService
from fastapi_playground_poc.schemas import UserCreate


class TestUserService:
    """Test class for UserService operations."""

    def setup_method(self):
        """Set up UserService instance for each test."""
        self.user_service = UserService()

    @pytest.mark.unit
    async def test_get_user_success(self, sample_user, mock_transactional_db):
        """Test get_user method with existing user."""
        user_id = sample_user.id
        
        with mock_transactional_db:
            result = await self.user_service.get_user(user_id)
        
        assert result is not None
        assert result.id == user_id
        assert result.name == sample_user.name
        assert result.user_info is not None
        assert result.user_info.address == sample_user.user_info.address

    @pytest.mark.unit
    async def test_get_user_not_found(self, mock_transactional_db):
        """Test get_user method with non-existent user."""
        non_existent_id = 99999
        
        with mock_transactional_db:
            result = await self.user_service.get_user(non_existent_id)
        
        assert result is None

    @pytest.mark.unit
    async def test_get_all_users_empty(self, mock_transactional_db):
        """Test get_all_users method with empty database."""
        with mock_transactional_db:
            result = await self.user_service.get_all_users()
        
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    async def test_get_all_users_with_data(self, multiple_users, mock_transactional_db):
        """Test get_all_users method with existing users."""
        with mock_transactional_db:
            result = await self.user_service.get_all_users()
        
        assert isinstance(result, list)
        assert len(result) == len(multiple_users)
        
        # Verify all users have user_info loaded
        for user in result:
            assert user.user_info is not None
            assert hasattr(user.user_info, 'address')

    @pytest.mark.unit
    async def test_create_user_success(self, mock_transactional_db):
        """Test create_user method with valid data."""
        user_data = UserCreate(
            name="Test User",
            address="123 Test Street",
            bio="Test bio"
        )
        
        with mock_transactional_db:
            result = await self.user_service.create_user(user_data)
        
        assert result is not None
        assert result.name == user_data.name
        assert result.user_info is not None
        assert result.user_info.address == user_data.address
        assert result.user_info.bio == user_data.bio
        assert isinstance(result.id, int)

    @pytest.mark.unit
    async def test_create_user_minimal_data(self, mock_transactional_db):
        """Test create_user method with minimal required data."""
        user_data = UserCreate(
            name="Minimal User",
            address="456 Minimal Street"
            # bio is optional
        )
        
        with mock_transactional_db:
            result = await self.user_service.create_user(user_data)
        
        assert result is not None
        assert result.name == user_data.name
        assert result.user_info is not None
        assert result.user_info.address == user_data.address
        assert result.user_info.bio is None