from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
import logging
import traceback
import uuid

from models import User, Saving
from schemas import SavingCreate, SavingResponse, SavingSummary
from database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/saving", response_model=SavingResponse)
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

@router.get("/savings/{user_id}", response_model=SavingSummary)
async def get_user_savings(user_id: str, db: Session = Depends(get_db)):
    """
    Get all savings for a specific user with total amount and count
    """
    try:
        logger.info(f"Fetching savings for user_id: {user_id}")
        
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
        
        # Get all savings for the user, ordered by creation date (newest first)
        savings = db.query(Saving).filter(Saving.user_id == user_uuid).order_by(Saving.created_at.desc()).all()
        
        # Calculate totals
        total_amount = sum(saving.amount for saving in savings)
        total_saving = len(savings)
        
        logger.info(f"Found {total_saving} savings for user: {user_id} (Total: {total_amount})")
        
        saving_responses = [
            SavingResponse(
                id=str(saving.id),
                user_id=str(saving.user_id),
                amount=saving.amount,
                created_at=saving.created_at
            )
            for saving in savings
        ]
        
        return SavingSummary(
            total_amount=total_amount,
            total_saving=total_saving,
            savings=saving_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching savings: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching savings: {str(e)}"
        )