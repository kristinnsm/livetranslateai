# 🚀 START HERE - Quick Setup Guide

## First-Time Setup (5 minutes)

### Step 1: Install Python Dependencies
```bash
# Create virtual environment
cd backend
python -m venv venv

# Activate it
# Windows PowerShell:
venv\Scripts\Activate.ps1

# Windows CMD:
venv\Scripts\activate.bat

# Mac/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 2: Install FFmpeg (Required for audio processing)

**Windows**:
```bash
# Using Chocolatey:
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
# Add to PATH
```

**Mac**:
```bash
brew install ffmpeg
```

**Linux**:
```bash
sudo apt install ffmpeg
```

### Step 3: Configure API Key
```bash
# Copy environment template
copy backend\.env.example .env

# Edit .env and add your OpenAI API key:
# OPENAI_API_KEY=sk-proj-...
```

### Step 4: Test Configuration
```bash
# From project root
python test_connection.py

# You should see:
# ✅ API key found
# ✅ GPT response: Hello from Babbelfish!
# 🎉 OpenAI connection test passed!
```

### Step 5: Start Backend
```bash
cd backend
uvicorn main:app --reload

# You should see:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# 🚀 Babbelfish starting in Realtime API mode
```

### Step 6: Start Frontend
```bash
# In a NEW terminal (don't close backend)
cd frontend

# Simple Python HTTP server:
python -m http.server 3000

# Or use any static server:
# npx serve -p 3000
# php -S localhost:3000
```

### Step 7: Open in Browser
```
Navigate to: http://localhost:3000

1. Click "Start Translation"
2. Allow microphone access
3. Say: "Hello, this is a test"
4. Watch for:
   - Live subtitles appearing
   - Translation audio playing
   - Latency shown in top-right
```

---

## Quick Health Check

### Backend Running?
Visit: http://localhost:8000/health

Should see:
```json
{
  "status": "healthy",
  "api_key_configured": true,
  "active_sessions": 0,
  "mode": "realtime"
}
```

### Frontend Loaded?
Open browser console (F12) → Should see:
```
🐠 Babbelfish initialized
```

### WebSocket Connected?
After clicking "Start" → Console should show:
```
WebSocket connected
```

---

## Common Issues

### ❌ "OPENAI_API_KEY not set"
→ Check `.env` file exists in project root (NOT in backend/)
→ Restart backend after editing .env

### ❌ "ModuleNotFoundError: No module named 'webrtcvad'"
→ Activate venv: `venv\Scripts\Activate.ps1`
→ Re-run: `pip install -r requirements.txt`

### ❌ "FFmpeg not found"
→ Install FFmpeg (see Step 2)
→ Restart terminal after installing

### ❌ Microphone permission denied
→ Check browser settings (chrome://settings/content/microphone)
→ Ensure using HTTP on localhost (or HTTPS if deployed)

### ❌ WebSocket won't connect
→ Check backend is running on port 8000
→ Check frontend `app.js` has correct `wsUrl`
→ Check firewall isn't blocking WebSocket

### ❌ High latency (>10s)
→ Check internet connection
→ Try `USE_REALTIME_API=false` in .env (traditional mode)
→ Check OpenAI API status: https://status.openai.com

---

## Day 1 Success Criteria

✅ Backend starts without errors  
✅ Frontend loads in browser  
✅ WebSocket connects (green status dot)  
✅ Mic access granted  
✅ Audio chunks streaming (check browser Network tab → WS frames)  
✅ No console errors for 30s of silence  

**You're ready for Day 2 if all checked!**

---

## Project Structure Reference

```
Project Babbelfish/
├── backend/
│   ├── main.py                      # FastAPI server + WebSocket routes
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Config template
│   ├── services/
│   │   ├── audio_processor.py       # VAD, chunking, WAV conversion
│   │   ├── translator_realtime.py   # Realtime API mode (low latency)
│   │   ├── translator_traditional.py # Whisper+GPT+TTS mode
│   │   └── buffer_manager.py        # Replay buffer + WebVTT export
│   └── utils/
│       └── logger.py                # Logging setup
├── frontend/
│   ├── index.html                   # UI layout
│   ├── app.js                       # WebSocket client + audio handling
│   └── styles.css                   # Dark theme styling
├── .env                             # Your API keys (create this!)
├── .gitignore                       # Don't commit secrets
├── test_connection.py               # Day 1 validation script
├── render.yaml                      # Backend deployment config
├── vercel.json                      # Frontend deployment config
├── README.md                        # Project overview
├── DEVELOPMENT.md                   # This file - problem analysis
└── START_HERE.md                    # You are here!
```

---

## Next: Read DEVELOPMENT.md

Once setup is complete, read `DEVELOPMENT.md` for:
- Detailed problem analysis
- Day-by-day testing strategies
- Cursor prompts for debugging
- Deployment checklist

**Time to first working demo: ~30 minutes** ⏱️

Good luck! 🎉

