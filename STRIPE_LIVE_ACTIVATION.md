# 🚀 Stripe Live Mode Activation Guide

**Status:** Step-by-step instructions to switch from Test Mode → Live Mode

---

## ⚠️ **IMPORTANT: Before You Start**

1. **Test Mode is Safe:** You can test as much as you want without real charges
2. **Live Mode = Real Money:** Once activated, real payments will be processed
3. **Backup Your Test Keys:** Save test keys somewhere safe (you might need them for testing)

---

## 📋 **Step 1: Switch Stripe Dashboard to Live Mode**

1. Go to: https://dashboard.stripe.com
2. **Toggle OFF "Test mode"** (top-right corner, toggle switch)
3. You'll see a warning: "You're switching to live mode"
4. Click **"Switch to live mode"**
5. ✅ **Dashboard now shows "Live mode"** (red badge in top-right)

---

## 🔑 **Step 2: Get Your LIVE API Keys**

1. In Stripe Dashboard (LIVE mode), go to: **Developers** → **API keys**
2. You'll see two keys:
   - **Publishable key** (starts with `pk_live_...`)
   - **Secret key** (starts with `sk_live_...`) - Click "Reveal" to see it
3. **Copy both keys** - you'll need them in Step 4

**⚠️ Keep Secret Key SECRET!** Never share it or commit it to git.

---

## 💰 **Step 3: Create LIVE Product & Price**

1. In Stripe Dashboard (LIVE mode), go to: **Products**
2. Click **"+ Add product"**
3. Fill in:
   - **Name:** `LiveTranslateAI Pro`
   - **Description:** `Unlimited real-time voice translation calls`
   - **Pricing model:** Recurring
   - **Price:** `29` USD
   - **Billing period:** Monthly
   - **Free trial:** 7 days ✅
4. Click **"Save product"**
5. **Copy the Price ID** (starts with `price_...`) - you'll need this!

**Example Price ID:** `price_1ABC123def456GHI789jkl012`

---

## 🔔 **Step 4: Set Up LIVE Webhook**

1. In Stripe Dashboard (LIVE mode), go to: **Developers** → **Webhooks**
2. Click **"+ Add endpoint"**
3. Enter your webhook URL:
   ```
   https://livetranslateai-backend.onrender.com/api/stripe/webhook
   ```
   *(Replace with your actual Render backend URL if different)*
4. Click **"Select events"** and choose:
   - ✅ `checkout.session.completed`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
   - ✅ `invoice.payment_failed`
5. Click **"Add endpoint"**
6. Click on your new webhook endpoint
7. Click **"Reveal"** under "Signing secret"
8. **Copy the webhook secret** (starts with `whsec_...`) - you'll need this!

**Example Webhook Secret:** `whsec_1ABC123def456GHI789jkl012`

---

## ⚙️ **Step 5: Update Render Environment Variables**

1. Go to: https://dashboard.render.com
2. Open your **LiveTranslateAI Backend** service
3. Go to **Environment** tab (left sidebar)
4. Update these variables:

### **Update STRIPE_SECRET_KEY:**
- Find `STRIPE_SECRET_KEY` in the list
- Click **Edit** (or delete old one and add new)
- **Value:** `sk_live_YOUR_LIVE_SECRET_KEY` (from Step 2)
- Click **Save**

### **Update STRIPE_PRICE_ID:**
- Find `STRIPE_PRICE_ID` in the list
- Click **Edit**
- **Value:** `price_YOUR_LIVE_PRICE_ID` (from Step 3)
- Click **Save**

### **Update STRIPE_WEBHOOK_SECRET:**
- Find `STRIPE_WEBHOOK_SECRET` in the list
- Click **Edit**
- **Value:** `whsec_YOUR_LIVE_WEBHOOK_SECRET` (from Step 4)
- Click **Save**

5. **Render will auto-redeploy** (~2 minutes)
6. ✅ Wait for deployment to complete (check "Events" tab)

---

## ✅ **Step 6: Verify Backend Deployment**

1. In Render Dashboard, go to **Events** tab
2. Wait for deployment to complete (status: "Live")
3. Check **Logs** tab for any errors
4. Look for: `✅ Server started successfully`

**If you see errors:**
- Check environment variables are correct (no typos)
- Check Stripe keys are LIVE mode (not test mode)
- Check webhook secret matches Stripe dashboard

---

## 🧪 **Step 7: Test LIVE Payment Flow**

