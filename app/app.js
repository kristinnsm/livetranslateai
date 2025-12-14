/**
 * Babbelfish Frontend - Real-Time Voice Translation
 * Handles WebRTC audio capture, WebSocket communication, and UI updates
 */

// Configuration
const CONFIG = {
    wsUrl: window.location.hostname === 'localhost' 
        ? 'ws://localhost:8000/ws/translate'
        : 'wss://livetranslateai.onrender.com/ws/translate',
    sampleRate: 16000,
    chunkDurationMs: 2000,
    reconnectDelay: 3000
};

// Global state
let websocket = null;
let mediaRecorder = null;
let audioContext = null;
let audioStream = null;
let isRecording = false;
let sessionId = null;
let segmentCount = 0;
let latencyStats = [];
let globalAudioPlayer = null; // Reusable audio player for mobile unlock

// Room state
let currentRoom = null;
let participantId = null;
let participantName = null; // Store participant's actual name for video display
let isHost = false;
let roomParticipants = []; // Track participants in the room

// Call timer for live usage tracking
let callStartTime = null;
let callTimerInterval = null;

// Replay state
let lastTranslation = null; // Store last translation for replay

// Daily.co video call state
let dailyCallFrame = null;
let dailyCallActive = false;
let isCameraOn = true;
let isMicOn = true;

// DOM elements
const elements = {
    startBtn: document.getElementById('startBtn'),
    stopBtn: document.getElementById('stopBtn'),
    replayBtn: document.getElementById('replayBtn'),
    replayBtnSidebar: document.getElementById('replayBtnSidebar'),
    sourceLang: document.getElementById('sourceLang'),
    targetLang: document.getElementById('targetLang'),
    replayDuration: document.getElementById('replayDuration'),
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText'),
    latencyDisplay: document.getElementById('latencyDisplay'),
    originalText: document.getElementById('originalText'),
    translatedText: document.getElementById('translatedText'),
    sessionIdDisplay: document.getElementById('sessionId'),
    translationMode: document.getElementById('translationMode'),
    segmentCountDisplay: document.getElementById('segmentCount'),
    micLevel: document.getElementById('micLevel'),
    replayPlayer: document.getElementById('replayPlayer'),
    replayAudio: document.getElementById('replayAudio'),
    replaySubtitles: document.getElementById('replaySubtitles'),
    replaySection: document.querySelector('.replay-section'),
    toastContainer: document.getElementById('toastContainer'),
    // Room elements
    createRoomBtn: document.getElementById('createRoomBtn'),
    joinRoomBtn: document.getElementById('joinRoomBtn'),
    roomInfo: document.getElementById('roomInfo'),
    roomCode: document.getElementById('roomCode'),
    copyRoomCode: document.getElementById('copyRoomCode'),
    participantCount: document.getElementById('participantCount'),
    participantList: document.getElementById('participantList')
};

// Event Listeners
elements.startBtn.addEventListener('click', startTranslation);
elements.stopBtn.addEventListener('click', stopTranslation);
elements.replayBtn.addEventListener('click', triggerReplay);
if (elements.replayBtnSidebar) {
    elements.replayBtnSidebar.addEventListener('click', () => {
        // Scroll to replay section (temporarily enable scrolling)
        const container = document.querySelector('.container');
        if (elements.replaySection && container) {
            container.classList.add('scroll-enabled');
            elements.replaySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            // Re-disable scrolling after scroll completes
            setTimeout(() => {
                container.classList.remove('scroll-enabled');
            }, 1500);
        }
        // Trigger replay after a short delay to allow scroll
        setTimeout(() => {
            triggerReplay();
        }, 300);
    });
}
elements.sourceLang.addEventListener('change', handleLanguageChange);
elements.targetLang.addEventListener('change', handleLanguageChange);

// Video call controls
document.getElementById('toggleCamera')?.addEventListener('click', toggleCamera);
document.getElementById('toggleMic')?.addEventListener('click', toggleMicrophone);
document.getElementById('leaveCall')?.addEventListener('click', leaveVideoCall);
document.getElementById('toggleFullscreen')?.addEventListener('click', toggleCustomFullscreen);

// Room event listeners
elements.createRoomBtn.addEventListener('click', () => {
    console.log('🏠 Create Room button clicked!');
    createRoom();
});
elements.joinRoomBtn.addEventListener('click', joinRoom);
elements.copyRoomCode.addEventListener('click', copyRoomCode);

/**
 * Start translation session
 */
async function startTranslation() {
    try {
        // Check if user has minutes remaining (SKIP for guests)
        const urlParams = new URLSearchParams(window.location.search);
        const isGuest = urlParams.get('guest') === 'true';
        
        if (!isGuest && window.auth && window.auth.canStartCall) {
            const canStart = await window.auth.canStartCall();
            if (!canStart) {
                console.log('❌ Usage limit reached, cannot start call');
                return;
            }
        } else if (isGuest) {
            console.log('👤 Guest mode - bypassing usage check (host pays)');
        }
        
        // If already recording, ignore (shouldn't happen with button states)
        if (isRecording) {
            console.log('Already recording');
            return;
        }
        
        // If WebSocket connected and mic active, just start new recording
        if (websocket && websocket.readyState === WebSocket.OPEN && audioStream) {
            console.log('🎤 Starting new recording in same session...');
            startAudioCapture();
            updateUIState('recording');
            showToast('Recording...', 'info');
            return;
        }

        // First time setup: Request microphone access
        audioStream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                sampleRate: CONFIG.sampleRate,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            } 
        });

        // Initialize audio context
        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: CONFIG.sampleRate
        });
        
        // Resume AudioContext on mobile (required for iOS/Android)
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
            console.log('✅ AudioContext resumed for mobile');
        }
        
        // Create global audio player and unlock it during user interaction
        // This player will be reused for all subsequent audio playback
        if (!globalAudioPlayer) {
            globalAudioPlayer = new Audio();
            globalAudioPlayer.preload = 'auto';
            
            // Unlock by playing silent audio during user interaction
            try {
                globalAudioPlayer.src = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';
                globalAudioPlayer.volume = 0.01; // Very quiet
                await globalAudioPlayer.play();
                globalAudioPlayer.pause();
                globalAudioPlayer.currentTime = 0;
                console.log('✅ Global audio player unlocked for mobile');
            } catch (e) {
                console.log('⚠️ Could not unlock audio:', e.message);
            }
        }

        // Setup WebSocket connection
        if (currentRoom) {
            // Already connected to room WebSocket, just send language settings
            const sourceLang = elements.sourceLang.value;
            const targetLang = elements.targetLang.value;
            console.log(`🌍 Sending language settings with participant_id: ${participantId}`);
            console.log(`🌍 participantId type: ${typeof participantId}, value: ${JSON.stringify(participantId)}`);
            
            if (!participantId) {
                console.error('🚨 participantId is null/undefined! Cannot send language settings.');
                return;
            }
            
            websocket.send(JSON.stringify({
                action: 'set_language',
                participant_id: participantId,
                source_lang: sourceLang,
                target_lang: targetLang
            }));
            console.log(`🌍 Room language settings sent: ${sourceLang} → ${targetLang}`);
        } else {
            // Connect to single-user WebSocket
            await connectWebSocket();
            
            // Send current language settings
            const sourceLang = elements.sourceLang.value;
            const targetLang = elements.targetLang.value;
            websocket.send(JSON.stringify({
                action: 'set_language',
                source_lang: sourceLang,
                target_lang: targetLang
            }));
            console.log(`🌍 Language settings sent: ${sourceLang} → ${targetLang}`);
        }

        // Start first recording
        startAudioCapture();

        // Update UI
        updateUIState('recording');
        showToast('🎤 Recording... press Stop when done', 'success');

    } catch (error) {
        console.error('Start error:', error);
        showToast(`Failed to start: ${error.message}`, 'error');
    }
}

