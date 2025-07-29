"""Dedicated startup module for running migrations before the app starts accepting requests."""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

# Add src to path so alembic can find our modules
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

import subprocess
from fastapi_playground_poc.config import settings
logger = logging.getLogger(__name__)


async def run_migrations() -> None:
    """Run database migrations using alembic CLI."""
    logger.info("Starting database migration check...")
    
    try:
        # Get alembic working directory (alembic folder)
        alembic_dir = Path(__file__).parent / "alembic"
        
        if not alembic_dir.exists():
            raise FileNotFoundError(f"Alembic directory not found at {alembic_dir}")
        
        # Set up environment variables for alembic
        env = {
            **dict(os.environ),
            "DATABASE_URL": settings.database_url,
        }
        
        # Run alembic upgrade using subprocess
        def run_alembic_upgrade():
            result = subprocess.run(
                ["python", "-m", "alembic", "upgrade", "head"],
                cwd=str(alembic_dir),  # Run from alembic directory
                env=env,
                # Don't capture output so logs appear directly in console
                timeout=60  # 60 second timeout
            )
            return result
        
        # Run in executor to avoid blocking async event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_alembic_upgrade)
        
        if result.returncode != 0:
            logger.error(f"Alembic upgrade failed with return code {result.returncode}")
            raise subprocess.CalledProcessError(result.returncode, ["alembic", "upgrade", "head"])
        
        logger.info("Database migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to run migrations: {type(e).__name__}: {e}")
        raise RuntimeError("Database migrations failed - cannot start application") from e


async def startup_event() -> None:
    """FastAPI startup event handler that runs migrations."""
    logger.info("Performing startup tasks...")
    
    try:
        await run_migrations()
        logger.info("Startup tasks completed successfully")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


def sync_startup() -> None:
    """Synchronous wrapper for running migrations at startup.
    
    This can be used for non-async startup scripts or command line tools.
    """
    logger.info("Running synchronous startup...")
    asyncio.run(startup_event())


if __name__ == "__main__":
    # Allow running migrations directly: python -m fastapi_playground_poc.startup
    sync_startup()