**⚠️ WARNING: This will create a REAL payment!**

### **Option A: Use Stripe Test Card (Recommended First Test)**

Stripe allows you to use test cards even in LIVE mode for testing:
- Card: `4242 4242 4242 4242`
- Expiry: Any future date (e.g., 12/25)
- CVC: Any 3 digits (e.g., 123)
- ZIP: Any 5 digits (e.g., 12345)

**Note:** Stripe will process this as a real payment, but you can refund it immediately.

### **Option B: Use Real Card (Small Amount)**

1. Go to: https://livetranslateai.com/app
2. Login with Google
3. Click **"Start Free Trial"** (or trigger upgrade modal)
4. Complete checkout with your real card
5. **Check Stripe Dashboard** → **Payments** → Should see your payment
6. **Check Stripe Dashboard** → **Subscriptions** → Should see active subscription
7. **Check your app** → Should show "✨ Premium - Unlimited calls"

---

## 🔍 **Step 8: Verify Webhook is Working**

1. Go to: **Stripe Dashboard** → **Webhooks**
2. Click on your webhook endpoint
3. Check **"Recent deliveries"** tab
4. You should see recent events:
   - `checkout.session.completed` ✅
   - `customer.subscription.created` ✅
5. Click on an event → Check **"Response"** → Should be `200 OK`

**If webhook fails:**
- Check webhook URL is correct (matches Render backend URL)
- Check `STRIPE_WEBHOOK_SECRET` matches Stripe dashboard
- Check Render logs for webhook errors

---

## 📊 **Step 9: Monitor First Payments**

**For the next 24 hours, monitor:**

1. **Stripe Dashboard** → **Payments**
   - Check payments are coming through
   - Verify amounts are correct ($29/month)

2. **Stripe Dashboard** → **Subscriptions**
   - Check subscriptions are active
   - Verify trial periods are set correctly (7 days)

3. **Render Logs**
   - Check for webhook errors
   - Check for upgrade confirmations: `✅ Upgraded user to premium`

4. **Your App**
   - Test that users upgrade correctly after payment
   - Test that customer portal works

---

## 🐛 **Troubleshooting**

### **"Webhook signature verification failed"**
- ✅ Check `STRIPE_WEBHOOK_SECRET` matches Stripe dashboard (LIVE mode)
- ✅ Check webhook URL is correct
- ✅ Check webhook is configured for LIVE mode (not test mode)

### **"Failed to create checkout session"**
- ✅ Check `STRIPE_SECRET_KEY` is LIVE mode (`sk_live_...`)
- ✅ Check `STRIPE_PRICE_ID` is LIVE mode (`price_...`)
- ✅ Check Render logs for detailed error

### **"User upgraded but still shows free tier"**
- ✅ Check webhook was received (Stripe Dashboard → Webhooks)
- ✅ Check Render logs for upgrade message
- ✅ User should logout/login to refresh data
- ✅ Check database: `SELECT * FROM users WHERE email='user@example.com';`

### **"Manage Subscription button doesn't work"**
- ✅ User must have active subscription
- ✅ Check user has `stripe_customer_id` in database
- ✅ Check `STRIPE_SECRET_KEY` is LIVE mode

---

## ✅ **Final Checklist**

Before considering Stripe "activated":

- [ ] Stripe Dashboard is in **LIVE mode** (not test mode)
- [ ] `STRIPE_SECRET_KEY` updated in Render (starts with `sk_live_...`)
- [ ] `STRIPE_PRICE_ID` updated in Render (from LIVE product)
- [ ] `STRIPE_WEBHOOK_SECRET` updated in Render (from LIVE webhook)
- [ ] Backend deployed successfully (no errors in Render logs)
- [ ] Test payment completed successfully
- [ ] Webhook received and processed (check Stripe Dashboard)
- [ ] User upgraded to premium tier after payment
- [ ] Customer portal works for premium users

---

## 🎉 **You're Live!**

Once all checkboxes are ✅, **Stripe is activated in production mode!**

**Next Steps:**
1. Monitor first few payments closely
2. Set up Stripe email notifications (optional)
3. Consider Stripe Radar for fraud detection (optional)
4. Set up Stripe billing portal branding (optional)

---

## 📞 **Support**

- **Stripe Support:** https://support.stripe.com
- **Stripe Docs:** https://stripe.com/docs
- **Render Support:** https://render.com/docs

---

**Last Updated:** Today  
**Status:** Ready for activation

