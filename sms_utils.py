import requests
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import urllib3
import logging
import os
from datetime import datetime
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

# Disable SSL warnings globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SSLAdapter(HTTPAdapter):
    """Custom SSL adapter to handle SSL issues with Africa's Talking API"""
    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)
    
    def init_poolmanager(self, *args, **pool_kwargs):
        if self.ssl_context:
            pool_kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(*args, **pool_kwargs)

class AfricaTalkingSMS:
    """Africa's Talking SMS service wrapper"""
    
    def __init__(self):
        # Get configuration from environment variables
        self.api_key = os.getenv("AFRICASTALKING_API_KEY")
        self.username = os.getenv("AFRICASTALKING_USERNAME", "IvaraConnect")
        self.use_sandbox = os.getenv("AFRICASTALKING_USE_SANDBOX", "false").lower() == "true"
        self.custom_sender_id = os.getenv("AFRICASTALKING_SENDER_ID")
        
        # Validate API key
        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            logger.error("❌ ERROR: Please set AFRICASTALKING_API_KEY in environment variables!")
            raise ValueError("Africa's Talking API key not configured")
        
        # Set up URLs and sender ID based on environment
        if self.use_sandbox:
            self.username = "sandbox"
            self.url = "https://api.sandbox.africastalking.com/version1/messaging"
            self.sender_id = "AFRICASTKNG"  # Force default sender for sandbox
            logger.info("🔧 Using SANDBOX environment (no real SMS sent)")
        else:
            self.url = "https://api.africastalking.com/version1/messaging"
            self.sender_id = self.custom_sender_id
            logger.info("🚀 Using PRODUCTION environment (real SMS sent)")
        
        # Set up headers
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "apiKey": self.api_key
        }
    
    def _make_request_with_fallback(self, data: dict) -> Optional[requests.Response]:
        """Make request to Africa's Talking API with multiple fallback approaches"""
        logger.info(f"🌐 Attempting to connect to: {self.url}")
        
        # Approach 1: Simple approach with verify=False
        try:
            logger.debug("📡 Approach 1: Simple request with SSL verification disabled...")
            session = requests.Session()
            session.verify = False
            
            response = session.post(self.url, headers=self.headers, data=data, timeout=30)
            logger.debug(f"Response received: {response.status_code}")
            
            if response.status_code == 401:
                logger.error("401 Error - API Key might be invalid or not authorized for this environment")
                logger.error(f"Response: {response.text[:200]}...")
            elif response.status_code != 201:
                logger.warning(f"Unexpected response code: {response.status_code}")
                logger.debug(f"Response: {response.text[:200]}...")
            
            return response
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP Error: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Connection Error: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"❌ Timeout Error: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request Error: {e}")
        except Exception as e:
            logger.error(f"❌ Approach 1 failed: {str(e)}")
        
        # Approach 2: Custom SSL context with legacy support
        try:
            logger.debug("📡 Approach 2: Custom SSL context with legacy support...")
            session = requests.Session()
            
            # Create SSL context with legacy support
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.set_ciphers('DEFAULT:@SECLEVEL=1')  # Allow legacy ciphers
            
            adapter = SSLAdapter(ssl_context=ssl_context)
            session.mount("https://", adapter)
            session.verify = False
            
            response = session.post(self.url, headers=self.headers, data=data, timeout=30)
            return response
            
        except Exception as e:
            logger.error(f"❌ Approach 2 failed: {str(e)}")
        
        # Approach 3: Basic requests with timeout
        try:
            logger.debug("📡 Approach 3: Basic requests with timeout...")
            response = requests.post(
                self.url, 
                headers=self.headers, 
                data=data, 
                timeout=30,
                verify=False
            )
            return response
            
        except Exception as e:
            logger.error(f"❌ Approach 3 failed: {str(e)}")
        
        return None
    
    def send_sms(self, phone_number: str, message: str) -> bool:
        """
        Send SMS to a phone number
        
        Args:
            phone_number (str): Phone number in international format (e.g., +250783857284)
            message (str): Message content
            
        Returns:
            bool: True if SMS was sent successfully, False otherwise
        """
        try:
            # Ensure phone number starts with +
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
            
            # Build data payload
            data = {
                "username": self.username,
                "to": phone_number,
                "message": message
            }
            
            # Add sender ID if specified
            if self.sender_id:
                data["from"] = self.sender_id
            
            logger.info(f"Sending SMS to {phone_number[:8]}***")
            logger.debug(f"Message preview: {message[:50]}...")
            
            # Make the request
            response = self._make_request_with_fallback(data)
            
            if response:
                logger.info(f"✅ SMS API Response - Status: {response.status_code}")
                
                if response.status_code == 201:
                    # Parse success response
                    try:
                        resp_json = response.json()
                        if 'SMSMessageData' in resp_json:
                            sms_data = resp_json['SMSMessageData']
                            logger.info(f"SMS sent successfully: {sms_data.get('Message', 'N/A')}")
                            
                            if 'Recipients' in sms_data and sms_data['Recipients']:
                                recipient = sms_data['Recipients'][0]
                                status_code = recipient.get('statusCode')
                                # Africa's Talking success status codes:
                                # 100: Queued (successfully queued for delivery)
                                # 101: Sent (message sent to carrier)
                                # 102: Received (message received by recipient)
                                if status_code in [100, 101, 102]:
                                    status_text = recipient.get('status', 'N/A')
                                    cost = recipient.get('cost', 'N/A')
                                    if status_code == 100:
                                        logger.info(f"SMS queued successfully - Status: {status_text} - Cost: {cost}")
                                    elif status_code == 101:
                                        logger.info(f"SMS sent successfully - Status: {status_text} - Cost: {cost}")
                                    elif status_code == 102:
                                        logger.info(f"SMS delivered successfully - Status: {status_text} - Cost: {cost}")
                                    return True
                                else:
                                    logger.warning(f"SMS failed - Status: {recipient.get('status', 'N/A')} ({status_code})")
                                    return False
                        else:
                            logger.warning("Unexpected response format")
                            return False
                    except Exception as e:
                        logger.error(f"Error parsing SMS response: {e}")
                        return False
                else:
                    logger.error(f"SMS API returned error: {response.status_code} - {response.text}")
                    return False
            else:
                logger.error("❌ All SMS sending approaches failed!")
                return False
                
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False

