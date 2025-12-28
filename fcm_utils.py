"""
FCM (Firebase Cloud Messaging) utility functions using Firebase Admin SDK
"""

import firebase_admin
from firebase_admin import credentials, messaging, exceptions
import logging
import os
import json
import re
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
_firebase_app = None

def initialize_firebase():
    """
    Initialize Firebase Admin SDK with service account credentials
    """
    global _firebase_app
    
    if _firebase_app is not None:
        return _firebase_app
    
    try:
        # Get credentials from environment variables
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")
        firebase_private_key_id = os.getenv("FIREBASE_PRIVATE_KEY_ID")
        firebase_private_key = os.getenv("FIREBASE_PRIVATE_KEY")
        firebase_client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
        firebase_client_id = os.getenv("FIREBASE_CLIENT_ID")
        
        if not all([firebase_project_id, firebase_private_key_id, firebase_private_key, firebase_client_email, firebase_client_id]):
            logger.error("Missing Firebase credentials in environment variables")
            return None
        
        # Replace escaped newlines in private key
        firebase_private_key = firebase_private_key.replace('\\n', '\n')
        
        # Create service account credentials
        cred_dict = {
            "type": "service_account",
            "project_id": firebase_project_id,
            "private_key_id": firebase_private_key_id,
            "private_key": firebase_private_key,
            "client_email": firebase_client_email,
            "client_id": firebase_client_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{firebase_client_email.replace('@', '%40')}",
            "universe_domain": "googleapis.com"
        }
        
        cred = credentials.Certificate(cred_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
        return _firebase_app
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
        return None

async def send_fcm_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None
) -> bool:
    """
    Send push notification via FCM using Firebase Admin SDK or Expo API
    Automatically detects token type and uses appropriate service
    
    Args:
        fcm_token: FCM token or Expo push token of the target device
        title: Notification title
        body: Notification body text
        data: Optional additional data to send
        
    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    if not fcm_token:
        logger.warning("No FCM token provided")
        return False
    
    # Check if it's an Expo push token
    if re.match(r'^ExponentPushToken\[[A-Za-z0-9_-]+\]$', fcm_token):
        return await send_expo_notification(fcm_token, title, body, data)
    else:
        return await send_firebase_notification(fcm_token, title, body, data)

async def send_expo_notification(
    expo_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None
) -> bool:
    """
    Send push notification via Expo Push API
    
    Args:
        expo_token: Expo push token of the target device
        title: Notification title
        body: Notification body text
        data: Optional additional data to send
        
    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    try:
        expo_url = "https://exp.host/--/api/v2/push/send"
        
        payload = {
            "to": expo_token,
            "title": title,
            "body": body,
            "data": data or {},
            "sound": "default",
            "badge": 1,
            "categoryId": "savings_notifications",
            "channelId": "savings_notifications"
        }
        
        headers = {
            "Accept": "application/json",
            "Accept-encoding": "gzip, deflate",
            "Content-Type": "application/json"
        }
        
        response = requests.post(expo_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Expo API response: {result}")
            
            # Handle both single response and array response formats
            if "data" in result:
                data = result["data"]
                
                # If data is a single object (not in array)
                if isinstance(data, dict):
                    if data.get("status") == "ok":
                        logger.info(f"Expo notification sent successfully: {data.get('id')}")
                        return True
                    else:
                        error_msg = data.get("message") or data.get("details", {}).get("error")
                        logger.warning(f"Expo notification failed: {error_msg}")
                        return False
                
                # If data is an array (original expected format)
                elif isinstance(data, list) and len(data) > 0:
                    ticket = data[0]
                    if ticket.get("status") == "ok":
                        logger.info(f"Expo notification sent successfully: {ticket.get('id')}")
                        return True
                    else:
                        error_msg = ticket.get("message") or ticket.get("details", {}).get("error")
                        logger.warning(f"Expo notification failed: {error_msg}")
                        return False
                else:
                    logger.warning(f"Expo notification: Unexpected data format: {data}")
                    return False
            else:
                logger.warning(f"Expo notification: No 'data' field in response: {result}")
                return False
        else:
            logger.error(f"Expo notification HTTP error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending Expo notification: {str(e)}")
        return False

async def send_firebase_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None
) -> bool:
    """
    Send push notification via Firebase FCM using Firebase Admin SDK
    
    Args:
        fcm_token: FCM token of the target device
        title: Notification title
        body: Notification body text
        data: Optional additional data to send
        
    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    app = initialize_firebase()
    if not app:
        logger.error("Firebase not initialized")
        return False
    
    try:
        # Create notification
        notification = messaging.Notification(
            title=title,
            body=body
        )
        
        # Create Android config for better notification handling
        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                sound='default',
                channel_id='savings_notifications'
            )
        )
        
        # Create APNS config for iOS
        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    badge=1,
                    sound='default'
                )
            )
        )
        
        # Create message
        message = messaging.Message(
            notification=notification,
            data=data or {},
            token=fcm_token,
            android=android_config,
            apns=apns_config
        )
        
        # Send message
        response = messaging.send(message)
        logger.info(f"FCM notification sent successfully: {response}")
        return True
        
    except exceptions.InvalidArgumentError as e:
        logger.warning(f"Invalid FCM token or message format: {str(e)}")
        return False
    except exceptions.UnregisteredError as e:
        logger.warning(f"FCM token is unregistered or expired: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error sending FCM notification: {str(e)}")
        return False

async def send_saving_notification(fcm_token: str, amount: float, username: str, saving_date: str = None) -> bool:
    """
    Send notification for new saving entry
    
    Args:
        fcm_token: FCM token of the user
        amount: Amount saved
        username: Username of the person who saved
        saving_date: Date when the saving was made
        
    Returns:
        bool: True if notification sent successfully
    """
    from datetime import datetime
    
    # Format the date for display
    if saving_date:
        try:
            # If saving_date is a string, parse it
            if isinstance(saving_date, str):
                date_obj = datetime.fromisoformat(saving_date.replace('Z', '+00:00'))
            else:
                date_obj = saving_date
            formatted_date = date_obj.strftime("%B %d, %Y")
            date_text = f" on {formatted_date}"
        except:
            date_text = ""
    else:
        date_text = " today"
    
    title = "💰 Saving Added Successfully!"
    body = f"Great job {username}! You saved {amount:,.0f} RWF{date_text}. Keep up the good work!"
    
    data = {
        "type": "saving_added",
        "amount": str(amount),
        "currency": "RWF",
        "username": username,
        "saving_date": saving_date or datetime.now().isoformat()
    }
    
    return await send_fcm_notification(fcm_token, title, body, data)

async def send_loan_notification(fcm_token: str, amount: float, username: str, approval_date: str = None) -> bool:
    """
    Send notification for new loan entry
    
    Args:
        fcm_token: FCM token of the user
        amount: Loan amount
        username: Username of the person who got the loan
        approval_date: Date when the loan was approved
        
    Returns:
        bool: True if notification sent successfully
    """
    from datetime import datetime
    
    title = "💳 Loan Application Approved!"
    body = f"Congratulations {username}! Your loan of {amount:,.0f} RWF has been approved and is now available."
    
    data = {
        "type": "loan_approved", 
        "amount": str(amount),
        "currency": "RWF",
        "username": username,
        "approval_date": approval_date or datetime.now().isoformat()
    }
    
    return await send_fcm_notification(fcm_token, title, body, data)

async def send_payment_notification(fcm_token: str, amount: float, username: str, payment_date: str = None) -> bool:
    """
    Send notification for loan payment
    
    Args:
        fcm_token: FCM token of the user
        amount: Payment amount
        username: Username of the person who made the payment
        payment_date: Date when the payment was made
        
    Returns:
        bool: True if notification sent successfully
    """
    from datetime import datetime
    
    title = "💸 Loan Payment Received!"
    body = f"Payment confirmed! {username} has paid {amount:,.0f} RWF towards their loan."
    
    data = {
        "type": "payment_received",
        "amount": str(amount),
        "currency": "RWF", 
        "username": username,
        "payment_date": payment_date or datetime.now().isoformat()
    }
    
    return await send_fcm_notification(fcm_token, title, body, data)

async def validate_fcm_token(fcm_token: str) -> bool:
    """
    Validate if an FCM token is properly formatted and potentially valid
    Supports both Firebase FCM tokens and Expo push tokens
    
    Args:
        fcm_token: FCM token or Expo push token to validate
        
    Returns:
        bool: True if token appears to be valid format
    """
    if not fcm_token or not isinstance(fcm_token, str):
        return False
    
    # Check for Expo push token format
    import re
    if re.match(r'^ExponentPushToken\[[A-Za-z0-9_-]+\]$', fcm_token):
        # Expo push token format: ExponentPushToken[xxxxxx]
        return len(fcm_token) > 20  # Basic length check for Expo tokens
    
    # Check for Firebase FCM token format
    # FCM tokens are typically 130+ characters long and contain specific patterns
    if len(fcm_token) < 130:
        return False
    
    # FCM tokens typically contain alphanumeric characters, dashes, underscores, and colons
    if not re.match(r'^[A-Za-z0-9_:.-]+$', fcm_token):
        return False
    
    return True

async def send_test_notification(fcm_token: str) -> bool:
    """
    Send a test notification to verify FCM token works
    
    Args:
        fcm_token: FCM token to test
        
    Returns:
        bool: True if test notification sent successfully
    """
    if not await validate_fcm_token(fcm_token):
        logger.warning("Invalid FCM token format")
        return False
    
    title = "🧪 Test Notification"
    body = "FCM integration is working correctly!"
    
    data = {
        "type": "test_notification",
        "timestamp": str(int(__import__('time').time()))
    }
    
    return await send_fcm_notification(fcm_token, title, body, data)