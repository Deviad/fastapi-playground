from fastapi import FastAPI
from flask_playground_poc.user_routes import router as user_router

# Create FastAPI application
app = FastAPI(
    title="Flask Playground POC",
    description="A FastAPI application with user management",
    version="0.1.0",
)

# Include user routes
app.include_router(user_router, tags=["users"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Flask Playground POC API"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
