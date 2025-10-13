# 🛠️ Development Guide - Babbelfish MVP

## Problem Analysis & Mitigation Strategies

Based on analysis of real-time voice translation projects, here are the **top 5 problem areas** ranked by impact, with mitigation strategies baked into this codebase.

---

### 🚨 #1: Latency Spikes (CRITICAL - MVP Killer)

**Problem**: Sequential pipeline (Whisper → GPT → TTS) easily exceeds 3-5s target. Whisper alone can take 1-2s per chunk, plus network overhead. Demos fail when lag makes conversations feel unnatural.

**Built-in Mitigations**:
- ✅ **Dual-mode architecture**: Toggle between Realtime API (~500ms) and Traditional (~3-5s)
- ✅ **Latency monitoring**: Real-time display in UI, logged per-segment
- ✅ **Early testing**: Day 2 timestamp logging to catch issues before polish phase
- ✅ **Async processing**: FastAPI async handlers prevent blocking

**Day 1 Action**:
```bash
# Test both modes early
# In .env set USE_REALTIME_API=true first, then false
# Compare latency in browser dev console
```

**Cursor Prompt (Day 2)**:
```
"Analyze latency bottlenecks in translator_traditional.py and suggest optimizations"
```

---

### 🎧 #2: Audio Chunking & Transcription Errors

**Problem**: 100-500ms PCM chunks risk mid-word splits → garbled text ("hel-lo there"). Whisper optimized for full utterances, not fragments. Accuracy drops to 70-80% on accents/jargon.

**Built-in Mitigations**:
- ✅ **Overlapping chunks**: `create_overlapping_chunks()` with 50% overlap (in `audio_processor.py`)
- ✅ **VAD silence trimming**: `webrtcvad` aggressiveness=2 to avoid silent chunk spam
- ✅ **Context continuity**: Whisper `prompt` parameter uses previous 200 chars
- ✅ **Audio normalization**: Levels normalized to 70% max for consistent quality
- ✅ **Buffer accumulation**: 3-second rolling buffer in `translator_traditional.py`

**Day 3 Testing**:
```python
# Manual WER (Word Error Rate) check
# Speak: "The quick brown fox jumps over the lazy dog"
# Check originalText in console
# Target: 90%+ match (allow for minor punctuation)
```

**Cursor Prompt (Day 3)**:
```
"Add GPT post-processing to fix mid-word breaks in Whisper output"
```

---

### 🌍 #3: Multilingual Accuracy & Language Mixing

**Problem**: Auto-detect works ~90% for clear English, drops to 75% on accents/French. GPT preserves tone poorly for slang. TTS voices sound robotic in non-English.

**Built-in Mitigations**:
- ✅ **Explicit language selection**: User confirms source/target (no blind auto-detect)
- ✅ **Start with EN↔ES only**: High-accuracy pair for MVP validation
- ✅ **Context-aware translation**: GPT prompt includes previous 150 chars for natural flow
- ✅ **Temperature tuning**: `temperature=0.3` for consistent (not creative) translation
- ✅ **Confidence logging**: Whisper confidence scores tracked

**Recommended MVP Scope**:
```javascript
// Limit to these pairs initially (high accuracy):
- EN ↔ ES (90%+)
- EN ↔ FR (85%+)
// Add others after validation
```

**Day 7 Validation**:
```
Test with bilingual phrases:
- "Let's eat, abuela está esperando" (code-switching)
- Slang: "That's fire!" → "¡Eso está increíble!"
Check if tone preserved
```

---

### 🌐 #4: Browser/WebRTC Reliability

**Problem**: `getUserMedia` finicky—Safari throttles audio, Firefox blocks permissions differently. WebSocket reconnections mid-call lose buffers. CORS issues on deploy. Render cold starts add 1-2s.

**Built-in Mitigations**:
- ✅ **Reconnection logic**: Auto-reconnect with 3s delay (in `app.js`)
- ✅ **CORS configured**: Broad allow for dev, ready to lock down
- ✅ **Buffer preservation**: Server-side storage survives brief disconnects
- ✅ **Graceful degradation**: VAD failures assume speech (fail-open)
- ✅ **Heartbeat pings**: 30s keepalive prevents idle disconnects

**Day 5 Cross-Browser Test**:
```
Test on:
1. Chrome (primary) - expected 95%+ success
2. Firefox - test permission flow
3. Safari (if Mac available) - known audio issues

Add adapter.js if Safari fails:
<script src="https://webrtc.github.io/adapter/adapter-latest.js"></script>
```

