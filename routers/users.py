from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
import logging
import traceback
import uuid
from datetime import datetime

from models import User, ProfilePhoto, Saving, Loan, LoanPayment
from schemas import ProfilePhotoResponse, HomeResponse, LatestSavingInfo, UserResponse, UserUpdate, MemberResponse
from database import get_db
from s3_utils import upload_file_to_s3, generate_presigned_url
from .auth import get_password_hash
from fastapi import Body

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/profile-photo", response_model=ProfilePhotoResponse)
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

@router.get("/home/{user_id}", response_model=HomeResponse)
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
        total_loan_amount = db.query(func.sum(Loan.amount)).filter(Loan.user_id == user_uuid).scalar() or 0.0
        
        # Calculate total loan payments
        total_loan_payments = db.query(func.sum(LoanPayment.amount)).filter(LoanPayment.user_id == user_uuid).scalar() or 0.0
        
        # Calculate current loan (total loans - total payments)
        current_loan = total_loan_amount - total_loan_payments
        
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
            total_loan=current_loan,
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


# Public/Admin: list members with basic info and profile image link
@router.get("/members", response_model=list[MemberResponse])
async def list_members(db: Session = Depends(get_db)):
    try:
        users = db.query(User).order_by(User.username.asc()).all()
        members = []
        for u in users:
            # find profile photo
            profile_photo = db.query(ProfilePhoto).filter(ProfilePhoto.user_id == u.id).first()
            image_preview_link = None
            if profile_photo:
                try:
                    image_preview_link = generate_presigned_url(profile_photo.photo)
                except Exception:
                    image_preview_link = None

            members.append(
                MemberResponse(
                    id=str(u.id),
                    username=u.username,
                    email=u.email,
                    phone_number=u.phone_number,
                    image_preview_link=image_preview_link,
                )
            )

        return members
    except Exception as e:
        logger.error(f"Error listing members: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin: list all users
@router.get("/users", response_model=list[UserResponse])
async def list_users(db: Session = Depends(get_db)):
    try:
        users = db.query(User).all()
        result: list[UserResponse] = []
        for u in users:
            # Calculate total saving for the user
            total_saving = db.query(func.sum(Saving.amount)).filter(Saving.user_id == u.id).scalar() or 0.0

            result.append(
                UserResponse(
                    id=str(u.id),
                    username=u.username,
                    email=u.email,
                    phone_number=u.phone_number,
                    total_saving=float(total_saving),
                )
            )

        return result
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin: update a user
@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, payload: UserUpdate = Body(...), db: Session = Depends(get_db)):
    try:
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Check uniqueness when updating username/email/phone
        if payload.username and payload.username != user.username:
            existing = db.query(User).filter(User.username == payload.username).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
            user.username = payload.username

        if payload.email and payload.email != user.email:
            existing = db.query(User).filter(User.email == payload.email).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already taken")
            user.email = payload.email

        if payload.phone_number and payload.phone_number != user.phone_number:
            existing = db.query(User).filter(User.phone_number == payload.phone_number).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already taken")
            user.phone_number = payload.phone_number

        if payload.password:
            user.hashed_password = get_password_hash(payload.password)

        db.commit()
        db.refresh(user)

        return UserResponse(id=str(user.id), username=user.username, email=user.email, phone_number=user.phone_number)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin: delete a user
@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db)):
    try:
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Attempt to delete user (may fail if FK constraints exist)
        db.delete(user)
        db.commit()
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))