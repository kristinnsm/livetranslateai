# Google Auth + Stripe Integration Guide

## 📋 Overview

This guide will walk you through integrating:
1. **Google OAuth** for user authentication
2. **Stripe** for subscription billing
3. **Usage tracking** for enforcing tier limits
4. **WordPress embedding** for the landing page

---

## 🔐 Part 1: Google OAuth Setup

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project: "LiveTranslateAI"
3. Enable **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Configure OAuth consent screen:
   - App name: LiveTranslateAI
   - User support email: your email
   - Authorized domains: `livetranslateai.com`, `livetranslateai.netlify.app`
6. Create OAuth Client ID:
   - Application type: **Web application**
   - Authorized JavaScript origins: 
     - `https://livetranslateai.com`
     - `https://livetranslateai.netlify.app`
   - Authorized redirect URIs:
     - `https://livetranslateai.com/auth/callback`
     - `https://livetranslateai.netlify.app/auth/callback`
7. Copy **Client ID** and **Client Secret**

### 2. Add Google Login to Frontend

Create `frontend/auth.js`:

```javascript
// Google OAuth Configuration
const GOOGLE_CLIENT_ID = 'YOUR_CLIENT_ID.apps.googleusercontent.com';

// Initialize Google Sign-In
function initGoogleAuth() {
    google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleLogin,
        auto_select: false,
        cancel_on_tap_outside: true,
    });
    
    // Render button
    google.accounts.id.renderButton(
        document.getElementById('google-login-btn'),
        { 
            theme: 'outline', 
            size: 'large',
            text: 'continue_with',
            shape: 'rectangular',
        }
    );
}

// Handle Google login response
async function handleGoogleLogin(response) {
    const credential = response.credential;
    
    try {
        // Send token to backend for verification
        const backendUrl = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000'
            : 'https://livetranslateai.onrender.com';
            
        const result = await fetch(`${backendUrl}/api/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: credential })
        });
        
        const data = await result.json();
        
        if (data.success) {
            // Store session token
            localStorage.setItem('auth_token', data.session_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            
            // Redirect to app
            window.location.href = '/app';
        } else {
            alert('Login failed: ' + data.error);
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('Login failed. Please try again.');
    }
}

// Check if user is logged in
function isAuthenticated() {
    return localStorage.getItem('auth_token') !== null;
}

// Get current user
function getCurrentUser() {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
}

// Logout
function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    window.location.href = '/';
}

// Initialize on page load
window.addEventListener('load', () => {
    initGoogleAuth();
});
```

### 3. Add Google Sign-In Script to HTML

Add to `<head>` in `frontend/index.html`:

```html
<!-- Google Sign-In -->
<script src="https://accounts.google.com/gsi/client" async defer></script>
<script src="auth.js"></script>

<!-- Login Button (add to your UI) -->
<div id="google-login-btn"></div>
```

### 4. Backend: Verify Google Token

Add to `backend/requirements.txt`:
```
google-auth==2.23.0
PyJWT==2.8.0
```

Create `backend/auth.py`:

```python
from google.oauth2 import id_token
from google.auth.transport import requests
import jwt
import uuid
from datetime import datetime, timedelta

GOOGLE_CLIENT_ID = "YOUR_CLIENT_ID.apps.googleusercontent.com"
JWT_SECRET = "your-secret-key-here"  # Store in .env in production!

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
```

### 5. Add Auth Endpoint to Backend

Add to `backend/minimal_main.py`:

```python
from auth import verify_google_token, create_session_token

# In-memory user storage (replace with database in production)
users_db = {}

@app.post("/api/auth/google")
async def google_auth(request: Request):
    """Verify Google OAuth token and create session"""
    try:
        data = await request.json()
        token = data.get('token')
        
        # Verify Google token
        user_info = await verify_google_token(token)
        
        if not user_info:
            return JSONResponse({"success": False, "error": "Invalid token"}, status_code=401)
        
        google_id = user_info['google_id']
        
        # Check if user exists
        if google_id not in users_db:
            # Create new user
            user_id = str(uuid.uuid4())
            users_db[google_id] = {
                "user_id": user_id,
                "google_id": google_id,
                "email": user_info['email'],
                "name": user_info['name'],
                "picture": user_info['picture'],
                "tier": "free",  # Default tier
                "minutes_used": 0,
                "created_at": datetime.utcnow().isoformat()
            }
        
        user = users_db[google_id]
        
        # Create session token
        session_token = create_session_token(user['user_id'])
        
        return JSONResponse({
            "success": True,
            "session_token": session_token,
            "user": {
                "name": user['name'],
                "email": user['email'],
                "picture": user['picture'],
                "tier": user['tier'],
                "minutes_used": user['minutes_used']
            }
        })
        
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
```

---

## 💳 Part 2: Stripe Integration

### 1. Create Stripe Account

1. Go to [Stripe.com](https://stripe.com)
2. Sign up (use US business entity for lower fees)
3. Complete business verification
4. Go to **Developers** → **API keys**
5. Copy **Publishable key** and **Secret key**

### 2. Create Stripe Products with 7-Day Trial

Using Stripe Dashboard:

1. Go to **Products** → **Add product**
2. Create products:
   - **Starter**: $19/month, recurring, **7-day free trial**
   - **Professional**: $79/month, recurring, **7-day free trial**
3. Enable trial period:
   - Click product → **Pricing** → **Add trial period**
   - Set **Trial period**: 7 days
   - Enable **Customer must add payment method** ✅
4. Copy **Price ID** for each product

**Stripe automatically handles:**
- No charge during 7-day trial
- Auto-conversion to paid after trial
- Email notifications before trial ends
- Easy cancellation (customer portal)

### 3. Frontend: Stripe Checkout

Add to `backend/requirements.txt`:
```
stripe==7.0.0
```

Create Stripe checkout session endpoint in `backend/minimal_main.py`:

```python
import stripe

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

