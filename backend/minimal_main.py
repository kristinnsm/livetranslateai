"""
Minimal LiveTranslateAI Backend - Ultra-simple version for deployment
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
import uuid
import time
import base64
import io
import requests
from datetime import datetime
from typing import Dict, List
import os

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Setup
app = FastAPI(title="LiveTranslateAI API", version="1.0.0")
logger = logging.getLogger(__name__)

# Room management
rooms: Dict[str, Dict] = {}
active_connections: Dict[str, List[WebSocket]] = {}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000", 
        "https://livetranslateai.netlify.app",
        "https://app.livetranslateai.com",
        "https://livetranslateai.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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

# Room management endpoints
@app.post("/api/rooms/create")
async def create_room():
    """Create a new translation room"""
    logger.info("🏠 POST /api/rooms/create - Creating new room")
    room_id = str(uuid.uuid4())[:8].upper()  # Short room code
    rooms[room_id] = {
        "id": room_id,
        "created_at": datetime.utcnow().isoformat(),
        "participants": [],
        "active": True
    }
    active_connections[room_id] = []
    logger.info(f"🏠 Created room: {room_id}")
    return {"room_id": room_id, "status": "created"}

@app.get("/api/rooms/{room_id}")
async def get_room(room_id: str):
    """Get room information"""
    logger.info(f"🔍 GET /api/rooms/{room_id} - room_id: {room_id}")
    if room_id not in rooms:
        logger.warning(f"❌ Room {room_id} not found")
        return {"error": "Room not found"}, 404
    
    room = rooms[room_id].copy()
    room["participant_count"] = len(active_connections.get(room_id, []))
    return room

@app.post("/api/rooms/{room_id}/join")
async def join_room(room_id: str, request: Request):
    """Join an existing room"""
    if room_id not in rooms:
        return {"error": "Room not found"}, 404
    
    if not rooms[room_id]["active"]:
        return {"error": "Room is not active"}, 400
    
    # Parse request body
    body = await request.json()
    participant_name = body.get("participant_name", "Anonymous")
    
    # Add participant to room
    participant_id = str(uuid.uuid4())[:8]
    participant = {
        "id": participant_id,
        "name": participant_name,
        "joined_at": datetime.utcnow().isoformat(),
        "source_lang": "en",
        "target_lang": "es"
    }
    
    rooms[room_id]["participants"].append(participant)
    logger.info(f"👤 {participant_name} joined room {room_id}")
    
    return {"participant_id": participant_id, "status": "joined"}

@app.post("/api/rooms/{room_id}/leave")
async def leave_room(room_id: str, participant_id: str):
    """Leave a room"""
    if room_id not in rooms:
        return {"error": "Room not found"}, 404
    
    # Remove participant
    rooms[room_id]["participants"] = [
        p for p in rooms[room_id]["participants"] 
        if p["id"] != participant_id
    ]
    
    logger.info(f"👋 Participant {participant_id} left room {room_id}")
    return {"status": "left"}

@app.websocket("/ws/translate/realtime")
async def websocket_translate_realtime(websocket: WebSocket):
    """
    Realtime translation using OpenAI Realtime API
    Ultra-low latency (300-1000ms)
    """
    await websocket.accept()
    logger.info("🔥 Realtime WebSocket connected")
    
    try:
        from services.translator_realtime import handle_realtime_translation
        await handle_realtime_translation(websocket)
    except Exception as e:
        logger.error(f"❌ Realtime translation error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Realtime API failed: {str(e)}"
        })
    finally:
        logger.info("🔌 Realtime WebSocket closed")

@app.websocket("/ws/translate")
async def websocket_translate(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")
    
    # Default language settings
    source_lang = "en"
    target_lang = "es"
    
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
                        whisper_start = time.time()
                        
                        # Step 1: Transcribe audio with Whisper (optimized)
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
                                "language": source_lang,  # Use selected source language
                                "response_format": "json"  # Explicit format
                            },
                            timeout=10  # Whisper is usually done in 2-4s
                        )
                        
                        if whisper_response.status_code != 200:
                            raise Exception(f"Whisper failed: {whisper_response.status_code} - {whisper_response.text}")
                        
                        transcription = whisper_response.json().get("text", "").strip()
                        whisper_time = int((time.time() - whisper_start) * 1000)
                        logger.info(f"✅ Transcription: '{transcription}' ({whisper_time}ms)")
                        
                        if not transcription:
                            raise Exception("Empty transcription - no speech detected")
                        
                        # Step 2: Translate with GPT-4o (ultra-fast)
                        translation_start = time.time()
                        logger.info("🌍 Starting translation...")
                        
                        # Use minimal system message for fastest response
                        translation_response = requests.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {OPENAI_API_KEY}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "gpt-3.5-turbo",  # 5x faster than GPT-4o for simple translations
                                "messages": [
                                    {"role": "user", "content": f"Translate from {source_lang} to {target_lang}:\n{transcription}"}
                                ],
                                "max_tokens": 200,
                                "temperature": 0,
                            },
                            timeout=4  # Much faster model
                        )
                        
                        if translation_response.status_code != 200:
                            raise Exception(f"Translation failed: {translation_response.status_code}")
                        
                        translated = translation_response.json()["choices"][0]["message"]["content"].strip()
                        translation_time = int((time.time() - translation_start) * 1000)
                        logger.info(f"✅ Translation: '{translated}' ({translation_time}ms)")
                        
                        # Step 3: Generate TTS audio (ultra-optimized)
                        tts_start = time.time()
                        logger.info("🔊 Starting TTS audio generation...")
                        tts_response = requests.post(
                            "https://api.openai.com/v1/audio/speech",
                            headers={
                                "Authorization": f"Bearer {OPENAI_API_KEY}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "tts-1",
                                "voice": "alloy",  # Fastest voice
                                "input": translated[:500],  # Limit to 500 chars for speed
                                "response_format": "opus",
                                "speed": 1.05  # Slightly faster (barely noticeable)
                            },
                            timeout=10
                        )
                        
                        if tts_response.status_code != 200:
                            logger.warning(f"TTS failed: {tts_response.status_code}")
                            audio_base64 = None
                        else:
                            # Convert audio to base64 for sending via WebSocket
                            import base64
                            audio_base64 = base64.b64encode(tts_response.content).decode('utf-8')
                            tts_time = int((time.time() - tts_start) * 1000)
                            logger.info(f"✅ TTS audio generated: {len(tts_response.content)} bytes ({tts_time}ms)")
                        
                        latency_ms = int((time.time() - start_time) * 1000)
                        logger.info(f"⏱️ Total latency: {latency_ms}ms (Whisper: {whisper_time}ms | Translation: {translation_time}ms | TTS: {tts_time if tts_response.status_code == 200 else 0}ms)")
                        
                        await websocket.send_json({
                            "type": "translation",
                            "timestamp": datetime.utcnow().timestamp(),
                            "original": transcription,
                            "translated": translated,
                            "source_lang": source_lang,
                            "target_lang": target_lang,
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
                    elif message.get("action") == "set_language":
                        source_lang = message.get("source_lang", "en")
                        target_lang = message.get("target_lang", "es")
                        logger.info(f"Language settings updated: {source_lang} → {target_lang}")
                        
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@app.websocket("/ws/room/{room_id}")
async def websocket_room(websocket: WebSocket, room_id: str):
    """Multi-user room WebSocket for translation"""
    await websocket.accept()
    
    if room_id not in rooms:
        await websocket.close(code=1000, reason="Room not found")
        return
    
    # Add connection to room
    if room_id not in active_connections:
        active_connections[room_id] = []
    active_connections[room_id].append(websocket)
    
    logger.info(f"🏠 User joined room {room_id} (total: {len(active_connections[room_id])})")
    
    try:
        # Send room info to all participants
        await broadcast_to_room(room_id, {
            "type": "room_update",
            "room_id": room_id,
            "participant_count": len(active_connections[room_id]),
            "participants": rooms[room_id]["participants"]
        })
        
        while True:
            try:
                data = await websocket.receive()
                logger.info(f"🔍 Received data type: {type(data)}, keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                
                if "bytes" in data:
                    # Handle audio data
                    audio_chunk = data["bytes"]
                    logger.info(f"🎤 Received audio in room {room_id}: {len(audio_chunk)} bytes")
                    logger.info(f"🎤 Audio chunk type: {type(audio_chunk)}, first 10 bytes: {audio_chunk[:10]}")
                    
                    # Process translation and broadcast to all participants
                    await process_room_translation(room_id, audio_chunk)
                    
                elif "text" in data:
                    message = json.loads(data["text"])
                    
                    if message.get("action") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif message.get("action") == "set_language":
                        # Update participant language
                        participant_id = message.get("participant_id")
                        source_lang = message.get("source_lang", "en")
                        target_lang = message.get("target_lang", "es")
                        
                        # Update participant in room
                        for participant in rooms[room_id]["participants"]:
                            if participant["id"] == participant_id:
                                participant["source_lang"] = source_lang
                                participant["target_lang"] = target_lang
                                break
                        
                        logger.info(f"🌍 Room {room_id}: Participant {participant_id} set language {source_lang} → {target_lang}")
                        
                        # Broadcast language update
                        await broadcast_to_room(room_id, {
                            "type": "language_update",
                            "participant_id": participant_id,
                            "source_lang": source_lang,
                            "target_lang": target_lang
                        })
                        
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Room WebSocket error: {e}")
                break
                
    except Exception as e:
        logger.error(f"Room WebSocket error: {e}")
    finally:
        # Remove connection from room
        if room_id in active_connections:
            active_connections[room_id] = [conn for conn in active_connections[room_id] if conn != websocket]
            logger.info(f"👋 User left room {room_id} (remaining: {len(active_connections[room_id])})")

async def process_room_translation(room_id: str, audio_chunk: bytes):
    """Process translation for room and broadcast to all participants"""
    try:
        start_time = time.time()
        
        # Get room participants and their language settings
        if room_id not in rooms:
            logger.error(f"Room {room_id} not found")
            return
        
        participants = rooms[room_id]["participants"]
        logger.info(f"👥 Processing translations for {len(participants)} participants")
        
        # Process translation for each participant
        for participant in participants:
            try:
                source_lang = participant.get("source_lang", "en")
                target_lang = participant.get("target_lang", "es")
                
                logger.info(f"🌍 Translating for {participant['name']}: {source_lang} → {target_lang}")
                
                # Skip if source and target are the same (no translation needed)
                if source_lang == target_lang:
                    logger.info(f"⏭️ Skipping {participant['name']} - same source and target language")
                    continue
                
                # Step 1: Transcribe audio with Whisper (using participant's source language)
                whisper_start = time.time()
                logger.info(f"📝 Starting Whisper transcription in {source_lang} for {participant['name']}...")
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
                        "language": source_lang,  # Use participant's source language
                        "response_format": "json"
                    },
                    timeout=10
                )
                
                if whisper_response.status_code != 200:
                    logger.error(f"Whisper failed for {participant['name']}: {whisper_response.status_code}")
                    continue
                
                transcription = whisper_response.json().get("text", "").strip()
                whisper_time = int((time.time() - whisper_start) * 1000)
                logger.info(f"✅ Transcription for {participant['name']}: '{transcription}' ({whisper_time}ms)")
                
                if not transcription:
                    logger.warning(f"Empty transcription for {participant['name']} - no speech detected")
                    continue
                
                # Step 2: Translate with GPT-3.5-turbo
                translation_start = time.time()
                translation_response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "user", "content": f"Translate from {source_lang} to {target_lang}:\n{transcription}"}
                        ],
                        "max_tokens": 200,
                        "temperature": 0,
                    },
                    timeout=4
                )
                
                if translation_response.status_code != 200:
                    logger.error(f"Translation failed for {participant['name']}: {translation_response.status_code}")
                    continue
                
                translated = translation_response.json()["choices"][0]["message"]["content"].strip()
                translation_time = int((time.time() - translation_start) * 1000)
                logger.info(f"✅ Translation for {participant['name']}: '{translated}' ({translation_time}ms)")
                
                # Step 3: Generate TTS audio
                tts_start = time.time()
                tts_response = requests.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "tts-1",
                        "voice": "alloy",
                        "input": translated[:500],
                        "response_format": "opus",
                        "speed": 1.05
                    },
                    timeout=10
                )
                
                audio_base64 = None
                if tts_response.status_code == 200:
                    audio_base64 = base64.b64encode(tts_response.content).decode('utf-8')
                    tts_time = int((time.time() - tts_start) * 1000)
                    logger.info(f"✅ TTS for {participant['name']}: {len(tts_response.content)} bytes ({tts_time}ms)")
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Send translation to this specific participant
                await send_to_participant(room_id, participant["id"], {
                    "type": "translation",
                    "timestamp": datetime.utcnow().timestamp(),
                    "original": transcription,
                    "translated": translated,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "latency_ms": latency_ms,
                    "audio_base64": audio_base64
                })
                
            except Exception as e:
                logger.error(f"❌ Translation error for {participant['name']}: {e}")
        
    except Exception as e:
        logger.error(f"❌ Room translation error: {e}")
        await broadcast_to_room(room_id, {
            "type": "error",
            "message": f"Translation failed: {str(e)}"
        })

async def send_to_participant(room_id: str, participant_id: str, message: dict):
    """Send message to a specific participant in a room"""
    if room_id not in active_connections:
        return
    
    # For now, send to all participants (we'll need to track participant IDs properly later)
    for connection in active_connections[room_id]:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send to participant {participant_id}: {e}")

async def broadcast_to_room(room_id: str, message: dict):
    """Broadcast message to all participants in a room"""
    if room_id not in active_connections:
        return
    
    for connection in active_connections[room_id]:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send to room participant: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
