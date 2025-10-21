#!/usr/bin/env python3
"""
LiveTranslateAI Production Startup Script
Handles environment setup and server startup
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Set production environment
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("LOG_LEVEL", "INFO")

if __name__ == "__main__":
    # Get port from environment (Render sets this)
    port = int(os.environ.get("PORT", 8000))
    
    # Start the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
