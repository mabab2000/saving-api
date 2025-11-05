from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import uvicorn
import os

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import routers (after loading env vars)
try:
    from routers import auth, savings, loans, penalties, users, dashboard
    logger.info("All routers imported successfully")
except Exception as e:
    logger.error(f"Failed to import routers: {str(e)}")
    raise

# Create FastAPI app
app = FastAPI(
    title="Saving Management System API",
    description="API for managing savings and user authentication",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Startup event to verify database connection"""
    try:
        from database import engine
        # Test database connection
        with engine.connect() as conn:
            logger.info("Database connection verified successfully")
    except Exception as e:
        logger.error(f"Database connection failed during startup: {str(e)}")
        raise

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(savings.router, prefix="/api", tags=["Savings"])
app.include_router(loans.router, prefix="/api", tags=["Loans"])
app.include_router(penalties.router, prefix="/api", tags=["Penalties"])
app.include_router(users.router, prefix="/api", tags=["Users"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])

@app.get("/")
async def root():
    """
    Root endpoint - API description
    """
    return {
        "message": "Saving Management System API",
        "description": "API for managing savings and user authentication",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/login, /api/login-by-id, /api/signup, /api/verify-phone",
            "savings": "/api/saving, /api/savings/{user_id}",
            "loans": "/api/loan, /api/loans/{user_id}, /api/loan-payment, /api/loan-payments/{loan_id}", 
            "penalties": "/api/penalty, /api/penalties/{user_id}",
            "users": "/api/profile-photo, /api/home/{user_id}",
            "dashboard": "/api/dashboard/{user_id}"
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)