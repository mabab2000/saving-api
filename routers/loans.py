from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
import logging
import traceback
import uuid

from models import User, Loan, LoanPayment
from schemas import (
    LoanCreate,
    LoanResponse,
    LoanSummary,
    LoanPaymentCreate,
    LoanPaymentResponse,
    LoanPaymentSummary,
    LoanUpdate,
)
from database import get_db
from fastapi import Body

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/loan", response_model=LoanResponse)
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
            status=db_loan.status,
            total_amount_paid=0.0,
            created_at=db_loan.created_at,
            updated_at=db_loan.updated_at,
            username=user.username if user else None,
            phone_number=user.phone_number if user else None,
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

@router.get("/loans/{user_id}", response_model=LoanSummary)
async def get_user_loans(user_id: str, db: Session = Depends(get_db)):
    """
    Get all loans for a specific user with total amount and count
    """
    try:
        logger.info(f"Fetching loans for user_id: {user_id}")
        
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
        
        # Get all loans for the user, ordered by creation date (newest first)
        loans = db.query(Loan).filter(Loan.user_id == user_uuid).order_by(Loan.created_at.desc()).all()
        
        # Calculate totals
        total_amount = sum(loan.amount for loan in loans)
        total_loan = len(loans)
        
        logger.info(f"Found {total_loan} loans for user: {user_id} (Total: {total_amount})")
        
        loan_responses = []
        for loan in loans:
            # Calculate total amount paid for this loan
            from sqlalchemy import func
            total_paid = db.query(func.sum(LoanPayment.amount)).filter(LoanPayment.loan_id == loan.id).scalar() or 0.0
            
            loan_responses.append(LoanResponse(
                id=str(loan.id),
                user_id=str(loan.user_id),
                amount=loan.amount,
                issued_date=loan.issued_date,
                deadline=loan.deadline,
                status=loan.status,
                total_amount_paid=float(total_paid),
                created_at=loan.created_at,
                updated_at=loan.updated_at,
                username=user.username if user else None,
                phone_number=user.phone_number if user else None,
            ))
        
        return LoanSummary(
            total_amount=total_amount,
            total_loan=total_loan,
            loans=loan_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching loans: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching loans: {str(e)}"
        )

@router.post("/loan-payment", response_model=LoanPaymentResponse)
async def create_loan_payment(payment_data: LoanPaymentCreate, db: Session = Depends(get_db)):
    """
    Record a new loan payment
    """
    try:
        logger.info(f"Creating loan payment for user_id: {payment_data.user_id}, loan_id: {payment_data.loan_id}, amount: {payment_data.amount}")
        
        # Verify user exists
        try:
            user_uuid = uuid.UUID(payment_data.user_id)
            loan_uuid = uuid.UUID(payment_data.loan_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID or loan ID format"
            )
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify loan exists and belongs to the user
        loan = db.query(Loan).filter(Loan.id == loan_uuid, Loan.user_id == user_uuid).first()
        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found or does not belong to the specified user"
            )
        
        # Create new loan payment
        db_payment = LoanPayment(
            user_id=user_uuid,
            loan_id=loan_uuid,
            amount=payment_data.amount
        )
        
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        
        logger.info(f"Loan payment created successfully: {db_payment.id}")
        
        return LoanPaymentResponse(
            id=str(db_payment.id),
            user_id=str(db_payment.user_id),
            loan_id=str(db_payment.loan_id),
            amount=db_payment.amount,
            created_at=db_payment.created_at,
            updated_at=db_payment.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating loan payment: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating loan payment: {str(e)}"
        )

