"""
Test the phone verification endpoint to check FCM token update
"""

import requests
import json

def test_phone_verification_endpoint():
    """Test the phone verification endpoint with your actual data"""
    
    base_url = "https://saving-api.mababa.app"
    
    # Test data with your actual phone number and FCM token
    test_data = {
        "phone_number": "+250791523793",  # Your phone number (needs + prefix)
        "fcm_token": "ExponentPushToken[nSVlkBF3mzK2TwaLVAaiNH]"  # Your FCM token
    }
    
    print("🔍 Testing Phone Verification Endpoint")
    print("=" * 45)
    print(f"📞 Phone: {test_data['phone_number']}")  # Already includes +
    print(f"🔑 FCM Token: {test_data['fcm_token']}")
    
    try:
        # Make the request
        response = requests.post(
            f"{base_url}/api/verify-phone",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success! Response:")
            print(json.dumps(result, indent=2))
            
            # Check if FCM token was validated and updated
            if "fcm_token_valid" in result:
                if result["fcm_token_valid"] is True:
                    print("\n🟢 FCM Token: Successfully validated and updated in database")
                elif result["fcm_token_valid"] is False:
                    print("\n🔴 FCM Token: Invalid format, not stored")
                elif result["fcm_token_valid"] is None:
                    print("\n⚪ FCM Token: Not provided in request")
                    
            if result.get("exists"):
                print(f"👤 User ID: {result.get('user_id')}")
                print("✅ Phone number verified successfully")
            else:
                print("❌ Phone number not found in database")
                
        else:
            print("❌ Error Response:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                print(response.text)
                
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server. Is it running on localhost:8000?")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_phone_verification_endpoint()