# 🐠 Babbelfish - Real-Time AI Voice Translator

A browser-based real-time voice translation app with playback and synchronized subtitles. Translate conversations in near real-time (~500ms-5s latency) with support for multiple languages.

## ✨ Features

- **Real-time translation**: Speak and hear translations with minimal latency
- **Multiple languages**: English, Spanish, French, German (easily extensible)
- **Live subtitles**: See original and translated text in real-time
- **Replay with sync**: Replay conversations with synchronized subtitles
- **Privacy-focused**: All processing in-memory, no data persistence
- **Two modes**: 
  - Realtime API mode (~500ms latency)
  - Traditional pipeline mode (~3-5s latency, more reliable)

## 🏗️ Architecture

### Backend (FastAPI + Python)
- WebSocket server for real-time audio streaming
- Dual translation modes:
  - **Realtime API**: OpenAI's WebSocket-based voice API (low latency)
  - **Traditional**: Whisper STT → GPT translation → TTS (fallback)
- Voice Activity Detection (VAD) to filter silence
- In-memory buffer management for replay
- WebVTT subtitle generation

### Frontend (Vanilla JS)
- WebRTC audio capture from microphone
- WebSocket streaming to backend
- AudioContext for playback
- Real-time subtitle display
- HTML5 audio player for replay

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- FFmpeg (for audio processing)
- OpenAI API key

### Installation

1. **Clone and setup backend**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. **Run backend**:
```bash
cd backend
uvicorn main:app --reload
```

4. **Open frontend**:
```bash
# Simple HTTP server
cd frontend
python -m http.server 3000
```

5. **Open browser**:
Navigate to `http://localhost:3000`

## 🎯 Usage

1. Select source and target languages
2. Click "Start Translation"
3. Grant microphone permission
4. Speak naturally
5. See live subtitles and hear translation
6. Click "Replay Last Minute" to review with synced subtitles

## ⚙️ Configuration

Edit `.env` file:

```bash
# Use Realtime API (lower latency) or Traditional pipeline
USE_REALTIME_API=true

# Max buffer duration for replay (seconds)
MAX_BUFFER_DURATION=300

# VAD sensitivity (0-3, higher = more aggressive)
VAD_AGGRESSIVENESS=2
```

## 📊 Performance Targets

| Component | Target Latency | Current |
|-----------|---------------|---------|
| Audio Capture | <500ms | ✅ |
| STT (Whisper) | 1s | ⏳ |
| Translation (GPT) | 500ms | ⏳ |
| TTS | 1-2s | ⏳ |
| **Total (Traditional)** | **3-5s** | ⏳ |
| **Total (Realtime API)** | **500ms-1s** | ⏳ |

## 🔧 Troubleshooting

### Mic access denied
- Check browser permissions (chrome://settings/content/microphone)
- Use HTTPS in production (HTTP ok for localhost)

### High latency
- Switch to `USE_REALTIME_API=true`
- Check internet connection
- Reduce `CHUNK_DURATION_MS` in config

### Audio quality issues
- Increase VAD aggressiveness if too much silence captured
- Use headphones to avoid echo
- Ensure quiet environment for testing

### WebSocket disconnections
- Check firewall settings
- Enable debug logging: `LOG_LEVEL=DEBUG`

## 🛠️ Development Roadmap

- [ ] Day 1-3: Core pipeline (STT → Translation → TTS)
- [ ] Day 4-5: Replay + WebVTT subtitles
- [ ] Day 6-7: Error handling, polish, deploy
- [ ] Day 8-9: User testing, optimization

**Future enhancements**:
- Video support (webcam feed)
- Multi-user calls (WebRTC peer-to-peer)
- Downloadable replay exports
- Advanced accent/dialect tuning
- Redis buffer storage for scaling

## 🔐 Privacy

- **No data storage**: All audio/text buffers exist in RAM only
- **Auto-pruning**: Buffers cleared after max duration or disconnect
- **No logs**: Sensitive content never written to disk
- **Local-first**: Can be run entirely on localhost

## 📦 Deployment

### Backend (Render)
```bash
# Deploy FastAPI to Render
# Add OPENAI_API_KEY in Render dashboard
```

### Frontend (Vercel/Netlify)
```bash
# Deploy static files
# Update WS_URL in app.js to production backend
```

## 📝 License

MIT License - Built for educational and research purposes

## 🙏 Credits

Powered by:
- OpenAI (Whisper, GPT-4o-mini, TTS, Realtime API)
- FastAPI
- WebRTC
- pydub, webvtt-py

---

Built with ❤️ and Cursor

