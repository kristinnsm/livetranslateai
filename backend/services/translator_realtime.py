"""
OpenAI Realtime API Integration for LiveTranslateAI
Ultra-low latency streaming translation (300-1000ms)
"""

import asyncio
import json
import logging
import os
import base64
from datetime import datetime
import websockets
from fastapi import WebSocketDisconnect

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REALTIME_API_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

class RealtimeTranslator:
    """
    OpenAI Realtime API translator with streaming audio translation
    """
    
    def __init__(self, client_ws):
        self.client_ws = client_ws
        self.openai_ws = None
        self.session_id = None
        self.is_running = False
        self.original_transcript = ""
        self.translated_text = ""
        
    async def connect(self):
        """Connect to OpenAI Realtime API"""
        try:
            logger.info("🔌 Connecting to OpenAI Realtime API...")
            logger.info(f"URL: {REALTIME_API_URL}")
            logger.info(f"API Key configured: {bool(OPENAI_API_KEY)}")
            
            # Connect with API key in header
            self.openai_ws = await websockets.connect(
                REALTIME_API_URL,
                extra_headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "OpenAI-Beta": "realtime=v1"
                }
            )
            
            logger.info("✅ Connected to OpenAI Realtime API")
            
            # Configure session for translation
            await self.configure_session()
            
            self.is_running = True
            
            # Notify client of successful connection
            await self.client_ws.send_json({
                "type": "status",
                "message": "Connected to Realtime API"
            })
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Realtime API: {e}", exc_info=True)
            # Send error to client
            await self.client_ws.send_json({
                "type": "error",
                "message": f"Failed to connect to Realtime API: {str(e)}"
            })
            raise
    
    async def configure_session(self):
        """Configure the Realtime API session for translation"""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": (
                    "You are a professional real-time translator for business calls. "
                    "When you receive English speech, immediately translate it to Spanish. "
                    "Maintain the tone, formality, and meaning of the original. "
                    "Be concise and natural. Only respond with the translation."
                ),
                "voice": "alloy",  # Nova not available yet, using alloy
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",  # Voice Activity Detection
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "temperature": 0.6,
                "max_response_output_tokens": 4096
            }
        }
        
        await self.openai_ws.send(json.dumps(config))
        logger.info("📝 Session configured for English→Spanish translation")
    
    async def send_audio(self, audio_chunk: bytes):
        """Send audio chunk to Realtime API"""
        try:
            # Convert WebM to PCM16 (required by Realtime API)
            # For now, we'll send the raw audio - TODO: Add proper conversion
            audio_base64 = base64.b64encode(audio_chunk).decode('utf-8')
            
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            
            await self.openai_ws.send(json.dumps(message))
            logger.info(f"📤 Sent audio chunk: {len(audio_chunk)} bytes")
            
        except Exception as e:
            logger.error(f"❌ Error sending audio: {e}")
    
    async def commit_audio(self):
        """Commit the audio buffer and trigger response"""
        try:
            message = {
                "type": "input_audio_buffer.commit"
            }
            await self.openai_ws.send(json.dumps(message))
            
            # Create a response
            response_message = {
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "instructions": "Translate to Spanish"
                }
            }
            await self.openai_ws.send(json.dumps(response_message))
            
            logger.info("✅ Audio committed, waiting for translation...")
            
        except Exception as e:
            logger.error(f"❌ Error committing audio: {e}")
    
    async def handle_realtime_events(self):
        """Handle incoming events from OpenAI Realtime API"""
        try:
            async for message in self.openai_ws:
                event = json.loads(message)
                event_type = event.get("type")
                
                # Log all events for debugging
                logger.info(f"📨 Received event: {event_type}")
                
                if event_type == "session.created":
                    self.session_id = event.get("session", {}).get("id")
                    logger.info(f"🎉 Session created: {self.session_id}")
                    
                    # Notify client
                    await self.client_ws.send_json({
                        "type": "connected",
                        "session_id": self.session_id,
                        "mode": "realtime",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif event_type == "session.updated":
                    logger.info("✅ Session updated successfully")
                
                elif event_type == "input_audio_buffer.speech_started":
                    logger.info("🎤 Speech detected")
                    await self.client_ws.send_json({
                        "type": "status",
                        "message": "Speech detected..."
                    })
                
                elif event_type == "input_audio_buffer.speech_stopped":
                    logger.info("🛑 Speech ended")
                
                elif event_type == "conversation.item.created":
                    item = event.get("item", {})
                    logger.info(f"💬 Conversation item: {item.get('type')}")
                
                elif event_type == "response.audio_transcript.delta":
                    # Streaming transcription
                    delta = event.get("delta", "")
                    logger.info(f"📝 Transcript delta: {delta}")
                
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # Original audio transcription completed
                    transcript = event.get("transcript", "")
                    self.original_transcript = transcript
                    logger.info(f"📝 Original transcript: {transcript}")
                
                elif event_type == "response.audio_transcript.done":
                    # Complete translated transcription
                    transcript = event.get("transcript", "")
                    self.translated_text = transcript
                    logger.info(f"✅ Translation transcript: {transcript}")
                
                elif event_type == "response.audio.delta":
                    # Streaming audio output
                    audio_delta = event.get("delta", "")
                    if audio_delta:
                        # Send audio chunk to client
                        await self.client_ws.send_json({
                            "type": "audio_delta",
                            "audio": audio_delta
                        })
                
                elif event_type == "response.audio.done":
                    logger.info("✅ Audio generation complete")
                
                elif event_type == "response.done":
                    # Full response complete
                    logger.info("✅ Response complete")
                    
                    # Send final translation with both original and translated text
                    await self.client_ws.send_json({
                        "type": "translation",
                        "timestamp": datetime.utcnow().timestamp(),
                        "original": self.original_transcript or "Realtime transcription",
                        "translated": self.translated_text or "Translation in progress...",
                        "source_lang": "en",
                        "target_lang": "es",
                        "latency_ms": 0  # Real-time, no need to track
                    })
                    
                    # Reset for next translation
                    self.original_transcript = ""
                    self.translated_text = ""
                
                elif event_type == "error":
                    error = event.get("error", {})
                    logger.error(f"❌ OpenAI error: {error}")
                    
                    await self.client_ws.send_json({
                        "type": "error",
                        "message": f"Realtime API error: {error.get('message')}"
                    })
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 OpenAI connection closed")
        except Exception as e:
            logger.error(f"❌ Error handling events: {e}")
    
    async def close(self):
        """Close the connection"""
        self.is_running = False
        if self.openai_ws:
            await self.openai_ws.close()
            logger.info("🔌 Disconnected from OpenAI Realtime API")


async def handle_realtime_translation(client_ws):
    """
    Main handler for realtime translation via OpenAI Realtime API
    """
    translator = RealtimeTranslator(client_ws)
    
    try:
        # Connect to OpenAI
        await translator.connect()
        
        # Start listening to OpenAI events
        event_task = asyncio.create_task(translator.handle_realtime_events())
        
        # Listen for client messages (audio bytes or JSON)
        while True:
            try:
                data = await client_ws.receive()
                
                if "bytes" in data:
                    # Binary audio chunk received
                    audio_chunk = data["bytes"]
                    logger.info(f"📥 Received audio chunk: {len(audio_chunk)} bytes")
                    await translator.send_audio(audio_chunk)
                    
                    # Auto-commit after receiving audio (for push-to-talk)
                    await translator.commit_audio()
                
                elif "text" in data:
                    # JSON message received
                    message = json.loads(data["text"])
                    
                    if message.get("action") == "ping":
                        await client_ws.send_json({"type": "pong"})
                    
                    elif message.get("action") == "disconnect":
                        break
                        
            except Exception as e:
                logger.error(f"❌ Error receiving data: {e}")
                break
        
        # Wait for event task to finish
        event_task.cancel()
        
    except Exception as e:
        logger.error(f"❌ Realtime translation error: {e}", exc_info=True)
        await client_ws.send_json({
            "type": "error",
            "message": str(e)
        })
    
    finally:
        await translator.close()