@router.get("/loan-payments/{loan_id}", response_model=LoanPaymentSummary)
async def get_loan_payments(loan_id: str, db: Session = Depends(get_db)):
    """
    Get all loan payments for a specific loan with total amount and count
    """
    try:
        logger.info(f"Fetching loan payments for loan_id: {loan_id}")
        
        # Verify loan exists
        try:
            loan_uuid = uuid.UUID(loan_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid loan ID format"
            )
        
        loan = db.query(Loan).filter(Loan.id == loan_uuid).first()
        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found"
            )
        
        # Get all loan payments for the specific loan, ordered by creation date (newest first)
        payments = db.query(LoanPayment).filter(LoanPayment.loan_id == loan_uuid).order_by(LoanPayment.created_at.desc()).all()
        
        # Calculate totals
        total_amount = sum(payment.amount for payment in payments)
        total_payments = len(payments)
        
        logger.info(f"Found {total_payments} loan payments for loan: {loan_id} (Total: {total_amount})")
        
        payment_responses = [
            LoanPaymentResponse(
                id=str(payment.id),
                user_id=str(payment.user_id),
                loan_id=str(payment.loan_id),
                amount=payment.amount,
                created_at=payment.created_at,
                updated_at=payment.updated_at
            )
            for payment in payments
        ]
        
        return LoanPaymentSummary(
            total_amount=total_amount,
            total_payments=total_payments,
            payments=payment_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching loan payments: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching loan payments: {str(e)}"
        )


# Admin: list all loans
@router.get("/loans", response_model=LoanSummary)
async def list_all_loans(db: Session = Depends(get_db)):
    try:
        loans = db.query(Loan).order_by(Loan.created_at.desc()).all()
        total_amount = sum(loan.amount for loan in loans)
        total_loan = len(loans)
        loan_responses = []
        for loan in loans:
            try:
                user_obj = db.query(User).filter(User.id == loan.user_id).first()
                username = user_obj.username if user_obj else None
                phone = user_obj.phone_number if user_obj else None
                
                # Calculate total amount paid
                total_paid = db.query(func.coalesce(func.sum(LoanPayment.amount), 0)).filter(
                    LoanPayment.loan_id == loan.id
                ).scalar()
            except Exception:
                username = None
                phone = None
                total_paid = 0

            loan_responses.append(
                LoanResponse(
                    id=str(loan.id),
                    user_id=str(loan.user_id),
                    amount=loan.amount,
                    issued_date=loan.issued_date,
                    deadline=loan.deadline,
                    created_at=loan.created_at,
                    updated_at=loan.updated_at,
                    username=username,
                    phone_number=phone,
                    status=loan.status,
                    total_amount_paid=total_paid,
                )
            )
        return LoanSummary(total_amount=total_amount, total_loan=total_loan, loans=loan_responses)
    except Exception as e:
        logger.error(f"Error listing all loans: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin: update a loan
@router.put("/loan/{loan_id}", response_model=LoanResponse)
async def update_loan(loan_id: str, payload: LoanUpdate = Body(...), db: Session = Depends(get_db)):
    try:
        try:
            loan_uuid = uuid.UUID(loan_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid loan ID format")

        loan = db.query(Loan).filter(Loan.id == loan_uuid).first()
        if not loan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

        if payload.amount is not None:
            loan.amount = payload.amount
        if payload.issued_date is not None:
            loan.issued_date = payload.issued_date
        if payload.deadline is not None:
            if payload.issued_date and payload.deadline <= payload.issued_date:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deadline must be after issued date")
            loan.deadline = payload.deadline

        db.commit()
        db.refresh(loan)

        # Calculate total amount paid
        total_paid = db.query(func.coalesce(func.sum(LoanPayment.amount), 0)).filter(
            LoanPayment.loan_id == loan.id
        ).scalar()

        return LoanResponse(
            id=str(loan.id),
            user_id=str(loan.user_id),
            amount=loan.amount,
            issued_date=loan.issued_date,
            deadline=loan.deadline,
            created_at=loan.created_at,
            updated_at=loan.updated_at,
            status=loan.status,
            total_amount_paid=total_paid,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating loan: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin: delete a loan and its payments
@router.delete("/loan/{loan_id}")
async def delete_loan(loan_id: str, db: Session = Depends(get_db)):
    try:
        try:
            loan_uuid = uuid.UUID(loan_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid loan ID format")

        loan = db.query(Loan).filter(Loan.id == loan_uuid).first()
        if not loan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

        # Delete associated payments first
        db.query(LoanPayment).filter(LoanPayment.loan_id == loan_uuid).delete()
        db.delete(loan)
        db.commit()

        return {"message": "Loan and associated payments deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting loan: {e}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))