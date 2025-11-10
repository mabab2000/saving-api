from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import logging
from sqlalchemy import func
from datetime import datetime

from database import SessionLocal
from models import User, Saving, Loan, Penalty, LoanPayment

router = APIRouter()
logger = logging.getLogger(__name__)


def compute_stats(db):
    # Total sums
    total_savings = db.query(func.coalesce(func.sum(Saving.amount), 0)).scalar() or 0.0
    total_loans = db.query(func.coalesce(func.sum(Loan.amount), 0)).scalar() or 0.0
    total_penalties = db.query(func.coalesce(func.sum(Penalty.amount), 0)).scalar() or 0.0
    user_count = db.query(func.count(User.id)).scalar() or 0

    # Latest saving month/year
    latest_saving = db.query(Saving).order_by(Saving.created_at.desc()).first()
    sum_latest_saving = 0.0
    if latest_saving and latest_saving.created_at:
        lm = latest_saving.created_at
        sum_latest_saving = db.query(func.coalesce(func.sum(Saving.amount), 0)).filter(
            func.extract('month', Saving.created_at) == lm.month,
            func.extract('year', Saving.created_at) == lm.year
        ).scalar() or 0.0

    # Latest loan payment month/year
    latest_payment = db.query(LoanPayment).order_by(LoanPayment.created_at.desc()).first()
    sum_latest_loan_payments = 0.0
    if latest_payment and latest_payment.created_at:
        pm = latest_payment.created_at
        sum_latest_loan_payments = db.query(func.coalesce(func.sum(LoanPayment.amount), 0)).filter(
            func.extract('month', LoanPayment.created_at) == pm.month,
            func.extract('year', LoanPayment.created_at) == pm.year
        ).scalar() or 0.0

    # Build result
    return {
        "total_savings": float(total_savings),
        "total_loans": float(total_loans),
        "total_penalties": float(total_penalties),
        "user_count": int(user_count),
        "sum_latest_saving": float(sum_latest_saving),
        "sum_latest_loan_payments": float(sum_latest_loan_payments),
        "generated_at": datetime.utcnow().isoformat() + 'Z'
    }


@router.websocket("/ws/stats")
async def websocket_stats(websocket: WebSocket):
    await websocket.accept()
    db = SessionLocal()
    try:
        while True:
            try:
                stats = compute_stats(db)
                await websocket.send_json(stats)
            except Exception as e:
                logger.exception("Error computing or sending stats: %s", e)
                await websocket.send_json({"error": str(e)})
            # wait for 10 seconds or until client sends a ping
            try:
                # wait for either a client message or timeout
                done, pending = await asyncio.wait(
                    [asyncio.create_task(websocket.receive_text()), asyncio.create_task(asyncio.sleep(10))],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                # If client sent a message, consume it (no-op) and continue to send next stats immediately
                for task in done:
                    if not task.cancelled() and task is not None:
                        try:
                            _ = task.result()
                        except Exception:
                            pass
                for p in pending:
                    p.cancel()
            except asyncio.CancelledError:
                break
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    finally:
        db.close()