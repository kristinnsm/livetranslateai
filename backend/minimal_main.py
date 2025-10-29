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
participant_connections: Dict[str, WebSocket] = {}  # participant_id -> websocket
websocket_to_participant: Dict[int, str] = {}  # websocket_id (id(websocket)) -> participant_id (reverse lookup)

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
    
    # Create host participant
    host_participant_id = str(uuid.uuid4())[:8]
    host_participant = {
        "id": host_participant_id,
        "name": "Host",
        "source_lang": "en",
        "target_lang": "es"
    }
    
    rooms[room_id] = {
        "id": room_id,
        "created_at": datetime.utcnow().isoformat(),
        "participants": [host_participant],
        "active": True
    }
    active_connections[room_id] = []
    logger.info(f"🏠 Created room: {room_id} with host participant: {host_participant_id}")
    return {
        "room_id": room_id,
        "participant_id": host_participant_id,
        "status": "created"
    }

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
    
    current_participant_id = None  # Will be set when participant sends their ID
    
    logger.info(f"🏠 User joined room {room_id} (total: {len(active_connections[room_id])})")
    
    try:
        # Send room info to all participants
        logger.info(f"📢 Preparing to broadcast room update...")
        room_update_msg = {
            "type": "room_update",
            "room_id": room_id,
            "participant_count": len(active_connections[room_id]),
            "participants": rooms[room_id]["participants"]
        }
        logger.info(f"📢 Room update message: {room_update_msg}")
        await broadcast_to_room(room_id, room_update_msg)
        logger.info(f"✅ Room update broadcast complete, entering message receive loop...")
        
        while True:
            try:
                logger.info(f"🔍 Waiting for message in room {room_id}...")
                data = await websocket.receive()
                
                # Check for disconnect message
                if data.get("type") == "websocket.disconnect":
                    logger.info(f"👋 WebSocket disconnect message received in room {room_id}")
                    break
                
                logger.info(f"🔍 Received data in room {room_id}, type: {type(data)}, keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                
                if "bytes" in data:
                    # Handle audio data
                    audio_chunk = data["bytes"]
                    
                    # Identify speaker from WebSocket connection using id() as key
                    websocket_id = id(websocket)
                    speaker_id = websocket_to_participant.get(websocket_id)
                    logger.info(f"🔍 Looking up speaker for WebSocket {websocket_id} in room {room_id}")
                    logger.info(f"🔍 Total tracked WebSockets: {len(websocket_to_participant)}")
                    logger.info(f"🔍 Tracked participant IDs: {list(participant_connections.keys())}")
                    
                    if not speaker_id:
                        logger.warning(f"⚠️ Received audio from untracked participant in room {room_id} (WebSocket id: {websocket_id})")
                        # Try to use current_participant_id as fallback
                        speaker_id = current_participant_id
                        if speaker_id:
                            logger.warning(f"⚠️ Using fallback current_participant_id: {speaker_id}")
                        else:
                            logger.error(f"❌ No current_participant_id available either!")
                    
                    if speaker_id:
                        logger.info(f"🎤 Received audio from participant {speaker_id} in room {room_id}: {len(audio_chunk)} bytes")
                        # Process translation for OTHER participants only (exclude speaker)
                        await process_room_translation(room_id, audio_chunk, speaker_id)
                    else:
                        logger.error(f"❌ Cannot process audio - no participant_id associated with WebSocket {websocket_id} in room {room_id}")
                        logger.error(f"❌ Current participant_id: {current_participant_id}")
                        logger.error(f"❌ WebSocket id {websocket_id} not found in websocket_to_participant mapping")
                    
                elif "text" in data:
                    try:
                        message = json.loads(data["text"])
                        logger.info(f"📨 Received text message in room {room_id}: {message.get('action', 'unknown')}")
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse JSON message in room {room_id}: {e}")
                        logger.error(f"❌ Raw message: {data['text'][:100]}")
                        continue
                    
                    if message.get("action") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif message.get("action") == "set_language":
                        # Update participant language
                        participant_id = message.get("participant_id")
                        source_lang = message.get("source_lang", "en")
                        target_lang = message.get("target_lang", "es")
                        
                        # Track participant connection (bidirectional mapping)
                        if participant_id:
                            participant_connections[participant_id] = websocket
                            websocket_to_participant[id(websocket)] = participant_id  # Reverse lookup using id()
                            current_participant_id = participant_id
                            logger.info(f"🔗 Tracked participant {participant_id} connection (WebSocket id: {id(websocket)})")
                            logger.info(f"🔗 Total tracked participants: {len(participant_connections)}")
                            logger.info(f"🔗 All participant IDs: {list(participant_connections.keys())}")
                        else:
                            logger.warning("⚠️ No participant_id in set_language message")
                        
                        # Update participant in room (only if we have a participant_id)
                        if participant_id:
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
                logger.info(f"👋 WebSocket disconnected in room {room_id}")
                break
            except Exception as e:
                logger.error(f"❌ Room WebSocket error in room {room_id}: {e}", exc_info=True)
                try:
                    await websocket.close()
                except:
                    pass
                break
                
    except Exception as e:
        logger.error(f"Room WebSocket error: {e}")
    finally:
        # Clean up participant tracking
        websocket_id = id(websocket)
        if websocket_id in websocket_to_participant:
            participant_id = websocket_to_participant[websocket_id]
            if participant_id in participant_connections:
                del participant_connections[participant_id]
            del websocket_to_participant[websocket_id]
            logger.info(f"🧹 Cleaned up tracking for participant {participant_id}")
        
        # Remove connection from room
        if room_id in active_connections:
            active_connections[room_id] = [conn for conn in active_connections[room_id] if conn != websocket]
            logger.info(f"👋 User left room {room_id} (remaining: {len(active_connections[room_id])})")

async def process_room_translation(room_id: str, audio_chunk: bytes, speaker_id: str):
    """Process translation for room and send to listeners (exclude speaker)"""
    try:
        start_time = time.time()
        
        # Get room participants and their language settings
        if room_id not in rooms:
            logger.error(f"Room {room_id} not found")
            return
        
        participants = rooms[room_id]["participants"]
        logger.info(f"👥 Processing translations for room {room_id} (speaker: {speaker_id}, {len(participants)} total participants)")
        
        # Find speaker participant to get their source language
        speaker_participant = None
        for p in participants:
            if p["id"] == speaker_id:
                speaker_participant = p
                break
        
        if not speaker_participant:
            logger.error(f"Speaker {speaker_id} not found in room participants")
            return
        
        speaker_source_lang = speaker_participant.get("source_lang", "en")
        logger.info(f"🎤 Speaker {speaker_id} is speaking in {speaker_source_lang}")
        
        # Step 1: Transcribe audio ONCE in the speaker's language
        whisper_start = time.time()
        logger.info(f"📝 Transcribing audio in {speaker_source_lang} (speaker's language)...")
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
                "language": speaker_source_lang,  # Use speaker's source language
                "response_format": "json"
            },
            timeout=10
        )
        
        if whisper_response.status_code != 200:
            logger.error(f"Whisper failed: {whisper_response.status_code} - {whisper_response.text}")
            return
        
        transcription = whisper_response.json().get("text", "").strip()
        whisper_time = int((time.time() - whisper_start) * 1000)
        logger.info(f"✅ Transcription: '{transcription}' ({whisper_time}ms)")
        
        if not transcription:
            logger.warning(f"Empty transcription - no speech detected")
            return
        
        # Step 2: Process translation for each listener (EXCLUDE the speaker)
        listeners = [p for p in participants if p["id"] != speaker_id]
        logger.info(f"👂 Translating for {len(listeners)} listeners...")
        
        if len(listeners) == 0:
            logger.warning(f"⚠️ No listeners found for room {room_id} (all participants might be the speaker)")
            return
        
        for listener in listeners:
            logger.info(f"👂 Processing listener: {listener.get('name', listener['id'])} (id: {listener['id']})")
            try:
                target_lang = listener.get("target_lang", "es")
                
                # Skip if target language is same as speaker's source (no translation needed)
                if target_lang == speaker_source_lang:
                    logger.info(f"⏭️ Skipping {listener['name']} - target matches speaker's language")
                    continue
                
                logger.info(f"🌍 Translating for {listener['name']}: {speaker_source_lang} → {target_lang}")
                
                # Step 2a: Translate with GPT-3.5-turbo
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
                            {"role": "user", "content": f"Translate from {speaker_source_lang} to {target_lang}:\n{transcription}"}
                        ],
                        "max_tokens": 200,
                        "temperature": 0,
                    },
                    timeout=4
                )
                
                if translation_response.status_code != 200:
                    logger.error(f"Translation failed for {listener['name']}: {translation_response.status_code}")
                    continue
                
                translated = translation_response.json()["choices"][0]["message"]["content"].strip()
                translation_time = int((time.time() - translation_start) * 1000)
                logger.info(f"✅ Translation for {listener['name']}: '{translated}' ({translation_time}ms)")
                
                # Step 2b: Generate TTS audio
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
                    logger.info(f"✅ TTS for {listener['name']}: {len(tts_response.content)} bytes ({tts_time}ms)")
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Send translation to this specific listener
                await send_to_participant(room_id, listener["id"], {
                    "type": "translation",
                    "timestamp": datetime.utcnow().timestamp(),
                    "original": transcription,
                    "translated": translated,
                    "source_lang": speaker_source_lang,
                    "target_lang": target_lang,
                    "latency_ms": latency_ms,
                    "audio_base64": audio_base64
                })
                
            except Exception as e:
                logger.error(f"❌ Translation error for {listener['name']}: {e}")
        
    except Exception as e:
        logger.error(f"❌ Room translation error: {e}")
        await broadcast_to_room(room_id, {
            "type": "error",
            "message": f"Translation failed: {str(e)}"
        })