/**
 * Stop translation session
 */
function stopTranslation() {
    // Stop current recording (sends complete audio for translation)
    if (mediaRecorder && isRecording) {
        console.log('🛑 Stopping recording - sending for translation...');
        mediaRecorder.stop();
        isRecording = false;
        
        // Update UI to show processing
        elements.statusText.textContent = 'Processing...';
        showToast('Processing your speech...', 'info');
        
        // Keep WebSocket open for next recording
        // Keep mic stream active for quick restart
        // User can click "Start" again to record next part
        
        updateUIState('connected'); // Ready for next recording
    } else {
        // If not recording, treat as full disconnect
        disconnectSession();
    }
}

/**
 * Completely disconnect session
 */
function disconnectSession() {
    console.log('Disconnecting session completely');
    
    // Stop audio capture
    if (mediaRecorder) {
        if (isRecording) mediaRecorder.stop();
        mediaRecorder = null;
    }
    isRecording = false;

    // Stop audio stream
    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
        audioStream = null;
    }

    // Close WebSocket
    if (websocket) {
        websocket.close();
        websocket = null;
    }

    // Close audio context
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }

    // Update UI
    updateUIState('stopped');
    showToast('Session ended', 'info');
}

/**
 * Connect to WebSocket server
 */
function connectWebSocket() {
    return new Promise((resolve, reject) => {
        try {
            console.log('Attempting to connect to:', CONFIG.wsUrl);
            websocket = new WebSocket(CONFIG.wsUrl);

            websocket.onopen = () => {
                console.log('WebSocket connected successfully!');
                updateStatus('connected', 'Connected');
                
                // Send a test message to verify communication
                setTimeout(() => {
                    if (websocket && websocket.readyState === WebSocket.OPEN) {
                        websocket.send(JSON.stringify({ action: 'ping' }));
                        console.log('Sent ping message');
                    }
                }, 1000);
                
                resolve();
            };

            websocket.onmessage = handleWebSocketMessage;

            websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                console.error('WebSocket readyState:', websocket.readyState);
                console.error('WebSocket URL:', CONFIG.wsUrl);
                updateStatus('error', 'Connection error');
                reject(error);
            };

            websocket.onclose = () => {
                console.log('WebSocket closed');
                updateStatus('disconnected', 'Disconnected');
                
                // Auto-reconnect if still recording
                if (isRecording) {
                    setTimeout(() => {
                        showToast('Reconnecting...', 'info');
                        connectWebSocket().catch(console.error);
                    }, CONFIG.reconnectDelay);
                }
            };

        } catch (error) {
            reject(error);
        }
    });
}

/**
 * Handle incoming WebSocket messages
 */
function handleWebSocketMessage(event) {
    try {
        // Handle binary data (audio)
        if (event.data instanceof Blob) {
            playTranslatedAudio(event.data);
            return;
        }

        // Handle JSON messages
        const message = JSON.parse(event.data);
        
        switch (message.type) {
            case 'connected':
                sessionId = message.session_id;
                elements.sessionIdDisplay.textContent = sessionId.substring(0, 12) + '...';
                elements.translationMode.textContent = message.mode;
                break;

            case 'translation':
                displayTranslation(message);
                updateLatency(message.latency_ms);
                segmentCount++;
                elements.segmentCountDisplay.textContent = segmentCount;
                // Store for replay
                lastTranslation = message;
                elements.replayBtn.disabled = false;
                if (elements.replayBtnSidebar) elements.replayBtnSidebar.disabled = false;
                break;

            case 'replay_ready':
                loadReplay(message);
                break;

            case 'language_updated':
                showToast(`Languages updated: ${message.source_lang} → ${message.target_lang}`, 'success');
                break;

            case 'error':
                showToast(`Error: ${message.message}`, 'error');
                break;

            case 'pong':
                // Heartbeat response
                console.log('Received pong from server');
                break;

            case 'status':
                // Processing status update (keeps connection alive)
                console.log('Server status:', message.message);
                break;
            
            case 'audio_delta':
                // Streaming audio from Realtime API
                if (message.audio) {
                    handleAudioDelta(message.audio);
                }
                break;
            
            case 'translation_complete':
                // Final translation text from Realtime API
                console.log('✅ Realtime translation complete:', message.translated);
                updateTranslationDisplay({
                    original: "Realtime transcription",
                    translated: message.translated,
                    latency_ms: 0
                });
                break;

            default:
                console.warn('Unknown message type:', message.type);
        }

    } catch (error) {
        console.error('Message handling error:', error);
    }
}

/**
 * Start capturing audio and streaming chunks
 */
function startAudioCapture() {
    try {
        // Create MediaRecorder with optimal settings
        const options = {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: 16000
        };

        mediaRecorder = new MediaRecorder(audioStream, options);
        
        // Handle audio chunks
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0 && websocket && websocket.readyState === WebSocket.OPEN) {
                console.log(`Sending audio chunk: ${event.data.size} bytes`);
                
                // Send audio chunk via WebSocket
                event.data.arrayBuffer().then(buffer => {
                    const timestamp = performance.now() / 1000;
                    
                    // Send as binary
                    websocket.send(buffer);
                    console.log(`Audio chunk sent: ${buffer.byteLength} bytes`);
                    
                    // Update mic level visualization
                    updateMicLevel();
                }).catch(error => {
                    console.error('Error sending audio chunk:', error);
                });
            }
        };

        // Handle when recording stops
        mediaRecorder.onstop = () => {
            console.log('Recording stopped - audio chunk ready');
            updateMicLevel(0); // Reset mic visualization
        };

        // Handle errors
        mediaRecorder.onerror = (event) => {
            console.error('MediaRecorder error:', event.error);
            showToast('Audio recording error', 'error');
        };

        // Start recording - will record until manually stopped
        mediaRecorder.start();
        isRecording = true;

        console.log('🎤 Push-to-talk recording started - speak now, press Stop when done');

    } catch (error) {
        console.error('Audio capture error:', error);
        showToast('Failed to start audio capture', 'error');
    }
}

