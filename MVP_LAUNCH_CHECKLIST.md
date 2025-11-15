# 🚀 MVP Launch Checklist - LiveTranslateAI

**Status:** Pre-Launch  
**Target:** Production-ready MVP

---

## ✅ **CRITICAL: Stripe Production Mode**

### **Current Status:** ⚠️ **TEST MODE** (sandbox)
### **Required:** ✅ **LIVE MODE** (production)

**Steps to Switch:**

1. **Stripe Dashboard → Toggle OFF "Test Mode"** (top-right corner)
2. **Get LIVE API Keys:**
   - Go to: https://dashboard.stripe.com/apikeys
   - Copy **Publishable key** (`pk_live_...`)
   - Copy **Secret key** (`sk_live_...`)

3. **Create LIVE Product & Price:**
   - Go to: https://dashboard.stripe.com/products
   - Create product: `LiveTranslateAI Pro`
   - Price: $29/month, 7-day free trial
   - Copy **Price ID** (`price_...`)

4. **Set Up LIVE Webhook:**
   - Go to: https://dashboard.stripe.com/webhooks
   - Add endpoint: `https://livetranslateai-backend.onrender.com/api/stripe/webhook`
   - Select events:
     - ✅ `checkout.session.completed`
     - ✅ `customer.subscription.updated`
     - ✅ `customer.subscription.deleted`
     - ✅ `invoice.payment_failed`
   - Copy **Webhook Secret** (`whsec_...`)

5. **Update Render Environment Variables:**
   ```
   STRIPE_SECRET_KEY=sk_live_YOUR_LIVE_KEY
   STRIPE_PRICE_ID=price_YOUR_LIVE_PRICE_ID
   STRIPE_WEBHOOK_SECRET=whsec_YOUR_LIVE_SECRET
   ```

6. **Update Frontend (Netlify):**
   - Go to: Netlify Dashboard → Site Settings → Environment Variables
   - Add: `STRIPE_PUBLISHABLE_KEY=pk_live_YOUR_LIVE_KEY`
   - (Check `app/auth.js` to see if it reads from env or hardcoded)

---

## ✅ **Backend Environment Variables (Render)**

**Required Variables:**

```bash
# OpenAI (REQUIRED)
OPENAI_API_KEY=sk-proj-...

# Stripe (REQUIRED - switch to LIVE keys)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PRICE_ID=price_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Database (REQUIRED)
DATABASE_URL=postgresql://...

# Daily.co (REQUIRED for video calls)
DAILY_API_KEY=...

# JWT Secret (REQUIRED for auth)
JWT_SECRET=your-super-secret-key-change-in-production

# Optional
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**Action:** Verify all are set in Render Dashboard → Environment tab

---

## ✅ **Frontend Environment Variables (Netlify)**

**Required Variables:**

```bash
# API Backend URL
VITE_API_URL=https://livetranslateai-backend.onrender.com

# Stripe Publishable Key (LIVE mode)
STRIPE_PUBLISHABLE_KEY=pk_live_...
```

**Action:** Verify in Netlify Dashboard → Site Settings → Environment Variables

---

## ✅ **Domain & SSL**

**Current Status:**
- ✅ Domain: `livetranslateai.com`
- ✅ SSL: Should be auto-configured by Netlify
- ⚠️ **Verify:** Visit `https://livetranslateai.com` - should show 🔒 (not "Not secure")

**Action:** 
- Test HTTPS redirect works
- Check SSL certificate is valid (Netlify dashboard)

---

## ✅ **Database (Neon PostgreSQL)**

**Required:**
- ✅ Database URL set in Render
- ✅ Tables created (should auto-create on first request)
- ⚠️ **Verify:** Check database has `users` table

**Action:**
- Test user creation works
- Check database connection in Render logs

---

## ✅ **Google OAuth**

**Current Status:** ✅ Configured  
**Client ID:** `712731007087-jmc0mscl0jrknp86hl7kjgqi6uk2q5v7.apps.googleusercontent.com`

**Required:**
- ✅ Authorized redirect URIs include:
  - `https://livetranslateai.com/auth/callback`
  - `https://app.livetranslateai.com/auth/callback`
  - `https://livetranslateai.netlify.app/auth/callback`

**Action:** Verify in Google Cloud Console → APIs & Services → Credentials

---

## ✅ **OpenAI API**

**Required:**
- ✅ API key set in Render
- ✅ **SPENDING LIMIT SET** ($200/month hard cap)
- ⚠️ **Verify:** Check spending limits at https://platform.openai.com/usage/limits

**Action:**
- Set hard cap: $200/month
- Set soft cap: $150/month (email alert)

---

## ✅ **Daily.co API**

**Required:**
- ✅ API key set in Render
- ✅ Free tier: 10,000 participant minutes/month (sufficient for MVP)

**Action:** Verify API key works (test room creation)

---

## ✅ **End-to-End Testing**

### **Test Flow 1: Free Tier User**
- [ ] Visit `https://livetranslateai.com`
- [ ] Click "Start Free Trial"
- [ ] Login with Google
- [ ] Create a room
- [ ] Test translation (15 minutes free)
- [ ] Verify usage tracking works

