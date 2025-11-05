from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
import traceback
import uuid

from models import User, Saving, Loan, Penalty, LoanPayment
from schemas import DashboardResponse
from database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/dashboard/{user_id}", response_model=DashboardResponse)
async def get_dashboard_info(user_id: str, db: Session = Depends(get_db)):
    """
    Get dashboard information for a user
    - Total savings amount
    - Total loans amount  
    - Total penalties amount
    """
    try:
        logger.info(f"Fetching dashboard info for user_id: {user_id}")
        
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
        
        # Calculate total savings
        total_saving = db.query(func.sum(Saving.amount)).filter(Saving.user_id == user_uuid).scalar() or 0.0
        
        # Calculate total loans
        total_loan_amount = db.query(func.sum(Loan.amount)).filter(Loan.user_id == user_uuid).scalar() or 0.0
        
        # Calculate total loan payments
        total_loan_payments = db.query(func.sum(LoanPayment.amount)).filter(LoanPayment.user_id == user_uuid).scalar() or 0.0
        
        # Calculate current loan (total loans - total payments)
        current_loan = total_loan_amount - total_loan_payments
        
        # Calculate total penalties
        total_penalties = db.query(func.sum(Penalty.amount)).filter(Penalty.user_id == user_uuid).scalar() or 0.0
        
        logger.info(f"Dashboard info retrieved successfully for user: {user_id} - Savings: {total_saving}, Current Loan: {current_loan} (Total: {total_loan_amount}, Payments: {total_loan_payments}), Penalties: {total_penalties}")
        
        return DashboardResponse(
            user_id=str(user_uuid),
            total_saving=total_saving,
            total_loan=current_loan,
            total_penalties=total_penalties
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dashboard info: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching dashboard info: {str(e)}"
        )