from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
import logging
import traceback
import uuid
import json
from datetime import datetime

from models import User, ProfilePhoto, Saving, Loan, LoanPayment
from schemas import ProfilePhotoResponse, HomeResponse, LatestSavingInfo, UserResponse, UserUpdate, MemberResponse, ProfilePhotoURLResponse
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

# Get user profile by user_id
@router.get("/profile/{user_id}", response_model=UserResponse)
async def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    """
    Get user profile information by user_id
    """
    try:
        logger.info(f"Fetching profile for user_id: {user_id}")
        
        # Verify user ID format
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        # Get user from database
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Calculate total savings
        total_saving = db.query(func.coalesce(func.sum(Saving.amount), 0)).filter(
            Saving.user_id == user_uuid
        ).scalar()
        
        # Get profile photo if exists
        profile_photo = db.query(ProfilePhoto).filter(ProfilePhoto.user_id == user_uuid).first()
        profile_image_url = None
        if profile_photo:
            try:
                profile_image_url = generate_presigned_url(profile_photo.photo)
            except Exception as e:
                logger.warning(f"Could not generate presigned URL for profile photo: {e}")
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            phone_number=user.phone_number,
            total_saving=total_saving,
            profile_image_url=profile_image_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user profile: {str(e)}"
        )

@router.websocket("/home/{user_id}")
async def websocket_home_info(websocket: WebSocket, user_id: str, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for real-time home dashboard information
    - Image preview link
    - Total saving
    - Total loan
    - Latest saving info (month, year, amount)
    """
    await websocket.accept()
    
    try:
        logger.info(f"WebSocket connection established for user_id: {user_id}")
        
        # Verify user exists
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            await websocket.send_text(json.dumps({
                "error": "Invalid user ID format"
            }))
            await websocket.close()
            return
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            await websocket.send_text(json.dumps({
                "error": "User not found"
            }))
            await websocket.close()
            return
        
        # Get profile photo
        profile_photo = db.query(ProfilePhoto).filter(ProfilePhoto.user_id == user_uuid).first()
        image_preview_link = None
        if profile_photo:
            try:
                # Generate pre-signed URL for the S3 object
                image_preview_link = generate_presigned_url(profile_photo.photo)
            except Exception as e:
                logger.warning(f"Could not generate presigned URL: {e}")
        
        # Calculate total savings
        total_saving = db.query(func.sum(Saving.amount)).filter(Saving.user_id == user_uuid).scalar() or 0.0
        
        # Calculate total loans
        total_loan_amount = db.query(func.sum(Loan.amount)).filter(Loan.user_id == user_uuid).scalar() or 0.0
        
        # Calculate total loan payments
        total_loan_payments = db.query(func.sum(LoanPayment.amount)).filter(
            LoanPayment.user_id == user_uuid
        ).scalar() or 0.0
        
        # Current loan balance
        total_loan = total_loan_amount - total_loan_payments
        
        # Get latest saving info
        latest_saving = db.query(Saving).filter(
            Saving.user_id == user_uuid
        ).order_by(Saving.created_at.desc()).first()
        
        latest_saving_info = None
        if latest_saving:
            latest_saving_info = {
                "month": latest_saving.created_at.strftime("%B"),
                "year": latest_saving.created_at.year,
                "amount": latest_saving.amount
            }
        
        # Send home data via WebSocket
        home_data = {
            "image_preview_link": image_preview_link,
            "total_saving": total_saving,
            "total_loan": total_loan,
            "latest_saving_info": latest_saving_info
        }
        
        await websocket.send_text(json.dumps(home_data))
        
        # Keep connection alive and listen for client messages
        while True:
            try:
                # Wait for client message (for potential real-time updates)
                data = await websocket.receive_text()
                logger.info(f"Received WebSocket message: {data}")
                
                # Could implement real-time updates here
                # For now, just echo back the current data
                await websocket.send_text(json.dumps(home_data))
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user_id}")
                break
                
    except Exception as e:
        logger.error(f"Error in WebSocket home endpoint: {str(e)}")
        try:
            await websocket.send_text(json.dumps({
                "error": f"Server error: {str(e)}"
            }))
        except:
            pass
        finally:
            try:
                await websocket.close()
            except:
                pass

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