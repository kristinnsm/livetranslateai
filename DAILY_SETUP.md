# Daily.co Video Call Setup Instructions

## 🎥 Enable Video Calls for Your App

Video calls are powered by Daily.co's API. Follow these steps to enable them:

---

## 1️⃣ Sign Up for Daily.co

1. Go to https://dashboard.daily.co/signup
2. Create a free account (no credit card required)
3. Confirm your email

**Free Tier Includes:**
- ✅ Up to 10,000 participant minutes/month
- ✅ Unlimited rooms
- ✅ Up to 20 participants per call
- ✅ Perfect for MVP testing!

---

## 2️⃣ Get Your API Key

1. Log into https://dashboard.daily.co/
2. Click **"Developers"** in the left sidebar
3. Copy your **API key** (starts with a long random string)

Example: `9a8b7c6d5e4f3g2h1i0j9k8l7m6n5o4p3q2r1s0t...`

---

## 3️⃣ Configure Your Backend (Render)

### On Render Dashboard:

1. Go to https://dashboard.render.com/
2. Find your **LiveTranslateAI** service
3. Click **"Environment"** in the left menu
4. Click **"Add Environment Variable"**
5. Add:
   - **Key:** `DAILY_API_KEY`
   - **Value:** `[paste your Daily.co API key here]`
6. Click **"Save Changes"**
7. Your service will automatically redeploy (~2 minutes)

---

## 4️⃣ Configure Your Daily.co Domain (Optional)

By default, you'll use Daily's shared domain: `https://[your-subdomain].daily.co`

To get a custom subdomain:
1. In Daily.co dashboard, go to **"Domain"**
2. Set a subdomain like `livetranslateai` 
3. Your rooms will be at `https://livetranslateai.daily.co/[room-id]`

---

## 5️⃣ Test Video Calls

After deploying with the API key:

1. Go to https://livetranslateai.netlify.app
2. Create a room
3. **You should see camera/mic permission prompt** ✅
4. Allow camera/mic
5. **Video should appear** ✅
6. Join from another device/browser
7. **Both videos should show** ✅

---

## 🐛 Troubleshooting

### ❌ "Video calls not configured"
- Check that `DAILY_API_KEY` is set in Render environment variables
- Verify the API key is correct (no extra spaces)
- Wait for Render redeploy to complete

### ❌ "Failed to create video room"
- Check Daily.co account is active
- Verify API key has permissions
- Check Daily.co dashboard for error logs

### ❌ Camera/mic permission denied
- Click padlock icon in browser address bar
- Allow camera and microphone
- Reload page

### ❌ "Meeting you're trying to join does not exist"
- This means the backend isn't creating rooms properly
- Check Render logs for Daily API errors
- Verify `DAILY_API_KEY` is set correctly

---

## 📊 Monitor Usage

Daily.co dashboard shows:
- Active rooms
- Participant minutes used
- API call logs
- Room history

Free tier resets monthly. Upgrade if needed at https://www.daily.co/pricing

---

## 🚀 Production Checklist

Before going live with real users:

- [ ] Daily.co API key configured in Render
- [ ] Test video calls work end-to-end
- [ ] Monitor participant minutes usage
- [ ] Set up Daily.co webhooks for analytics (optional)
- [ ] Configure custom domain if desired
- [ ] Test on mobile (iOS Safari, Android Chrome)

---

## 🔗 Useful Links

- Daily.co Dashboard: https://dashboard.daily.co/
- Daily.co Docs: https://docs.daily.co/
- API Reference: https://docs.daily.co/reference/rest-api
- Pricing: https://www.daily.co/pricing
- Support: https://help.daily.co/

