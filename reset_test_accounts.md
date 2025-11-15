# 🔄 Reset Test Accounts for Stripe Testing

## Quick Reset Method

You have an admin endpoint to reset accounts. Here's how to use it:

### **Option 1: Browser Console (Easiest)**

1. **Login to the app** with the account you want to reset
2. **Open browser console** (F12)
3. **Run this command:**

```javascript
// Get your user ID from localStorage
const user = JSON.parse(localStorage.getItem('user'));
const userId = user.user_id;
const authToken = localStorage.getItem('auth_token');

// Reset the account
fetch('https://livetranslateai.onrender.com/api/admin/reset-account', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify({ user_id: userId })
})
.then(r => r.json())
.then(data => {
    console.log('✅ Account reset:', data);
    alert('Account reset! Refresh the page.');
    location.reload();
})
.catch(err => {
    console.error('❌ Reset failed:', err);
    alert('Reset failed. Check console.');
});
```

### **Option 2: PowerShell Script**

Save this as `reset-account.ps1`:

```powershell
# Reset a test account
param(
    [Parameter(Mandatory=$true)]
    [string]$UserId
)

$body = @{
    user_id = $UserId
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "https://livetranslateai.onrender.com/api/admin/reset-account" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

Write-Host "✅ Account reset:" -ForegroundColor Green
$response | ConvertTo-Json
```

**Usage:**
```powershell
.\reset-account.ps1 -UserId "your-user-id-here"
```

### **Option 3: Direct API Call (Any Tool)**

**Endpoint:** `POST https://livetranslateai.onrender.com/api/admin/reset-account`

**Body:**
```json
{
    "user_id": "your-user-id-here"
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Account reset for email@example.com. You can now go through checkout again."
}
```

---

## 🎯 What Gets Reset

- ✅ Tier: `premium` → `free`
- ✅ Stripe customer ID: Cleared (set to `NULL`)
- ✅ Subscription ID: Cleared
- ⚠️ **Minutes used: NOT reset** (still tracks usage)

---

## 💳 Better Testing Strategy

Instead of using real credit cards, use **Stripe test cards** (they work infinitely):

### **Stripe Test Cards:**

| Card Number | Result | Notes |
|-------------|--------|-------|
| `4242 4242 4242 4242` | ✅ Success | Instant approval |
| `4000 0025 0000 3155` | ✅ Success | Requires 3D Secure |
| `4000 0000 0000 9995` | ❌ Declined | Test declined card |
| `4000 0000 0000 0069` | ❌ Expired | Test expired card |

**All test cards:**
- Expiry: Any future date (e.g., `12/34`)
- CVC: Any 3 digits (e.g., `123`)
- ZIP: Any 5 digits (e.g., `12345`)

### **Why Test Cards Are Better:**

- ✅ **Unlimited uses** - No need to reset accounts
- ✅ **No real charges** - Safe testing
- ✅ **Instant results** - No waiting for real payment processing
- ✅ **Test edge cases** - Declined cards, 3D Secure, etc.

---

## 🔍 Find Your User ID

**In Browser Console:**
```javascript
const user = JSON.parse(localStorage.getItem('user'));
console.log('User ID:', user.user_id);
console.log('Email:', user.email);
console.log('Tier:', user.tier);
```

**Or check the Network tab:**
- Look for `/api/user/usage?user_id=...` requests
- The `user_id` is in the URL

---

## 🚀 Quick Reset All Your Test Accounts

**Browser Console Script (Reset Current Account):**

```javascript
(async function() {
    const user = JSON.parse(localStorage.getItem('user'));
    const authToken = localStorage.getItem('auth_token');
    
    console.log(`🔄 Resetting account: ${user.email} (${user.user_id})`);
    
    const response = await fetch('https://livetranslateai.onrender.com/api/admin/reset-account', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ user_id: user.user_id })
    });
    
    const data = await response.json();
    console.log('✅ Result:', data);
    
    // Refresh page to see changes
    setTimeout(() => location.reload(), 1000);
})();
```

**Copy-paste this into console, then logout/login to reset another account.**

---

## ⚠️ Important Notes

1. **This only works for YOUR accounts** - You need to be logged in to reset
2. **Rate limited** - Max 10 resets per minute (to prevent abuse)
3. **Minutes used persists** - Only tier and Stripe data are reset
4. **Stripe subscriptions** - You may need to cancel them manually in Stripe dashboard (test mode)

---

## 🎯 Recommended Testing Flow

1. **Use Stripe test cards** (`4242 4242 4242 4242`) instead of real cards
2. **Test with one account** - Reset it when needed
3. **Only use real cards** when testing live mode (production)
4. **Reset accounts** when switching between test/live mode

---

## 🐛 Troubleshooting

**"Reset failed"**
- Check you're logged in
- Check user_id is correct
- Check backend logs for errors

**"Account still shows premium"**
- Refresh the page (F5)
- Logout and login again
- Check browser console for errors

**"Stripe still has subscription"**
- Go to Stripe Dashboard → Customers
- Find the customer
- Cancel the subscription manually (test mode)