PRICE_IDS = {
    'starter': 'price_XXXXXXXXXXXXX',  # Replace with your Price IDs
    'professional': 'price_YYYYYYYYYYYYY'
}

@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request):
    """Create Stripe checkout session"""
    try:
        data = await request.json()
        tier = data.get('tier')  # 'starter' or 'professional'
        user_id = data.get('user_id')
        
        if tier not in PRICE_IDS:
            return JSONResponse({"error": "Invalid tier"}, status_code=400)
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': PRICE_IDS[tier],
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://livetranslateai.netlify.app/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://livetranslateai.netlify.app/pricing',
            client_reference_id=user_id,  # Link to your user
            metadata={
                'user_id': user_id,
                'tier': tier
            }
        )
        
        return JSONResponse({"checkout_url": checkout_session.url})
        
    except Exception as e:
        print(f"❌ Checkout error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
```

### 4. Frontend: Redirect to Stripe Checkout

Add to `frontend/app.js`:

```javascript
async function upgradeTier(tier) {
    const user = getCurrentUser();
    if (!user) {
        alert('Please login first');
        return;
    }
    
    try {
        const response = await fetch(`${backendUrl}/api/create-checkout-session`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
            },
            body: JSON.stringify({ 
                tier: tier,
                user_id: user.user_id 
            })
        });
        
        const data = await response.json();
        
        if (data.checkout_url) {
            // Redirect to Stripe checkout
            window.location.href = data.checkout_url;
        } else {
            alert('Checkout failed: ' + data.error);
        }
    } catch (error) {
        console.error('Upgrade error:', error);
        alert('Failed to start checkout');
    }
}
```

### 5. Handle Stripe Webhooks

Stripe sends webhooks when subscriptions are created/canceled. Add endpoint:

```python
@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except Exception as e:
        print(f"❌ Webhook signature verification failed: {e}")
        return JSONResponse({"error": "Invalid signature"}, status_code=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session['metadata']['user_id']
        tier = session['metadata']['tier']
        
        # Update user tier in database
        for google_id, user in users_db.items():
            if user['user_id'] == user_id:
                user['tier'] = tier
                user['subscription_id'] = session['subscription']
                print(f"✅ Upgraded user {user_id} to {tier}")
                break
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Downgrade user to free tier
        for google_id, user in users_db.items():
            if user.get('subscription_id') == subscription['id']:
                user['tier'] = 'free'
                user['minutes_used'] = 0  # Reset usage
                print(f"✅ Downgraded user to free tier")
                break
    
    return JSONResponse({"success": True})
```

**Important**: Configure webhook in Stripe Dashboard:
1. Go to **Developers** → **Webhooks**
2. Add endpoint: `https://livetranslateai.onrender.com/api/webhooks/stripe`
3. Select events: `checkout.session.completed`, `customer.subscription.deleted`
4. Copy **Webhook signing secret** to `.env`

---

## ⏱️ Part 3: Usage Tracking

### 1. Add Usage Tracking to WebSocket

Modify `backend/minimal_main.py`:

```python
@websocket_endpoint("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket handler with usage tracking"""
    await websocket.accept()
    participant_id = str(uuid.uuid4())
    start_time = time.time()
    user_id = None  # Get from auth token in production
    
    try:
        # Get user's tier and check limits
        user = get_user_by_id(user_id) if user_id else None
        if user:
            tier_limits = {
                'free': 10,  # 10 minutes
                'starter': 300,  # 5 hours
                'professional': 1500  # 25 hours
            }
            
            limit = tier_limits.get(user['tier'], 10)
            if user['minutes_used'] >= limit:
                await websocket.send_json({
                    "type": "error",
                    "message": "Usage limit exceeded. Please upgrade your plan."
                })
                await websocket.close()
                return
        
        # ... existing WebSocket logic ...
        
    finally:
        # Track usage when disconnecting
        duration_minutes = (time.time() - start_time) / 60
        if user:
            user['minutes_used'] += duration_minutes
            print(f"📊 User {user_id} used {duration_minutes:.2f} minutes (total: {user['minutes_used']:.2f})")
```

### 2. Add Usage Display to Frontend

Add to `frontend/app.js`:

```javascript
async function updateUsageDisplay() {
    const user = getCurrentUser();
    if (!user) return;
    
    const response = await fetch(`${backendUrl}/api/user/usage`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
    });
    
    const usage = await response.json();
    
    document.getElementById('usage-meter').innerHTML = `
        <div class="usage-bar">
            <div class="usage-progress" style="width: ${(usage.used / usage.limit) * 100}%"></div>
        </div>
        <p>${usage.used.toFixed(0)} / ${usage.limit} minutes used this month</p>
    `;
    
    // Show upgrade prompt if near limit
    if (usage.used / usage.limit > 0.8) {
        showUpgradePrompt();
    }
}
```

---

## 🌐 Part 4: WordPress Embedding

### Option 1: Custom HTML Page (Recommended)

1. In WordPress admin, go to **Pages** → **Add New**
2. Switch to **HTML/Code editor** (not visual editor)
3. Paste the entire `landing-page.html` contents
4. Set permalink to `/` (homepage)
5. Publish

### Option 2: Header/Footer Integration

1. Install plugin: **Insert Headers and Footers**
2. Go to **Settings** → **Insert Headers and Footers**
3. Paste in **Header** section:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://accounts.google.com/gsi/client" async defer></script>
```
4. Create page with custom template
5. Add CSS to **Appearance** → **Customize** → **Additional CSS**

### Option 3: Custom Theme

1. Create child theme directory: `/wp-content/themes/livetranslate-child/`
2. Copy `landing-page.html` to `page-landing.php`
3. Add template header:
```php
<?php
/*
Template Name: Landing Page
*/
?>
<!DOCTYPE html>
<!-- Rest of landing-page.html -->
```
4. Activate theme and create page using this template

---

## 🚀 Deployment Checklist

### Environment Variables (.env)

Add to both frontend and backend:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_live_XXXXXXXXXX
STRIPE_SECRET_KEY=sk_live_XXXXXXXXXX
STRIPE_WEBHOOK_SECRET=whsec_XXXXXXXXXX

# JWT
JWT_SECRET=your-super-secret-key-here

# Pricing IDs
STRIPE_STARTER_PRICE_ID=price_XXXXX
STRIPE_PRO_PRICE_ID=price_YYYYY
```

### Backend Deployment (Render)

1. Add environment variables in Render dashboard
2. Update `requirements.txt`:
```
google-auth==2.23.0
PyJWT==2.8.0
stripe==7.0.0
```
3. Deploy

### Frontend Deployment (Netlify)

1. Add environment variables in Netlify dashboard (prefix with `VITE_` or `REACT_APP_` if using build tools)
2. Update `netlify.toml`:
```toml
[[redirects]]
  from = "/auth/callback"
  to = "/index.html"
  status = 200
```
3. Deploy

---

## 📊 Testing Checklist

- [ ] Google login works on localhost
- [ ] Google login works on production
- [ ] Free tier gets 10 minutes
- [ ] Stripe checkout redirects correctly
- [ ] Webhook updates user tier
- [ ] Usage tracking increments correctly
- [ ] Usage limit blocks new calls
- [ ] Upgrade prompt shows at 80%
- [ ] Cancellation downgrades to free
- [ ] Landing page loads on WordPress
- [ ] All links work on landing page

---

## 💡 Quick Start Commands

```bash
# Install Python dependencies
pip install google-auth PyJWT stripe

# Test Stripe webhook locally (requires Stripe CLI)
stripe listen --forward-to localhost:8000/api/webhooks/stripe

# Generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🎯 Next Steps

1. **Week 1**: Set up Google OAuth + basic auth flow
2. **Week 2**: Integrate Stripe + test checkout
3. **Week 3**: Add usage tracking + enforcement
4. **Week 4**: Launch with landing page on WordPress
5. **Week 5**: Monitor metrics + iterate based on feedback

---

## 🆘 Troubleshooting

### Google OAuth issues:
- Check authorized domains in Google Console
- Verify redirect URIs match exactly
- Use HTTPS (not HTTP) in production

### Stripe issues:
- Test with Stripe test mode first
- Use Stripe CLI to test webhooks locally
- Check webhook signature verification

### Usage tracking issues:
- Verify WebSocket connection includes auth token
- Check user_id is being passed correctly
- Monitor backend logs for tracking updates

---

**Ready to launch! 🚀**

