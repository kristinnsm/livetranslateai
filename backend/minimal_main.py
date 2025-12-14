"""
Minimal LiveTranslateAI Backend - Ultra-simple version for deployment
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import logging
import uuid
import time
import base64
import io
import requests
from datetime import datetime
from typing import Dict, List
import os
from auth import verify_google_token, create_session_token
from usage import check_usage_limit, get_usage_info
from database import (
    init_database, create_user, get_user_by_google_id, 
    get_user_by_user_id, update_user_usage, update_user_last_login,
    check_fingerprint_used, update_user_tier, get_user_by_subscription_id,
    update_stripe_customer, get_user_stripe_customer_id, get_db_connection
)
from stripe_integration import (
    create_checkout_session, create_portal_session,
    verify_webhook_signature, handle_checkout_completed,
    handle_subscription_updated, handle_subscription_deleted
)
# Rate limiting for security (prevent API abuse)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Sentry error tracking (optional - set SENTRY_DSN env var to enable)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
            environment=os.getenv("ENVIRONMENT", "production"),
        )
        print("✅ Sentry error tracking enabled")
    else:
        print("ℹ️ Sentry DSN not set - error tracking disabled")
except ImportError:
    print("ℹ️ Sentry SDK not installed - error tracking disabled")
except Exception as e:
    print(f"⚠️ Sentry initialization failed: {e}")

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DAILY_API_KEY = os.getenv("DAILY_API_KEY")  # Get from https://dashboard.daily.co/developers
FREE_MINUTES_LIMIT = 15  # Free tier limit
MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB max audio chunk (security limit)
MAX_CONCURRENT_CALLS_PER_USER = 3  # Prevent abuse

# Helper function for two-step translation (improves quality via English intermediary)
def translate_via_english(text: str, source_lang: str, target_lang: str) -> str:
    """
    Two-step translation: source → English → target
    Improves quality because English has the best training data
    Works for any language pair, especially useful for Icelandic
    
    Args:
        text: Source text to translate
        source_lang: Source language code
        target_lang: Target language code
    
    Returns:
        Translated text
    """
    try:
        # Step 1: Translate to English (if not already English)
        if source_lang != "en":
            logger.info(f"🌍 Step 1: Translating {source_lang} → English")
            step1_response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "user", "content": f"Translate from {source_lang} to English. Maintain natural conversational tone. Use correct spelling, grammar, and punctuation.\n\nText to translate:\n{text}"}
                    ],
                    "max_tokens": 200,
                    "temperature": 0,
                },
                timeout=4
            )
            
            if step1_response.status_code != 200:
                raise Exception(f"Step 1 translation failed: {step1_response.status_code}")
            
            english_text = step1_response.json()["choices"][0]["message"]["content"].strip()
            logger.info(f"✅ English intermediate: '{english_text}'")
        else:
            english_text = text
        
        # Step 2: Translate English → target language
        logger.info(f"🌍 Step 2: Translating English → {target_lang}")
        
        # Add Icelandic-specific instructions only if target is Icelandic
        target_instructions = ""
        if target_lang == "is":
            target_instructions = "\n\nCRITICAL for Icelandic: Use correct spelling and grammar. Pay special attention to:\n- Special characters: ð (eth), þ (thorn), æ, ö\n- Correct declensions and conjugations\n- Proper capitalization (Icelandic uses lowercase for most nouns)\n- Natural Icelandic word order\n"
        
        step2_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": f"Translate from English to {target_lang}.{target_instructions}Maintain natural conversational tone. Use correct spelling, grammar, and punctuation.\n\nText to translate:\n{english_text}"}
                ],
                "max_tokens": 200,
                "temperature": 0,
            },
            timeout=4
        )
        
        if step2_response.status_code != 200:
            raise Exception(f"Step 2 translation failed: {step2_response.status_code}")
        
        final_translation = step2_response.json()["choices"][0]["message"]["content"].strip()
        logger.info(f"✅ Final translation: '{final_translation}'")
        
        return final_translation
        
    except Exception as e:
        logger.error(f"❌ Two-step translation error: {e}")
        raise

# Setup
app = FastAPI(title="LiveTranslateAI API", version="1.0.0")

# Rate Limiting (protect against API abuse)
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Get logger - uvicorn handles basic config, we just ensure our logs show
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Ensure handler exists to output logs
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = True  # Let uvicorn see our logs too

# Room management
rooms: Dict[str, Dict] = {}
active_connections: Dict[str, List[WebSocket]] = {}
participant_connections: Dict[str, WebSocket] = {}  # participant_id -> websocket
websocket_to_participant: Dict[int, str] = {}  # websocket_id (id(websocket)) -> participant_id (reverse lookup)

FREE_MINUTES_LIMIT = 15  # Reduced from 30 to prevent abuse

# Initialize database on startup
try:
    if os.getenv('DATABASE_URL'):
        init_database()
        logger.info("✅ Database initialized successfully")
    else:
        logger.warning("⚠️ DATABASE_URL not set - using in-memory storage (data will be lost on restart!)")
        # Fallback to in-memory for development
        users_db: Dict[str, Dict] = {}
        used_fingerprints: Dict[str, str] = {}
except Exception as e:
    logger.error(f"❌ Database initialization failed: {e}")
    logger.warning("⚠️ Falling back to in-memory storage")
    users_db: Dict[str, Dict] = {}
    used_fingerprints: Dict[str, str] = {}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000", 
        "https://livetranslateai.netlify.app",
        "https://app.livetranslateai.com",
        "https://livetranslateai.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"service": "LiveTranslateAI", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "api_key_configured": bool(OPENAI_API_KEY),
        "mode": "minimal"
    }

@app.post("/api/auth/google")
@limiter.limit("10/minute")  # Max 10 login attempts per minute per IP (prevent brute force)
async def google_auth(request: Request):
    """Verify Google OAuth token and create session"""
    try:
        data = await request.json()
        token = data.get('token')
        fingerprint = data.get('fingerprint', 'unknown')
        client_ip = request.client.host
        
        logger.info(f"🔐 Google auth request received from IP: {client_ip}, fingerprint: {fingerprint}")
        
        # Verify Google token
        user_info = await verify_google_token(token)
        
        if not user_info:
            logger.error("❌ Invalid Google token")
            return JSONResponse(
                {"success": False, "error": "Invalid token"}, 
                status_code=401
            )
        
        google_id = user_info['google_id']
        
        # Check if user exists in database
        user = get_user_by_google_id(google_id)
        
        if not user:
            # Log fingerprint for analytics (but don't block - Stripe protects against abuse via free trial limits)
            existing_google_id = check_fingerprint_used(fingerprint)
            if existing_google_id and existing_google_id != google_id:
                logger.info(f"ℹ️ Fingerprint {fingerprint} previously used by account {existing_google_id}, but allowing signup (Stripe protects via free trial limits)")
            
            # Create new user in database
            user_id = str(uuid.uuid4())
            user_data = {
                "user_id": user_id,
                "google_id": google_id,
                "email": user_info['email'],
                "name": user_info['name'],
                "picture": user_info.get('picture', ''),
                "tier": "free",
                "fingerprint": fingerprint,
                "ip_address": client_ip,
                "abuse_flagged": False  # Not abuse if we let them through
            }
            user = create_user(user_data)
            logger.info(f"✅ New user created in DB: {user['name']}")
        else:
            # Update last login
            update_user_last_login(google_id)
            logger.info(f"✅ Existing user logged in from DB: {user['name']}")
        
        # Create session token
        session_token = create_session_token(user['user_id'])
        
        return JSONResponse({
            "success": True,
            "session_token": session_token,
            "user": {
                "user_id": user['user_id'],
                "name": user['name'],
                "email": user['email'],
                "picture": user['picture'],
                "tier": user['tier'],
                "minutes_used": user['minutes_used']
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Auth error: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)}, 
            status_code=500
        )

@app.get("/api/user/usage")
async def get_user_usage(request: Request):
    """Get current user's usage information"""
    try:
        # Get user_id from query params
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return JSONResponse({"error": "User ID required"}, status_code=400)
        
        logger.info(f"📊 Usage check for user_id: {user_id}")
        
        # Get user from database
        user = get_user_by_user_id(user_id)
        
        if not user:
            logger.warning(f"⚠️ User {user_id} not found in database")
            # Return default instead of error
            return JSONResponse({
                "tier": "free",
                "minutes_used": 0.0,
                "minutes_limit": FREE_MINUTES_LIMIT,
                "minutes_remaining": FREE_MINUTES_LIMIT,
                "percentage_used": 0,
                "can_use": True,
                "status": "ok",
                "note": "Session not found. Please logout and login again."
            })
        
        # Get usage info
        usage_info = get_usage_info(user)
        
        return JSONResponse(usage_info)
        
    except Exception as e:
        logger.error(f"❌ Usage check error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# Room management endpoints
@app.post("/api/rooms/create")
@limiter.limit("20/hour")  # Max 20 rooms per hour per IP (prevent spam)
async def create_room(request: Request):
    """Create a new translation room (HOST only)"""
    try:
        data = await request.json()
        user_id = data.get('user_id')  # HOST's user ID
        
        logger.info(f"🏠 POST /api/rooms/create - Creating new room for user: {user_id}")
        
        # Get HOST user from database
        host_user = get_user_by_user_id(user_id)
        
        if not host_user:
            logger.error(f"❌ User {user_id} not found in database")
            return JSONResponse({
                "error": "User not found. Please logout and login again."
            }, status_code=404)
        
        # Check if HOST has minutes remaining (for free tier)
        if host_user.get('tier') == 'free':
            minutes_used = host_user.get('minutes_used', 0)
            if minutes_used >= FREE_MINUTES_LIMIT:
                return JSONResponse({
                    "error": f"Free tier limit reached ({FREE_MINUTES_LIMIT} minutes). Please upgrade to create rooms.",
                    "usage_exceeded": True
                }, status_code=403)
        
        room_id = str(uuid.uuid4())[:8].upper()  # Short room code
        
        # Create host participant
        host_participant_id = str(uuid.uuid4())[:8]
        host_participant = {
            "id": host_participant_id,
            "name": host_user.get('name', 'Host'),
            "source_lang": "en",
            "target_lang": "es",
            "is_host": True
        }
        
        rooms[room_id] = {
            "id": room_id,
            "host_user_id": user_id,  # Track HOST for billing
            "host_name": host_user.get('name', 'Host'),
            "created_at": datetime.utcnow().isoformat(),
            "participants": [host_participant],
            "active": True
        }
        active_connections[room_id] = []
        logger.info(f"🏠 Created room: {room_id} for HOST: {host_user.get('name')} (user_id: {user_id})")
        return {
            "room_id": room_id,
            "participant_id": host_participant_id,
            "host_name": host_user.get('name', 'Host'),
            "status": "created"
        }
    except Exception as e:
        logger.error(f"❌ Room creation error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/rooms/{room_id}")
async def get_room(room_id: str):
    """Get room information"""
    logger.info(f"🔍 GET /api/rooms/{room_id} - room_id: {room_id}")
    if room_id not in rooms:
        logger.warning(f"❌ Room {room_id} not found")
        return {"error": "Room not found"}, 404
    
    room = rooms[room_id].copy()
    room["participant_count"] = len(active_connections.get(room_id, []))
    return room

@app.post("/api/rooms/{room_id}/join")
async def join_room(room_id: str, request: Request):
    """Join an existing room"""
    if room_id not in rooms:
        return {"error": "Room not found"}, 404
    
    if not rooms[room_id]["active"]:
        return {"error": "Room is not active"}, 400
    
    # Parse request body
    body = await request.json()
    participant_name = body.get("participant_name", "Anonymous")
    
    # Add participant to room
    participant_id = str(uuid.uuid4())[:8]
    participant = {
        "id": participant_id,
        "name": participant_name,
        "joined_at": datetime.utcnow().isoformat(),
        "source_lang": "en",
        "target_lang": "es"
    }
    
    rooms[room_id]["participants"].append(participant)
    logger.info(f"👤 {participant_name} joined room {room_id}")
    
    return {"participant_id": participant_id, "status": "joined"}

@app.post("/api/rooms/{room_id}/leave")
async def leave_room(room_id: str, participant_id: str):
    """Leave a room"""
    if room_id not in rooms:
        return {"error": "Room not found"}, 404
    
    # Remove participant
    rooms[room_id]["participants"] = [
        p for p in rooms[room_id]["participants"] 
        if p["id"] != participant_id
    ]
    
    logger.info(f"👋 Participant {participant_id} left room {room_id}")
    return {"status": "left"}

@app.post("/api/daily/create-room")
async def create_daily_room(request: Request):
    """Create a Daily.co video room for a translation room"""
    if not DAILY_API_KEY:
        logger.warning("⚠️ DAILY_API_KEY not set, video calls disabled")
        return {"error": "Video calls not configured", "video_enabled": False}, 503
    
    try:
        body = await request.json()
        room_name = body.get("room_name")  # Our translation room ID
        
        # Create Daily.co room via API
        headers = {
            "Authorization": f"Bearer {DAILY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Room config: expires in 10 minutes, auto-deletes after
        daily_response = requests.post(
            "https://api.daily.co/v1/rooms",
            headers=headers,
            json={
                "name": room_name,
                "privacy": "public",  # Anyone with link can join
                "properties": {
                    "exp": int(time.time()) + 600,  # Expires in 10 minutes
                    "enable_screenshare": False,
                    "enable_chat": False,
                    "enable_knocking": False,
                    "enable_prejoin_ui": False,
                    "start_video_off": False,
                    "start_audio_off": False
                }
            },
            timeout=10
        )
        
        if daily_response.status_code == 200:
            room_data = daily_response.json()
            logger.info(f"✅ Created Daily room: {room_data['url']}")
            return {
                "url": room_data["url"],
                "name": room_data["name"],
                "video_enabled": True
            }
        elif daily_response.status_code == 400:
            # Room already exists - fetch it instead
            response_json = daily_response.json()
            if "already exists" in response_json.get("info", ""):
                logger.info(f"📹 Daily room {room_name} already exists, fetching it...")
                get_response = requests.get(
                    f"https://api.daily.co/v1/rooms/{room_name}",
                    headers=headers,
                    timeout=10
                )
                if get_response.status_code == 200:
                    room_data = get_response.json()
                    logger.info(f"✅ Retrieved existing Daily room: {room_data['url']}")
                    return {
                        "url": room_data["url"],
                        "name": room_data["name"],
                        "video_enabled": True
                    }
            logger.error(f"❌ Daily API error: {daily_response.status_code} - {daily_response.text}")
            return {"error": "Failed to create video room", "video_enabled": False}, 500
        else:
            logger.error(f"❌ Daily API error: {daily_response.status_code} - {daily_response.text}")
            return {"error": "Failed to create video room", "video_enabled": False}, 500
            
    except Exception as e:
        logger.error(f"❌ Failed to create Daily room: {e}")
        return {"error": str(e), "video_enabled": False}, 500

# ===================================
# Stripe Payment Endpoints
# ===================================

@app.post("/api/stripe/create-checkout-session")
@limiter.limit("5/minute")  # Max 5 checkout attempts per minute (prevent spam)
async def create_stripe_checkout(request: Request):
    """Create a Stripe Checkout session for subscription signup"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            return JSONResponse({"error": "user_id required"}, status_code=400)
        
        # Get user from database
        user = get_user_by_user_id(user_id)
        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)
        
        # Create Stripe checkout session
        frontend_url = data.get('frontend_url', 'https://livetranslateai.com')
        success_url = f"{frontend_url}/app?payment=success"
        cancel_url = f"{frontend_url}/app?payment=cancelled"
        promo_code = data.get('promo_code')  # Optional promo code (e.g., "PRODUCTHUNT50")
        
        session = create_checkout_session(
            user_id=user['user_id'],
            user_email=user['email'],
            success_url=success_url,
            cancel_url=cancel_url,
            promo_code=promo_code
        )
        
        # Store Stripe customer ID
        update_stripe_customer(user['user_id'], session['customer_id'])
        
        logger.info(f"✅ Created Stripe checkout session for {user['email']}")
        
        return JSONResponse({
            "checkout_url": session['url'],
            "session_id": session['id']
        })
        
    except Exception as e:
        logger.error(f"❌ Stripe checkout error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/admin/reset-account")
@limiter.limit("10/minute")  # Rate limit admin endpoints
async def reset_account(request: Request):
    """Admin endpoint to reset user account (clear test mode Stripe data)"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            return JSONResponse({"error": "user_id required"}, status_code=400)
        
        # Get user
        user = get_user_by_user_id(user_id)
        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)
        
        # Reset to free tier and clear Stripe data
        update_user_tier(user['user_id'], 'free', None)
        
        # Clear stripe_customer_id
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET stripe_customer_id = NULL
                    WHERE user_id = %s
                """, (user['user_id'],))
                conn.commit()
                logger.info(f"✅ Cleared Stripe customer ID for user {user['user_id']}")
        except Exception as e:
            logger.error(f"❌ Failed to clear customer ID: {e}")
        
        logger.info(f"✅ Reset account for user {user['user_id']} ({user['email']})")
        
        return JSONResponse({
            "status": "success",
            "message": f"Account reset for {user['email']}. You can now go through checkout again."
        })
        
    except Exception as e:
        logger.error(f"❌ Reset account error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/admin/sync-stripe")
@limiter.limit("10/minute")  # Rate limit admin endpoints
async def sync_stripe_subscription(request: Request):
    """Manually sync user subscription from Stripe (useful if webhook didn't fire)"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            return JSONResponse({"error": "user_id required"}, status_code=400)
        
        # Get user
        user = get_user_by_user_id(user_id)
        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)
        
        logger.info(f"🔄 Syncing Stripe subscription for user {user_id} ({user['email']})")
        
        # Look up customer in Stripe by email
        import stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        customers = stripe.Customer.list(email=user['email'], limit=1)
        if not customers.data:
            return JSONResponse({
                "status": "no_subscription",
                "message": "No Stripe customer found for this email"
            })
        
        customer = customers.data[0]
        customer_id = customer.id
        
        # Get subscriptions for this customer (check both active and trialing status)
        # Trialing = 7-day free trial, Active = paid subscription
        subscriptions_active = stripe.Subscription.list(customer=customer_id, status='active', limit=1)
        subscriptions_trialing = stripe.Subscription.list(customer=customer_id, status='trialing', limit=1)
        
        subscription = None
        if subscriptions_active.data:
            subscription = subscriptions_active.data[0]
        elif subscriptions_trialing.data:
            subscription = subscriptions_trialing.data[0]
        
        if subscription:
            subscription_id = subscription.id
            subscription_status = subscription.status
            
            # Store customer ID and upgrade user (both trialing and active count as premium)
            update_stripe_customer(user_id, customer_id)
            update_user_tier(user_id, 'premium', subscription_id)
            
            logger.info(f"✅ Synced subscription: customer={customer_id}, subscription={subscription_id}, status={subscription_status}")
            
            return JSONResponse({
                "status": "success",
                "message": f"User upgraded to premium (subscription status: {subscription_status})",
                "customer_id": customer_id,
                "subscription_id": subscription_id,
                "subscription_status": subscription_status
            })
        else:
            # No subscription found
            logger.warning(f"⚠️ Customer {customer_id} exists but no subscription found (checked active and trialing)")
            return JSONResponse({
                "status": "no_subscription",
                "message": "Customer exists but no subscription found (checked active and trialing status)"
            })
        
    except Exception as e:
        logger.error(f"❌ Sync Stripe error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/stripe/create-portal-session")
async def create_stripe_portal(request: Request):
    """Create a Stripe Customer Portal session for subscription management"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            return JSONResponse({"error": "user_id required"}, status_code=400)
        
        # Get user data
        user = get_user_by_user_id(user_id)
        if not user:
            logger.error(f"❌ User not found: {user_id}")
            return JSONResponse({"error": "User not found"}, status_code=404)
        
        logger.info(f"🔍 Looking for Stripe customer ID for user: {user['email']} (tier: {user.get('tier')})")
        
        # Get user's Stripe customer ID
        customer_id = get_user_stripe_customer_id(user_id)
        
        # Try to create portal session, but if customer ID is invalid, recover from Stripe
        frontend_url = data.get('frontend_url', 'https://livetranslateai.com')
        return_url = f"{frontend_url}/app"
        
        try:
            # Try to create portal session with existing customer ID
            if customer_id:
                session = create_portal_session(customer_id, return_url)
            else:
                raise Exception("No customer ID in database")
        except Exception as portal_error:
            # Customer ID might be invalid (e.g., test mode ID in live mode, or deleted customer)
            # Try to recover from Stripe by email
            logger.warning(f"⚠️ Portal creation failed with customer ID {customer_id}: {portal_error}")
            
            # Clear invalid customer ID from database
            if customer_id:
                logger.info(f"🧹 Clearing invalid customer ID {customer_id} from database")
                update_stripe_customer(user_id, None)  # Clear invalid ID
            
            logger.info(f"🔍 Attempting to recover customer ID from Stripe by email: {user['email']}")
            
            try:
                import stripe
                stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
                
                # Search Stripe for customer by email
                customers = stripe.Customer.list(email=user['email'], limit=1)
                if customers.data:
                    found_customer_id = customers.data[0].id
                    logger.info(f"✅ Found customer in Stripe: {found_customer_id}, storing in DB...")
                    
                    # Verify customer has an active subscription before allowing portal access
                    subscriptions = stripe.Subscription.list(customer=found_customer_id, status='all', limit=10)
                    active_subscriptions = [s for s in subscriptions.data if s.status in ['active', 'trialing', 'past_due']]
                    
                    if not active_subscriptions:
                        logger.warning(f"⚠️ Customer {found_customer_id} exists but has no active subscription")
                        return JSONResponse({
                            "error": "No active subscription found. Your subscription may have been cancelled. Please subscribe again to manage your account."
                        }, status_code=404)
                    
                    # Store it in database for next time
                    update_stripe_customer(user_id, found_customer_id)
                    customer_id = found_customer_id
                    
                    # Try portal session again with recovered customer ID
                    session = create_portal_session(customer_id, return_url)
                    logger.info(f"✅ Recovered customer ID from Stripe and created portal session")
                else:
                    logger.error(f"❌ Customer not found in Stripe for email: {user['email']}")
                    
                    # Try to recover customer ID from subscription_id if user has one
                    subscription_id = user.get('subscription_id')
                    if subscription_id:
                        logger.info(f"🔍 User has subscription_id {subscription_id}, attempting to retrieve customer from subscription...")
                        try:
                            subscription = stripe.Subscription.retrieve(subscription_id)
                            if subscription and subscription.customer:
                                found_customer_id = subscription.customer
                                logger.info(f"✅ Found customer {found_customer_id} from subscription {subscription_id}")
                                
                                # Store it in database for next time
                                update_stripe_customer(user_id, found_customer_id)
                                customer_id = found_customer_id
                                
                                # Try portal session with recovered customer ID
                                session = create_portal_session(customer_id, return_url)
                                logger.info(f"✅ Recovered customer ID from subscription and created portal session")
                            else:
                                raise Exception("Subscription has no customer")
                        except Exception as sub_error:
                            logger.warning(f"⚠️ Could not retrieve customer from subscription {subscription_id}: {sub_error}")
                    
                    # If still no customer found
                    if not customer_id:
                        # If user is marked as premium but has no Stripe customer, they may need to subscribe
                        if user.get('tier') == 'premium':
                            logger.warning(f"⚠️ User {user_id} is marked premium but has no Stripe customer - may need to subscribe")
                            return JSONResponse({
                                "error": "No subscription found. You may need to subscribe. Please try logging out and back in, or contact support@livetranslateai.com"
                            }, status_code=404)
                        else:
                            return JSONResponse({
                                "error": "No subscription found. Please subscribe to access subscription management."
                            }, status_code=404)
            except Exception as stripe_error:
                logger.error(f"❌ Failed to recover customer from Stripe: {stripe_error}")
                return JSONResponse({
                    "error": "Unable to access subscription. If you just paid, please wait 30 seconds and try again. Otherwise, contact support@livetranslateai.com"
                }, status_code=404)
        
        logger.info(f"✅ Created Stripe portal session for user {user_id} ({user['email']})")
        
        return JSONResponse({
            "portal_url": session['url']
        })
        
    except Exception as e:
        logger.error(f"❌ Stripe portal error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    try:
        # Log that webhook endpoint was hit (even if signature fails)
        logger.info(f"📨 Webhook endpoint hit from IP: {request.client.host}")
        
        # Get raw body for signature verification
        payload = await request.body()
        signature = request.headers.get('stripe-signature')
        
        if not signature:
            logger.error("❌ Missing Stripe signature")
            return JSONResponse({"error": "Missing signature"}, status_code=400)
        
        logger.info(f"📨 Webhook signature present: {signature[:20]}...")
        
        # Verify webhook signature
        event = verify_webhook_signature(payload, signature)
        if not event:
            logger.error("❌ Invalid webhook signature - check STRIPE_WEBHOOK_SECRET matches Stripe dashboard")
            return JSONResponse({"error": "Invalid signature"}, status_code=400)
        
        event_type = event['type']
        logger.info(f"📨 Stripe webhook received: {event_type}")
        
        # Handle different event types
        if event_type == 'checkout.session.completed':
            # Payment successful, activate subscription
            session = event['data']['object']
            result = handle_checkout_completed(session)
            
            # Upgrade user to premium tier AND store customer ID
            if result['user_id']:
                # First, ensure customer ID is stored
                update_stripe_customer(result['user_id'], result['customer_id'])
                logger.info(f"✅ Stored Stripe customer ID {result['customer_id']} for user {result['user_id']}")
                
                # Then upgrade tier
                update_user_tier(
                    result['user_id'],
                    'premium',
                    result['subscription_id']
                )
                logger.info(f"✅ Upgraded user {result['user_id']} to premium")
        
        elif event_type == 'customer.subscription.updated':
            # Subscription status changed
            subscription = event['data']['object']
            result = handle_subscription_updated(subscription)
            
            # Update user tier based on status
            if result['user_id']:
                if result['status'] == 'active':
                    update_user_tier(result['user_id'], 'premium', result['subscription_id'])
                elif result['status'] in ['past_due', 'unpaid']:
                    logger.warning(f"⚠️ Subscription {result['subscription_id']} is {result['status']}")
                elif result['status'] == 'canceled':
                    update_user_tier(result['user_id'], 'free', None)
                    logger.info(f"❌ Downgraded user {result['user_id']} to free (subscription cancelled)")
        
        elif event_type == 'customer.subscription.deleted':
            # Subscription cancelled
            subscription = event['data']['object']
            result = handle_subscription_deleted(subscription)
            
            # Downgrade user to free tier
            if result['user_id']:
                update_user_tier(result['user_id'], 'free', None)
                logger.info(f"❌ Downgraded user {result['user_id']} to free")
        
        elif event_type == 'invoice.payment_failed':
            # Payment failed
            invoice = event['data']['object']
            logger.warning(f"⚠️ Payment failed for subscription: {invoice.get('subscription')}")
        
        else:
            logger.info(f"ℹ️ Unhandled webhook event: {event_type}")
        
        return JSONResponse({"status": "success"})
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ===================================
# WebSocket Endpoints
# ===================================

@app.websocket("/ws/translate/realtime")
async def websocket_translate_realtime(websocket: WebSocket):
    """
    Realtime translation using OpenAI Realtime API
    Ultra-low latency (300-1000ms)
    """
    await websocket.accept()
    logger.info("🔥 Realtime WebSocket connected")
    
    try:
        from services.translator_realtime import handle_realtime_translation
        await handle_realtime_translation(websocket)
    except Exception as e:
        logger.error(f"❌ Realtime translation error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Realtime API failed: {str(e)}"
        })
    finally:
        logger.info("🔌 Realtime WebSocket closed")

@app.websocket("/ws/translate")
async def websocket_translate(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")
    
    # Default language settings
    source_lang = "en"
    target_lang = "es"
    
    try:
        await websocket.send_json({
            "type": "connected",
            "session_id": "minimal-session-001",
            "mode": "minimal",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            try:
                data = await websocket.receive()
                
                if "bytes" in data:
                    # Audio chunk received
                    audio_chunk = data["bytes"]
                    logger.info(f"Received audio: {len(audio_chunk)} bytes")
                    
                    # Real translation pipeline: Whisper STT → GPT Translation
                    try:
                        import requests
                        import io
                        import time
                        
                        start_time = time.time()
                        whisper_start = time.time()
                        
                        # Step 1: Transcribe audio with Whisper (optimized)
                        logger.info("📝 Starting Whisper transcription...")
                        
                        # Add Icelandic-specific prompt to improve transcription accuracy
                        whisper_prompt = None
                        if source_lang == "is":
                            whisper_prompt = "Þetta er íslenskur texti með íslenskum stöfum: ð, þ, æ, ö. Algeng orð og setningar: vandamálið, prófum, prófa, prófað, prófun, þýðing, þýðingin, þýðingar, þýða, þýðir, þýddi, spænska, spænsku, íslenska, íslensku, íslenskar, íslenskum, nokkurnvegin, nokkurn veginn, rétt, réttur, réttur, rétt, réttri, réttum, textinn, texti, texta, þarf, þarft, þurfa, þurftu, nákvæmlega, nákvæmur, nákvæmt, getur, geta, getum, getið, gettu, leiðinlegt, leiðinlegur, leiðinleg, sjáum, sjá, sér, séð, smátt, smá, smáir, smáar, smáum, hversu, hversu mikið, hversu lengi, ættir, ætti, ættum, ættuð, ættu, appið, app, appi, appin, finn, finna, finnur, finnum, finnið, finna, núna, hægt, rólega, rólegur, rólegt, missa, missir, missum, missið, missa, venjuna, venja, venjur, venjum, einbeita, einbeitir, einbeitum, einbeitið, einbeita, einbeita mér, einbeitir sér, einbeitum okkur, mikið, mikill, mikil, miklu, miklar, miklar, hluti, hlutir, hlutum, hluta, fara, fer, förum, farið, fara, taka, tekur, tökum, takið, taka, rólega, bókka, bókkar, bókkum, bókkið, bókka, ykkur, ykkar, án, án skotands, án áhyggjna, byrja, byrjar, byrjum, byrjið, byrja, byrja mér, róa, róar, róum, róið, róa, róa mér, standa, stendur, stöndum, standið, standa, standast, stendst, stöndumst, standist, standast, þar, held, halda, höldum, haldið, halda, eiginlega, væri, værum, væruð, væru, væri, fallið, fallinn, fallin, fallnir, fallnar, nýtt, nýr, ný, nýjum, nýja, nýjar, erfitt, erfiður, erfið, erfiðir, erfiðar, erfiðum, erfiða, láta, lætur, látum, látið, láta, láta mér, ná, nær, náum, náið, ná, ná það, vaga, vagar, vöguð, vagið, vaga, vaga mér."
                        
                        whisper_data = {
                            "model": "whisper-1",
                            "language": source_lang,  # Use selected source language
                            "response_format": "json"  # Explicit format
                        }
                        if whisper_prompt:
                            whisper_data["prompt"] = whisper_prompt
                        
                        whisper_response = requests.post(
                            "https://api.openai.com/v1/audio/transcriptions",
                            headers={
                                "Authorization": f"Bearer {OPENAI_API_KEY}"
                            },
                            files={
                                "file": ("audio.webm", io.BytesIO(audio_chunk), "audio/webm")
                            },
                            data=whisper_data,
                            timeout=10  # Whisper is usually done in 2-4s
                        )
                        
                        if whisper_response.status_code != 200:
                            raise Exception(f"Whisper failed: {whisper_response.status_code} - {whisper_response.text}")
                        
                        transcription = whisper_response.json().get("text", "").strip()
                        whisper_time = int((time.time() - whisper_start) * 1000)
                        logger.info(f"✅ Transcription: '{transcription}' ({whisper_time}ms)")
                        
                        if not transcription:
                            raise Exception("Empty transcription - no speech detected")
                        
                        # Step 2: Translate with GPT-3.5-turbo
                        # Use two-step translation (via English) for Icelandic translations
                        # This improves quality because English has the best training data
                        translation_start = time.time()
                        logger.info("🌍 Starting translation...")
                        
                        if target_lang == "is" and source_lang != "en":
                            # Two-step: source → English → Icelandic (better quality)
                            logger.info(f"🌍 Using two-step translation for better Icelandic quality: {source_lang} → English → Icelandic")
                            translated = translate_via_english(transcription, source_lang, target_lang)
                        elif source_lang == "is" and target_lang != "en":
                            # Two-step: Icelandic → English → target (ensures proper translation from Icelandic)
                            logger.info(f"🌍 Using two-step translation from Icelandic: {source_lang} → English → {target_lang}")
                            translated = translate_via_english(transcription, source_lang, target_lang)
                        else:
                            # Direct translation (faster, sufficient for most cases)
                            icelandic_instructions = ""
                            if target_lang == "is":
                                icelandic_instructions = "\n\nCRITICAL for Icelandic: Use correct spelling and grammar. Pay special attention to:\n- Special characters: ð (eth), þ (thorn), æ, ö\n- Correct declensions and conjugations\n- Proper capitalization (Icelandic uses lowercase for most nouns)\n- Natural Icelandic word order\n"
                            
                            translation_prompt = f"Translate from {source_lang} to {target_lang}.{icelandic_instructions}Maintain natural conversational tone. Use correct spelling, grammar, and punctuation.\n\nText to translate:\n{transcription}"
                            
                            translation_response = requests.post(
                                "https://api.openai.com/v1/chat/completions",
                                headers={
                                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                                    "Content-Type": "application/json"
                                },
                                json={
                                    "model": "gpt-3.5-turbo",  # 5x faster than GPT-4o for simple translations
                                    "messages": [
                                        {"role": "user", "content": translation_prompt}
                                    ],
                                    "max_tokens": 200,
                                    "temperature": 0,
                                },
                                timeout=4  # Much faster model
                            )
                            
                            if translation_response.status_code != 200:
                                raise Exception(f"Translation failed: {translation_response.status_code}")
                            
                            translated = translation_response.json()["choices"][0]["message"]["content"].strip()
                        
                        translation_time = int((time.time() - translation_start) * 1000)
                        logger.info(f"✅ Translation: '{translated}' ({translation_time}ms)")
                        
                        # Step 3: Generate TTS audio (ultra-optimized)
                        tts_start = time.time()
                        logger.info("🔊 Starting TTS audio generation...")
                        tts_response = requests.post(
                            "https://api.openai.com/v1/audio/speech",
                            headers={
                                "Authorization": f"Bearer {OPENAI_API_KEY}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "tts-1",
                                "voice": "alloy",  # Fastest voice
                                "input": translated[:4096],  # OpenAI TTS max is 4096 chars
                                "response_format": "opus",
                                "speed": 1.05  # Slightly faster (barely noticeable)
                            },
                            timeout=10
                        )
                        
                        if tts_response.status_code != 200:
                            logger.warning(f"TTS failed: {tts_response.status_code}")
                            audio_base64 = None
                        else:
                            # Convert audio to base64 for sending via WebSocket
                            import base64
                            audio_base64 = base64.b64encode(tts_response.content).decode('utf-8')
                            tts_time = int((time.time() - tts_start) * 1000)
                            logger.info(f"✅ TTS audio generated: {len(tts_response.content)} bytes ({tts_time}ms)")
                        
                        latency_ms = int((time.time() - start_time) * 1000)
                        logger.info(f"⏱️ Total latency: {latency_ms}ms (Whisper: {whisper_time}ms | Translation: {translation_time}ms | TTS: {tts_time if tts_response.status_code == 200 else 0}ms)")
                        
                        # Hide original transcription ONLY when source is Icelandic (workers don't need to see what they said)
                        # BUT show it when target is Icelandic (workers need to see what refugees said)
                        # So: hide when source_lang == "is", show when target_lang == "is"
                        original_display = "" if source_lang == "is" else transcription
                        
                        await websocket.send_json({
                            "type": "translation",
                            "timestamp": datetime.utcnow().timestamp(),
                            "original": original_display,
                            "translated": translated,
                            "source_lang": source_lang,
                            "target_lang": target_lang,
                            "latency_ms": latency_ms,
                            "audio_base64": audio_base64
                        })
                            
                    except Exception as e:
                        logger.error(f"❌ Translation error: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Translation failed: {str(e)}"
                        })
                
                elif "text" in data:
                    message = json.loads(data["text"])
                    if message.get("action") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif message.get("action") == "set_language":
                        source_lang = message.get("source_lang", "en")
                        target_lang = message.get("target_lang", "es")
                        logger.info(f"Language settings updated: {source_lang} → {target_lang}")
                        
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@app.websocket("/ws/room/{room_id}")
async def websocket_room(websocket: WebSocket, room_id: str):
    """Multi-user room WebSocket for translation with usage tracking"""
    logger.info(f"🔌 WebSocket connection request for room {room_id}")
    
    # Track call start time for usage billing
    call_start_time = time.time()
    current_user_id = None
    
    try:
        await websocket.accept()
        logger.info(f"✅ WebSocket accepted for room {room_id}")
    except Exception as e:
        logger.error(f"❌ Failed to accept WebSocket for room {room_id}: {e}", exc_info=True)
        return
    
    if room_id not in rooms:
        logger.error(f"❌ Room {room_id} not found in rooms dict")
        await websocket.close(code=1000, reason="Room not found")
        return
    
    # Add connection to room
    if room_id not in active_connections:
        active_connections[room_id] = []
    active_connections[room_id].append(websocket)
    
    current_participant_id = None  # Will be set when participant sends their ID
    
    logger.info(f"🏠 User joined room {room_id} (total: {len(active_connections[room_id])})")
    
    try:
        # Send room info to all participants
        logger.info(f"📢 Preparing to broadcast room update...")
        room_update_msg = {
            "type": "room_update",
            "room_id": room_id,
            "participant_count": len(active_connections[room_id]),
            "participants": rooms[room_id]["participants"]
        }
        logger.info(f"📢 Room update message: {room_update_msg}")
        await broadcast_to_room(room_id, room_update_msg)
        logger.info(f"✅ Room update broadcast complete, entering message receive loop...")
        
        while True:
            try:
                logger.info(f"🔍 Waiting for message in room {room_id}...")
                data = await websocket.receive()
                
                # Check for disconnect message
                if data.get("type") == "websocket.disconnect":
                    logger.info(f"👋 WebSocket disconnect message received in room {room_id}")
                    break
                
                logger.info(f"🔍 Received data in room {room_id}, type: {type(data)}, keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                
                if "bytes" in data:
                    # Handle audio data
                    audio_chunk = data["bytes"]
                    
                    # Security: Validate audio size (prevent malicious huge uploads)
                    if len(audio_chunk) > MAX_AUDIO_SIZE:
                        logger.warning(f"⚠️ Audio chunk too large: {len(audio_chunk)} bytes (max: {MAX_AUDIO_SIZE})")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Audio chunk too large. Maximum 10MB per chunk."
                        })
                        continue
                    
                    # Identify speaker from WebSocket connection using id() as key
                    websocket_id = id(websocket)
                    speaker_id = websocket_to_participant.get(websocket_id)
                    logger.info(f"🔍 Looking up speaker for WebSocket {websocket_id} in room {room_id}")
                    logger.info(f"🔍 Total tracked WebSockets: {len(websocket_to_participant)}")
                    logger.info(f"🔍 Tracked participant IDs: {list(participant_connections.keys())}")
                    
                    if not speaker_id:
                        logger.warning(f"⚠️ Received audio from untracked participant in room {room_id} (WebSocket id: {websocket_id})")
                        # Try to use current_participant_id as fallback
                        speaker_id = current_participant_id
                        if speaker_id:
                            logger.warning(f"⚠️ Using fallback current_participant_id: {speaker_id}")
                        else:
                            logger.error(f"❌ No current_participant_id available either!")
                    
                    if speaker_id:
                        logger.info(f"🎤 Received audio from participant {speaker_id} in room {room_id}: {len(audio_chunk)} bytes")
                        # Process translation for OTHER participants only (exclude speaker)
                        await process_room_translation(room_id, audio_chunk, speaker_id)
                    else:
                        logger.error(f"❌ Cannot process audio - no participant_id associated with WebSocket {websocket_id} in room {room_id}")
                        logger.error(f"❌ Current participant_id: {current_participant_id}")
                        logger.error(f"❌ WebSocket id {websocket_id} not found in websocket_to_participant mapping")
                    
                elif "text" in data:
                    try:
                        message = json.loads(data["text"])
                        logger.info(f"📨 Received text message in room {room_id}: {message.get('action', 'unknown')}")
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse JSON message in room {room_id}: {e}")
                        logger.error(f"❌ Raw message: {data['text'][:100]}")
                        continue
                    
                    if message.get("action") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif message.get("action") == "set_language":
                        # Update participant language
                        participant_id = message.get("participant_id")
                        source_lang = message.get("source_lang", "en")
                        target_lang = message.get("target_lang", "es")
                        
                        # Track participant connection (bidirectional mapping)
                        if participant_id:
                            participant_connections[participant_id] = websocket
                            websocket_to_participant[id(websocket)] = participant_id  # Reverse lookup using id()
                            current_participant_id = participant_id
                            logger.info(f"🔗 Tracked participant {participant_id} connection (WebSocket id: {id(websocket)})")
                            logger.info(f"🔗 Total tracked participants: {len(participant_connections)}")
                            logger.info(f"🔗 All participant IDs: {list(participant_connections.keys())}")
                        else:
                            logger.warning("⚠️ No participant_id in set_language message")
                        
                        # Update participant in room (only if we have a participant_id)
                        if participant_id:
                            updated = False
                            for participant in rooms[room_id]["participants"]:
                                if participant["id"] == participant_id:
                                    old_source = participant.get("source_lang", "en")
                                    old_target = participant.get("target_lang", "es")
                                    participant["source_lang"] = source_lang
                                    participant["target_lang"] = target_lang
                                    updated = True
                                    logger.info(f"🌍 Room {room_id}: Participant {participant_id} updated language from {old_source} → {old_target} to {source_lang} → {target_lang}")
                                    break
                            
                            if not updated:
                                logger.warning(f"⚠️ Participant {participant_id} not found in room {room_id} participants list")
                            else:
                                logger.info(f"✅ Room {room_id}: Participant {participant_id} language now set to {source_lang} → {target_lang}")
                            
                            # Broadcast language update
                            await broadcast_to_room(room_id, {
                                "type": "language_update",
                                "participant_id": participant_id,
                                "source_lang": source_lang,
                                "target_lang": target_lang
                            })
                        
            except WebSocketDisconnect:
                logger.info(f"👋 WebSocket disconnected in room {room_id}")
                break
            except Exception as e:
                logger.error(f"❌ Room WebSocket error in room {room_id}: {e}", exc_info=True)
                try:
                    await websocket.close()
                except:
                    pass
                break
                
    except Exception as e:
        logger.error(f"Room WebSocket error: {e}")
    finally:
        # Track usage duration
        call_duration_seconds = time.time() - call_start_time
        call_duration_minutes = call_duration_seconds / 60.0
        
        logger.info(f"⏱️ Call ended. Duration: {call_duration_minutes:.2f} minutes")
        
        # Track usage for HOST only (not guests)
        # Find the room's HOST and update their usage in database
        if room_id in rooms:
            host_user_id = rooms[room_id].get('host_user_id')
            
            if host_user_id:
                try:
                    # Update usage in database (persistent!)
                    updated_user = update_user_usage(host_user_id, call_duration_minutes)
                    if updated_user:
                        logger.info(f"📊 Updated HOST usage in DB: {updated_user['name']} now at {updated_user['minutes_used']:.2f} / {FREE_MINUTES_LIMIT} minutes")
                    else:
                        logger.warning(f"⚠️ Could not update usage for user {host_user_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to update usage in DB: {e}")
            else:
                logger.warning(f"⚠️ Room {room_id} has no host_user_id for usage tracking")
        
        # Clean up participant tracking
        websocket_id = id(websocket)
        if websocket_id in websocket_to_participant:
            participant_id = websocket_to_participant[websocket_id]
            if participant_id in participant_connections:
                del participant_connections[participant_id]
            del websocket_to_participant[websocket_id]
            logger.info(f"🧹 Cleaned up tracking for participant {participant_id}")
        
        # Remove connection from room
        if room_id in active_connections:
            active_connections[room_id] = [conn for conn in active_connections[room_id] if conn != websocket]
            logger.info(f"👋 User left room {room_id} (remaining: {len(active_connections[room_id])})")

async def process_room_translation(room_id: str, audio_chunk: bytes, speaker_id: str):
    """Process translation for room and send to listeners (exclude speaker)"""
    try:
        start_time = time.time()
        
        # Get room participants and their language settings
        if room_id not in rooms:
            logger.error(f"Room {room_id} not found")
            return
        
        participants = rooms[room_id]["participants"]
        logger.info(f"👥 Processing translations for room {room_id} (speaker: {speaker_id}, {len(participants)} total participants)")
        
        # Find speaker participant to get their source language
        speaker_participant = None
        for p in participants:
            if p["id"] == speaker_id:
                speaker_participant = p
                break
        
        if not speaker_participant:
            logger.error(f"Speaker {speaker_id} not found in room participants")
            return
        
        speaker_source_lang = speaker_participant.get("source_lang", "en")
        logger.info(f"🎤 Speaker {speaker_id} is speaking in {speaker_source_lang}")
        
        # Step 1: Transcribe audio ONCE in the speaker's language
        whisper_start = time.time()
        logger.info(f"📝 Transcribing audio in {speaker_source_lang} (speaker's language)...")
        
        # Add Icelandic-specific prompt to improve transcription accuracy
        whisper_prompt = None
        if speaker_source_lang == "is":
            whisper_prompt = "Þetta er íslenskur texti með íslenskum stöfum: ð, þ, æ, ö. Algeng orð og setningar: vandamálið, prófum, prófa, prófað, prófun, þýðing, þýðingin, þýðingar, þýða, þýðir, þýddi, spænska, spænsku, íslenska, íslensku, íslenskar, íslenskum, nokkurnvegin, nokkurn veginn, rétt, réttur, réttur, rétt, réttri, réttum, textinn, texti, texta, þarf, þarft, þurfa, þurftu, nákvæmlega, nákvæmur, nákvæmt, getur, geta, getum, getið, gettu, leiðinlegt, leiðinlegur, leiðinleg, sjáum, sjá, sér, séð, smátt, smá, smáir, smáar, smáum, hversu, hversu mikið, hversu lengi, ættir, ætti, ættum, ættuð, ættu, appið, app, appi, appin, finn, finna, finnur, finnum, finnið, finna, núna, hægt, rólega, rólegur, rólegt, missa, missir, missum, missið, missa, venjuna, venja, venjur, venjum, einbeita, einbeitir, einbeitum, einbeitið, einbeita, einbeita mér, einbeitir sér, einbeitum okkur, mikið, mikill, mikil, miklu, miklar, miklar, hluti, hlutir, hlutum, hluta, fara, fer, förum, farið, fara, taka, tekur, tökum, takið, taka, rólega, bókka, bókkar, bókkum, bókkið, bókka, ykkur, ykkar, án, án skotands, án áhyggjna, byrja, byrjar, byrjum, byrjið, byrja, byrja mér, róa, róar, róum, róið, róa, róa mér, standa, stendur, stöndum, standið, standa, standast, stendst, stöndumst, standist, standast, þar, held, halda, höldum, haldið, halda, eiginlega, væri, værum, væruð, væru, væri, fallið, fallinn, fallin, fallnir, fallnar, nýtt, nýr, ný, nýjum, nýja, nýjar, erfitt, erfiður, erfið, erfiðir, erfiðar, erfiðum, erfiða, láta, lætur, látum, látið, láta, láta mér, ná, nær, náum, náið, ná, ná það, vaga, vagar, vöguð, vagið, vaga, vaga mér."
        
        whisper_data = {
            "model": "whisper-1",
            "language": speaker_source_lang,  # Use speaker's source language
            "response_format": "json"
        }
        if whisper_prompt:
            whisper_data["prompt"] = whisper_prompt
        
        whisper_response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            },
            files={
                "file": ("audio.webm", io.BytesIO(audio_chunk), "audio/webm")
            },
            data=whisper_data,
            timeout=10
        )
        
        if whisper_response.status_code != 200:
            logger.error(f"Whisper failed: {whisper_response.status_code} - {whisper_response.text}")
            return
        
        transcription = whisper_response.json().get("text", "").strip()
        whisper_time = int((time.time() - whisper_start) * 1000)
        logger.info(f"✅ Transcription: '{transcription}' ({whisper_time}ms)")
        
        if not transcription:
            logger.warning(f"Empty transcription - no speech detected")
            return
        
        # Step 2: Process translation for each listener (EXCLUDE the speaker)
        listeners = [p for p in participants if p["id"] != speaker_id]
        logger.info(f"👂 Translating for {len(listeners)} listeners...")
        
        if len(listeners) == 0:
            logger.warning(f"⚠️ No listeners found for room {room_id} (all participants might be the speaker)")
            return
        
        for listener in listeners:
            listener_id = listener['id']
            listener_name = listener.get('name', listener_id)
            source_lang_listener = listener.get("source_lang", "en")
            target_lang_listener = listener.get("target_lang", "es")
            
            logger.info(f"👂 Processing listener: {listener_name} (id: {listener_id})")
            logger.info(f"👂 Listener language settings: source={source_lang_listener} (native), target={target_lang_listener} (speaks to others)")
            logger.info(f"👂 Speaker is speaking: {speaker_source_lang}, Listener will receive translations in: {source_lang_listener}")
            
            try:
                # FIXED: Translate to listener's SOURCE language (native), not target_lang
                # In bidirectional rooms: source = what they want to HEAR, target = what they SPEAK
                translate_to_lang = source_lang_listener
                logger.info(f"🔍 DEBUG - translate_to_lang set to: {translate_to_lang}")
                
                # IMPORTANT: In bidirectional translation:
                # - listener's target_lang = what language they want to HEAR translations in
                # - speaker's source_lang = what language the speaker is actually speaking
                # 
                # We ALWAYS translate from speaker's language to listener's target language
                # UNLESS the listener's target matches the speaker's source (they already understand)
                #
                # BUT WAIT - if listener has "en → es", they speak English but want Spanish.
                # When someone speaks Spanish, they SHOULD get English (their native language), not Spanish!
                # The target_lang is what they want OUTPUT in, which should be their native/comfortable language.
                
                # Actually, let's think about this differently:
                # If listener has source=en, target=es, that means they want Spanish translations
                # When speaker speaks Spanish, listener already understands Spanish, so skip ✓
                # When speaker speaks English, listener wants Spanish, so translate en→es ✓
                #
                # But this is wrong for bidirectional! The listener should get their COMFORT language (source)
                # when others speak foreign languages, not the target.
                
                # FIX: Listeners should receive translations in their SOURCE language (what they're comfortable with)
                # not their target language. Target is what they want to speak TO others.
                # Let's change the logic: translate TO listener's source_lang (their native/comfortable language)
                
                # Skip if speaker is already speaking listener's native language
                if translate_to_lang == speaker_source_lang:
                    logger.info(f"⏭️ Skipping {listener_name} - speaker is already speaking {speaker_source_lang} which matches listener's native language {translate_to_lang}")
                    continue
                
                # Translate to listener's native language (source), not target
                logger.info(f"🌍 Translating for {listener_name}: {speaker_source_lang} → {translate_to_lang} (speaker speaks {speaker_source_lang}, listener wants {translate_to_lang})")
                
                # Step 2a: Translate with GPT-3.5-turbo
                # Use two-step translation (via English) for Icelandic translations
                translation_start = time.time()
                
                if translate_to_lang == "is" and speaker_source_lang != "en":
                    # Two-step: source → English → Icelandic (better quality)
                    logger.info(f"🌍 Using two-step translation for better Icelandic quality: {speaker_source_lang} → English → Icelandic")
                    try:
                        translated = translate_via_english(transcription, speaker_source_lang, translate_to_lang)
                    except Exception as e:
                        logger.error(f"Two-step translation failed for {listener['name']}: {e}")
                        continue
                elif speaker_source_lang == "is" and translate_to_lang != "en":
                    # Two-step: Icelandic → English → target (ensures proper translation from Icelandic)
                    logger.info(f"🌍 Using two-step translation from Icelandic: {speaker_source_lang} → English → {translate_to_lang}")
                    try:
                        translated = translate_via_english(transcription, speaker_source_lang, translate_to_lang)
                    except Exception as e:
                        logger.error(f"Two-step translation failed for {listener['name']}: {e}")
                        continue
                else:
                    # Direct translation (faster, sufficient for most cases)
                    icelandic_instructions = ""
                    if translate_to_lang == "is":
                        icelandic_instructions = "\n\nCRITICAL for Icelandic: Use correct spelling and grammar. Pay special attention to:\n- Special characters: ð (eth), þ (thorn), æ, ö\n- Correct declensions and conjugations\n- Proper capitalization (Icelandic uses lowercase for most nouns)\n- Natural Icelandic word order\n"
                    
                    translation_prompt = f"Translate from {speaker_source_lang} to {translate_to_lang}.{icelandic_instructions}Maintain natural conversational tone. Use correct spelling, grammar, and punctuation.\n\nText to translate:\n{transcription}"
                    
                    translation_response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENAI_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "gpt-3.5-turbo",
                            "messages": [
                                {"role": "user", "content": translation_prompt}
                            ],
                            "max_tokens": 1000,  # Increased to handle longer translations
                            "temperature": 0,
                        },
                        timeout=4
                    )
                    
                    if translation_response.status_code != 200:
                        logger.error(f"Translation failed for {listener['name']}: {translation_response.status_code}")
                        continue
                    
                    translated = translation_response.json()["choices"][0]["message"]["content"].strip()
                
                translation_time = int((time.time() - translation_start) * 1000)
                logger.info(f"✅ Translation for {listener['name']}: '{translated}' ({translation_time}ms)")
                logger.info(f"🔍 DEBUG - Translation details: speaker_lang={speaker_source_lang}, translate_to_lang={translate_to_lang}, translated_text_lang={translate_to_lang}")
                
                # Step 2b: Generate TTS audio
                tts_start = time.time()
                tts_response = requests.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "tts-1",
                        "voice": "alloy",
                        "input": translated[:4096],  # OpenAI TTS max is 4096 chars
                        "response_format": "opus",
                        "speed": 1.05
                    },
                    timeout=10
                )
                
                audio_base64 = None
                if tts_response.status_code == 200:
                    audio_base64 = base64.b64encode(tts_response.content).decode('utf-8')
                    tts_time = int((time.time() - tts_start) * 1000)
                    logger.info(f"✅ TTS for {listener['name']}: {len(tts_response.content)} bytes ({tts_time}ms)")
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Hide original transcription ONLY when source is Icelandic (workers don't need to see what they said)
                # BUT show it when target is Icelandic (workers need to see what refugees said)
                # So: hide when speaker_source_lang == "is", show when translate_to_lang == "is"
                original_display = "" if speaker_source_lang == "is" else transcription
                
                # Send translation to this specific listener
                translation_message = {
                    "type": "translation",
                    "timestamp": datetime.utcnow().timestamp(),
                    "original": original_display,
                    "translated": translated,
                    "source_lang": speaker_source_lang,
                    "target_lang": translate_to_lang,
                    "latency_ms": latency_ms,
                    "audio_base64": audio_base64
                }
                logger.info(f"🔍 DEBUG - Sending to {listener_name}: original_lang={speaker_source_lang}, translated_lang={translate_to_lang}")
                logger.info(f"🔍 DEBUG - Message content: original='{transcription[:50]}...', translated='{translated[:50]}...'")
                await send_to_participant(room_id, listener["id"], translation_message)
                
            except Exception as e:
                logger.error(f"❌ Translation error for {listener['name']}: {e}")
        
    except Exception as e:
        logger.error(f"❌ Room translation error: {e}")
        await broadcast_to_room(room_id, {
            "type": "error",
            "message": f"Translation failed: {str(e)}"
        })

async def send_to_participant(room_id: str, participant_id: str, message: dict):
    """Send message to a specific participant in a room"""
    logger.info(f"📤 Attempting to send translation to participant {participant_id} in room {room_id}")
    logger.info(f"📤 Available participant connections: {list(participant_connections.keys())}")
    
    if participant_id not in participant_connections:
        logger.warning(f"⚠️ Participant {participant_id} not found in connections (available: {list(participant_connections.keys())})")
        return
    
    try:
        # Add participant ID to message for frontend filtering
        message["target_participant"] = participant_id
        websocket = participant_connections[participant_id]
        logger.info(f"📤 Sending translation to participant {participant_id}: {message.get('original', '')[:50]}... → {message.get('translated', '')[:50]}...")
        await websocket.send_json(message)
        logger.info(f"✅ Successfully sent translation message to participant {participant_id}")
    except Exception as e:
        logger.error(f"❌ Failed to send to participant {participant_id}: {e}", exc_info=True)
        # Remove dead connection
        if participant_id in participant_connections:
            del participant_connections[participant_id]
            # Also remove from reverse mapping
            websocket_id_to_remove = None
            for ws_id, pid in websocket_to_participant.items():
                if pid == participant_id:
                    websocket_id_to_remove = ws_id
                    break
            if websocket_id_to_remove:
                del websocket_to_participant[websocket_id_to_remove]

async def broadcast_to_room(room_id: str, message: dict):
    """Broadcast message to all participants in a room"""
    logger.info(f"📢 broadcast_to_room called for room {room_id}")
    if room_id not in active_connections:
        logger.warning(f"⚠️ Room {room_id} not in active_connections")
        return
    
    connections = active_connections[room_id]
    logger.info(f"📢 Broadcasting to {len(connections)} connections in room {room_id}")
    
    for i, connection in enumerate(connections):
        try:
            logger.info(f"📢 Sending message to connection {i+1}/{len(connections)}")
            await connection.send_json(message)
            logger.info(f"✅ Successfully sent message to connection {i+1}")
        except Exception as e:
            logger.error(f"❌ Failed to send to room participant {i+1}: {e}", exc_info=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
