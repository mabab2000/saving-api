"""
Test script for FCM token validation and notifications
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fcm_utils import validate_fcm_token, send_test_notification

async def test_fcm_validation():
    """Test FCM token validation and notification sending"""
    
    # Test cases for token validation
    test_tokens = [
        # Invalid tokens (should return False)
        "",
        "short_token",
        None,
        "invalid@characters",
        
        # Sample valid format FCM (but not real) - should pass validation but fail to send
        "f1BdLGhuEMfj7H1bVz9gJ3:APA91bF1BdLGhuEMfj7H1bVz9gJ3K4L5M6N7O8P9Q0R1S2T3U4V5W6X7Y8Z9A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2X3Y4Z5A6",
        
        # Real Expo token from your database (should pass validation)
        "ExponentPushToken[nSVlkBF3mzK2TwaLVAaiNH]"
    ]
    
    print("🧪 Testing FCM Token Validation\n")
    
    for i, token in enumerate(test_tokens, 1):
        if token is None:
            display_token = "None"
        elif len(str(token)) > 50:
            display_token = f"{str(token)[:20]}...{str(token)[-20:]}"
        else:
            display_token = str(token)
            
        is_valid = await validate_fcm_token(token)
        print(f"Test {i}: {display_token}")
        print(f"  Valid: {'✅' if is_valid else '❌'}")
        print()
    
    # Test sending notification with your real Expo token
    print("📱 Testing Notification Sending\n")
    expo_token = "ExponentPushToken[nSVlkBF3mzK2TwaLVAaiNH]"
    
    print(f"Testing with Expo token: {expo_token}")
    success = await send_test_notification(expo_token)
    print(f"Notification sent: {'✅' if success else '❌'}")
    
    if success:
        print("\n🎉 Great! Your Expo token is working and notification was sent!")
    else:
        print("\n💡 Note: Expo token format is valid, but notification may have failed.")
        print("   This could be due to the device not being reachable or token expiration.")

if __name__ == "__main__":
    print("🔥 FCM Validation and Testing Script")
    print("=" * 40)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the test
    asyncio.run(test_fcm_validation())