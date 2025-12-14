# Product Hunt Promo Code Setup

## Creating the 50% Off Promo Code in Stripe

1. **Log into Stripe Dashboard**: https://dashboard.stripe.com
2. **Go to Products → Coupons**: Click "Create coupon"
3. **Create the Coupon**:
   - **Name**: "Product Hunt 50% Off"
   - **ID**: `producthunt50` (optional, auto-generated if not set)
   - **Discount**: 50% off
   - **Duration**: Forever (applies to all future billing cycles)
   - **Applies to**: All products
   - **Redemption limits**: Optional - set max redemptions if needed
   - Click "Create coupon"

4. **Create the Promotion Code**:
   - After creating the coupon, click "Create promotion code"
   - **Code**: `PRODUCTHUNT50` (or your preferred code)
   - **Coupon**: Select the coupon you just created
   - **Active**: Yes
   - **Expiration**: Optional - set if you want it to expire
   - Click "Create promotion code"

## Using the Promo Code

### Option 1: Users Enter Manually (Already Enabled)
- Users can enter `PRODUCTHUNT50` in the Stripe checkout page
- The promo code field is already visible (`allow_promotion_codes=True`)

### Option 2: Pre-apply via API (New Feature)
- The backend now accepts a `promo_code` parameter
- Frontend can pass it when creating checkout session
- Example: `{ "user_id": "...", "promo_code": "PRODUCTHUNT50" }`

## Testing

1. Create a test coupon in Stripe (test mode)
2. Use the promo code in checkout
3. Verify 50% discount is applied
4. Check that discount persists for future billing cycles

## Notes

- The promo code applies to the subscription price ($29/month → $14.50/month)
- The 7-day free trial still applies before billing starts
- Discount continues for all future billing cycles (forever duration)
- Users can still manually enter promo codes even if not pre-applied
