# SMS Integration Setup Guide

This guide explains how to set up and use the SMS notifications for savings in your API.

## Overview

When a user creates a new saving entry, the system will automatically:
1. Save the record to the database
2. Send an FCM push notification (if configured)
3. Send an SMS notification to the user's phone number (NEW)

## SMS Message Format

The SMS is sent in Kinyarwanda and follows this format:

```
SAVING
Muraho [User Name], ubwizigame bwawe bwa [Month Year] bwakiriwe neza. 
Umubare: [Amount] Rwf uinjijwe.
Ubwizigame bwose: [Total Savings] Rwf
Ubwizigame bwawe buri muri konti: [Actual Savings] Rwf.
```

**Example:**
```
SAVING
Muraho John Doe, ubwizigame bwawe bwa May 2026 bwakiriwe neza. 
Umubare: 3,000 Rwf uinjijwe.
Ubwizigame bwose: 15,000 Rwf
Ubwizigame bwawe buri muri konti: 12,500 Rwf.
```

**Note**: 
- **Total Savings**: Sum of all money saved
- **Actual Savings**: Total savings minus distributions, penalties, and loan payments

## Configuration

### Environment Variables

Add these variables to your `.env` file:

```bash
# SMS Configuration (Africa's Talking)
AFRICASTALKING_API_KEY=atsk_719728113fd68b4faa643dc5487182fbe0b2ceceab45b406966f3b7d4926618b1d25b86d
AFRICASTALKING_USERNAME=IvaraConnect
AFRICASTALKING_USE_SANDBOX=false
AFRICASTALKING_SENDER_ID=
```

### Configuration Options

- **AFRICASTALKING_API_KEY**: Your Africa's Talking API key
- **AFRICASTALKING_USERNAME**: Your Africa's Talking username (default: IvaraConnect)
- **AFRICASTALKING_USE_SANDBOX**: Set to `true` for testing, `false` for production
- **AFRICASTALKING_SENDER_ID**: Custom sender ID (optional, leave empty for default)

## How It Works

1. **When a saving is created** via `POST /api/saving`:
   - The system validates the user exists
   - Creates the saving record in the database
   - Calculates the user's total savings
   - Sends FCM notification (if user has FCM token)
   - **NEW**: Sends SMS notification (if user has phone number)

2. **SMS Sending Process**:
   - Gets user's phone number from the database
   - Formats the message in Kinyarwanda with user details
   - Uses Africa's Talking API with SSL fallback mechanisms
   - Logs success/failure but doesn't block saving creation

## Testing SMS Functionality

### 1. Check SMS Service Status

```bash
GET /api/sms-status
```

Response:
```json
{
  "configured": true,
  "sandbox_mode": false,
  "username": "IvaraConnect",
  "sender_id": null,
  "api_url": "https://api.africastalking.com/version1/messaging"
}
```

### 2. Send Test SMS

```bash
POST /api/test-sms
Content-Type: application/json

{
  "phone_number": "+250783857284",
  "user_name": "Test User",
  "amount": 1000.0,
  "total_savings": 5000.0,
  "actual_savings": 4500.0
}
```

Response:
```json
{
  "success": true,
  "message": "Test SMS sent successfully to +250783857284",
  "phone_number": "+250783857284",
  "user_name": "Test User"
}
```

## Requirements

The SMS functionality requires these dependencies (already in requirements.txt):
- `requests`: For HTTP API calls
- `python-dotenv`: For environment variables

## Error Handling

The SMS integration is designed to be non-blocking:
- If SMS fails to send, the saving operation will still complete successfully
- Errors are logged for debugging
- The API returns success even if SMS fails (saving is more important)

## Phone Number Format

Phone numbers should be stored in international format in the database:
- ✅ Correct: `+250783857284`
- ✅ Also works: `250783857284` (automatically adds +)
- ❌ Incorrect: `0783857284`

## Troubleshooting

### Common Issues

1. **SMS not sending**:
   - Check API key is correct
   - Verify phone number format
   - Check internet connectivity
   - Review logs for detailed error messages

2. **401 Unauthorized**:
   - Verify API key
   - Check if using correct environment (sandbox vs production)

3. **Invalid phone number**:
   - Ensure phone number starts with country code
   - Use international format (+250...)

### Logs

Check application logs for SMS-related messages:
- `SMS notification sent successfully`
- `SMS notification failed`
- `Failed to send SMS notification`

## Production Considerations

1. **API Credits**: Ensure your Africa's Talking account has sufficient credits
2. **Rate Limits**: Be aware of API rate limits for high-volume applications  
3. **Monitoring**: Set up monitoring for SMS delivery failures
4. **Fallback**: Consider alternative notification methods if SMS fails

## Files Modified

- `sms_utils.py`: New SMS utility module
- `routers/savings.py`: Updated to include SMS notifications
- `routers/sms_test.py`: New test endpoints for SMS
- `main.py`: Registered SMS test router
- `.env`: Added SMS configuration
- `.env.example`: Updated with SMS config template