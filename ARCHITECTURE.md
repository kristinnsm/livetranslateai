# 🏗️ Babbelfish Architecture

## System Overview

```
┌─────────────────┐         WebSocket          ┌─────────────────┐
│                 │    (Audio + Control)        │                 │
│    Browser      │◄──────────────────────────►│  FastAPI Server │
│   (Frontend)    │                             │    (Backend)    │
│                 │                             │                 │
└─────────────────┘                             └─────────────────┘
        │                                                │
        │                                                │
        ▼                                                ▼
┌─────────────────┐                             ┌─────────────────┐
│  WebRTC Audio   │                             │  OpenAI APIs    │
│   - Mic capture │                             │  - Whisper STT  │
│   - VAD         │                             │  - GPT-4o-mini  │
│   - Playback    │                             │  - TTS          │
└─────────────────┘                             └─────────────────┘
```

---

## Data Flow (Realtime Mode)

```
Speak → Mic Capture → WebSocket Send → Realtime API → Translate → TTS
                                            │                        │
                                            └────── <500ms ──────────┘
                                                       │
                                                       ▼
                                              WebSocket Send → Play Audio
                                                       │
                                                       ▼
                                              Buffer for Replay
```

**Latency Target**: 500ms - 1s total

---

## Data Flow (Traditional Mode)

```
Speak → Mic Capture → WebSocket Send → VAD Check → Whisper STT
                                            │            │
                                            ▼            ▼ (1-2s)
                                      [Discard]      Transcription
                                                           │
                                                           ▼
                                                   GPT Translation
                                                           │ (500ms)
                                                           ▼
                                                       TTS Audio
                                                           │ (1-2s)
                                                           ▼
                                              WebSocket Send → Play Audio
                                                           │
                                                           ▼
                                                  Buffer for Replay
```

**Latency Target**: 3-5s total

---

## Component Breakdown

### Frontend (`frontend/`)

#### `index.html`
- Language selectors (source/target)
- Start/Stop/Mute controls
- Live subtitle display (original + translated)
- Replay controls + audio player
- Status indicators (connection, latency)

#### `app.js`
- **WebRTC Audio Capture**:
  - `getUserMedia()` for mic access
  - MediaRecorder with 500ms chunks
  - Opus codec in WebM container
  
- **WebSocket Client**:
  - Bidirectional communication
  - Binary frames for audio
  - JSON for control messages
  
- **Audio Playback**:
  - AudioContext for TTS playback
  - HTML5 audio for replay
  
- **UI Updates**:
  - Real-time subtitle sync
  - Latency monitoring
  - Toast notifications

#### `styles.css`
- Dark theme with gradient backgrounds
- Responsive layout (mobile-friendly)
- Animated status indicators
- Accessible controls

---

### Backend (`backend/`)

#### `main.py` (FastAPI Server)
- **Endpoints**:
  - `GET /`: Health check
  - `GET /health`: Detailed status
  - `WebSocket /ws/translate`: Main translation endpoint

- **Session Management**:
  - In-memory session storage
  - Auto-cleanup on disconnect
  - Buffer isolation per session

- **Message Routing**:
  - Binary → Audio processing
  - JSON → Control commands (replay, language change)

#### `services/audio_processor.py`
- **Voice Activity Detection (VAD)**:
  - webrtcvad library
  - Aggressiveness: 0-3 (configurable)
  - Filters silence to reduce API calls
  
- **Audio Conversion**:
  - PCM → WAV for Whisper
  - Normalization to 70% max volume
  
- **Chunking Strategy**:
  - Overlapping windows (50% overlap)
  - Prevents mid-word splits
  - 3-second rolling buffer

#### `services/translator_realtime.py`
- **OpenAI Realtime API** (when available):
  - WebSocket connection to OpenAI
  - Streaming STT + Translation + TTS
  - Context continuity across utterances
  
- **Fallback Logic**:
  - Degrades to traditional pipeline if unavailable
  - Same interface for seamless switching

#### `services/translator_traditional.py`
- **Sequential Pipeline**:
  1. **Whisper STT**:
     - Convert audio to WAV
     - Send to `whisper-1` model
     - Use previous transcript as prompt for context
  
  2. **GPT Translation**:
     - `gpt-4o-mini` model
     - Temperature: 0.3 (consistent, not creative)
     - System prompt: Maintain tone, use context
  
  3. **TTS**:
     - `tts-1` model (or `tts-1-hd`)
     - Voice: alloy (configurable)
     - Output: MP3 format

- **Error Handling**:
  - `@retry` decorator with exponential backoff
  - Graceful degradation on API failures

#### `services/buffer_manager.py`
- **In-Memory Buffer**:
  - Stores segments with timestamps
  - Max duration: 5 minutes (configurable)
  - Auto-prunes old segments
  
- **Replay Export**:
  - **Audio**: Concatenate MP3 segments with pydub
  - **Subtitles**: Generate WebVTT format
    - Cue timing from timestamps
    - Synced text display
  
- **Privacy**:
  - No disk writes
  - Cleared on disconnect
  - No logging of content

#### `utils/logger.py`
- Structured logging (timestamp, level, module)
- Console output for development
- Configurable levels (DEBUG, INFO, WARNING, ERROR)

---

## Message Protocol

### Client → Server

#### Audio Chunk (Binary)
```
WebSocket.send(audioBuffer)  // Raw audio bytes
```

