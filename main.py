from fastapi import FastAPI, Request, Form, HTTPException, status, Depends
from fastapi import FastAPI, Request, Form, HTTPException, status, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic import BaseModel
from pydantic import BaseModel, Field, field_validator
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
import uvicorn
import traceback
import logging
import uuid
import re
import os
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

# Load environment variables
load_dotenv()

# Default password
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "Default@123")

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "saving-api-photos")

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/saving")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-keep-it-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# S3 Upload Helper Functions
def upload_file_to_s3(file_content: bytes, file_name: str, content_type: str) -> str:
    """
    Upload file to S3 and return the S3 key (file path)
    """
    try:
        # Upload file to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=file_name,
            Body=file_content,
            ContentType=content_type
        )
        
        # Return the S3 key (we'll generate pre-signed URLs when needed)
        return file_name
        
    except NoCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AWS credentials not found"
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading to S3: {str(e)}"
        )

def generate_presigned_url(s3_key: str, expiration: int = 604800) -> str:
    """
    Generate a pre-signed URL for accessing an S3 object
    Default expiration: 604800 seconds = 7 days
    """
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=expiration
        )
        return response
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating pre-signed URL: {str(e)}"
        )

app = FastAPI(title="Saving Management System API",
             description="API for managing savings and user authentication")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Database Models
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Saving(Base):
    __tablename__ = "savings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Loan(Base):
    __tablename__ = "loans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    issued_date = Column(DateTime, nullable=False)
    deadline = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class ProfilePhoto(Base):
    __tablename__ = "profile_photos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    photo = Column(String, nullable=False)  # File path to the photo
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class UserLoginById(BaseModel):
    user_id: str  # UUID as string

class UserLogin(BaseModel):
    user_id: str  # Can be username or email
    password: str

class UserSignup(BaseModel):
    username: str
    email: str
    phone_number: str = Field(..., description="Phone number with country code 250 followed by 9 digits")
    password: str = None  # Optional, will use default if not provided
    confirm_password: str = None  # Optional, will use default if not provided
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        # Remove any spaces or dashes
        phone = v.replace(" ", "").replace("-", "")
        
        # Check if it matches the pattern: 250 followed by 9 digits
        if not re.match(r'^250\d{9}$', phone):
            raise ValueError('Phone number must be country code 250 followed by 9 digits (e.g., 250123456789)')
        return phone

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenWithUserInfo(BaseModel):
    access_token: str
    token_type: str
    user_info: dict

class SavingCreate(BaseModel):
    user_id: str  # UUID as string
    amount: float = Field(..., gt=0, description="Amount must be greater than 0")

class SavingResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class LoanCreate(BaseModel):
    user_id: str  # UUID as string
    amount: float = Field(..., gt=0, description="Amount must be greater than 0")
    issued_date: datetime
    deadline: datetime

class LoanResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    issued_date: datetime
    deadline: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProfilePhotoResponse(BaseModel):
    id: str
    user_id: str
    photo: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class LatestSavingInfo(BaseModel):
    month: int
    year: int
    amount: float

class HomeResponse(BaseModel):
    user_id: str
    image_preview_link: str | None
    total_saving: float
    total_loan: float
    latest_saving_info: LatestSavingInfo | None

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@app.get("/")
async def root():
    """
    Root endpoint - API description
    """
    return {
        "message": "Saving Management System API",
        "description": "API for managing savings and user authentication",
        "version": "1.0.0",
       
    }

