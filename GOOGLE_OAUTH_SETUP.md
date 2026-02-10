# Google OAuth Authentication Setup Guide

This guide explains how to integrate Google OAuth authentication into your FastAPI application.

## Features Implemented

✅ **Email/Password Login** - Traditional authentication with bcrypt password hashing  
✅ **Google OAuth Login** - Sign in with Google account  
✅ **Automatic User Creation** - New users are automatically created during Google sign-in  
✅ **FCM Token Support** - Push notification tokens can be provided during login  
✅ **Profile Picture Support** - Google profile pictures are stored  

## Setup Instructions

### 1. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google+ API** or **Google Identity Services**
4. Go to **Credentials** → **Create Credentials** → **OAuth Client ID**
5. Configure the OAuth consent screen if prompted
6. Select **Web application** as the application type
7. Add authorized JavaScript origins (e.g., `http://localhost:3000`, `https://yourdomain.com`)
8. Add authorized redirect URIs (e.g., `http://localhost:3000/auth/callback`)
9. Copy the **Client ID** - you'll need this!

### 2. Update Environment Variables

Open your `.env` file and add your Google Client ID:

```env
GOOGLE_CLIENT_ID=your-actual-google-client-id.apps.googleusercontent.com
```

⚠️ Replace `your-actual-google-client-id.apps.googleusercontent.com` with your actual Client ID from Google Cloud Console.

### 3. Install Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

This will install:
- `google-auth` - Google authentication library
- `google-auth-oauthlib` - OAuth 2.0 support
- `google-auth-httplib2` - HTTP transport for Google auth

### 4. Run Database Migration

Run the migration script to add OAuth columns to your database:

```bash
python scripts/add_oauth_columns.py
```

This adds the following columns to the `saving_users` table:
- `oauth_provider` - Provider name (e.g., 'google')
- `oauth_id` - OAuth provider's user ID
- `profile_picture` - URL to the user's profile picture
- Makes `hashed_password` nullable (for OAuth-only users)

### 5. Restart Your Server

```bash
uvicorn main:app --reload
```

## API Endpoints

### 1. Email/Password Login
**POST** `/auth/login`

```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_info": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_doe",
    "email": "user@example.com",
    "phone_number": "250123456789"
  }
}
```

### 2. Google OAuth Login
**POST** `/auth/login/google`

```json
{
  "token": "google_id_token_from_client",
  "fcm_token": "optional_firebase_cloud_messaging_token"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_info": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_doe",
    "email": "user@example.com",
    "phone_number": null,
    "profile_picture": "https://lh3.googleusercontent.com/a/...",
    "oauth_provider": "google"
  }
}
```

## Client-Side Implementation

### React Example with Google Sign-In

```javascript
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';

function LoginPage() {
  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const response = await fetch('http://your-api.com/auth/login/google', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: credentialResponse.credential,
          fcm_token: 'optional_fcm_token_here'
        }),
      });
      
      const data = await response.json();
      localStorage.setItem('access_token', data.access_token);
      // Redirect to dashboard or home
      
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <GoogleOAuthProvider clientId="your-google-client-id">
      <GoogleLogin
        onSuccess={handleGoogleSuccess}
        onError={() => console.log('Login Failed')}
      />
    </GoogleOAuthProvider>
  );
}
```

### HTML/JavaScript Example

```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://accounts.google.com/gsi/client" async defer></script>
</head>
<body>
  <div id="g_id_onload"
       data-client_id="your-google-client-id.apps.googleusercontent.com"
       data-callback="handleCredentialResponse">
  </div>
  <div class="g_id_signin" data-type="standard"></div>

  <script>
    function handleCredentialResponse(response) {
      fetch('http://your-api.com/auth/login/google', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: response.credential
        })
      })
      .then(res => res.json())
      .then(data => {
        localStorage.setItem('access_token', data.access_token);
        window.location.href = '/dashboard';
      })
      .catch(error => console.error('Error:', error));
    }
  </script>
</body>
</html>
```

## How It Works

1. **Client-Side**: User clicks "Sign in with Google" button
2. **Google**: User authenticates and grants permissions
3. **Client-Side**: Receives ID token from Google
4. **Client-Side**: Sends ID token to your FastAPI backend
5. **Backend**: Verifies token with Google servers
6. **Backend**: Creates or updates user in database
7. **Backend**: Returns JWT access token
8. **Client-Side**: Stores token and uses it for authenticated requests

## Security Considerations

✅ **Token Verification**: All Google tokens are verified with Google's servers  
✅ **Email Verification**: Only accepts verified email addresses from Google  
✅ **Secure Storage**: OAuth IDs and user data stored securely in database  
✅ **JWT Tokens**: Access tokens expire after 30 minutes  
✅ **Password Optional**: OAuth users don't need passwords  

## Testing

### Test Google OAuth Login

```bash
curl -X POST "http://localhost:8000/auth/login/google" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your_google_id_token_here"
  }'
```

### Test Email/Password Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

## Troubleshooting

### Error: "Invalid Google token"
- Verify that `GOOGLE_CLIENT_ID` in `.env` matches your Google Cloud Console
- Ensure the token is fresh (Google tokens expire)
- Check that you're using the ID token, not the access token

### Error: "Email not verified by Google"
- The user must have a verified email address in their Google account

### Error: "Column does not exist"
- Run the migration script: `python scripts/add_oauth_columns.py`

## Database Schema

The `saving_users` table now includes:

```sql
CREATE TABLE saving_users (
    id UUID PRIMARY KEY,
    username VARCHAR UNIQUE,
    email VARCHAR UNIQUE,
    phone_number VARCHAR UNIQUE,
    hashed_password VARCHAR NULLABLE,  -- Nullable for OAuth users
    fcm_token VARCHAR,
    oauth_provider VARCHAR(50),        -- 'google', 'facebook', etc.
    oauth_id VARCHAR(255),              -- Provider's user ID
    profile_picture VARCHAR(500)        -- URL to profile picture
);
```

## Next Steps

- [ ] Add Facebook OAuth support
- [ ] Add Apple Sign In
- [ ] Implement password reset for email/password users
- [ ] Add 2FA (Two-Factor Authentication)
- [ ] Add refresh token support

## Support

For issues or questions, please check:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Identity Documentation](https://developers.google.com/identity)
- [python-jose Documentation](https://python-jose.readthedocs.io/)

---

**Created:** February 10, 2026  
**Version:** 1.0  
**Author:** Your Development Team
