"""
Stripe Integration for LiveTranslateAI
Handles subscriptions, checkout, and webhooks
"""
import os
import stripe
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Stripe with API key from environment
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')  # Price ID for $29/month subscription

# Product details
PRODUCT_NAME = "LiveTranslateAI Pro"
PRODUCT_PRICE = 2900  # $29.00 in cents
TRIAL_DAYS = 7

def create_checkout_session(
    user_id: str,
    user_email: str,
    success_url: str,
    cancel_url: str,
    promo_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a Stripe Checkout Session for subscription signup
    
    Args:
        user_id: Internal user ID
        user_email: User's email address
        success_url: Redirect URL after successful payment
        cancel_url: Redirect URL if user cancels
        promo_code: Optional promo code to apply (e.g., "PRODUCTHUNT50")
    
    Returns:
        Dict with checkout session details (id, url)
    """
    try:
        logger.info(f"💳 Creating Stripe checkout session for user {user_id}")
        
        # Create or retrieve customer
        customers = stripe.Customer.list(email=user_email, limit=1)
        if customers.data:
            customer = customers.data[0]
            logger.info(f"💳 Found existing Stripe customer: {customer.id}")
        else:
            customer = stripe.Customer.create(
                email=user_email,
                metadata={'user_id': user_id}
            )
            logger.info(f"💳 Created new Stripe customer: {customer.id}")
        
        # Prepare checkout session parameters
        session_params = {
            'customer': customer.id,
            'payment_method_types': ['card'],
            'line_items': [{
                'price': STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            'mode': 'subscription',
            'subscription_data': {
                'trial_period_days': TRIAL_DAYS,
                'metadata': {
                    'user_id': user_id
                }
            },
            'success_url': success_url + '?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': cancel_url,
            'allow_promotion_codes': True,
            'billing_address_collection': 'auto',
            'metadata': {
                'user_id': user_id
            }
        }
        
        # Apply promo code if provided
        if promo_code:
            try:
                # Look up the promotion code
                promo_codes = stripe.PromotionCode.list(code=promo_code, limit=1)
                if promo_codes.data:
                    coupon_id = promo_codes.data[0].coupon.id
                    session_params['discounts'] = [{'coupon': coupon_id}]
                    logger.info(f"🎟️ Applying promo code: {promo_code} (coupon: {coupon_id})")
                else:
                    logger.warning(f"⚠️ Promo code {promo_code} not found in Stripe, continuing without discount")
            except Exception as promo_error:
                logger.warning(f"⚠️ Error applying promo code {promo_code}: {promo_error}, continuing without discount")
        
        # Create checkout session with 7-day free trial
        session = stripe.checkout.Session.create(**session_params)
        
        logger.info(f"✅ Checkout session created: {session.id}")
        
        return {
            'id': session.id,
            'url': session.url,
            'customer_id': customer.id
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"❌ Stripe error: {str(e)}")
        raise Exception(f"Failed to create checkout session: {str(e)}")


def create_portal_session(customer_id: str, return_url: str) -> Dict[str, str]:
    """
    Create a Stripe Customer Portal session for subscription management
    
    Args:
        customer_id: Stripe customer ID
        return_url: URL to redirect after portal session
    
    Returns:
        Dict with portal session URL
    """
    try:
        logger.info(f"🔧 Creating customer portal session for {customer_id}")
        
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
        
        logger.info(f"✅ Portal session created: {session.id}")
        
        return {'url': session.url}
        
    except stripe.error.StripeError as e:
        logger.error(f"❌ Stripe portal error: {str(e)}")
        raise Exception(f"Failed to create portal session: {str(e)}")


def verify_webhook_signature(payload: bytes, signature: str) -> Optional[Dict[str, Any]]:
    """
    Verify Stripe webhook signature and return event data
    
    Args:
        payload: Raw request body bytes
        signature: Stripe-Signature header value
    
    Returns:
        Event data dict if valid, None if invalid
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"✅ Webhook signature verified: {event['type']}")
        return event
    except ValueError as e:
        logger.error(f"❌ Invalid webhook payload: {str(e)}")
        return None
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"❌ Invalid webhook signature: {str(e)}")
        return None


def handle_checkout_completed(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle successful checkout completion
    
    Args:
        session: Stripe checkout session object
    
    Returns:
        Dict with user_id and subscription details
    """
    user_id = session['metadata'].get('user_id')
    customer_id = session['customer']
    subscription_id = session['subscription']
    
    logger.info(f"🎉 Checkout completed for user {user_id}")
    logger.info(f"💳 Customer ID: {customer_id}")
    logger.info(f"📋 Subscription ID: {subscription_id}")
    
    # Retrieve subscription details
    subscription = stripe.Subscription.retrieve(subscription_id)
    
    return {
        'user_id': user_id,
        'customer_id': customer_id,
        'subscription_id': subscription_id,
        'status': subscription['status'],
        'trial_end': subscription['trial_end'],
        'current_period_end': subscription['current_period_end']
    }


def handle_subscription_updated(subscription: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle subscription status changes
    
    Args:
        subscription: Stripe subscription object
    
    Returns:
        Dict with user_id and new status
    """
    subscription_id = subscription['id']
    status = subscription['status']
    user_id = subscription['metadata'].get('user_id')
    
    logger.info(f"🔄 Subscription {subscription_id} updated: {status}")
    
    return {
        'user_id': user_id,
        'subscription_id': subscription_id,
        'status': status,
        'current_period_end': subscription.get('current_period_end'),
        'cancel_at_period_end': subscription.get('cancel_at_period_end', False)
    }


def handle_subscription_deleted(subscription: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle subscription cancellation
    
    Args:
        subscription: Stripe subscription object
    
    Returns:
        Dict with user_id and cancellation details
    """
    subscription_id = subscription['id']
    user_id = subscription['metadata'].get('user_id')
    
    logger.info(f"❌ Subscription {subscription_id} cancelled for user {user_id}")
    
    return {
        'user_id': user_id,
        'subscription_id': subscription_id,
        'status': 'cancelled'
    }


def get_subscription_status(subscription_id: str) -> Dict[str, Any]:
    """
    Get current subscription status from Stripe
    
    Args:
        subscription_id: Stripe subscription ID
    
    Returns:
        Dict with subscription details
    """
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        return {
            'id': subscription['id'],
            'status': subscription['status'],
            'current_period_end': subscription['current_period_end'],
            'cancel_at_period_end': subscription.get('cancel_at_period_end', False),
            'trial_end': subscription.get('trial_end')
        }
    except stripe.error.StripeError as e:
        logger.error(f"❌ Failed to get subscription status: {str(e)}")
        return None


def cancel_subscription(subscription_id: str, immediately: bool = False) -> bool:
    """
    Cancel a subscription
    
    Args:
        subscription_id: Stripe subscription ID
        immediately: If True, cancel immediately. If False, cancel at period end.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if immediately:
            stripe.Subscription.delete(subscription_id)
            logger.info(f"❌ Subscription {subscription_id} cancelled immediately")
        else:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            logger.info(f"⏰ Subscription {subscription_id} will cancel at period end")
        
        return True
    except stripe.error.StripeError as e:
        logger.error(f"❌ Failed to cancel subscription: {str(e)}")
        return False