/**
 * Display translation in UI
 */
function displayTranslation(data) {
    // Hide original text ONLY when source is Icelandic (workers don't need to see what they said)
    // BUT show it when target is Icelandic (workers need to see what refugees said)
    const hideOriginal = data.source_lang === "is";
    
    if (hideOriginal) {
        // Hide the original text box when source is Icelandic
        elements.originalText.textContent = "";
        elements.originalText.parentElement.style.display = "none";
    } else {
        // Show original text for other languages (including when target is Icelandic)
        elements.originalText.parentElement.style.display = "";
        if (data.original) {
            elements.originalText.textContent = data.original;
            elements.originalText.classList.add('fade-in');
            setTimeout(() => elements.originalText.classList.remove('fade-in'), 500);
        }
    }

    // Update translated text
    if (data.translated) {
        elements.translatedText.textContent = data.translated;
        elements.translatedText.classList.add('fade-in');
        setTimeout(() => elements.translatedText.classList.remove('fade-in'), 500);
    }

    console.log(`Translation: "${data.original || '(hidden for Icelandic)'}" → "${data.translated}" (${data.latency_ms}ms)`);
    
    // Play TTS audio if available
    if (data.audio_base64) {
        console.log('🔊 Playing translated audio...');
        playAudioFromBase64(data.audio_base64);
    }
}

/**
 * Play translated audio through speakers
 */
async function playTranslatedAudio(audioBlob) {
    try {
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        
        audio.onended = () => URL.revokeObjectURL(audioUrl);
        
        await audio.play();
        
    } catch (error) {
        console.error('Audio playback error:', error);
    }
}

/**
 * Buffer for streaming audio deltas from Realtime API
 */
let audioStreamBuffer = [];
let audioStreamElement = null;

/**
 * Handle streaming audio delta from Realtime API
 */
function handleAudioDelta(audioBase64) {
    try {
        // Add to buffer
        audioStreamBuffer.push(audioBase64);
        
        console.log(`🔊 Received audio delta (${audioStreamBuffer.length} chunks)`);
        
        // If first chunk, start playback
        if (audioStreamBuffer.length === 1) {
            playStreamingAudio();
        }
        
    } catch (error) {
        console.error('❌ Error handling audio delta:', error);
    }
}

/**
 * Play streaming audio from buffer
 */
async function playStreamingAudio() {
    try {
        // For now, we'll collect all chunks and play them together
        // TODO: Implement true streaming playback
        
        // Wait a bit to collect chunks
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Combine all audio chunks
        const combinedBase64 = audioStreamBuffer.join('');
        audioStreamBuffer = []; // Clear buffer
        
        if (combinedBase64) {
            console.log('🔊 Playing combined realtime audio...');
            await playAudioFromBase64(combinedBase64);
        }
        
    } catch (error) {
        console.error('❌ Error playing streaming audio:', error);
    }
}

/**
 * Convert PCM16 base64 to WAV blob for playback
 */
function pcm16ToWav(base64Pcm16) {
    // Decode base64
    const pcmData = atob(base64Pcm16);
    const pcmBytes = new Uint8Array(pcmData.length);
    for (let i = 0; i < pcmData.length; i++) {
        pcmBytes[i] = pcmData.charCodeAt(i);
    }
    
    // WAV header configuration for PCM16
    const sampleRate = 24000; // Realtime API uses 24kHz
    const numChannels = 1; // Mono
    const bitsPerSample = 16;
    const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
    const blockAlign = numChannels * (bitsPerSample / 8);
    const dataSize = pcmBytes.length;
    
    // Create WAV header (44 bytes)
    const header = new ArrayBuffer(44);
    const view = new DataView(header);
    
    // "RIFF" chunk descriptor
    view.setUint32(0, 0x52494646, false); // "RIFF"
    view.setUint32(4, 36 + dataSize, true); // File size - 8
    view.setUint32(8, 0x57415645, false); // "WAVE"
    
    // "fmt " sub-chunk
    view.setUint32(12, 0x666d7420, false); // "fmt "
    view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
    view.setUint16(20, 1, true); // AudioFormat (1 = PCM)
    view.setUint16(22, numChannels, true); // NumChannels
    view.setUint32(24, sampleRate, true); // SampleRate
    view.setUint32(28, byteRate, true); // ByteRate
    view.setUint16(32, blockAlign, true); // BlockAlign
    view.setUint16(34, bitsPerSample, true); // BitsPerSample
    
    // "data" sub-chunk
    view.setUint32(36, 0x64617461, false); // "data"
    view.setUint32(40, dataSize, true); // Subchunk2Size
    
    // Combine header + PCM data
    const wavBytes = new Uint8Array(44 + dataSize);
    wavBytes.set(new Uint8Array(header), 0);
    wavBytes.set(pcmBytes, 44);
    
    return new Blob([wavBytes], { type: 'audio/wav' });
}

/**
 * Play audio from base64 encoded string
 */
async function playAudioFromBase64(base64Audio) {
    try {
        // Decode base64 to bytes
        const byteCharacters = atob(base64Audio);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        
        // Detect format by checking magic bytes
        let audioBlob;
        if (byteArray[0] === 0x4F && byteArray[1] === 0x67 && byteArray[2] === 0x67 && byteArray[3] === 0x53) {
            // "OggS" magic bytes - it's Opus
            audioBlob = new Blob([byteArray], { type: 'audio/ogg; codecs=opus' });
            console.log('🔊 Detected Opus audio format');
        } else {
            // Assume raw PCM16, convert to WAV
            audioBlob = pcm16ToWav(base64Audio);
            console.log('🔊 Converted PCM16 to WAV for playback');
        }
        
        // Use global audio player (already unlocked) or create new one
        const audio = globalAudioPlayer || new Audio();
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // Set source and reset player
        audio.src = audioUrl;
        audio.volume = 1.0;
        audio.currentTime = 0;
        audio.muted = false;
        
        // Cleanup handler
        const cleanup = () => {
            URL.revokeObjectURL(audioUrl);
            console.log('✅ Audio playback finished');
        };
        
        audio.onended = cleanup;
        
        audio.onerror = (error) => {
            console.error('❌ Audio playback error:', error);
            console.error('❌ Error details:', audio.error);
            cleanup();
            
            // Show user-friendly error on mobile
            showToast('Audio playback blocked - tap replay to hear', 'warning');
        };
        
        // Try to play - should work because player was unlocked during Start Speaking click
        try {
            const playPromise = audio.play();
            if (playPromise !== undefined) {
                await playPromise;
                console.log('🔊 Playing TTS audio via unlocked player');
            }
        } catch (playError) {
            console.warn('⚠️ Autoplay still blocked:', playError.message);
            console.log('💡 Use replay button to hear audio');
            // Don't throw - audio is still stored for replay
        }
        
    } catch (error) {
        console.error('❌ Failed to play audio from base64:', error);
    }
}

