from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
import logging
import traceback
import uuid
import re
import os

from models import User
from schemas import UserLoginById, UserLogin, UserSignup, TokenWithUserInfo, PhoneVerification
from database import get_db

# Setup
router = APIRouter()
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "Default@123")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-keep-it-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Security Functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Login by ID only (Super Login)
@router.post("/login-by-id", response_model=TokenWithUserInfo)
async def api_login_by_id(user_data: UserLoginById, db: Session = Depends(get_db)):
    """
    Super login endpoint - Login with UUID only (no password required)
    """
    try:
        user = db.query(User).filter(User.id == uuid.UUID(user_data.user_id)).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        access_token = create_access_token(data={"sub": user.username})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_info": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "phone_number": user.phone_number
            }
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

# Login with username/email and password
@router.post("/login", response_model=TokenWithUserInfo)
async def api_login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Standard login endpoint - Login with email and password
    """
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_info": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "phone_number": user.phone_number
        }
    }

# Verify phone number endpoint
@router.post("/verify-phone")
async def verify_phone_number(phone_data: PhoneVerification, db: Session = Depends(get_db)):
    """
    Verify if a phone number exists in the database and update FCM token
    """
    try:
        # Phone number is already validated by Pydantic
        phone = phone_data.phone_number
        fcm_token = phone_data.fcm_token
        
        # Check if phone number exists
        user = db.query(User).filter(User.phone_number == phone).first()
        
        if user:
            # Update FCM token if provided
            if fcm_token:
                user.fcm_token = fcm_token
                db.commit()
                db.refresh(user)
                logger.info(f"FCM token updated for user {user.id}")
            
            return {
                "exists": True,
                "message": "Verification successful",
                "user_id": str(user.id)
            }
        else:
            return {
                "exists": False,
                "message": "Phone number is available"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during phone verification: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying phone number: {str(e)}"
        )

# Signup endpoint
@router.post("/signup", response_model=dict)
async def api_signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """
    API endpoint for user signup using JSON data
    """
    try:
        logger.info(f"API Signup attempt for username: {user_data.username}, email: {user_data.email}, phone: {user_data.phone_number}")
        
        # Use default password if not provided
        password = user_data.password if user_data.password else DEFAULT_PASSWORD
        confirm_password = user_data.confirm_password if user_data.confirm_password else DEFAULT_PASSWORD
        
        if password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Check if username already exists
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            logger.warning(f"Username already exists: {user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            logger.warning(f"Email already exists: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if phone number already exists
        existing_phone = db.query(User).filter(User.phone_number == user_data.phone_number).first()
        if existing_phone:
            logger.warning(f"Phone number already exists: {user_data.phone_number}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        
        # Create new user
        logger.info("Hashing password...")
        hashed_password = get_password_hash(password)
        
        logger.info("Creating user object...")
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            phone_number=user_data.phone_number,
            hashed_password=hashed_password
        )
        
        logger.info("Adding user to database...")
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User created successfully: {user_data.username}")
        return {
            "message": "Signup successful",
            "user_id": str(db_user.id),
            "username": user_data.username,
            "email": user_data.email,
            "phone_number": user_data.phone_number,
            "default_password_used": user_data.password is None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during API signup: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )