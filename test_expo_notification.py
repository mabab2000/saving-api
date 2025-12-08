"""
Test Expo push notification with your actual token
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from fcm_utils import send_fcm_notification, validate_fcm_token

async def test_expo_notification():
    """Test sending notification to your Expo token"""
    
    # Your actual Expo token
    expo_token = "ExponentPushToken[nSVlkBF3mzK2TwaLVAaiNH]"
    
    print("🧪 Testing Expo Push Notification")
    print("=" * 40)
    print(f"📱 Token: {expo_token}")
    
    # Validate token first
    is_valid = await validate_fcm_token(expo_token)
    print(f"🔍 Token Valid: {'✅' if is_valid else '❌'}")
    
    if not is_valid:
        print("❌ Token validation failed, not sending notification")
        return
    
    # Send test notification
    print("\n📤 Sending test notification...")
    
    title = "💰 Savings App Test"
    body = "Your Expo push notification is working! 🎉"
    data = {
        "type": "test",
        "timestamp": "1734509999"
    }
    
    success = await send_fcm_notification(expo_token, title, body, data)
    
    if success:
        print("✅ Notification sent successfully!")
        print("📱 Check your device for the notification!")
    else:
        print("❌ Failed to send notification")
        print("💡 This could be due to:")
        print("   - Device not reachable")
        print("   - Token expired")
        print("   - App not installed")

if __name__ == "__main__":
    asyncio.run(test_expo_notification())