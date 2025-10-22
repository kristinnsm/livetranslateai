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

// DOM elements
const elements = {
    startBtn: document.getElementById('startBtn'),
    stopBtn: document.getElementById('stopBtn'),
    disconnectBtn: document.getElementById('disconnectBtn'),
    replayBtn: document.getElementById('replayBtn'),
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
    toastContainer: document.getElementById('toastContainer')
};

// Event Listeners
elements.startBtn.addEventListener('click', startTranslation);
elements.stopBtn.addEventListener('click', stopTranslation);
elements.disconnectBtn.addEventListener('click', disconnectSession);
elements.replayBtn.addEventListener('click', triggerReplay);
elements.sourceLang.addEventListener('change', updateLanguages);
elements.targetLang.addEventListener('change', updateLanguages);

/**
 * Start translation session
 */
async function startTranslation() {
    try {
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

        // Setup WebSocket connection
        await connectWebSocket();

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
                elements.replayBtn.disabled = false;
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
    // Update original text
    if (data.original) {
        elements.originalText.textContent = data.original;
        elements.originalText.classList.add('fade-in');
        setTimeout(() => elements.originalText.classList.remove('fade-in'), 500);
    }

    // Update translated text
    if (data.translated) {
        elements.translatedText.textContent = data.translated;
        elements.translatedText.classList.add('fade-in');
        setTimeout(() => elements.translatedText.classList.remove('fade-in'), 500);
    }

    console.log(`Translation: "${data.original}" → "${data.translated}" (${data.latency_ms}ms)`);
    
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
        
        // Create audio element and play
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        
        audio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            console.log('✅ Audio playback finished');
        };
        
        audio.onerror = (error) => {
            console.error('❌ Audio playback error:', error);
            URL.revokeObjectURL(audioUrl);
        };
        
        await audio.play();
        console.log('🔊 Playing TTS audio');
        
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
 * Trigger replay request
 */
function triggerReplay() {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
        showToast('Not connected', 'error');
        return;
    }

    const duration = parseInt(elements.replayDuration.value);
    
    websocket.send(JSON.stringify({
        action: 'replay',
        duration: duration
    }));

    showToast(`Generating ${duration}s replay...`, 'info');
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
 * Update language settings
 */
function updateLanguages() {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;

    const sourceLang = elements.sourceLang.value;
    const targetLang = elements.targetLang.value;

    websocket.send(JSON.stringify({
        action: 'set_language',
        source_lang: sourceLang,
        target_lang: targetLang
    }));
}

/**
 * Update connection status
 */
function updateStatus(state, text) {
    elements.statusDot.className = `status-dot status-${state}`;
    elements.statusText.textContent = text;
}

/**
 * Update UI state based on recording status
 */
function updateUIState(state) {
    switch (state) {
        case 'recording':
            elements.startBtn.disabled = true;
            elements.stopBtn.disabled = false;
            elements.disconnectBtn.disabled = false;
            updateStatus('recording', '🎤 Recording...');
            break;

        case 'connected':
            elements.startBtn.disabled = false;
            elements.stopBtn.disabled = true;
            elements.disconnectBtn.disabled = false;
            updateStatus('connected', '✓ Ready for next recording');
            break;

        case 'stopped':
            elements.startBtn.disabled = false;
            elements.stopBtn.disabled = true;
            elements.disconnectBtn.disabled = true;
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

// Initialize on load
console.log('🚀 LiveTranslateAI initialized');

