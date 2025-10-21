# 🎥 LiveTranslateAI - Zoom/Teams Integration Guide

## 🎯 **Goal**
Use LiveTranslateAI during live Zoom, Teams, or Google Meet calls for real-time translation.

---

## 🔧 **METHOD 1: Virtual Audio Cable (Recommended)**

### **What You Need:**
- VB-Audio Virtual Cable (Free software)
- LiveTranslateAI running (localhost:3000)
- Zoom/Teams/Meet app

---

### **📥 STEP 1: Install VB-Audio Cable**

**Windows:**
1. Download from: https://vb-audio.com/Cable/
2. Extract ZIP file
3. Right-click `VBCABLE_Setup_x64.exe` → Run as Administrator
4. Click "Install Driver"
5. Restart your computer (required!)

**Mac:**
1. Download from: https://vb-audio.com/Cable/
2. Open DMG file
3. Run installer
4. Grant system permissions in Security & Privacy settings
5. Restart your Mac

**Verify Installation:**
- Windows: Control Panel → Sound → You should see "CABLE Input" and "CABLE Output"
- Mac: System Preferences → Sound → You should see "VB-Cable"

---

### **🎤 STEP 2: Configure LiveTranslateAI**

1. **Start the servers:**
   ```bash
   # Terminal 1 - Backend
   cd backend
   .\venv\Scripts\uvicorn.exe main:app --host 127.0.0.1 --port 8000

   # Terminal 2 - Frontend
   cd frontend
   python -m http.server 3000
   ```

2. **Open LiveTranslateAI:**
   ```
   http://localhost:3000
   ```

3. **Set audio devices in browser:**
   - Chrome: Settings → Privacy & Security → Site Settings → Microphone
   - Select your **REAL microphone** (not CABLE)

---

### **🎥 STEP 3: Configure Zoom**

1. **Open Zoom Settings:**
   - Click gear icon (⚙️) → Audio

2. **Configure Microphone:**
   - Microphone: Select **"CABLE Output (VB-Audio Virtual Cable)"**
   - This sends audio FROM LiveTranslateAI TO Zoom participants

3. **Configure Speaker:**
   - Speaker: Select your **REAL speakers/headphones**
   - This lets you hear the other person

4. **Test:**
   - Click "Test Mic" → You should see NO bars (normal, we'll send audio manually)
   - Click "Test Speaker" → You should hear sound

---

### **💼 STEP 4: Configure Teams (Similar)**

1. **Open Teams Settings:**
   - Click profile picture → Settings → Devices

2. **Microphone:** "CABLE Output"

3. **Speaker:** Your real speakers

---

### **🌐 STEP 5: Configure Google Meet (Browser)**

1. **Join meeting**

2. **Click 3 dots → Settings → Audio**

3. **Microphone:** "CABLE Output"

4. **Speakers:** Your real speakers

---

### **🎬 STEP 6: Usage Workflow**

**During a Call:**

1. **Start your Zoom/Teams call** (join meeting as normal)

2. **Mute yourself in Zoom/Teams** (don't want your real voice going through)

3. **Open LiveTranslateAI** (localhost:3000)

4. **When it's your turn to speak:**
   - Click **"Start Speaking"** 🎤
   - Speak your message in English
   - Click **"Stop & Translate"** ⏹️
   - Wait ~7 seconds for translation
   - Spanish audio automatically plays through Zoom microphone!
   - Other person hears Spanish translation

5. **When other person speaks:**
   - They use their LiveTranslateAI (or speak Spanish)
   - You hear them through your speakers

6. **Repeat!** Click "Start Speaking" for your next turn

---

### **🔊 AUDIO FLOW DIAGRAM:**

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR COMPUTER                        │
│                                                         │
│  [Your Mic] → [LiveTranslateAI]                       │
│                      ↓                                   │
│               (Translates EN→ES)                        │
│                      ↓                                   │
│            [Translated Audio]                           │
│                      ↓                                   │
│              [CABLE Input]                              │
│                      ↓                                   │
│  [Zoom Microphone: CABLE Output]                       │
│                      ↓                                   │
│              [Internet] ──────────→ [Other Person]     │
│                                                         │
│  [Your Speakers] ←──────────── [Other Person's Voice]  │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 **TIPS FOR BEST RESULTS:**

### **Audio Quality:**
- Use a good microphone (headset recommended)
- Quiet environment (reduce background noise)
- Speak clearly and at normal pace
- Wait for translation before continuing

### **Timing:**
- Speak in 10-15 second chunks
- Don't rush (translation takes 7-9 seconds)
- Give other person time to respond
- Use "Stop & Translate" promptly

### **Professional Use:**
- Test with a colleague BEFORE important calls
- Have backup plan (Google Translate on phone)
- Explain to other party "there may be slight delays"
- Keep sentences simple for better accuracy

---

## 🐛 **TROUBLESHOOTING:**

### **"Other person can't hear me"**
- Check: Zoom microphone is set to "CABLE Output"
- Check: LiveTranslateAI audio is playing (you should hear Spanish)
- Check: Unmute in Zoom after translation plays

### **"I can't hear translation"**
- Check: Browser permission for speakers
- Check: Translation shows in LiveTranslateAI UI
- Check: Volume not muted

### **"Audio is choppy"**
- Close other apps (reduce CPU load)
- Use wired internet (not WiFi)
- Lower Zoom video quality (Settings → Video → Manual)

### **"Translation is inaccurate"**
- Speak slower and clearer
- Use shorter sentences
- Avoid slang/idioms
- Spell out technical terms

### **"Still not working?"**
1. Restart LiveTranslateAI (refresh browser)
2. Restart Zoom/Teams
3. Restart VB-Audio Cable (Windows: Services → restart "VB-Audio")
4. Reboot computer (last resort)

---

## 🔜 **COMING SOON: Native Integrations**

We're working on **native app integrations** that won't require VB-Audio Cable:

- **Zoom App** (Zoom App Marketplace) - ETA: 3 months
- **Teams App** (Microsoft Teams Store) - ETA: 4 months
- **Desktop App** (Electron, auto audio routing) - ETA: 2 months

These will make setup **one-click easy!**

---

## 📞 **NEED HELP?**

**Support:** support@livetranslateai.com  
**Sales:** sales@livetranslateai.com  
**Discord:** discord.gg/livetranslateai (coming soon)

---

## 🎬 **VIDEO TUTORIAL**

Watch our step-by-step video guide:  
**YouTube:** https://youtube.com/livetranslateai (coming soon)

---

*Last Updated: October 20, 2025*  
*Works with: Zoom, Teams, Google Meet, Discord, WhatsApp, any video app!*