### **Test Flow 2: Premium Upgrade**
- [ ] Use up free minutes (or trigger upgrade modal)
- [ ] Click "Start Free Trial" (Stripe checkout)
- [ ] Use **LIVE** test card: `4242 4242 4242 4242`
- [ ] Complete payment
- [ ] Verify redirect to app with success message
- [ ] Verify user tier updated to "Premium"
- [ ] Verify unlimited calls work

### **Test Flow 3: Customer Portal**
- [ ] As premium user, click "Manage Subscription"
- [ ] Verify Stripe Customer Portal opens
- [ ] Test canceling subscription
- [ ] Verify user downgrades to free tier

### **Test Flow 4: Abuse Prevention**
- [ ] Try creating account on same device twice (should be blocked)
- [ ] Verify rate limiting works (spam requests)
- [ ] Verify audio size limits enforced

---

## ✅ **Monitoring & Logging**

**Set Up:**
- [ ] Render logs accessible (should be automatic)
- [ ] Stripe webhook logs monitored
- [ ] OpenAI usage dashboard bookmarked
- [ ] Error tracking (consider Sentry for production)

**Action:** Bookmark these dashboards:
- Render: https://dashboard.render.com
- Stripe: https://dashboard.stripe.com
- OpenAI: https://platform.openai.com/usage

---

## ✅ **Security Checklist**

- [x] API keys in environment variables (not hardcoded)
- [x] Rate limiting enabled (slowapi)
- [x] CORS whitelist configured (no wildcards)
- [x] Device fingerprinting active
- [x] Audio size limits enforced (10MB)
- [x] Webhook signature verification enabled
- [ ] **JWT_SECRET changed from default** (if still using default)
- [ ] **HTTPS enforced** (no HTTP access)

**Action:** 
- Generate new JWT_SECRET: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Update in Render environment variables

---

## ✅ **Performance & Reliability**

**Check:**
- [ ] Backend cold start time (< 30s acceptable for Render free tier)
- [ ] WebSocket connections stable
- [ ] Translation latency acceptable (< 5s traditional, < 1s realtime)
- [ ] Frontend loads quickly (< 3s)

**Action:** Run performance tests with real users

---

## ✅ **Legal & Compliance**

**Required:**
- [ ] Privacy Policy page (if collecting user data)
- [ ] Terms of Service page
- [ ] GDPR compliance (if targeting EU users)
- [ ] Cookie consent (if using cookies)

**Action:** Add legal pages to website

---

## ✅ **Marketing & Launch**

**Pre-Launch:**
- [ ] Landing page SEO optimized (already done ✅)
- [ ] Sitemap submitted to Google Search Console (already done ✅)
- [ ] Social media accounts ready
- [ ] Customer acquisition plan ready (4-week plan ✅)

**Launch Day:**
- [ ] Announce on LinkedIn/Twitter
- [ ] Post on Reddit (carefully, avoid ban)
- [ ] Email existing contacts
- [ ] Monitor for issues

---

## 🚨 **CRITICAL: Before Going Live**

### **Must-Have:**
1. ✅ Stripe in **LIVE mode** (not test mode)
2. ✅ OpenAI spending limit set ($200/month)
3. ✅ All environment variables set correctly
4. ✅ End-to-end test completed successfully
5. ✅ HTTPS working (no "Not secure" warnings)

### **Nice-to-Have:**
- Error tracking (Sentry)
- Analytics (Google Analytics)
- Customer support email/chat
- Legal pages (Privacy Policy, Terms)

---

## 📋 **Quick Launch Checklist**

**5-Minute Pre-Launch:**
- [ ] Stripe: Toggle to LIVE mode
- [ ] Stripe: Copy LIVE keys → Update Render + Netlify
- [ ] Stripe: Create LIVE webhook → Update Render
- [ ] OpenAI: Set $200/month spending limit
- [ ] Test: Complete one full payment flow with LIVE Stripe
- [ ] Verify: HTTPS working, no "Not secure" warnings

**If all ✅ → You're ready to launch! 🚀**

---

## 🐛 **Common Issues & Fixes**

### **"Stripe checkout not upgrading user"**
- Check webhook is LIVE mode (not test)
- Check webhook secret matches Render env var
- Check webhook events are selected correctly

### **"Not secure" SSL warning**
- Netlify should auto-configure SSL
- Check domain DNS settings
- Force HTTPS redirect in `netlify.toml` (already done ✅)

### **"Database connection failed"**
- Check `DATABASE_URL` in Render
- Verify Neon database is active
- Check database connection string format

### **"OpenAI API rate limit exceeded"**
- Check spending limit is set high enough
- Check rate limits in OpenAI dashboard
- Consider upgrading OpenAI plan

---

## 📞 **Support Resources**

- **Stripe Docs:** https://stripe.com/docs
- **Render Docs:** https://render.com/docs
- **Netlify Docs:** https://docs.netlify.com
- **OpenAI Docs:** https://platform.openai.com/docs

---

**Last Updated:** Today  
**Next Review:** After launch (monitor for 48 hours)

