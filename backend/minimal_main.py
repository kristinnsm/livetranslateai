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
            "session_id": "minimal-session-001",
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
                    
                    # Real translation pipeline: Whisper STT → GPT Translation
                    try:
                        import requests
                        import io
                        import time
                        
                        start_time = time.time()
                        
                        # Step 1: Transcribe audio with Whisper
                        logger.info("📝 Starting Whisper transcription...")
                        whisper_response = requests.post(
                            "https://api.openai.com/v1/audio/transcriptions",
                            headers={
                                "Authorization": f"Bearer {OPENAI_API_KEY}"
                            },
                            files={
                                "file": ("audio.webm", io.BytesIO(audio_chunk), "audio/webm")
                            },
                            data={
                                "model": "whisper-1",
                                "language": "en"
                            },
                            timeout=30
                        )
                        
                        if whisper_response.status_code != 200:
                            raise Exception(f"Whisper failed: {whisper_response.status_code} - {whisper_response.text}")
                        
                        transcription = whisper_response.json().get("text", "").strip()
                        logger.info(f"✅ Transcription: '{transcription}'")
                        
                        if not transcription:
                            raise Exception("Empty transcription - no speech detected")
                        
                        # Step 2: Translate with GPT-4o-mini
                        logger.info("🌍 Starting translation...")
                        translation_response = requests.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {OPENAI_API_KEY}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "gpt-4o-mini",
                                "messages": [
                                    {"role": "system", "content": "You are a professional translator. Translate the following text from English to Spanish. Only return the translation, nothing else."},
                                    {"role": "user", "content": transcription}
                                ],
                                "max_tokens": 200,
                                "temperature": 0.3
                            },
                            timeout=15
                        )
                        
                        if translation_response.status_code != 200:
                            raise Exception(f"Translation failed: {translation_response.status_code}")
                        
                        translated = translation_response.json()["choices"][0]["message"]["content"].strip()
                        logger.info(f"✅ Translation: '{translated}'")
                        
                        # Step 3: Generate TTS audio
                        logger.info("🔊 Starting TTS audio generation...")
                        tts_response = requests.post(
                            "https://api.openai.com/v1/audio/speech",
                            headers={
                                "Authorization": f"Bearer {OPENAI_API_KEY}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "tts-1",
                                "voice": "nova",
                                "input": translated,
                                "response_format": "mp3"
                            },
                            timeout=30
                        )
                        
                        if tts_response.status_code != 200:
                            logger.warning(f"TTS failed: {tts_response.status_code}")
                            audio_base64 = None
                        else:
                            # Convert audio to base64 for sending via WebSocket
                            import base64
                            audio_base64 = base64.b64encode(tts_response.content).decode('utf-8')
                            logger.info(f"✅ TTS audio generated: {len(tts_response.content)} bytes")
                        
                        latency_ms = int((time.time() - start_time) * 1000)
                        logger.info(f"⏱️ Total latency: {latency_ms}ms")
                        
                        await websocket.send_json({
                            "type": "translation",
                            "timestamp": datetime.utcnow().timestamp(),
                            "original": transcription,
                            "translated": translated,
                            "source_lang": "en",
                            "target_lang": "es",
                            "latency_ms": latency_ms,
                            "audio_base64": audio_base64
                        })
                            
                    except Exception as e:
                        logger.error(f"❌ Translation error: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Translation failed: {str(e)}"
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
