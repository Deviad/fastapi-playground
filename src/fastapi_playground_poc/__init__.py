"""fastapi Playground POC - A FastAPI application with user and course management."""

from fastapi_playground_poc.app import app

__version__ = "0.1.0"
__all__ = ["app", "main"]


def main():
    """Main entry point for the application."""
    import uvicorn
    
    uvicorn.run(
        "fastapi_playground_poc.app:app",
        host="0.0.0.0", 
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()