#### Control Messages (JSON)
```javascript
// Set language
{ "action": "set_language", "source_lang": "en", "target_lang": "es" }

// Request replay
{ "action": "replay", "duration": 60 }

// Heartbeat
{ "action": "ping" }
```

### Server → Client

#### Translation Result (JSON)
```json
{
  "type": "translation",
  "timestamp": 1234567890.123,
  "original": "Hello world",
  "translated": "Hola mundo",
  "source_lang": "en",
  "target_lang": "es",
  "latency_ms": 850
}
```

#### Audio Response (Binary)
```
WebSocket.send(mp3Bytes)  // Translated audio
```

#### Replay Package (JSON + Binary)
```json
{
  "type": "replay_ready",
  "duration": 60,
  "segments_count": 12,
  "vtt": "WEBVTT\n\n1\n00:00:00.000 --> 00:00:03.000\nHola mundo\n..."
}
// Followed by binary audio data
```

#### System Messages (JSON)
```json
// Connection established
{ "type": "connected", "session_id": "session_123...", "mode": "realtime" }

// Language updated
{ "type": "language_updated", "source_lang": "en", "target_lang": "fr" }

// Errors
{ "type": "error", "message": "Translation failed" }
```

---

## Configuration (`.env`)

```bash
# API Keys
OPENAI_API_KEY=sk-proj-...

# Translation Mode
USE_REALTIME_API=true          # true = Realtime API, false = Traditional

# Audio Settings
SAMPLE_RATE=16000              # 16kHz (optimal for Whisper)
CHUNK_DURATION_MS=500          # 500ms chunks
VAD_AGGRESSIVENESS=2           # 0-3 (higher = more aggressive)

# Buffer Settings
MAX_BUFFER_DURATION=300        # 5 minutes max

# Language Defaults
DEFAULT_SOURCE_LANG=en
DEFAULT_TARGET_LANG=es

# Logging
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR
```

---

## State Management

### Frontend State
```javascript
{
  websocket: WebSocket | null,
  mediaRecorder: MediaRecorder | null,
  audioContext: AudioContext | null,
  audioStream: MediaStream | null,
  isRecording: boolean,
  isMuted: boolean,
  sessionId: string | null,
  segmentCount: number,
  latencyStats: number[]
}
```

### Backend Session State
```python
{
  "session_id": {
    "buffer": BufferManager,
    "processor": AudioProcessor,
    "translator": RealtimeTranslator | TraditionalTranslator,
    "connected_at": ISO timestamp
  }
}
```

---

## Scaling Considerations

### Current MVP (In-Memory)
- ✅ Simple, privacy-focused
- ✅ No database overhead
- ❌ Doesn't scale horizontally
- ❌ Lost on server restart

### Future (Redis/Persistent)
- Store buffers in Redis
- Horizontal scaling with load balancer
- Session persistence across restarts
- Multi-server WebSocket routing

---

## Security

### Current Implementation
- ✅ CORS configured (lock down for production)
- ✅ No data persistence
- ✅ API keys in environment variables
- ✅ No sensitive logging
- ❌ No user authentication (add later)
- ❌ No rate limiting (rely on OpenAI quotas)

### Production Additions Needed
- [ ] User authentication (JWT tokens)
- [ ] Rate limiting per user
- [ ] Input validation/sanitization
- [ ] Stricter CORS origins
- [ ] HTTPS enforcement
- [ ] API key rotation

---

## Performance Targets

| Metric | Target | Current Status |
|--------|--------|---------------|
| **Realtime Mode** | <1s latency | ⏳ Testing needed |
| **Traditional Mode** | 3-5s latency | ⏳ Testing needed |
| **Audio Capture** | <500ms delay | ✅ Built-in |
| **VAD Processing** | <100ms | ✅ webrtcvad |
| **Transcription Accuracy** | 85%+ WER | ⏳ Testing needed |
| **Translation Quality** | Natural tone | ⏳ Testing needed |
| **Replay Sync** | ±200ms | ⏳ Testing needed |
| **WebSocket Reliability** | 95%+ uptime | ⏳ Testing needed |

---

## Testing Strategy

### Unit Tests (Future)
```python
# Test audio processing
test_vad_filters_silence()
test_audio_normalization()
test_chunk_overlap()

# Test translation
test_whisper_transcription()
test_gpt_translation()
test_tts_generation()

# Test buffer
test_buffer_pruning()
test_vtt_generation()
test_audio_concatenation()
```

### Integration Tests (Current)
- Manual end-to-end testing
- Latency logging in browser console
- WER calculation (manual comparison)

---

## Deployment Architecture

### Development
```
Frontend: localhost:3000 (Python HTTP server)
Backend:  localhost:8000 (Uvicorn)
```

### Production
```
Frontend: Vercel/Netlify CDN
          ↓ WebSocket →
Backend:  Render.com (or Railway/Fly.io)
          ↓ API calls →
OpenAI:   api.openai.com
```

---

## File Size Estimates

| Component | Lines of Code | Complexity |
|-----------|--------------|------------|
| `backend/main.py` | ~250 | Medium |
| `translator_traditional.py` | ~150 | Medium |
| `audio_processor.py` | ~120 | Medium |
| `buffer_manager.py` | ~150 | Low |
| `frontend/app.js` | ~400 | Medium |
| `frontend/index.html` | ~120 | Low |
| `frontend/styles.css` | ~400 | Low |
| **Total** | **~1600** | **MVP-sized** |

---

Built with 💡 Cursor AI

