"""
Global exception handlers for the FastAPI application.
Similar to Spring's @ControllerAdvice, this provides centralized exception handling.

Usage in app.py:
    from fastapi_playground_poc.exception_handlers import register_exception_handlers
    register_exception_handlers(app)
"""

from fastapi import Request, HTTPException, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
import logging

from starlette.responses import JSONResponse

from fastapi_playground_poc.services.exceptions import DomainException

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors - return 400 Bad Request"""
    logger.warning(f"Validation error on {request.url}: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error", 
            "detail": "Invalid input data",
            "errors": exc.errors()
        }
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle SQLAlchemy IntegrityError - return 409 Conflict"""
    logger.warning(f"Integrity constraint violation on {request.url}: {exc}")
    
    # Check if it's a duplicate key error (common pattern)
    error_msg = str(exc.orig) if exc.orig else str(exc)
    if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
        detail = "Resource already exists"
    else:
        detail = "Data integrity constraint violation"
    
    return JSONResponse(
        status_code=409,
        content={
            "error": "Conflict",
            "detail": detail
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException - preserve original status codes and details"""
    logger.info(f"HTTP exception on {request.url}: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "detail": exc.detail
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions - return 500 Internal Server Error"""
    logger.error(f"Unhandled exception on {request.url}: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred"
        }
    )
# This variant is to avoid 20, 30, 40 handlers.
def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    """Convert domain exception to API response format"""
    logger.error(f"Unhandled exception on {request.url}: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error_code": exc.error_code,
            "error_type": exc.error_type.value,
            "message": exc.message,
            "context": exc.context,
        }
    )

def register_exception_handlers(app: FastAPI):
    """
    Register all exception handlers with the FastAPI app.
    This is the FastAPI equivalent of Spring's @ControllerAdvice.
    """
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(DomainException, domain_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Global exception handlers registered successfully")