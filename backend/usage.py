"""
Usage tracking and tier enforcement
"""

FREE_MINUTES_LIMIT = 15

def check_usage_limit(user: dict) -> tuple[bool, str]:
    """
    Check if user has exceeded their usage limit
    Returns: (can_use, message)
    """
    tier = user.get('tier', 'free')
    minutes_used = user.get('minutes_used', 0.0)
    
    if tier == 'free':
        if minutes_used >= FREE_MINUTES_LIMIT:
            remaining = 0
            return False, f"Free tier limit reached ({FREE_MINUTES_LIMIT} minutes used). Please upgrade to continue."
        else:
            remaining = FREE_MINUTES_LIMIT - minutes_used
            return True, f"{remaining:.1f} minutes remaining in free tier"
    else:
        # Paid tier = unlimited
        return True, "Unlimited minutes (paid tier)"

def get_usage_info(user: dict) -> dict:
    """Get formatted usage information for user"""
    tier = user.get('tier', 'free')
    minutes_used = user.get('minutes_used', 0.0)
    
    if tier == 'free':
        limit = FREE_MINUTES_LIMIT
        remaining = max(0, limit - minutes_used)
        percentage = min(100, (minutes_used / limit) * 100)
        
        return {
            "tier": "free",
            "minutes_used": round(minutes_used, 1),
            "minutes_limit": limit,
            "minutes_remaining": round(remaining, 1),
            "percentage_used": round(percentage, 1),
            "can_use": remaining > 0,
            "status": "ok" if percentage < 80 else ("warning" if percentage < 100 else "exceeded")
        }
    else:
        return {
            "tier": tier,
            "minutes_used": round(minutes_used, 1),
            "minutes_limit": "unlimited",
            "minutes_remaining": "unlimited",
            "percentage_used": 0,
            "can_use": True,
            "status": "ok"
        }