# Global SMS service instance
sms_service = None

def get_sms_service() -> Optional[AfricaTalkingSMS]:
    """Get or initialize the SMS service"""
    global sms_service
    try:
        if sms_service is None:
            sms_service = AfricaTalkingSMS()
        return sms_service
    except Exception as e:
        logger.error(f"Failed to initialize SMS service: {e}")
        return None

def send_saving_sms_notification(
    phone_number: str, 
    user_name: str, 
    amount: float, 
    total_savings: float,
    actual_savings: float, 
    saving_date: datetime
) -> bool:
    """
    Send SMS notification for a new saving entry
    
    Args:
        phone_number (str): User's phone number
        user_name (str): User's name  
        amount (float): Amount saved
        total_savings (float): Total savings amount (sum of all savings)
        actual_savings (float): Actual savings (total - distributions - penalties - loan payments)
        saving_date (datetime): Date when saving was recorded
        
    Returns:
        bool: True if SMS was sent successfully, False otherwise
    """
    try:
        service = get_sms_service()
        if not service:
            logger.error("SMS service not available")
            return False
        
        # Format the date in a readable format  
        formatted_date = saving_date.strftime("%B %Y")  # e.g., "May 2026"
        day_date = saving_date.strftime("%d/%m/%Y")  # e.g., "03/05/2026"
        
        # Create shorter message in Kinyarwanda with SAVING Update format
        message = (
            f"SAVING Update : Muraho {user_name}! Ubwizigame bwawe bwa {formatted_date}: {amount:,.0f}Rwf. "
            f"Yose hamwe ni: {total_savings:,.0f}Rwf. Balance: {actual_savings:,.0f}Rwf."
        )
        
        logger.info(f"Sending saving notification SMS to {user_name}")
        return service.send_sms(phone_number, message)
        
    except Exception as e:
        logger.error(f"Error sending saving SMS notification: {str(e)}")
        return False