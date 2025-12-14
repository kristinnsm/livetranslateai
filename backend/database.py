"""
PostgreSQL Database Connection and Schema
Using Neon (serverless Postgres)
"""
import os
import psycopg
from psycopg.rows import dict_row
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')

# Create database schema
SCHEMA_SQL = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    picture TEXT,
    tier VARCHAR(50) DEFAULT 'free',
    minutes_used DECIMAL(10, 2) DEFAULT 0.0,
    fingerprint VARCHAR(255),
    ip_address VARCHAR(100),
    abuse_flagged BOOLEAN DEFAULT FALSE,
    subscription_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rooms table (for analytics - optional for MVP)
CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    room_id VARCHAR(50) UNIQUE NOT NULL,
    host_user_id VARCHAR(255) REFERENCES users(user_id),
    host_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    total_duration_minutes DECIMAL(10, 2) DEFAULT 0.0
);

-- Usage logs table (for detailed tracking - optional for MVP)
CREATE TABLE IF NOT EXISTS usage_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(user_id),
    room_id VARCHAR(50),
    duration_minutes DECIMAL(10, 2),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_fingerprint ON users(fingerprint);
"""

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not set!")
        raise ValueError("DATABASE_URL environment variable not set")
    
    conn = None
    try:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def init_database():
    """Initialize database schema"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SCHEMA_SQL)
            logger.info("✅ Database schema initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

# User CRUD operations
def _convert_decimals(user_dict: dict) -> dict:
    """Convert Decimal types to float for JSON serialization"""
    if user_dict:
        user_dict = dict(user_dict)
        if 'minutes_used' in user_dict:
            user_dict['minutes_used'] = float(user_dict['minutes_used'])
        return user_dict
    return None

def create_user(user_data: dict) -> dict:
    """Create a new user in database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (
                    user_id, google_id, email, name, picture, 
                    tier, fingerprint, ip_address, abuse_flagged
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                user_data['user_id'],
                user_data['google_id'],
                user_data['email'],
                user_data['name'],
                user_data.get('picture', ''),
                user_data.get('tier', 'free'),
                user_data.get('fingerprint', ''),
                user_data.get('ip_address', ''),
                user_data.get('abuse_flagged', False)
            ))
            user = _convert_decimals(cursor.fetchone())
            logger.info(f"✅ Created user in database: {user['name']}")
            return user
    except Exception as e:
        logger.error(f"❌ Failed to create user: {e}")
        raise

def get_user_by_google_id(google_id: str) -> dict:
    """Get user by Google ID"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE google_id = %s", (google_id,))
            user = cursor.fetchone()
            return _convert_decimals(user) if user else None
    except Exception as e:
        logger.error(f"❌ Failed to get user: {e}")
        return None

def get_user_by_user_id(user_id: str) -> dict:
    """Get user by user_id"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            return _convert_decimals(user) if user else None
    except Exception as e:
        logger.error(f"❌ Failed to get user: {e}")
        return None

def update_user_usage(user_id: str, minutes_to_add: float) -> dict:
    """Update user's usage minutes"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET minutes_used = minutes_used + %s
                WHERE user_id = %s
                RETURNING *
            """, (minutes_to_add, user_id))
            user = cursor.fetchone()
            if user:
                user = _convert_decimals(user)
                logger.info(f"📊 Updated usage in DB: {user['name']} now at {user['minutes_used']:.2f} minutes")
                return user
            return None
    except Exception as e:
        logger.error(f"❌ Failed to update usage: {e}")
        raise

def update_user_last_login(google_id: str):
    """Update user's last login timestamp"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP
                WHERE google_id = %s
            """, (google_id,))
    except Exception as e:
        logger.error(f"❌ Failed to update last login: {e}")

def check_fingerprint_used(fingerprint: str) -> str:
    """Check if fingerprint was already used by different user"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT google_id FROM users WHERE fingerprint = %s", (fingerprint,))
            result = cursor.fetchone()
            return result['google_id'] if result else None
    except Exception as e:
        logger.error(f"❌ Failed to check fingerprint: {e}")
        return None

def update_user_tier(user_id: str, new_tier: str, subscription_id: str = None):
    """Update user's subscription tier"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if subscription_id:
                cursor.execute("""
                    UPDATE users 
                    SET tier = %s, subscription_id = %s
                    WHERE user_id = %s
                """, (new_tier, subscription_id, user_id))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET tier = %s
                    WHERE user_id = %s
                """, (new_tier, user_id))
            logger.info(f"✅ Updated user tier to: {new_tier}")
    except Exception as e:
        logger.error(f"❌ Failed to update tier: {e}")
        raise

def get_user_by_subscription_id(subscription_id: str) -> dict:
    """Get user by Stripe subscription ID"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE subscription_id = %s", (subscription_id,))
            user = cursor.fetchone()
            return _convert_decimals(user) if user else None
    except Exception as e:
        logger.error(f"❌ Failed to get user by subscription ID: {e}")
        return None

def update_stripe_customer(user_id: str, stripe_customer_id: str = None):
    """Store Stripe customer ID for user (or clear it if None)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Add stripe_customer_id column if it doesn't exist
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255)
            """)
            cursor.execute("""
                UPDATE users 
                SET stripe_customer_id = %s
                WHERE user_id = %s
            """, (stripe_customer_id, user_id))
            if stripe_customer_id:
                logger.info(f"✅ Stored Stripe customer ID for user {user_id}")
            else:
                logger.info(f"🧹 Cleared Stripe customer ID for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to store Stripe customer ID: {e}")
        raise

def get_user_stripe_customer_id(user_id: str) -> str:
    """Get user's Stripe customer ID"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT stripe_customer_id FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return result['stripe_customer_id'] if result and result.get('stripe_customer_id') else None
    except Exception as e:
        logger.error(f"❌ Failed to get Stripe customer ID: {e}")
        return None

