from fastapi import APIRouter, HTTPException, status, Depends, Body
from sqlalchemy.orm import Session
import logging
import traceback
import uuid
from datetime import datetime

from models import PayLoanUsingSaving, User
from schemas import PayLoanUsingSavingCreate, PayLoanUsingSavingResponse, PayLoanUsingSavingUpdate
from database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/pay-loan-using-saving", response_model=PayLoanUsingSavingResponse)
async def create_payment(payload: PayLoanUsingSavingCreate, db: Session = Depends(get_db)):
    try:
        try:
            user_uuid = uuid.UUID(payload.user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        payment = PayLoanUsingSaving(user_id=user_uuid, amount=payload.amount, description=payload.description)
        db.add(payment)
        db.commit()
        db.refresh(payment)

        return PayLoanUsingSavingResponse(
            id=str(payment.id),
            user_id=str(payment.user_id),
            full_name=user.username if user else None,
            amount=payment.amount,
            description=payment.description,
            created_at=payment.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/pay-loan-using-savings/{user_id}", response_model=list[PayLoanUsingSavingResponse])
async def get_user_payments(user_id: str, db: Session = Depends(get_db)):
    try:
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        payments = db.query(PayLoanUsingSaving).filter(PayLoanUsingSaving.user_id == user_uuid).order_by(PayLoanUsingSaving.created_at.desc()).all()
        resp = []
        for p in payments:
            resp.append(PayLoanUsingSavingResponse(
                id=str(p.id),
                user_id=str(p.user_id),
                full_name=user.username if user else None,
                amount=p.amount,
                description=p.description,
                created_at=p.created_at
            ))
        return resp
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching payments: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/pay-loan-using-savings", response_model=list[PayLoanUsingSavingResponse])
async def list_all_payments(db: Session = Depends(get_db)):
    try:
        payments = db.query(PayLoanUsingSaving).order_by(PayLoanUsingSaving.created_at.desc()).all()
        resp = []
        for p in payments:
            try:
                user = db.query(User).filter(User.id == p.user_id).first()
                full_name = user.username if user else None
            except Exception:
                full_name = None

            resp.append(PayLoanUsingSavingResponse(
                id=str(p.id),
                user_id=str(p.user_id),
                full_name=full_name,
                amount=p.amount,
                description=p.description,
                created_at=p.created_at
            ))
        return resp
    except Exception as e:
        logger.error(f"Error listing payments: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/pay-loan-using-saving/{payment_id}", response_model=PayLoanUsingSavingResponse)
async def update_payment(payment_id: str, payload: PayLoanUsingSavingUpdate = Body(...), db: Session = Depends(get_db)):
    try:
        try:
            pay_uuid = uuid.UUID(payment_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment ID format")

        payment = db.query(PayLoanUsingSaving).filter(PayLoanUsingSaving.id == pay_uuid).first()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        if payload.amount is not None:
            if payload.amount <= 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than 0")
            payment.amount = payload.amount

        if payload.description is not None:
            payment.description = payload.description

        if getattr(payload, 'created_at', None) is not None:
            try:
                payment.created_at = payload.created_at
            except Exception:
                pass

        db.commit()
        db.refresh(payment)

        user = db.query(User).filter(User.id == payment.user_id).first()

        return PayLoanUsingSavingResponse(
            id=str(payment.id),
            user_id=str(payment.user_id),
            full_name=user.username if user else None,
            amount=payment.amount,
            description=payment.description,
            created_at=payment.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating payment: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/pay-loan-using-saving/{payment_id}")
async def delete_payment(payment_id: str, db: Session = Depends(get_db)):
    try:
        try:
            pay_uuid = uuid.UUID(payment_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment ID format")

        payment = db.query(PayLoanUsingSaving).filter(PayLoanUsingSaving.id == pay_uuid).first()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        db.delete(payment)
        db.commit()
        return {"message": "Payment deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting payment: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