async def send_to_participant(room_id: str, participant_id: str, message: dict):
    """Send message to a specific participant in a room"""
    logger.info(f"📤 Attempting to send translation to participant {participant_id} in room {room_id}")
    logger.info(f"📤 Available participant connections: {list(participant_connections.keys())}")
    
    if participant_id not in participant_connections:
        logger.warning(f"⚠️ Participant {participant_id} not found in connections (available: {list(participant_connections.keys())})")
        return
    
    try:
        # Add participant ID to message for frontend filtering
        message["target_participant"] = participant_id
        websocket = participant_connections[participant_id]
        logger.info(f"📤 Sending translation to participant {participant_id}: {message.get('original', '')[:50]}... → {message.get('translated', '')[:50]}...")
        await websocket.send_json(message)
        logger.info(f"✅ Successfully sent translation message to participant {participant_id}")
    except Exception as e:
        logger.error(f"❌ Failed to send to participant {participant_id}: {e}", exc_info=True)
        # Remove dead connection
        if participant_id in participant_connections:
            del participant_connections[participant_id]
            # Also remove from reverse mapping
            websocket_id_to_remove = None
            for ws_id, pid in websocket_to_participant.items():
                if pid == participant_id:
                    websocket_id_to_remove = ws_id
                    break
            if websocket_id_to_remove:
                del websocket_to_participant[websocket_id_to_remove]

async def broadcast_to_room(room_id: str, message: dict):
    """Broadcast message to all participants in a room"""
    logger.info(f"📢 broadcast_to_room called for room {room_id}")
    if room_id not in active_connections:
        logger.warning(f"⚠️ Room {room_id} not in active_connections")
        return
    
    connections = active_connections[room_id]
    logger.info(f"📢 Broadcasting to {len(connections)} connections in room {room_id}")
    
    for i, connection in enumerate(connections):
        try:
            logger.info(f"📢 Sending message to connection {i+1}/{len(connections)}")
            await connection.send_json(message)
            logger.info(f"✅ Successfully sent message to connection {i+1}")
        except Exception as e:
            logger.error(f"❌ Failed to send to room participant {i+1}: {e}", exc_info=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
