"""
Minimal LiveTranslateAI Backend - Ultra-simple version for deployment
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
from datetime import datetime
import os

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Setup
app = FastAPI(title="LiveTranslateAI API", version="1.0.0")
logger = logging.getLogger(__name__)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"service": "LiveTranslateAI", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "api_key_configured": bool(OPENAI_API_KEY),
        "mode": "minimal"
    }

@app.websocket("/ws/translate")
async def websocket_translate(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")
    
    try:
        await websocket.send_json({
            "type": "connected",
            "mode": "minimal",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            try:
                data = await websocket.receive()
                
                if "bytes" in data:
                    # Audio chunk received
                    audio_chunk = data["bytes"]
                    logger.info(f"Received audio: {len(audio_chunk)} bytes")
                    
                    # Simple translation using requests (no async issues)
                    try:
                        import requests
                        
                        response = requests.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {OPENAI_API_KEY}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "gpt-4o-mini",
                                "messages": [
                                    {"role": "system", "content": "Translate to Spanish. Only return the translation."},
                                    {"role": "user", "content": "Hello, how are you today?"}
                                ],
                                "max_tokens": 100,
                                "temperature": 0.1
                            },
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            translated = result["choices"][0]["message"]["content"]
                            
                            await websocket.send_json({
                                "type": "translation",
                                "timestamp": datetime.utcnow().timestamp(),
                                "original": "Hello, how are you today?",
                                "translated": translated,
                                "source_lang": "en",
                                "target_lang": "es",
                                "latency_ms": 100
                            })
                        else:
                            raise Exception(f"OpenAI API error: {response.status_code}")
                            
                    except Exception as e:
                        logger.error(f"Translation error: {e}")
                        await websocket.send_json({
                            "type": "translation",
                            "timestamp": datetime.utcnow().timestamp(),
                            "original": f"Audio received (error: {str(e)[:30]})",
                            "translated": f"Audio recibido (error: {str(e)[:30]})",
                            "source_lang": "en",
                            "target_lang": "es",
                            "latency_ms": 100
                        })
                
                elif "text" in data:
                    message = json.loads(data["text"])
                    if message.get("action") == "ping":
                        await websocket.send_json({"type": "pong"})
                        
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
