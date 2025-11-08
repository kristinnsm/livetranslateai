"""
Google OAuth Authentication
"""
from google.oauth2 import id_token
from google.auth.transport import requests
import jwt
import uuid
from datetime import datetime, timedelta
import os

GOOGLE_CLIENT_ID = "712731007087-jmc0mscl0jrknp86hl7kjgqi6uk2q5v7.apps.googleusercontent.com"
JWT_SECRET = os.getenv('JWT_SECRET', 'your-super-secret-key-change-in-production')

async def verify_google_token(token: str) -> dict:
    """Verify Google OAuth token and return user info"""
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Extract user info
        user_data = {
            "google_id": idinfo['sub'],
            "email": idinfo['email'],
            "name": idinfo.get('name', ''),
            "picture": idinfo.get('picture', ''),
            "email_verified": idinfo.get('email_verified', False),
        }
        
        return user_data
        
    except Exception as e:
        print(f"❌ Token verification failed: {e}")
        return None

def create_session_token(user_id: str) -> str:
    """Create JWT session token"""
    expiration = datetime.utcnow() + timedelta(days=30)
    
    payload = {
        "user_id": user_id,
        "exp": expiration
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token

def verify_session_token(token: str) -> dict:
    """Verify JWT session token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except Exception:
        return None

