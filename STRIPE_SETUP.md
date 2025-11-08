# Stripe Integration Setup Guide

## 🎯 What's Been Built

A complete Stripe integration with:
- ✅ **7-day free trial** ($29/month after trial)
- ✅ **Auto-upgrade on payment** (free → premium tier)
- ✅ **Webhook handling** (subscription updates, cancellations)
- ✅ **Customer Portal** (users can manage subscriptions themselves)
- ✅ **Database persistence** (tracks subscriptions in PostgreSQL)

---

## 📋 Setup Checklist

### **1. Create Stripe Account**

1. Go to: https://dashboard.stripe.com/register
2. Complete signup and verify your email
3. **Enable Test Mode** (toggle in top-right corner)

---

### **2. Create Your Product & Price**

1. Go to: https://dashboard.stripe.com/products
2. Click **"+ Add product"**
3. Fill in:
   - **Name:** `LiveTranslateAI Pro`
   - **Description:** `Unlimited real-time voice translation calls`
   - **Pricing model:** Recurring
   - **Price:** `29` USD
   - **Billing period:** Monthly
   - **Free trial:** 7 days
4. Click **"Save product"**
5. **Copy the Price ID** (starts with `price_...`) - you'll need this!

---

### **3. Get Your API Keys**

1. Go to: https://dashboard.stripe.com/apikeys
2. Copy these keys:
   - **Publishable key** (starts with `pk_test_...`)
   - **Secret key** (starts with `sk_test_...`) - **Keep this secret!**

---

### **4. Add Environment Variables to Render**

1. Go to: https://dashboard.render.com
2. Open your backend service
3. Go to **Environment** tab
4. Add these variables:

```
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_PRICE_ID=price_YOUR_PRICE_ID_HERE
STRIPE_WEBHOOK_SECRET=(leave empty for now - we'll add this in step 6)
```

5. Click **"Save Changes"** - backend will auto-redeploy

---

### **5. Set Up Stripe Webhook**

**IMPORTANT:** You need to set this up so Stripe can notify your backend about payments!

#### **Option A: Using Render Domain (Recommended)**

1. Go to: https://dashboard.stripe.com/webhooks
2. Click **"+ Add endpoint"**
3. Enter your webhook URL:
   ```
   https://livetranslateai.onrender.com/api/stripe/webhook
   ```
4. Click **"Select events"** and choose:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
5. Click **"Add endpoint"**
6. Click on your new webhook
7. Click **"Reveal" under "Signing secret"**
8. Copy the webhook secret (starts with `whsec_...`)
9. Go back to Render → Environment
10. Set `STRIPE_WEBHOOK_SECRET=whsec_YOUR_SECRET_HERE`
11. Save - backend redeploys

#### **Option B: Using Stripe CLI for Local Testing**

1. Install Stripe CLI: https://stripe.com/docs/stripe-cli
2. Run: `stripe listen --forward-to localhost:8000/api/stripe/webhook`
3. Copy the webhook signing secret
4. Set locally: `export STRIPE_WEBHOOK_SECRET=whsec_...`

---

### **6. Test Your Integration**

#### **Test Checkout Flow:**

1. Visit: https://livetranslateai.com/app
2. Login with Google
3. Use all 15 free minutes (or manually trigger upgrade modal)
4. Click **"Start Free Trial"**
5. You'll be redirected to Stripe Checkout
6. Use test card: `4242 4242 4242 4242`
   - Expiry: Any future date
   - CVC: Any 3 digits
   - ZIP: Any 5 digits
7. Complete payment
8. You'll be redirected back with success message
9. Check your profile bar - should show **"✨ Premium - Unlimited calls"**

#### **Test Webhook:**

1. Go to: https://dashboard.stripe.com/webhooks
2. Click on your webhook
3. Click **"Send test webhook"**
4. Select `checkout.session.completed`
5. Click **"Send test webhook"**
6. Check Render logs - you should see: `"📨 Stripe webhook received: checkout.session.completed"`

#### **Test Customer Portal:**

1. As a premium user, click **"Manage Subscription"** button
2. You'll be redirected to Stripe Customer Portal
3. Try canceling subscription
4. Go back to app - should show free tier again

---

### **7. Switch to Live Mode (When Ready to Launch)**

1. Go to: https://dashboard.stripe.com
2. Toggle **"View test data"** OFF (top-right)
3. Repeat steps 2-5 with LIVE mode keys
4. Update Render environment variables with live keys (no `_test_` prefix)
5. **Enable production webhook** with live domain

---

## 🧪 Test Card Numbers

### **Success:**
- `4242 4242 4242 4242` - Succeeds immediately
- `4000 0025 0000 3155` - Requires authentication (3D Secure)

### **Failure:**
- `4000 0000 0000 9995` - Declined card
- `4000 0000 0000 0069` - Expired card

More test cards: https://stripe.com/docs/testing

---

## 📊 Monitoring

### **Check Payments:**
- https://dashboard.stripe.com/payments

### **Check Subscriptions:**
- https://dashboard.stripe.com/subscriptions

### **Check Webhooks:**
- https://dashboard.stripe.com/webhooks
- See delivery attempts and responses

### **Check Logs:**
- Render backend logs show all Stripe events:
  - `💳 Created Stripe checkout session`
  - `📨 Stripe webhook received`
  - `✅ Upgraded user to premium`

---

## 🔒 Security Checklist

- ✅ **Never commit API keys to git**
- ✅ **Use test mode until ready to launch**
- ✅ **Webhook signature verification** (already implemented)
- ✅ **HTTPS only** (Stripe requires it)
- ✅ **Backend handles all payment logic** (frontend just redirects)

---

## 💰 Pricing Strategy

**Current Setup:**
- **Free Tier:** 15 minutes/month
- **Premium Tier:** $29/month unlimited (7-day free trial)

**To Change Pricing:**
1. Create new price in Stripe dashboard
2. Update `STRIPE_PRICE_ID` in Render
3. Update frontend text in `app/index.html` (search for "$29")

---

## 🐛 Troubleshooting

### **"Failed to create checkout session"**
- Check `STRIPE_SECRET_KEY` is set in Render
- Check `STRIPE_PRICE_ID` is correct
- Check backend logs for errors

### **"Webhook signature verification failed"**
- Check `STRIPE_WEBHOOK_SECRET` is set
- Check webhook endpoint URL matches Render domain
- Check webhook is configured to send correct events

### **"User upgraded but still shows free tier"**
- Check webhook was received (Stripe dashboard)
- Check backend logs for upgrade message
- Logout and login again (refreshes user data)
- Check database: `SELECT * FROM users WHERE email='your@email.com';`

### **"Manage Subscription button doesn't work"**
- User must have active subscription
- Check user has `stripe_customer_id` in database
- Check backend logs for portal creation errors

---

## 📞 Support

- **Stripe Docs:** https://stripe.com/docs
- **Stripe Support:** https://support.stripe.com
- **Dashboard:** https://dashboard.stripe.com

---

## ✅ You're Done!

Your Stripe integration is complete! 🎉

Users can now:
1. Sign up with Google (15 min free)
2. Start 7-day free trial
3. Get charged $29/month after trial
4. Manage/cancel subscription anytime

**Next steps:**
1. Set up Stripe account (test mode)
2. Add environment variables to Render
3. Test with test card
4. Switch to live mode when ready! 🚀

