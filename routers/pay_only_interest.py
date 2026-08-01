import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Loan, PayOnlyInterest
from schemas import PayOnlyInterestCreate, PayOnlyInterestResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def to_interest_payment_response(payment: PayOnlyInterest) -> PayOnlyInterestResponse:
    """Serialize UUID database fields as the strings expected by the API."""
    return PayOnlyInterestResponse(
        id=str(payment.id),
        loan_id=str(payment.loan_id),
        amount=payment.amount,
        created_at=payment.created_at,
    )


@router.post("/pay-only-interest", response_model=PayOnlyInterestResponse, status_code=status.HTTP_201_CREATED)
async def create_interest_payment(payload: PayOnlyInterestCreate, db: Session = Depends(get_db)):
    """Record an interest-only payment for a loan."""
    try:
        loan_uuid = uuid.UUID(payload.loan_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid loan ID format")

    loan = db.query(Loan).filter(Loan.id == loan_uuid).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    try:
        payment = PayOnlyInterest(loan_id=loan_uuid, amount=payload.amount)
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return to_interest_payment_response(payment)
    except Exception as exc:
        db.rollback()
        logger.exception("Error creating interest-only payment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create interest-only payment",
        ) from exc


@router.get("/pay-only-interest/{loan_id}", response_model=list[PayOnlyInterestResponse])
async def get_interest_payments_by_loan(loan_id: str, db: Session = Depends(get_db)):
    """Return all interest-only payments for one loan, newest first."""
    try:
        loan_uuid = uuid.UUID(loan_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid loan ID format")

    loan = db.query(Loan).filter(Loan.id == loan_uuid).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    payments = (
        db.query(PayOnlyInterest)
        .filter(PayOnlyInterest.loan_id == loan_uuid)
        .order_by(PayOnlyInterest.created_at.desc())
        .all()
    )
    return [to_interest_payment_response(payment) for payment in payments]
