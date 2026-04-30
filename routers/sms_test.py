from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import logging
from sms_utils import send_saving_sms_notification, get_sms_service
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

class SMSTestRequest(BaseModel):
    phone_number: str
    user_name: str
    amount: float = 1000.0
    total_savings: float = 5000.0
    actual_savings: float = 4500.0

@router.post("/test-sms")
async def test_sms_notification(request: SMSTestRequest):
    """
    Test SMS notification functionality
    """
    try:
        logger.info(f"Testing SMS notification for {request.phone_number}")
        
        # Test if SMS service is configured
        sms_service = get_sms_service()
        if not sms_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SMS service not configured properly. Check environment variables."
            )
        
        # Send test SMS
        success = send_saving_sms_notification(
            phone_number=request.phone_number,
            user_name=request.user_name,
            amount=request.amount,
            total_savings=request.total_savings,
            actual_savings=request.actual_savings,
            saving_date=datetime.now()
        )
        
        if success:
            return {
                "success": True,
                "message": f"Test SMS sent successfully to {request.phone_number}",
                "phone_number": request.phone_number,
                "user_name": request.user_name
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send SMS. Check logs for details."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in SMS test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing SMS: {str(e)}"
        )

@router.get("/sms-status")
async def get_sms_status():
    """
    Check SMS service configuration status
    """
    try:
        sms_service = get_sms_service()
        if sms_service:
            return {
                "configured": True,
                "sandbox_mode": sms_service.use_sandbox,
                "username": sms_service.username,
                "sender_id": sms_service.sender_id,
                "api_url": sms_service.url
            }
        else:
            return {
                "configured": False,
                "message": "SMS service not configured. Check environment variables."
            }
    except Exception as e:
        logger.error(f"Error checking SMS status: {str(e)}")
        return {
            "configured": False,
            "error": str(e)
        }