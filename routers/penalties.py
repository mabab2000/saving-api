from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
import logging
import traceback
import uuid

from models import User, Penalty
from schemas import PenaltyCreate, PenaltyResponse, PenaltySummary
from database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/penalty", response_model=PenaltyResponse)
async def create_penalty(penalty_data: PenaltyCreate, db: Session = Depends(get_db)):
    """
    Create a new penalty entry
    """
    try:
        logger.info(f"Creating penalty for user_id: {penalty_data.user_id}, amount: {penalty_data.amount}, reason: {penalty_data.reason}")
        
        # Verify user exists
        try:
            user_uuid = uuid.UUID(penalty_data.user_id)
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
        
        # Create new penalty
        db_penalty = Penalty(
            user_id=user_uuid,
            reason=penalty_data.reason,
            amount=penalty_data.amount,
            status=penalty_data.status
        )
        
        db.add(db_penalty)
        db.commit()
        db.refresh(db_penalty)
        
        logger.info(f"Penalty created successfully: {db_penalty.id}")
        
        return PenaltyResponse(
            id=str(db_penalty.id),
            user_id=str(db_penalty.user_id),
            reason=db_penalty.reason,
            amount=db_penalty.amount,
            status=db_penalty.status,
            created_at=db_penalty.created_at,
            updated_at=db_penalty.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating penalty: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating penalty: {str(e)}"
        )

@router.get("/penalties/{user_id}", response_model=PenaltySummary)
async def get_user_penalties(user_id: str, db: Session = Depends(get_db)):
    """
    Get all penalties for a specific user with totals for paid and unpaid penalties
    """
    try:
        logger.info(f"Fetching penalties for user_id: {user_id}")
        
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
        
        # Get all penalties for the user, ordered by creation date (newest first)
        penalties = db.query(Penalty).filter(Penalty.user_id == user_uuid).order_by(Penalty.created_at.desc()).all()
        
        # Calculate totals
        total_paid = sum(penalty.amount for penalty in penalties if penalty.status.lower() == "paid")
        total_unpaid = sum(penalty.amount for penalty in penalties if penalty.status.lower() == "unpaid")
        
        logger.info(f"Found {len(penalties)} penalties for user: {user_id} (Paid: {total_paid}, Unpaid: {total_unpaid})")
        
        penalty_responses = [
            PenaltyResponse(
                id=str(penalty.id),
                user_id=str(penalty.user_id),
                reason=penalty.reason,
                amount=penalty.amount,
                status=penalty.status,
                created_at=penalty.created_at,
                updated_at=penalty.updated_at
            )
            for penalty in penalties
        ]
        
        return PenaltySummary(
            total_paid=total_paid,
            total_unpaid=total_unpaid,
            penalties=penalty_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching penalties: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching penalties: {str(e)}"
        )