/**
 * Update microphone level visualization
 */
function updateMicLevel() {
    if (!audioContext || !audioStream) return;

    try {
        const analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(audioStream);
        source.connect(analyser);
        
        analyser.fftSize = 256;
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        
        const updateLevel = () => {
            if (!isRecording) return;
            
            analyser.getByteFrequencyData(dataArray);
            const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
            const level = Math.min(100, (average / 255) * 100);
            
            elements.micLevel.style.width = `${level}%`;
            
            requestAnimationFrame(updateLevel);
        };
        
        updateLevel();
        
    } catch (error) {
        console.error('Mic level error:', error);
    }
}

/**
 * Update latency display
 */
function updateLatency(latencyMs) {
    latencyStats.push(latencyMs);
    if (latencyStats.length > 10) latencyStats.shift();
    
    const avgLatency = latencyStats.reduce((a, b) => a + b, 0) / latencyStats.length;
    elements.latencyDisplay.textContent = `${avgLatency.toFixed(0)}ms avg`;
    
    // Color code by latency
    if (avgLatency < 2000) {
        elements.latencyDisplay.className = 'latency latency-good';
    } else if (avgLatency < 4000) {
        elements.latencyDisplay.className = 'latency latency-medium';
    } else {
        elements.latencyDisplay.className = 'latency latency-poor';
    }
}

/**
 * Trigger replay request - plays last translation
 */
function triggerReplay() {
    if (!lastTranslation) {
        showToast('No translation to replay', 'error');
        return;
    }

    // Ensure video section stays visible during replay
    const videoSection = document.getElementById('videoSection');
    if (videoSection && dailyCallActive) {
        videoSection.style.display = 'flex';
        videoSection.style.visibility = 'visible';
    }

    // Show replay UI
    elements.replayPlayer.classList.remove('hidden');
    
    // Display the last translation text (hide original for Icelandic)
    const isIcelandic = lastTranslation.source_lang === "is";
    const originalSection = isIcelandic ? '' : `
        <div style="margin-bottom: 10px;">
            <strong style="color: #64B5F6;">Original:</strong><br>
            <span style="font-size: 1.1em;">${lastTranslation.original || ''}</span>
        </div>
    `;
    
    elements.replaySubtitles.innerHTML = `
        <div style="padding: 15px; background: rgba(0,0,0,0.2); border-radius: 8px; margin-bottom: 10px;">
            ${originalSection}
            <div>
                <strong style="color: #81C784;">Translation:</strong><br>
                <span style="font-size: 1.1em;">${lastTranslation.translated}</span>
            </div>
        </div>
    `;
    
    // Play the audio if available
    if (lastTranslation.audio_base64) {
        try {
            // Decode base64 to blob
            const byteCharacters = atob(lastTranslation.audio_base64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            
            // Create blob and URL
            const audioBlob = new Blob([byteArray], { type: 'audio/ogg; codecs=opus' });
            const audioUrl = URL.createObjectURL(audioBlob);
            
            // Set audio source and play
            elements.replayAudio.src = audioUrl;
            elements.replayAudio.play();
            
            showToast('Replaying last translation', 'success');
        } catch (error) {
            console.error('Failed to replay audio:', error);
            showToast('Failed to replay audio', 'error');
        }
    } else {
        showToast('No audio available for replay', 'warning');
    }
}

/**
 * Load and display replay
 */
function loadReplay(data) {
    try {
        // Show replay player
        elements.replayPlayer.classList.remove('hidden');
        
        // Note: Audio and VTT will arrive as separate binary messages
        // For MVP, we'll handle them when they arrive
        
        showToast(`Replay ready: ${data.segments_count} segments`, 'success');
        
        // The audio blob will arrive next as binary data
        // We'll set it up in the binary message handler
        
        // Load VTT subtitles
        if (data.vtt) {
            displayReplaySubtitles(data.vtt);
        }
        
    } catch (error) {
        console.error('Replay load error:', error);
        showToast('Failed to load replay', 'error');
    }
}

/**
 * Display replay subtitles (WebVTT format)
 */
function displayReplaySubtitles(vttContent) {
    // For MVP, display VTT as formatted text
    // In production, you'd use <track> element with the audio player
    
    const subtitleDiv = elements.replaySubtitles;
    subtitleDiv.textContent = vttContent;
    subtitleDiv.style.whiteSpace = 'pre-wrap';
    subtitleDiv.style.fontFamily = 'monospace';
    subtitleDiv.style.fontSize = '0.9em';
}

/**
 * Handle language change from dropdown
 */
function handleLanguageChange() {
    // In room mode, warn that language changes aren't recommended mid-session
    if (currentRoom) {
        const confirmed = confirm(
            "⚠️ Changing languages mid-session can cause translation errors.\n\n" +
            "For best results, set your language before speaking.\n\n" +
            "Continue with language change?"
        );
        
        if (!confirmed) {
            // Revert to previous values (read from room data)
            // For now, just warn
            showToast('Language change cancelled', 'info');
            return;
        }
    }
    
    updateLanguages();
}

/**
 * Update language settings
 */
function updateLanguages() {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;

    const sourceLang = elements.sourceLang.value;
    const targetLang = elements.targetLang.value;

    // In room mode, always include participant_id
    const message = {
        action: 'set_language',
        source_lang: sourceLang,
        target_lang: targetLang
    };
    
    if (currentRoom && participantId) {
        message.participant_id = participantId;
        console.log(`🌍 Updating language settings with participant_id: ${participantId}`);
        showToast(`Language updated: ${sourceLang} → ${targetLang}`, 'success');
    }

    websocket.send(JSON.stringify(message));
}

/**
 * Update connection status
 */
function updateStatus(state, text) {
    elements.statusDot.className = `status-dot status-${state}`;
    elements.statusText.textContent = text;
    
    // Store status for i18n if needed
    elements.statusText.setAttribute('data-current-status', state);
}

/**
 * Update UI state based on recording status
 */
function updateUIState(state) {
    switch (state) {
        case 'recording':
            elements.startBtn.disabled = true;
            elements.stopBtn.disabled = false;
            elements.stopBtn.setAttribute('data-tooltip', 'Stop & Translate');
            updateStatus('recording', '🎤 Recording...');
            break;

        case 'connected':
            elements.startBtn.disabled = false;
            elements.stopBtn.disabled = true;
            elements.startBtn.setAttribute('data-tooltip', 'Start Speaking');
            updateStatus('connected', '✓ Ready for next recording');
            break;

        case 'stopped':
            elements.startBtn.disabled = false;
            elements.stopBtn.disabled = true;
            elements.startBtn.setAttribute('data-tooltip', 'Start Speaking');
            updateStatus('disconnected', 'Disconnected');
            elements.originalText.textContent = 'Waiting for speech...';
            elements.translatedText.textContent = 'Ready to translate...';
            break;
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    elements.toastContainer.appendChild(toast);

    // Animate in
    setTimeout(() => toast.classList.add('show'), 10);

    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Heartbeat to keep connection alive
 */
setInterval(() => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ action: 'ping' }));
    }
}, 30000); // Every 30 seconds

