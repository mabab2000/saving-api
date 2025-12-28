"""
Test the updated notification system with RWF currency
"""

import asyncio
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from fcm_utils import send_saving_notification, validate_fcm_token

async def test_rwf_notification():
    """Test the updated notification with RWF currency and date"""
    
    # Your actual Expo token
    expo_token = "ExponentPushToken[nSVlkBF3mzK2TwaLVAaiNH]"
    
    print("🧪 Testing Updated RWF Notification")
    print("=" * 45)
    print(f"📱 Token: {expo_token}")
    
    # Validate token first
    is_valid = await validate_fcm_token(expo_token)
    print(f"🔍 Token Valid: {'✅' if is_valid else '❌'}")
    
    if not is_valid:
        print("❌ Token validation failed, not sending notification")
        return
    
    # Test with RWF amount and current date
    print("\n📤 Sending updated RWF notification...")
    
    test_amount = 5000.0  # 5000 RWF
    test_username = "John Doe"
    test_date = datetime.now().isoformat()
    
    print(f"💰 Amount: {test_amount:,.0f} RWF")
    print(f"👤 Username: {test_username}")
    print(f"📅 Date: {datetime.now().strftime('%B %d, %Y')}")
    
    success = await send_saving_notification(
        expo_token, 
        test_amount, 
        test_username, 
        test_date
    )
    
    if success:
        print("\n✅ RWF Notification sent successfully!")
        print("📱 Check your device for the updated notification format!")
        print("\n🎉 New Features:")
        print("   • Currency shown in RWF")
        print("   • Clear success message")
        print("   • Saving date included")
        print("   • Custom app icon")
        print("   • Better formatting")
    else:
        print("\n❌ Failed to send notification")
        print("💡 Check the server logs for more details")

if __name__ == "__main__":
    asyncio.run(test_rwf_notification())