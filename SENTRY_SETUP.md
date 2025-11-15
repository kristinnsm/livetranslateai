# 🔍 Sentry Error Tracking Setup

## Why Sentry?

Sentry automatically captures errors in production, giving you visibility into issues BEFORE users complain. Critical for MVP launch.

---

## Setup Steps

### 1. Create Sentry Account

1. Go to: https://sentry.io/signup/
2. Sign up (free tier: 5,000 events/month - plenty for MVP)
3. Create a new **Organization** (e.g., "Titanium Enterprises")

### 2. Create Projects

You need **TWO projects** (one for backend, one for frontend):

#### **Backend Project (Python/FastAPI)**
1. Click **"Create Project"**
2. Select **"FastAPI"** (or "Python")
3. Project name: `livetranslateai-backend`
4. Copy the **DSN** (looks like: `https://xxx@xxx.ingest.sentry.io/xxx`)

#### **Frontend Project (JavaScript)**
1. Click **"Create Project"** again
2. Select **"JavaScript"** → **"Browser"**
3. Project name: `livetranslateai-frontend`
4. Copy the **DSN**

---

## 3. Configure Backend (Render)

### Add Environment Variable

1. Go to: https://dashboard.render.com
2. Select your backend service (`livetranslateai-backend`)
3. Go to **Environment** tab
4. Add new variable:
   ```
   SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
   ```
   (Use the **backend DSN** you copied)

5. Click **"Save Changes"** → Backend will auto-redeploy

### Verify It Works

1. Check Render logs after deployment
2. Look for: `✅ Sentry error tracking enabled`
3. If you see errors, Sentry will capture them automatically

---

## 4. Configure Frontend (Netlify)

### Add Environment Variable

1. Go to: https://app.netlify.com
2. Select your site (`livetranslateai`)
3. Go to **Site Settings** → **Environment Variables**
4. Add new variable:
   ```
   SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
   ```
   (Use the **frontend DSN** you copied)

5. **Important:** Set it for **Production** environment
6. Click **"Save"**

### Update Netlify Build Script

Since Netlify doesn't automatically inject env vars into static HTML, we need a build script:

1. Create `netlify-build.sh` in project root:
```bash
#!/bin/bash
# Replace SENTRY_DSN placeholder in HTML files
if [ -n "$SENTRY_DSN" ]; then
    find app -name "*.html" -type f -exec sed -i "s|{{SENTRY_DSN}}|$SENTRY_DSN|g" {} \;
fi
```

2. Update `netlify.toml`:
```toml
[build]
  command = "bash netlify-build.sh && echo 'Build complete'"
  publish = "."
```

**OR** manually edit `app/index.html` and replace `{{SENTRY_DSN}}` with your actual DSN (less ideal, but works).

### Redeploy Frontend

1. Trigger a new deployment (or push a commit)
2. Check browser console after deployment
3. Look for: `✅ Sentry error tracking enabled`

---

## 5. Test Error Tracking

### Test Backend

1. Trigger an error (e.g., invalid API request)
2. Check Sentry dashboard → Backend project
3. You should see the error appear within seconds

### Test Frontend

1. Open browser console
2. Run: `throw new Error("Test error")`
3. Check Sentry dashboard → Frontend project
4. You should see the error appear

---

## 6. Set Up Alerts (Optional but Recommended)

1. Go to Sentry dashboard → **Alerts**
2. Create alert rules:
   - **New Issues:** Email me when a new error occurs
   - **High Volume:** Email me if >10 errors/hour
   - **Critical Errors:** Email me for 5xx errors

---

## Cost

**Free Tier:**
- 5,000 events/month per project
- 2 projects = 10,000 total events/month
- **Cost: $0/month**

**Paid Tier (if needed later):**
- $26/month for 50K events/month
- Only upgrade if you exceed free tier

---

## What Gets Tracked

### Backend (Automatic):
- Unhandled exceptions
- API errors (500, 502, etc.)
- WebSocket errors
- Database connection failures
- OpenAI API errors

### Frontend (Automatic):
- JavaScript errors
- Unhandled promise rejections
- Network errors (failed API calls)
- WebSocket connection failures

---

## Next Steps

1. ✅ Set up Sentry account
2. ✅ Add DSNs to Render + Netlify
3. ✅ Redeploy backend + frontend
4. ✅ Test error tracking
5. ✅ Set up email alerts
6. ✅ Monitor for first 48 hours after launch

---

## Troubleshooting

### "Sentry DSN not set" in logs
- Check environment variable is set correctly
- Check variable name matches exactly: `SENTRY_DSN`
- Redeploy after adding variable

### Errors not appearing in Sentry
- Check DSN is correct (no typos)
- Check project is active in Sentry dashboard
- Check browser console for Sentry initialization errors
- Verify environment variable is set for correct environment (Production vs Preview)

### Frontend Sentry not working
- Check `window.SENTRY_DSN` is available in browser console
- Check Netlify build logs for environment variable injection
- May need to add build script to inject DSN into HTML

---

**Last Updated:** January 2025