# Login by ID only (Super Login)
@app.post("/api/login-by-id", response_model=TokenWithUserInfo)
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
@app.post("/api/login", response_model=TokenWithUserInfo)
async def api_login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Standard login endpoint - Login with username/email and password
    """
    # Try to find user by username or email
    user = db.query(User).filter(
        (User.username == user_data.user_id) | (User.email == user_data.user_id)
    ).first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID or password"
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
@app.post("/api/verify-phone")
async def verify_phone_number(phone_data: dict, db: Session = Depends(get_db)):
    """
    Verify if a phone number exists in the database
    """
    try:
        phone_number = phone_data.get("phone_number")
        
        if not phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is required"
            )
        
        # Remove any spaces or dashes
        phone = phone_number.replace(" ", "").replace("-", "")
        
        # Validate phone number format
        if not re.match(r'^250\d{9}$', phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format. Must be country code 250 followed by 9 digits"
            )
        
        # Check if phone number exists
        user = db.query(User).filter(User.phone_number == phone).first()
        
        if user:
            return {
                "exists": True,
                "message": "Verfication successful",
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying phone number: {str(e)}"
        )

# Signup endpoint
@app.post("/api/signup", response_model=dict)
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

# Saving endpoint
@app.post("/api/saving", response_model=SavingResponse)
async def create_saving(saving_data: SavingCreate, db: Session = Depends(get_db)):
    """
    Create a new saving entry
    """
    try:
        logger.info(f"Creating saving for user_id: {saving_data.user_id}, amount: {saving_data.amount}")
        
        # Verify user exists
        try:
            user_uuid = uuid.UUID(saving_data.user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create new saving
        db_saving = Saving(
            user_id=user_uuid,
            amount=saving_data.amount
        )
        
        db.add(db_saving)
        db.commit()
        db.refresh(db_saving)
        
        logger.info(f"Saving created successfully: {db_saving.id}")
        
        return SavingResponse(
            id=str(db_saving.id),
            user_id=str(db_saving.user_id),
            amount=db_saving.amount,
            created_at=db_saving.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating saving: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating saving: {str(e)}"
        )

# Loan endpoint
@app.post("/api/loan", response_model=LoanResponse)
async def create_loan(loan_data: LoanCreate, db: Session = Depends(get_db)):
    """
    Create a new loan entry
    """
    try:
        logger.info(f"Creating loan for user_id: {loan_data.user_id}, amount: {loan_data.amount}")
        
        # Verify user exists
        try:
            user_uuid = uuid.UUID(loan_data.user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate dates
        if loan_data.deadline <= loan_data.issued_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deadline must be after issued date"
            )
        
        # Create new loan
        db_loan = Loan(
            user_id=user_uuid,
            amount=loan_data.amount,
            issued_date=loan_data.issued_date,
            deadline=loan_data.deadline
        )
        
        db.add(db_loan)
        db.commit()
        db.refresh(db_loan)
        
        logger.info(f"Loan created successfully: {db_loan.id}")
        
        return LoanResponse(
            id=str(db_loan.id),
            user_id=str(db_loan.user_id),
            amount=db_loan.amount,
            issued_date=db_loan.issued_date,
            deadline=db_loan.deadline,
            created_at=db_loan.created_at,
            updated_at=db_loan.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating loan: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating loan: {str(e)}"
        )

# Profile photo upload endpoint
@app.post("/api/profile-photo", response_model=ProfilePhotoResponse)
async def upload_profile_photo(
    user_id: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload or update profile photo for a user
    """
    try:
        logger.info(f"Uploading profile photo for user_id: {user_id}")
        
        # Verify user exists
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate file type
        allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        file_ext = Path(photo.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique filename
        unique_filename = f"{user_uuid}{file_ext}"
        
        # Upload to S3
        try:
            contents = await photo.read()
            content_type = photo.content_type or "image/jpeg"
            s3_key = upload_file_to_s3(contents, unique_filename, content_type)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading file to S3: {str(e)}"
            )
        
        # Check if profile photo already exists for this user
        existing_photo = db.query(ProfilePhoto).filter(ProfilePhoto.user_id == user_uuid).first()
        
        if existing_photo:
            # Update existing photo
            existing_photo.photo = s3_key
            existing_photo.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_photo)
            
            logger.info(f"Profile photo updated successfully: {existing_photo.id}")
            
            return ProfilePhotoResponse(
                id=str(existing_photo.id),
                user_id=str(existing_photo.user_id),
                photo=existing_photo.photo,
                created_at=existing_photo.created_at,
                updated_at=existing_photo.updated_at
            )
        else:
            # Create new profile photo entry
            db_photo = ProfilePhoto(
                user_id=user_uuid,
                photo=s3_key
            )
            
            db.add(db_photo)
            db.commit()
            db.refresh(db_photo)
            
            logger.info(f"Profile photo uploaded successfully: {db_photo.id}")
            
            return ProfilePhotoResponse(
                id=str(db_photo.id),
                user_id=str(db_photo.user_id),
                photo=db_photo.photo,
                created_at=db_photo.created_at,
                updated_at=db_photo.updated_at
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading profile photo: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading profile photo: {str(e)}"
        )

# Home endpoint
@app.get("/api/home/{user_id}", response_model=HomeResponse)
async def get_home_info(user_id: str, db: Session = Depends(get_db)):
    """
    Get home dashboard information for a user
    - Image preview link
    - Total saving
    - Total loan
    - Latest saving info (month, year, amount)
    """
    try:
        logger.info(f"Fetching home info for user_id: {user_id}")
        
        # Verify user exists
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get profile photo
        profile_photo = db.query(ProfilePhoto).filter(ProfilePhoto.user_id == user_uuid).first()
        image_preview_link = None
        if profile_photo:
            # Generate pre-signed URL for the S3 object
            image_preview_link = generate_presigned_url(profile_photo.photo)
        
        # Calculate total savings
        total_saving = db.query(func.sum(Saving.amount)).filter(Saving.user_id == user_uuid).scalar() or 0.0
        
        # Calculate total loans
        total_loan = db.query(func.sum(Loan.amount)).filter(Loan.user_id == user_uuid).scalar() or 0.0
        
        # Get latest saving info
        latest_saving = db.query(Saving).filter(Saving.user_id == user_uuid).order_by(Saving.created_at.desc()).first()
        
        latest_saving_info = None
        if latest_saving:
            latest_saving_info = LatestSavingInfo(
                month=latest_saving.created_at.month,
                year=latest_saving.created_at.year,
                amount=latest_saving.amount
            )
        
        logger.info(f"Home info retrieved successfully for user: {user_id}")
        
        return HomeResponse(
            user_id=str(user_uuid),
            image_preview_link=image_preview_link,
            total_saving=total_saving,
            total_loan=total_loan,
            latest_saving_info=latest_saving_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching home info: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching home info: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)