/**
 * Room Management Functions
 */

async function createRoom() {
    // Check if user is logged in (HOST requirement)
    if (!window.auth || !window.auth.isAuthenticated()) {
        alert('Please login to create a room. Only the host needs an account - guests can join without logging in!');
        return;
    }
    
    // Check if HOST has minutes remaining
    if (window.auth && window.auth.canStartCall) {
        const canStart = await window.auth.canStartCall();
        if (!canStart) {
            console.log('❌ Usage limit reached, cannot create room');
            return;
        }
    }
    
    // Prevent multiple clicks
    if (elements.createRoomBtn.disabled) {
        console.log('🏠 Create room already in progress...');
        return;
    }
    
    try {
        // Disable button to prevent multiple clicks
        elements.createRoomBtn.disabled = true;
        elements.createRoomBtn.textContent = 'Creating...';
        
        const user = window.auth.getCurrentUser();
        
        console.log('🏠 Creating room as HOST...');
        const backendUrl = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000'
            : 'https://livetranslateai.onrender.com';
            
        console.log(`🏠 Backend URL: ${backendUrl}`);
        const response = await fetch(`${backendUrl}/api/rooms/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.user_id })
        });
        
        console.log(`🏠 Response status: ${response.status}`);
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`🏠 API Error: ${response.status} - ${errorText}`);
            throw new Error(`Failed to create room: ${response.status} - ${errorText}`);
        }
        
        const data = await response.json();
        currentRoom = data.room_id;
        participantId = data.participant_id;  // Set participant ID from backend
        participantName = data.host_name || 'Host'; // Use host name from backend
        isHost = true;
        
        // Generate shareable link
        const shareableLink = `${window.location.origin}/room/${currentRoom}`;
        
        // Show FULL LINK in room code (not just code)
        elements.roomCode.textContent = shareableLink;
        elements.roomCode.style.fontSize = '0.85rem'; // Smaller font for long link
        elements.roomCode.style.wordBreak = 'break-all'; // Allow wrapping
        elements.participantCount.textContent = '1';
        elements.roomInfo.style.display = 'flex';
        
        // Hide room creation buttons
        elements.createRoomBtn.style.display = 'none';
        elements.joinRoomBtn.style.display = 'none';
        
        // Show shareable link message
        showToast(`Room link copied to clipboard! Share it with guests.`, 'success', 5000);
        
        // Copy link to clipboard automatically
        try {
            await navigator.clipboard.writeText(shareableLink);
            console.log('📋 Room link copied to clipboard:', shareableLink);
        } catch (e) {
            console.log('⚠️ Could not auto-copy link');
        }
        
        // Connect to room WebSocket
        await connectToRoom();
        
    } catch (error) {
        console.error('❌ Failed to create room:', error);
        showToast('Failed to create room', 'error');
        
        // Re-enable button on error
        elements.createRoomBtn.disabled = false;
        elements.createRoomBtn.textContent = 'Create Room';
    }
}

async function joinRoom() {
    // Prevent multiple clicks
    if (elements.joinRoomBtn.disabled) {
        console.log('🏠 Join room already in progress...');
        return;
    }
    
    const roomCode = prompt('Enter room code:');
    if (!roomCode) return;
    
    const enteredName = prompt('Enter your name:');
    if (!enteredName) return;
    
    try {
        // Disable button to prevent multiple clicks
        elements.joinRoomBtn.disabled = true;
        elements.joinRoomBtn.textContent = 'Joining...';
        const backendUrl = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000'
            : 'https://livetranslateai.onrender.com';
            
        const response = await fetch(`${backendUrl}/api/rooms/${roomCode}/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ participant_name: enteredName })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to join room');
        }
        
        const data = await response.json();
        currentRoom = roomCode;
        participantId = data.participant_id;
        participantName = enteredName; // Store the actual name
        isHost = false;
        
        // Show room info
        elements.roomCode.textContent = currentRoom;
        elements.participantCount.textContent = '2'; // Will be updated by WebSocket
        elements.roomInfo.style.display = 'flex';
        
        // Hide room creation buttons
        elements.createRoomBtn.style.display = 'none';
        elements.joinRoomBtn.style.display = 'none';
        
        showToast(`Joined room: ${currentRoom}`, 'success');
        
        // Connect to room WebSocket
        await connectToRoom();
        
    } catch (error) {
        console.error('❌ Failed to join room:', error);
        showToast(error.message, 'error');
        
        // Re-enable button on error
        elements.joinRoomBtn.disabled = false;
        elements.joinRoomBtn.textContent = 'Join Room';
    }
}

