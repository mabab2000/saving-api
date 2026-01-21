from fastapi import APIRouter, HTTPException, status, Depends, Body
from sqlalchemy.orm import Session
import logging
import traceback
import uuid
from datetime import datetime

from models import Distribution, User
from schemas import DistributionCreate, DistributionResponse, DistributionUpdate
from database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/distribution", response_model=DistributionResponse)
async def create_distribution(payload: DistributionCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Creating distribution for user_id: {payload.user_id}, amount: {payload.amount}")

        try:
            user_uuid = uuid.UUID(payload.user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        dist = Distribution(user_id=user_uuid, amount=payload.amount)
        db.add(dist)
        db.commit()
        db.refresh(dist)

        return DistributionResponse(
            id=str(dist.id),
            user_id=str(dist.user_id),
            full_name=user.username if user else None,
            amount=dist.amount,
            year=dist.created_at.year
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating distribution: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/distributions/{user_id}", response_model=list[DistributionResponse])
async def get_user_distributions(user_id: str, db: Session = Depends(get_db)):
    try:
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        dists = db.query(Distribution).filter(Distribution.user_id == user_uuid).order_by(Distribution.created_at.desc()).all()
        resp = []
        for d in dists:
            resp.append(DistributionResponse(
                id=str(d.id),
                user_id=str(d.user_id),
                full_name=user.username if user else None,
                amount=d.amount,
                year=d.created_at.year
            ))
        return resp
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching distributions: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/distributions", response_model=list[DistributionResponse])
async def list_all_distributions(db: Session = Depends(get_db)):
    try:
        dists = db.query(Distribution).order_by(Distribution.created_at.desc()).all()
        resp = []
        for d in dists:
            try:
                user = db.query(User).filter(User.id == d.user_id).first()
                full_name = user.username if user else None
            except Exception:
                full_name = None

            resp.append(DistributionResponse(
                id=str(d.id),
                user_id=str(d.user_id),
                full_name=full_name,
                amount=d.amount,
                year=d.created_at.year
            ))
        return resp
    except Exception as e:
        logger.error(f"Error listing distributions: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/distribution/{distribution_id}", response_model=DistributionResponse)
async def update_distribution(distribution_id: str, payload: DistributionUpdate = Body(...), db: Session = Depends(get_db)):
    try:
        try:
            dist_uuid = uuid.UUID(distribution_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid distribution ID format")

        dist = db.query(Distribution).filter(Distribution.id == dist_uuid).first()
        if not dist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Distribution not found")

        if payload.amount is not None:
            if payload.amount <= 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than 0")
            dist.amount = payload.amount

        if getattr(payload, 'created_at', None) is not None:
            try:
                dist.created_at = payload.created_at
            except Exception:
                pass

        db.commit()
        db.refresh(dist)

        user = db.query(User).filter(User.id == dist.user_id).first()

        return DistributionResponse(
            id=str(dist.id),
            user_id=str(dist.user_id),
            full_name=user.username if user else None,
            amount=dist.amount,
            year=dist.created_at.year
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating distribution: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/distribution/{distribution_id}")
async def delete_distribution(distribution_id: str, db: Session = Depends(get_db)):
    try:
        try:
            dist_uuid = uuid.UUID(distribution_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid distribution ID format")

        dist = db.query(Distribution).filter(Distribution.id == dist_uuid).first()
        if not dist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Distribution not found")

        db.delete(dist)
        db.commit()
        return {"message": "Distribution deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting distribution: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
