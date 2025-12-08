"""
Test phone verification with FCM token validation
"""
import requests
import json

# Test data
base_url = "http://localhost:8000"
test_cases = [
    {
        "name": "Valid FCM token format",
        "phone_number": "+250788123456",  # Replace with a real phone number from your database
        "fcm_token": "f1BdLGhuEMfj7H1bVz9gJ3:APA91bF1BdLGhuEMfj7H1bVz9gJ3K4L5M6N7O8P9Q0R1S2T3U4V5W6X7Y8Z9A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2X3Y4Z5A6"
    },
    {
        "name": "Invalid FCM token (too short)",
        "phone_number": "+250788123456",
        "fcm_token": "short_token"
    },
    {
        "name": "Invalid FCM token (invalid characters)",
        "phone_number": "+250788123456",
        "fcm_token": "invalid@characters#token"
    },
    {
        "name": "No FCM token",
        "phone_number": "+250788123456",
        "fcm_token": None
    }
]

def test_phone_verification():
    print("🔍 Testing Phone Verification with FCM Token Validation")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📱 Test {i}: {test_case['name']}")
        print("-" * 40)
        
        # Prepare request data
        data = {
            "phone_number": test_case["phone_number"]
        }
        
        if test_case["fcm_token"]:
            data["fcm_token"] = test_case["fcm_token"]
            token_display = f"{test_case['fcm_token'][:20]}..." if len(test_case["fcm_token"]) > 20 else test_case["fcm_token"]
            print(f"📞 Phone: {test_case['phone_number']}")
            print(f"🔑 FCM Token: {token_display}")
        else:
            print(f"📞 Phone: {test_case['phone_number']}")
            print(f"🔑 FCM Token: None")
        
        try:
            # Make request
            response = requests.post(
                f"{base_url}/api/verify-phone",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"📋 Response: {json.dumps(result, indent=2)}")
                
                if "fcm_token_valid" in result:
                    if result["fcm_token_valid"] is True:
                        print("🟢 FCM Token: Valid and stored")
                    elif result["fcm_token_valid"] is False:
                        print("🔴 FCM Token: Invalid format, not stored")
                    else:
                        print("⚪ FCM Token: Not provided")
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"📋 Error: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Error: Could not connect to server. Is it running on localhost:8000?")
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_phone_verification()