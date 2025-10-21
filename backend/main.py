"""
LiveTranslateAI Backend - Real-Time AI Voice Translator for Business
FastAPI server with WebSocket support for audio streaming
Supports both OpenAI Realtime API and traditional pipeline
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

from services.audio_processor import AudioProcessor
from services.translator_realtime import RealtimeTranslator
from services.translator_traditional import TraditionalTranslator
from services.buffer_manager import BufferManager
from utils.logger import setup_logger

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_REALTIME_API = os.getenv("USE_REALTIME_API", "true").lower() == "true"
MAX_BUFFER_DURATION = int(os.getenv("MAX_BUFFER_DURATION", "300"))  # 5 minutes

# Setup
app = FastAPI(title="LiveTranslateAI API", version="1.0.0")
logger = setup_logger(__name__)

# CORS - production ready
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://livetranslateai.com",
        "https://www.livetranslateai.com", 
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
    
    mode = "Realtime API" if USE_REALTIME_API else "Traditional Pipeline"
    logger.info(f"[STARTUP] LiveTranslateAI starting in {mode} mode")
    logger.info(f"[CONFIG] Max buffer duration: {MAX_BUFFER_DURATION}s")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "LiveTranslateAI",
        "status": "running",
        "mode": "realtime" if USE_REALTIME_API else "traditional",
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
            "mode": "realtime" if USE_REALTIME_API else "traditional"
        }
    )


@app.websocket("/ws/translate")
async def websocket_translate(websocket: WebSocket):
    logger.info("[WEBSOCKET] WebSocket endpoint /ws/translate accessed")
    logger.info(f"[WEBSOCKET] Client: {websocket.client}")
    """
    Main WebSocket endpoint for real-time translation
    Handles audio streaming, translation, and buffer management
    """
    await websocket.accept()
    logger.info("[WEBSOCKET] WebSocket connection accepted")
    
    session_id = f"session_{datetime.utcnow().timestamp()}"
    
    # Initialize session
    buffer_manager = BufferManager(max_duration=MAX_BUFFER_DURATION)
    audio_processor = AudioProcessor()
    
    # Choose translator based on config
    if USE_REALTIME_API:
        translator = RealtimeTranslator(api_key=OPENAI_API_KEY)
    else:
        translator = TraditionalTranslator(api_key=OPENAI_API_KEY)
    
    active_sessions[session_id] = {
        "buffer": buffer_manager,
        "processor": audio_processor,
        "translator": translator,
        "connected_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"[SESSION] New session: {session_id}")
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "mode": "realtime" if USE_REALTIME_API else "traditional",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Main message loop
        while True:
            try:
                # Receive message (audio chunk or control command)
                data = await websocket.receive()
                logger.info(f"[WS_MSG] Received WebSocket message: type={type(data)}, keys={list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                
                # Check for disconnect
                if data.get("type") == "websocket.disconnect":
                    logger.info(f"[WS_DISCONNECT] Client requested disconnect: {data}")
                    break
                
                if "bytes" in data:
                    # Audio chunk received
                    audio_chunk = data["bytes"]
                    timestamp = datetime.utcnow().timestamp()
                    
                    logger.info(f"[AUDIO_CHUNK] Received audio chunk: {len(audio_chunk)} bytes, timestamp: {timestamp}")
                    
                    # Skip tiny chunks (less than 0.05 seconds at 16kHz)
                    min_chunk_size = 16000 * 2 * 0.05  # 0.05 seconds of 16-bit PCM
                    if len(audio_chunk) < min_chunk_size:
                        logger.debug(f"Skipping tiny chunk: {len(audio_chunk)} bytes")
                        continue
                    
                    # Process audio through pipeline
                    await process_audio_chunk(
                        websocket=websocket,
                        session_id=session_id,
                        audio_chunk=audio_chunk,
                        timestamp=timestamp
                    )
                    
                elif "text" in data:
                    # Control message (JSON)
                    message = json.loads(data["text"])
                    await handle_control_message(
                        websocket=websocket,
                        session_id=session_id,
                        message=message
                    )
                    
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
                    # WebSocket might be closed, just log and continue
                    logger.warning("Could not send error message - WebSocket closed")
                    break
    
    finally:
        # Cleanup session
        if session_id in active_sessions:
            # Clear buffers for privacy
            active_sessions[session_id]["buffer"].clear()
            del active_sessions[session_id]
            logger.info(f"[CLEANUP] Session cleaned up: {session_id}")


async def process_audio_chunk(
    websocket: WebSocket,
    session_id: str,
    audio_chunk: bytes,
    timestamp: float
):
    """Process incoming audio chunk through translation pipeline"""
    try:
        session = active_sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for audio processing")
            return
        
        processor = session["processor"]
        translator = session["translator"]
        buffer_manager = session["buffer"]
        
        # VAD check (skip silent chunks)
        if not processor.is_speech(audio_chunk):
            logger.debug(f"Skipping silent chunk: {len(audio_chunk)} bytes")
            return
        
        logger.info(f"Processing audio chunk: {len(audio_chunk)} bytes")
        logger.info(f"[DEBUG] Translator type: {type(translator)}, has process_audio: {hasattr(translator, 'process_audio')}")
        
        # Send "processing" status to keep WebSocket alive
        async def send_heartbeat():
            try:
                await websocket.send_json({"type": "status", "message": "processing"})
                logger.debug("Sent heartbeat to keep connection alive")
            except:
                pass
        
        # Add to processing queue
        logger.info("[DEBUG] About to call translator.process_audio")
        result = await translator.process_audio(audio_chunk, timestamp, heartbeat_callback=send_heartbeat)
        logger.info(f"[DEBUG] Translator returned: {result is not None}")
        
        if result:
            # Buffer for replay
            buffer_manager.add_segment(
                timestamp=timestamp,
                original_text=result.get("original_text", ""),
                translated_text=result.get("translated_text", ""),
                audio_data=result.get("audio_data"),
                source_lang=result.get("source_lang", ""),
                target_lang=result.get("target_lang", "")
            )
            
            # Check if WebSocket is still open before sending
            if websocket.client_state.name != "CONNECTED":
                logger.warning("WebSocket closed - cannot send result")
                return
            
            # Send to client
            await websocket.send_json({
                "type": "translation",
                "timestamp": timestamp,
                "original": result.get("original_text"),
                "translated": result.get("translated_text"),
                "source_lang": result.get("source_lang"),
                "target_lang": result.get("target_lang"),
                "latency_ms": result.get("latency_ms", 0)
            })
            
            # Send audio if available
            if result.get("audio_data"):
                await websocket.send_bytes(result["audio_data"])
                
            logger.info(f"Translation sent successfully: {result.get('original_text', '')[:30]}...")
        else:
            logger.warning("No translation result - skipping")
            
    except Exception as e:
        logger.error(f"Error processing audio chunk: {e}", exc_info=True)
        # Don't close the WebSocket - just log the error and continue
        try:
            await websocket.send_json({
                "type": "error", 
                "message": f"Audio processing error: {str(e)}"
            })
        except:
            pass  # WebSocket might already be closed


async def handle_control_message(
    websocket: WebSocket,
    session_id: str,
    message: dict
):
    """Handle control messages (replay, language change, etc.)"""
    action = message.get("action")
    session = active_sessions.get(session_id)
    
    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        return
    
    if action == "replay":
        # Generate replay with subtitles
        duration = message.get("duration", 60)
        await generate_replay(websocket, session_id, duration)
    
    elif action == "set_language":
        # Update target language
        source_lang = message.get("source_lang", "en")
        target_lang = message.get("target_lang", "es")
        session["translator"].set_languages(source_lang, target_lang)
        await websocket.send_json({
            "type": "language_updated",
            "source_lang": source_lang,
            "target_lang": target_lang
        })
    
    elif action == "ping":
        # Heartbeat
        await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
    
    else:
        await websocket.send_json({"type": "error", "message": f"Unknown action: {action}"})


async def generate_replay(websocket: WebSocket, session_id: str, duration: int):
    """Generate replay with concatenated audio and WebVTT subtitles"""
    session = active_sessions.get(session_id)
    if not session:
        return
    
    buffer_manager = session["buffer"]
    
    # Get segments from buffer
    segments = buffer_manager.get_segments(last_n_seconds=duration)
    
    if not segments:
        await websocket.send_json({
            "type": "replay_error",
            "message": "No segments available for replay"
        })
        return
    
    # Generate concatenated audio and VTT
    audio_data, vtt_data = buffer_manager.export_replay(segments)
    
    # Send replay package
    await websocket.send_json({
        "type": "replay_ready",
        "duration": duration,
        "segments_count": len(segments),
        "vtt": vtt_data
    })
    
    # Send audio data
    if audio_data:
        await websocket.send_bytes(audio_data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

