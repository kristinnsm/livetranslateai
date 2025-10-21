"""
LiveTranslateAI Simple Backend - Minimal version for deployment
FastAPI server with WebSocket support for audio streaming
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_BUFFER_DURATION = int(os.getenv("MAX_BUFFER_DURATION", "300"))  # 5 minutes

# Setup
app = FastAPI(title="LiveTranslateAI API", version="1.0.0")
logger = logging.getLogger(__name__)

# CORS - production ready
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://livetranslateai.com",
        "https://www.livetranslateai.com",
        "https://app.livetranslateai.com",
        "https://api.livetranslateai.com",
        "http://localhost:3000",  # For development
        "http://127.0.0.1:3000"   # For development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Session storage (in-memory for MVP)
active_sessions: Dict[str, Dict] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set in environment")
        raise RuntimeError("Missing OpenAI API key")
    
    logger.info("[STARTUP] LiveTranslateAI Simple Backend starting")
    logger.info(f"[CONFIG] Max buffer duration: {MAX_BUFFER_DURATION}s")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "LiveTranslateAI",
        "status": "running",
        "mode": "simple",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "api_key_configured": bool(OPENAI_API_KEY),
            "active_sessions": len(active_sessions),
            "mode": "simple"
        }
    )


@app.websocket("/ws/translate")
async def websocket_translate(websocket: WebSocket):
    """Simple WebSocket endpoint for testing"""
    await websocket.accept()
    logger.info("[WEBSOCKET] WebSocket connection accepted")
    
    session_id = f"session_{datetime.utcnow().timestamp()}"
    active_sessions[session_id] = {
        "connected_at": datetime.utcnow().isoformat()
    }
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "mode": "simple",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Simple message loop
        while True:
            try:
                data = await websocket.receive()
                
                if "bytes" in data:
                    # Audio chunk received
                    audio_chunk = data["bytes"]
                    logger.info(f"[AUDIO_CHUNK] Received audio chunk: {len(audio_chunk)} bytes")
                    
                    # Process with real OpenAI translation
                    try:
                        from openai import AsyncOpenAI
                        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                        
                        # For now, send a simple text response
                        # TODO: Add real audio processing
                        response = await client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "You are a professional translator. Translate the following text from English to Spanish. Only return the translation, nothing else."},
                                {"role": "user", "content": "Hello, how are you today?"}
                            ],
                            max_tokens=100
                        )
                        
                        translated_text = response.choices[0].message.content
                        
                        await websocket.send_json({
                            "type": "translation",
                            "timestamp": datetime.utcnow().timestamp(),
                            "original": "Hello, how are you today?",
                            "translated": translated_text,
                            "source_lang": "en",
                            "target_lang": "es",
                            "latency_ms": 100
                        })
                        
                    except Exception as e:
                        logger.error(f"Translation error: {e}")
                        # Fallback to mock response
                        await websocket.send_json({
                            "type": "translation",
                            "timestamp": datetime.utcnow().timestamp(),
                            "original": "Audio received (translation error)",
                            "translated": "Audio recibido (error de traducción)",
                            "source_lang": "en",
                            "target_lang": "es",
                            "latency_ms": 100
                        })
                    
                elif "text" in data:
                    # Control message (JSON)
                    message = json.loads(data["text"])
                    action = message.get("action")
                    
                    if action == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                    else:
                        await websocket.send_json({"type": "error", "message": f"Unknown action: {action}"})
                    
            except WebSocketDisconnect:
                logger.info(f"[DISCONNECT] Client disconnected: {session_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                await websocket.send_json({"type": "error", "message": "Invalid message format"})
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                try:
                    await websocket.send_json({"type": "error", "message": str(e)})
                except:
                    break
    
    finally:
        # Cleanup session
        if session_id in active_sessions:
            del active_sessions[session_id]
            logger.info(f"[CLEANUP] Session cleaned up: {session_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
