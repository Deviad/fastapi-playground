"""
Environment configuration module for fastapi-playground-poc using Pydantic BaseSettings.

This module provides configuration utilities using Pydantic BaseSettings for
automatic environment variable parsing and validation.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings."""
    
    environment: str = Field(default="local", alias="ENVIRONMENT")
    
    # Database configuration
    database_url: str = Field(
        default="postgresql+asyncpg://dev-user:password@localhost:5432/dev_db",
        env="DATABASE_URL"
    )
    
    # Define which environments should have swagger enabled
    allowed_swagger_environments: List[str] = ["local", "dev"]
    
    
    def __is_swagger_enabled(self) -> bool:
        """Check if swagger should be enabled based on the environment."""
        return self.environment.lower() in self.allowed_swagger_environments
    
    @property
    def should_include_docs(self) -> bool:
        """Check if documentation endpoints should be included."""
        return self.__is_swagger_enabled()

    """Pydantic configuration."""
    model_config = SettingsConfigDict(case_sensitive = False)

# Create a singleton instance
settings = Settings()
