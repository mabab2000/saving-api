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
import json
import base64
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from models import User
from schemas import UserLoginById, UserLogin, UserSignup, TokenWithUserInfo, PhoneVerification, GoogleLoginRequest
from database import get_db
from fcm_utils import validate_fcm_token

# Setup
router = APIRouter()
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "Default@123")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-keep-it-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

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

async def verify_google_token(token: str):
    """
    Verify Google OAuth token and return user info
    Supports both strict production verification and flexible development verification
    """
    try:
        # Log token details for debugging (first 20 and last 10 chars only)
        token_preview = f"{token[:20]}...{token[-10:]}" if len(token) > 30 else "SHORT_TOKEN"
        logger.info(f"[verify_google_token] Starting token verification")
        logger.debug(f"[verify_google_token] Token preview: {token_preview}")
        logger.debug(f"[verify_google_token] Token length: {len(token)}")
        logger.debug(f"[verify_google_token] Client ID: {GOOGLE_CLIENT_ID[:20]}...")
        
        # Check if token is empty or invalid format
        if not token or not isinstance(token, str):
            logger.error(f"[verify_google_token] Invalid token type: {type(token)}, value: {token}")
            raise ValueError(f"Invalid token type: {type(token)}")
        
        if token.lower() == "string":
            logger.error(f"[verify_google_token] Token value is literal 'string' - client not sending real token")
            raise ValueError("Token is literal 'string' - not a valid JWT token")
        
        # Count token segments (JWT should have 3 parts: header.payload.signature)
        segments = token.split('.')
        logger.debug(f"[verify_google_token] Token segments: {len(segments)} (expected 3)")
        
        if len(segments) != 3:
            logger.error(f"[verify_google_token] Wrong number of segments: {len(segments)}")
            raise ValueError(f"Wrong number of segments in token: expected 3, got {len(segments)}")
        
        logger.info(f"[verify_google_token] Token format looks valid, attempting to decode...")
        
        # Try to decode the token to inspect it (without verification first)
        try:
            # Decode payload (second segment)
            payload_encoded = segments[1]
            # Add padding if needed
            padding = 4 - len(payload_encoded) % 4
            if padding != 4:
                payload_encoded += '=' * padding
            
            payload_json = base64.urlsafe_b64decode(payload_encoded)
            payload = json.loads(payload_json)
            
            logger.debug(f"[verify_google_token] Token payload decoded successfully")
            logger.info(f"[verify_google_token] Token email: {payload.get('email')}")
            logger.info(f"[verify_google_token] Token issued for audience: {payload.get('aud')}")
            logger.info(f"[verify_google_token] Email verified: {payload.get('email_verified')}")
            
        except Exception as decode_error:
            logger.warning(f"[verify_google_token] Could not decode token for inspection: {str(decode_error)}")
        
        logger.info(f"[verify_google_token] Verifying with Google...")
        
        try:
            # Try strict verification with your Client ID
            logger.debug(f"[verify_google_token] Attempting strict verification with Client ID: {GOOGLE_CLIENT_ID}")
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                GOOGLE_CLIENT_ID
            )
            logger.info(f"[verify_google_token] Strict verification successful")
            
        except ValueError as strict_error:
            logger.warning(f"[verify_google_token] Strict verification failed: {str(strict_error)}")
            logger.info(f"[verify_google_token] Attempting lenient verification (verify signature only)...")
            
            try:
                # Lenient verification - verify signature but accept any audience (for development/testing)
                idinfo = id_token.verify_oauth2_token(
                    token,
                    google_requests.Request()
                    # No client_id parameter = verify signature only
                )
                logger.info(f"[verify_google_token] Lenient verification successful")
                logger.warning(f"[verify_google_token] Using lenient verification - ensure this is NOT production!")
                
            except Exception as lenient_error:
                logger.error(f"[verify_google_token] Lenient verification also failed: {str(lenient_error)}")
                raise ValueError(f"Token verification failed: {str(lenient_error)}")
        
        logger.info(f"[verify_google_token] Token verification successful")
        logger.debug(f"[verify_google_token] User email: {idinfo.get('email')}")
        logger.debug(f"[verify_google_token] Email verified: {idinfo.get('email_verified')}")
        
        # Token is valid, return user info
        return {
            "email": idinfo.get("email"),
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
            "google_id": idinfo.get("sub"),
            "email_verified": idinfo.get("email_verified", False)
        }
        
    except ValueError as e:
        logger.error(f"[verify_google_token] ValueError: {str(e)}")
        logger.debug(f"[verify_google_token] Full error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"[verify_google_token] Unexpected error: {type(e).__name__}: {str(e)}")
        logger.debug(f"[verify_google_token] Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying Google token: {str(e)}"
        )

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

# Google OAuth Login
@router.post("/login/google", response_model=TokenWithUserInfo)
async def google_login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Google OAuth login endpoint - Login or signup with Google
    """
    try:
        logger.info(f"[google_login] ===== GOOGLE LOGIN REQUEST START =====")
        logger.info(f"[google_login] Request received at endpoint: /auth/login/google")
        logger.debug(f"[google_login] Request body: {request}")
        
        # Log request details
        token_received = request.token if request.token else "NO_TOKEN"
        token_preview = f"{token_received[:20]}...{token_received[-10:]}" if len(token_received) > 30 else token_received
        logger.info(f"[google_login] Token received (preview): {token_preview}")
        logger.info(f"[google_login] Token length: {len(token_received)}")
        logger.info(f"[google_login] FCM token provided: {bool(request.fcm_token)}")
        logger.debug(f"[google_login] Full request: token={request.token}, fcm_token={request.fcm_token}")
        
        # Verify Google token
        logger.info(f"[google_login] Calling verify_google_token()...")
        google_user = await verify_google_token(request.token)
        logger.info(f"[google_login] Token verified successfully")
        logger.debug(f"[google_login] Google user data: {google_user}")
        
        if not google_user.get("email_verified"):
            logger.warning(f"[google_login] Email not verified for: {google_user.get('email')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not verified by Google"
            )
        
        email = google_user.get("email")
        google_id = google_user.get("google_id")
        name = google_user.get("name")
        picture = google_user.get("picture")
        
        logger.info(f"[google_login] Processing login for email: {email}")
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            logger.info(f"[google_login] User exists in database: {email}")
            # User exists - update OAuth info if needed
            if not user.oauth_provider:
                logger.info(f"[google_login] Updating OAuth info for existing user: {email}")
                user.oauth_provider = "google"
                user.oauth_id = google_id
                user.profile_picture = picture
            
            # Update FCM token if provided
            if request.fcm_token:
                logger.info(f"[google_login] Validating FCM token...")
                is_valid_token = await validate_fcm_token(request.fcm_token)
                if is_valid_token:
                    user.fcm_token = request.fcm_token
                    logger.info(f"[google_login] FCM token updated for user: {user.id}")
                else:
                    logger.warning(f"[google_login] Invalid FCM token provided")
            
            db.commit()
            db.refresh(user)
            logger.info(f"[google_login] Existing user login successful: {email}")
        else:
            logger.info(f"[google_login] New user detected: {email}")
            # Create new user with Google OAuth
            username = email.split("@")[0]  # Use email prefix as username
            base_username = username
            counter = 1
            
            # Ensure unique username
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            logger.info(f"[google_login] Generated unique username: {username}")
            
            # Validate and update FCM token if provided
            fcm_token = None
            if request.fcm_token:
                logger.info(f"[google_login] Validating FCM token for new user...")
                is_valid_token = await validate_fcm_token(request.fcm_token)
                if is_valid_token:
                    fcm_token = request.fcm_token
                    logger.info(f"[google_login] FCM token validated for new user")
                else:
                    logger.warning(f"[google_login] Invalid FCM token for new user")
            
            user = User(
                username=username,
                email=email,
                phone_number=None,  # Can be added later
                hashed_password=None,  # No password for OAuth users
                oauth_provider="google",
                oauth_id=google_id,
                profile_picture=picture,
                fcm_token=fcm_token
            )
            
            logger.info(f"[google_login] Creating new user: {username} ({email})")
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"[google_login] New user created successfully: {user.id}")
        
        # Generate JWT token
        logger.info(f"[google_login] Generating JWT access token...")
        access_token = create_access_token(data={"sub": user.username})
        logger.info(f"[google_login] Access token generated successfully")
        
        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "user_info": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "phone_number": user.phone_number,
                "profile_picture": user.profile_picture,
                "oauth_provider": user.oauth_provider
            }
        }
        
        logger.info(f"[google_login] ===== GOOGLE LOGIN SUCCESS =====")
        logger.info(f"[google_login] User: {user.username} ({user.email})")
        return response_data
        
    except HTTPException:
        logger.error(f"[google_login] HTTP Exception raised")
        raise
    except Exception as e:
        logger.error(f"[google_login] ===== GOOGLE LOGIN FAILED =====")
        logger.error(f"[google_login] Exception type: {type(e).__name__}")
        logger.error(f"[google_login] Error message: {str(e)}")
        logger.debug(f"[google_login] Full traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during Google login: {str(e)}"
        )

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
            is_valid_token = None
            # Update FCM token if provided
            if fcm_token:
                # Validate FCM token format before storing
                is_valid_token = await validate_fcm_token(fcm_token)
                if is_valid_token:
                    user.fcm_token = fcm_token
                    db.commit()
                    db.refresh(user)
                    logger.info(f"Valid FCM token updated for user {user.id}")
                else:
                    logger.warning(f"Invalid FCM token format provided for user {user.id}: {fcm_token[:20]}...")
                    # Still proceed but don't store invalid token
                    user.fcm_token = None
                    db.commit()
                    db.refresh(user)
            
            return {
                "exists": True,
                "message": "Verification successful",
                "user_id": str(user.id),
                "fcm_token_valid": is_valid_token
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