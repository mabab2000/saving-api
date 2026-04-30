#!/usr/bin/env python3
"""
Simple SMS test script for testing Africa's Talking integration
Run this script to test SMS functionality independently of the main API
"""

import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Add the current directory to Python path so we can import our modules
import sys
sys.path.append('.')

from sms_utils import send_saving_sms_notification, get_sms_service

def test_sms_service():
    """Test SMS service configuration and send a test message"""
    
    print("🧪 Testing SMS Service Configuration...")
    print("=" * 50)
    
    # Test if service is configured
    try:
        service = get_sms_service()
        if not service:
            print("❌ SMS service not configured!")
            print("Please check your .env file and ensure these variables are set:")
            print("- AFRICASTALKING_API_KEY")
            print("- AFRICASTALKING_USERNAME")
            return False
        
        print("✅ SMS service configured successfully!")
        print(f"📊 Configuration:")
        print(f"   Username: {service.username}")
        print(f"   Sandbox Mode: {service.use_sandbox}")
        print(f"   API URL: {service.url}")
        print(f"   Sender ID: {service.sender_id or 'Default'}")
        print()
        
    except Exception as e:
        print(f"❌ Error initializing SMS service: {e}")
        return False
    
    # Test SMS sending
    print("📱 Testing SMS Sending...")
    print("=" * 50)
    
    # Test configuration - modify these values
    test_phone = input("Enter phone number to test (e.g., +250783857284): ").strip()
    test_name = input("Enter test user name (e.g., John Doe): ").strip() or "Test User"
    
    if not test_phone:
        print("❌ Phone number is required!")
        return False
    
    # Send test SMS
    try:
        success = send_saving_sms_notification(
            phone_number=test_phone,
            user_name=test_name,
            amount=5000.0,
            total_savings=25000.0,
            actual_savings=20000.0,
            saving_date=datetime.now()
        )
        
        if success:
            print("✅ Test SMS sent successfully!")
            print(f"📱 Check {test_phone} for the message")
            return True
        else:
            print("❌ Failed to send test SMS!")
            print("Check the console output above for error details")
            return False
            
    except Exception as e:
        print(f"❌ Error sending test SMS: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Africa's Talking SMS Test Script")
    print("=" * 50)
    
    # Check environment variables
    api_key = os.getenv("AFRICASTALKING_API_KEY")
    if not api_key:
        print("❌ AFRICASTALKING_API_KEY not found in environment!")
        print("\n📝 Setup Instructions:")
        print("1. Create a .env file in the project root")
        print("2. Add: AFRICASTALKING_API_KEY=your_api_key_here")
        print("3. Add: AFRICASTALKING_USERNAME=your_username")
        print("4. Run this script again")
        return
    
    print(f"🔑 API Key found: {api_key[:20]}...")
    print()
    
    # Run the test
    success = test_sms_service()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SMS test completed successfully!")
        print("✅ Your SMS integration is working correctly!")
        print("\n🚀 Next steps:")
        print("1. Start your FastAPI server: uvicorn main:app --reload")
        print("2. Create a saving via POST /api/saving")
        print("3. SMS will be sent automatically!")
    else:
        print("❌ SMS test failed!")
        print("\n🔍 Troubleshooting:")
        print("1. Check your API key is correct")
        print("2. Verify your Africa's Talking account has credits")
        print("3. Check internet connectivity")
        print("4. Review error messages above")

if __name__ == "__main__":
    main()