---

### ⚠️ #5: Error Handling & Edge Cases (Creeping Impact)

**Problem**: OpenAI rate limits (429s) crash sessions. Noisy environments overwhelm VAD. Empty replay buffers frustrate users. Env var leaks risk API keys.

**Built-in Mitigations**:
- ✅ **Retry logic**: `@retry` decorators with exponential backoff (via `tenacity`)
- ✅ **Toast notifications**: User-facing error messages (not just console logs)
- ✅ **Empty replay handling**: Check segment count before export
- ✅ **Env var protection**: `.gitignore` blocks `.env`, example file provided
- ✅ **Try-catch everywhere**: Backend wrapped in exception handlers

**Day 6 Edge Case Tests**:
```javascript
// Simulate in Chrome DevTools:
1. Network throttle: Slow 3G → check reconnect
2. Offline: Network tab → check "Reconnecting..." toast
3. No mic: Block permissions → check error message
4. Noisy audio: Play background music → VAD should filter
5. Empty replay: Click replay immediately → check toast
```

---

## 🎯 Testing Strategy

### Day 1: Connectivity
```bash
# Backend health check
curl http://localhost:8000/health

# WebSocket connection
# Open frontend → Check console: "WebSocket connected"
```

### Day 2-3: Pipeline Accuracy
```javascript
// In browser console:
console.log('Latency stats:', latencyStats);
// Target: 3-5s traditional, <1s realtime

// Manual transcription check (10 phrases):
// Speak clearly → Compare originalText to what you said
// Target: 85%+ WER
```

### Day 4-5: Replay Sync
```bash
# After 30s conversation:
# 1. Click "Replay Last Minute"
# 2. Play audio
# 3. Check: Subtitles appear at correct timestamps (±200ms tolerance)
```

### Day 6: Stress Test
```python
# Rapid speech test (15s monologue)
# Check: No dropped segments, buffer handles overflow
```

---

## 🚀 Deployment Checklist

### Pre-Deploy
- [ ] Test on 3 browsers (Chrome, Firefox, Safari)
- [ ] Verify API rate limits won't hit during demo
- [ ] Lock down CORS origins to production domain
- [ ] Add API key to Render env vars
- [ ] Test cold start latency (<3s from sleep)

### Deploy Commands
```bash
# Backend to Render
render deploy --config render.yaml

# Frontend to Vercel
cd frontend
vercel --prod
```

### Post-Deploy
- [ ] Update `CONFIG.wsUrl` in `app.js` to production WebSocket URL
- [ ] Test end-to-end on deployed site
- [ ] Share link for feedback

---

## 🐛 Known Limitations (MVP)

1. **Audio-only**: No video feed (add `getUserMedia({video: true})` later)
2. **1:1 simulation**: Loopback testing (add WebRTC peer-to-peer for multi-user)
3. **No persistence**: Buffers lost on disconnect (fine for privacy)
4. **Limited languages**: 2-4 high-accuracy pairs only
5. **Replay export**: No MP4 download yet (add FFmpeg later)

---

## 📚 Useful Cursor Prompts

### Debugging
```
"Fix async audio buffering in FastAPI WebSocket handler"
"Why is Whisper returning empty text for this audio chunk?"
"Optimize WebSocket reconnection logic to preserve buffer"
```

### Features
```
"Add downloadable MP4 export for replay using FFmpeg"
"Implement WebRTC signaling for peer-to-peer calls"
"Add confidence threshold for low-quality transcriptions"
```

### Performance
```
"Profile latency in traditional pipeline and identify bottlenecks"
"Reduce TTS latency by streaming audio chunks"
"Add client-side VAD to reduce backend load"
```

---

## 💡 Next Steps After MVP

1. **User testing**: Share with 2-3 bilingual friends
2. **Metrics**: Add analytics for latency/accuracy distribution
3. **Scaling**: Redis for buffers if multi-session needed
4. **Quality**: Test with diverse accents, noisy environments
5. **Export**: MP4 downloads with burned-in subs
6. **Multi-user**: Add signaling server for true peer-to-peer

---

## 🎬 Demo Script

1. Open app → Select EN → ES
2. Start translation
3. Say: "Hello, my name is [Your Name]. How are you today?"
4. Show live subtitles appearing
5. Play translated audio
6. After 30s, click Replay
7. Show synchronized subtitles on playback

**Target impression**: "Wow, that's almost instant!"

---

Built with Cursor 🤖

