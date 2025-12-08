"""
Test script for Firebase FCM notifications
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(__file__))

from fcm_utils import send_saving_notification, send_loan_notification, initialize_firebase, validate_fcm_token, send_test_notification

async def test_fcm_notifications():
    """Test FCM notification functionality"""
    
    print("🔥 Testing Firebase FCM Integration...")
    
    # Initialize Firebase
    app = initialize_firebase()
    if not app:
        print("❌ Failed to initialize Firebase. Check your credentials.")
        return
    
    print("✅ Firebase initialized successfully!")
    
    # Test FCM token (replace with a real FCM token from your app)
    test_fcm_token = "test-token-replace-with-real-token"
    
    print(f"\n📱 Testing notifications with token: {test_fcm_token[:20]}...")
    
    # Validate FCM token format
    print("\n🔍 Validating FCM token format...")
    is_valid = await validate_fcm_token(test_fcm_token)
    if is_valid:
        print("✅ FCM token format is valid")
    else:
        print("❌ FCM token format is invalid - this will likely fail")
    
    # Test basic notification
    print("\n🧪 Testing basic notification...")
    success = await send_test_notification(test_fcm_token)
    if success:
        print("✅ Test notification sent successfully!")
    else:
        print("❌ Failed to send test notification")
    
    # Test saving notification
    print("\n💰 Testing saving notification...")
    success = await send_saving_notification(
        fcm_token=test_fcm_token,
        amount=1500.0,
        username="John Doe"
    )
    
    if success:
        print("✅ Saving notification sent successfully!")
    else:
        print("❌ Failed to send saving notification")
    
    # Test loan notification
    print("\n💳 Testing loan notification...")
    success = await send_loan_notification(
        fcm_token=test_fcm_token,
        amount=5000.0,
        username="John Doe"
    )
    
    if success:
        print("✅ Loan notification sent successfully!")
    else:
        print("❌ Failed to send loan notification")
    
    print("\n🎉 FCM test completed!")

if __name__ == "__main__":
    asyncio.run(test_fcm_notifications())