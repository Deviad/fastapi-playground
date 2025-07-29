from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi_playground_poc.application.web.controller.user_routes import router as user_router
from fastapi_playground_poc.application.web.controller.courses_routes import router as courses_router
from fastapi_playground_poc.infrastructure.exception_handlers import register_exception_handlers
from fastapi_playground_poc.config import settings
from fastapi_playground_poc.infrastructure.startup import startup_event
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for managing startup and shutdown events."""
    # Startup: Run migrations before accepting requests
    logger.info("Application is starting")
    print(f"App environment is: {settings.environment}")
    if settings.environment != "test":
        await startup_event()
        logger.info("Migrations executed")
    yield
    logger.info("Application is stopping")
    # Shutdown: Add cleanup tasks here if needed in the future

# Create FastAPI application with lifespan handler
app = FastAPI(
    title="fastapi Playground POC",
    description="A FastAPI application with user and course management",
    version="0.1.0",
    docs_url="/docs" if settings.should_include_docs else None,
    openapi_url="/openapi.json" if settings.should_include_docs else None,
    lifespan=lifespan
)

# Register global exception handlers (FastAPI equivalent of Spring @ControllerAdvice)
register_exception_handlers(app)

# Include user routes
app.include_router(user_router, tags=["users"])

# Include courses routes
app.include_router(courses_router, tags=["courses"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to fastapi Playground POC API"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