async function connectToRoom() {
    if (!currentRoom) return;
    
    const wsUrl = window.location.hostname === 'localhost' 
        ? `ws://localhost:8000/ws/room/${currentRoom}`
        : `wss://livetranslateai.onrender.com/ws/room/${currentRoom}`;
    
    try {
        websocket = new WebSocket(wsUrl);
        
        websocket.onopen = () => {
            console.log(`🏠 Connected to room: ${currentRoom}`);
            showToast('Connected to room', 'success');
            
            // Start call timer for live usage display
            callStartTime = Date.now();
            if (callTimerInterval) clearInterval(callTimerInterval);
            
            callTimerInterval = setInterval(() => {
                if (callStartTime && window.auth && window.auth.getCurrentUser()) {
                    const elapsedMinutes = (Date.now() - callStartTime) / 60000;
                    const user = window.auth.getCurrentUser();
                    
                    // Only update for free tier users (premium = unlimited)
                    if (user.tier === 'premium') {
                        return; // Skip for premium users
                    }
                    
                    // Show estimated remaining time during call
                    const estimatedUsed = (user.minutes_used || 0) + elapsedMinutes;
                    const remaining = Math.max(0, 15 - estimatedUsed);
                    
                    // Update profile bar with live estimate
                    const userTierElem = document.querySelector('.user-tier');
                    if (userTierElem && !isGuest) {
                        userTierElem.textContent = `Free Tier - ${remaining.toFixed(1)} min remaining (live)`;
                        userTierElem.style.color = remaining < 2 ? '#EF4444' : '#4F46E5';
                    }
                }
            }, 2000); // Update every 2 seconds for more responsive display
            
            // Start video call when WebSocket connects (auto-start on all devices)
            if (window.DailyIframe && !dailyCallActive) {
                const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
                
                console.log(`📹 Attempting to start video call (${isMobile ? 'mobile - optimized quality' : 'desktop - full quality'})...`);
                setTimeout(() => {
                    initializeVideoCall(isMobile).catch(err => {
                        console.error('📹 Video call failed:', err);
                        // Don't show error toast - video is optional
                    });
                }, 500); // Small delay to ensure room is fully set up
            }
            
            // Send language settings and user ID immediately after connection
            if (participantId) {
                const sourceLang = elements.sourceLang.value;
                const targetLang = elements.targetLang.value;
                
                // Get current user for usage tracking
                const user = window.auth ? window.auth.getCurrentUser() : null;
                const userId = user ? user.user_id : null;
                
                console.log(`🌍 Auto-sending language settings after connection: ${participantId}, user_id: ${userId}`);
                
                // Send identify with user_id for usage tracking
                websocket.send(JSON.stringify({
                    action: 'identify',
                    participant_id: participantId,
                    user_id: userId,
                    source_lang: sourceLang,
                    target_lang: targetLang
                }));
                
                // Also send set_language for backwards compatibility
                websocket.send(JSON.stringify({
                    action: 'set_language',
                    participant_id: participantId,
                    source_lang: sourceLang,
                    target_lang: targetLang
                }));
            }
        };
        
        websocket.onmessage = handleRoomMessage;
        websocket.onclose = () => {
            console.log('🏠 Room connection closed');
            showToast('Room connection lost', 'warning');
            
            // Stop call timer
            if (callTimerInterval) {
                clearInterval(callTimerInterval);
                callTimerInterval = null;
            }
            callStartTime = null;
            
            // Refresh usage from backend (get actual updated value)
            // Give backend 3 seconds to process the disconnect and update DB
            if (window.auth && window.auth.refreshUsage) {
                console.log('⏳ Waiting 3 seconds for backend to update usage...');
                setTimeout(async () => {
                    console.log('📊 Refreshing usage from backend...');
                    await window.auth.refreshUsage();
                    console.log('✅ Usage refreshed after call ended');
                    showToast('Usage updated', 'info');
                }, 3000); // Wait 3 sec for backend to update
            }
        };
        
        websocket.onerror = (error) => {
            console.error('🏠 Room WebSocket error:', error);
            showToast('Room connection error', 'error');
        };
        
    } catch (error) {
        console.error('❌ Failed to connect to room:', error);
        showToast('Failed to connect to room', 'error');
    }
}

function handleRoomMessage(event) {
    try {
        const message = JSON.parse(event.data);
        
        switch (message.type) {
            case 'room_update':
                elements.participantCount.textContent = message.participant_count;
                roomParticipants = message.participants; // Store participants
                updateParticipantList(roomParticipants);
                console.log(`🏠 Room update: ${message.participant_count} participants`);
                break;
                
            case 'language_update':
                // Update the specific participant's language settings
                const participant = roomParticipants.find(p => p.id === message.participant_id);
                if (participant) {
                    participant.source_lang = message.source_lang;
                    participant.target_lang = message.target_lang;
                    updateParticipantList(roomParticipants); // Refresh the display
                }
                console.log(`🌍 Language update: ${message.participant_id} set ${message.source_lang} → ${message.target_lang}`);
                break;
                
            case 'translation':
                console.log(`🔍 Received translation message:`, message);
                console.log(`🔍 My participant ID: ${participantId}, Target: ${message.target_participant}`);
                
                // Only handle translation if it's intended for this participant
                if (message.target_participant && message.target_participant !== participantId) {
                    console.log(`🔇 Ignoring translation for participant ${message.target_participant} (not for me)`);
                    break;
                }
                
                console.log(`✅ Processing translation for me!`);
                console.log(`🔍 Translation data - source_lang: ${message.source_lang}, target_lang: ${message.target_lang}`);
                console.log(`🔍 Original text (${message.source_lang}): "${message.original ? message.original.substring(0, 50) : '(hidden for Icelandic)'}..."`);
                console.log(`🔍 Translated text (${message.target_lang}): "${message.translated.substring(0, 50)}..."`);
                
                // Hide original text ONLY when source is Icelandic (workers don't need to see what they said)
                // BUT show it when target is Icelandic (workers need to see what refugees said)
                const hideOriginal = message.source_lang === "is";
                
                if (hideOriginal) {
                    // Hide the original text box when source is Icelandic
                    elements.originalText.textContent = "";
                    elements.originalText.parentElement.style.display = "none";
                } else {
                    // Show original text for other languages (including when target is Icelandic)
                    elements.originalText.parentElement.style.display = "";
                    elements.originalText.textContent = message.original || "";
                }
                
                elements.translatedText.textContent = message.translated;
                elements.latencyDisplay.textContent = `${message.latency_ms}ms`;
                
                // Store for replay
                lastTranslation = message;
                elements.replayBtn.disabled = false;
                if (elements.replayBtnSidebar) elements.replayBtnSidebar.disabled = false;
                
                // Play audio if available
                if (message.audio_base64) {
                    playAudioFromBase64(message.audio_base64);
                }
                break;
                
            case 'pong':
                console.log('🏠 Received pong from room');
                break;
                
            default:
                console.log('🏠 Unknown room message:', message);
        }
        
    } catch (error) {
        console.error('❌ Failed to parse room message:', error);
    }
}

function copyRoomCode() {
    // Always copy the full link, not just the code
    const fullLink = `${window.location.origin}/room/${currentRoom}`;
    
    navigator.clipboard.writeText(fullLink).then(() => {
        showToast('Room link copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy link', 'error');
    });
}

/**
 * Update participant list display
 */
function updateParticipantList(participants) {
    if (!participants || participants.length === 0) {
        elements.participantList.innerHTML = '<div style="color: var(--text-muted); font-size: 0.9em;">No participants</div>';
        return;
    }
    
    const languageNames = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'zh': 'Chinese',
        'ar': 'Arabic',
        'ru': 'Russian',
        'ja': 'Japanese',
        'ko': 'Korean',
        'pt': 'Portuguese',
        'it': 'Italian',
        'nl': 'Dutch',
        'hi': 'Hindi',
        'tr': 'Turkish',
        'vi': 'Vietnamese'
    };
    
    elements.participantList.innerHTML = participants.map((p, index) => {
        const isHost = index === 0;
        const isMe = p.id === participantId;
        const sourceLang = languageNames[p.source_lang] || p.source_lang;
        const targetLang = languageNames[p.target_lang] || p.target_lang;
        
        return `
            <div class="participant-item ${isHost ? 'host' : ''}">
                <span class="participant-name">${p.name}${isMe ? ' (You)' : ''}</span>
                ${isHost ? '<span class="participant-badge">Host</span>' : ''}
                <span class="participant-lang">${sourceLang} → ${targetLang}</span>
            </div>
        `;
    }).join('');
}

// UI Language selector
const uiLanguageSelect = document.getElementById('uiLanguage');
if (uiLanguageSelect) {
    // Set saved language on load
    const savedLang = localStorage.getItem('uiLanguage') || 'en';
    uiLanguageSelect.value = savedLang;
    
    // Apply saved language immediately
    if (typeof updateUILanguage === 'function') {
        updateUILanguage(savedLang);
    }
    
    // Handle language change
    uiLanguageSelect.addEventListener('change', (e) => {
        if (typeof updateUILanguage === 'function') {
            updateUILanguage(e.target.value);
            showToast(`Interface language: ${e.target.value.toUpperCase()}`, 'success');
        }
    });
}

// ===================================
// Daily.co Video Call Functions
// ===================================

async function initializeVideoCall(isMobileMode = false) {
    // Don't initialize if already active
    if (dailyCallActive || dailyCallFrame) {
        console.log('📹 Video call already active, skipping initialization');
        return;
    }
    
    try {
        console.log('📹 Initializing Daily.co video call...');
        console.log('📹 Current room:', currentRoom);
        console.log('📹 Participant ID:', participantId);
        console.log('📹 Mobile mode:', isMobileMode);
        
        // Request camera and microphone permissions first
        let stream;
        try {
            stream = await navigator.mediaDevices.getUserMedia({ 
                audio: true, 
                video: isMobileMode ? { width: 640, height: 480 } : true // Lower resolution on mobile
            });
            console.log('✅ Camera and microphone permissions granted');
            // Stop the tracks as Daily will handle them
            stream.getTracks().forEach(track => track.stop());
        } catch (permError) {
            console.warn('⚠️ Camera/microphone permission denied, trying audio only:', permError);
            try {
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                console.log('✅ Microphone permission granted (camera denied)');
                stream.getTracks().forEach(track => track.stop());
                isCameraOn = false; // Disable camera if permission denied
            } catch (audioError) {
                throw new Error('Microphone access required for video calls');
            }
        }
        
        // Show video section
        document.getElementById('videoSection').style.display = 'block';
        
        // Create Daily call frame with mobile-optimized settings
        dailyCallFrame = window.DailyIframe.createFrame(
            document.getElementById('dailyCallContainer'),
            {
                showLeaveButton: false,
                showFullscreenButton: false, // Disable Daily's fullscreen - we'll use custom one
                showLocalVideo: true,
                showParticipantsBar: false, // Hide participants bar to maximize video space
                iframeStyle: {
                    width: '100%',
                    height: '100%',
                    border: '0',
                    borderRadius: '8px',
                    position: 'absolute',
                    top: '0',
                    left: '0'
                }
            }
        );

        // Set up Daily event listeners
        dailyCallFrame
            .on('joined-meeting', handleJoinedMeeting)
            .on('participant-joined', handleParticipantJoined)
            .on('participant-left', handleParticipantLeft)
            .on('track-started', handleTrackStarted)
            .on('left-meeting', handleLeftMeeting)
            .on('error', handleDailyError);

        // Create Daily.co room via backend API
        console.log('📹 Creating Daily room via backend...');
        const backendUrl = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000'
            : 'https://livetranslateai.onrender.com';
            
        const dailyResponse = await fetch(`${backendUrl}/api/daily/create-room`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_name: currentRoom })
        });
        
        if (!dailyResponse.ok) {
            const errorData = await dailyResponse.json();
            throw new Error(errorData.error || 'Failed to create video room');
        }
        
        const dailyData = await dailyResponse.json();
        if (!dailyData.video_enabled) {
            throw new Error('Video calls not enabled on server');
        }
        
        const dailyRoomUrl = dailyData.url;
        console.log('📹 Joining Daily room:', dailyRoomUrl);
        
        // Join with mobile-optimized settings if needed
        const joinConfig = { 
            url: dailyRoomUrl,
            userName: participantName || 'Guest', // Use actual name, not ID
            videoSource: isCameraOn,
            audioSource: true
        };
        
        // Add mobile optimizations
        if (isMobileMode) {
            joinConfig.dailyConfig = {
                experimentalChromeVideoMuteLightOff: true,
                camSimulcastEncodings: [
                    { maxBitrate: 100000, scaleResolutionDownBy: 4 } // Lower quality for mobile
                ]
            };
        }
        
        // Configure Daily.co to use proper layout that doesn't crop videos
        await dailyCallFrame.join(joinConfig);
        
        // Set Daily.co layout to ensure all videos are visible
        try {
            // Use grid layout to show all participants properly
            await dailyCallFrame.setLayoutMode('grid');
            // Ensure videos are not cropped
            await dailyCallFrame.setBandwidth({
                video: 2000, // Higher bandwidth for better quality
                screenShare: 3000
            });
        } catch (layoutError) {
            console.warn('Could not set Daily.co layout:', layoutError);
            // Continue anyway - layout might not be available in all Daily.co versions
        }

        dailyCallActive = true;
        
        console.log('✅ Successfully joined Daily video call');
        showToast('Video call connected!', 'success');
        
    } catch (error) {
        console.error('❌ Failed to initialize video call:', error);
        showToast('Video call failed: ' + error.message, 'error');
        // Hide video section if failed
        document.getElementById('videoSection').style.display = 'none';
    }
}

function handleJoinedMeeting(event) {
    console.log('✅ Joined Daily meeting:', event);
}

function handleParticipantJoined(event) {
    console.log('👋 Participant joined:', event.participant.user_name);
    showToast(`${event.participant.user_name} joined the call`, 'info');
}

function handleParticipantLeft(event) {
    console.log('👋 Participant left:', event.participant.user_name);
    showToast(`${event.participant.user_name} left the call`, 'info');
}

function handleTrackStarted(event) {
    console.log('🎬 Track started:', event.track.kind, 'from', event.participant?.user_name);
    
    // Note: We're using push-to-talk for translation, not continuous audio from Daily
    // Future enhancement: Could implement continuous translation from Daily audio streams
    if (event.track.kind === 'audio' && !event.participant.local) {
        console.log('🎤 Remote audio track available (not used for translation yet)');
    }
}

function handleLeftMeeting() {
    console.log('📞 Left Daily meeting');
    dailyCallActive = false;
    document.getElementById('videoSection').style.display = 'none';
}

function handleDailyError(error) {
    console.error('❌ Daily.co error:', error);
    showToast('Video call error: ' + error.errorMsg, 'error');
}

function showMobileVideoPrompt() {
    // Show video section with a join button instead of auto-joining
    const videoSection = document.getElementById('videoSection');
    const dailyContainer = document.getElementById('dailyCallContainer');
    
    videoSection.style.display = 'block';
    dailyContainer.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; text-align: center;">
            <h3 style="margin-bottom: 1rem; font-size: 1.2rem;">📱 Video Call Available</h3>
            <p style="margin-bottom: 1.5rem; opacity: 0.9; font-size: 0.95rem;">Join the video call when you're ready. Note: Video calls may use more battery and data on mobile.</p>
            <button id="joinVideoBtn" style="
                background: white;
                color: #667eea;
                border: none;
                padding: 0.75rem 2rem;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            ">
                Join Video Call
            </button>
        </div>
    `;
    
    document.getElementById('joinVideoBtn').addEventListener('click', async () => {
        dailyContainer.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%;"><p style="color: #666;">Loading video...</p></div>';
        try {
            await initializeVideoCall(true); // Pass true for mobile mode
        } catch (err) {
            dailyContainer.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: #666;">
                    <p>Failed to join video call</p>
                    <button onclick="location.reload()" style="margin-top: 1rem; padding: 0.5rem 1rem; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer;">Try Again</button>
                </div>
            `;
        }
    });
}

async function toggleCamera() {
    if (!dailyCallFrame) return;
    
    try {
        isCameraOn = !isCameraOn;
        await dailyCallFrame.setLocalVideo(isCameraOn);
        document.getElementById('toggleCamera').textContent = isCameraOn ? '📹' : '🚫';
        console.log(`📹 Camera ${isCameraOn ? 'enabled' : 'disabled'}`);
        showToast(`Camera ${isCameraOn ? 'on' : 'off'}`, 'info');
    } catch (error) {
        console.error('Failed to toggle camera:', error);
    }
}

async function toggleMicrophone() {
    if (!dailyCallFrame) return;
    
    try {
        isMicOn = !isMicOn;
        await dailyCallFrame.setLocalAudio(isMicOn);
        document.getElementById('toggleMic').textContent = isMicOn ? '🎤' : '🔇';
        console.log(`🎤 Microphone ${isMicOn ? 'enabled' : 'disabled'}`);
        showToast(`Microphone ${isMicOn ? 'on' : 'off'}`, 'info');
    } catch (error) {
        console.error('Failed to toggle microphone:', error);
    }
}

// Custom fullscreen toggle - maintains side-by-side layout
function toggleCustomFullscreen() {
    const wrapper = document.querySelector('.video-translation-wrapper');
    if (!wrapper) return;
    
    const isFullscreen = wrapper.classList.contains('fullscreen-mode');
    const videoSection = document.getElementById('videoSection');
    
    if (isFullscreen) {
        // Exit fullscreen
        wrapper.classList.remove('fullscreen-mode');
        document.body.classList.remove('fullscreen-active'); // Remove class for CSS fallback
        document.getElementById('toggleFullscreen').textContent = '⛶';
        document.body.style.overflow = '';
        
        // Ensure video section stays visible after exiting fullscreen
        if (videoSection && dailyCallActive) {
            videoSection.style.display = 'flex';
            videoSection.style.visibility = 'visible';
            videoSection.style.opacity = '1';
            
            // Force Daily.co to recalculate layout after exiting fullscreen
            if (dailyCallFrame) {
                try {
                    // Use requestAnimationFrame for smoother transition
                    requestAnimationFrame(() => {
                        // Trigger resize events to force Daily.co to recalculate
                        window.dispatchEvent(new Event('resize'));
                        
                        // Also trigger a custom event that Daily.co might listen to
                        const resizeEvent = new UIEvent('resize', { bubbles: true, cancelable: false });
                        window.dispatchEvent(resizeEvent);
                        
                        // Force browser to recalculate layout for the container
                        const dailyContainer = document.getElementById('dailyCallContainer');
                        if (dailyContainer) {
                            // Temporarily force reflow to ensure proper sizing
                            const iframe = dailyContainer.querySelector('iframe');
                            if (iframe) {
                                // Reset iframe dimensions to force recalculation
                                const currentWidth = iframe.style.width;
                                const currentHeight = iframe.style.height;
                                iframe.style.width = '99%';
                                iframe.style.height = '99%';
                                dailyContainer.offsetHeight; // Trigger reflow
                                iframe.style.width = currentWidth || '100%';
                                iframe.style.height = currentHeight || '100%';
                            }
                        }
                    });
                } catch (error) {
                    console.warn('Could not refresh Daily.co layout:', error);
                }
            }
        }
    } else {
        // Enter fullscreen
        wrapper.classList.add('fullscreen-mode');
        document.body.classList.add('fullscreen-active'); // Add class for CSS fallback
        document.getElementById('toggleFullscreen').textContent = '⛶';
        document.body.style.overflow = 'hidden';
        
        // Ensure video section is visible when entering fullscreen
        if (videoSection && dailyCallActive) {
            videoSection.style.display = 'flex';
            videoSection.style.visibility = 'visible';
        }
    }
}

async function leaveVideoCall() {
    if (!dailyCallFrame) return;
    
    // Exit fullscreen if active
    const wrapper = document.querySelector('.video-translation-wrapper');
    if (wrapper) {
        wrapper.classList.remove('fullscreen-mode');
        document.body.style.overflow = '';
    }
    
    try {
        await dailyCallFrame.leave();
        dailyCallFrame.destroy();
        dailyCallFrame = null;
        dailyCallActive = false;
        document.getElementById('videoSection').style.display = 'none';
        console.log('📞 Left video call');
        showToast('Left video call', 'info');
    } catch (error) {
        console.error('Failed to leave call:', error);
    }
}

// Show mobile video tip if on mobile device
const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
if (isMobileDevice) {
    const mobileVideoTip = document.getElementById('mobileVideoTip');
    if (mobileVideoTip) {
        mobileVideoTip.style.display = 'block';
    }
}

// Initialize on load
console.log('🚀 LiveTranslateAI initialized');

