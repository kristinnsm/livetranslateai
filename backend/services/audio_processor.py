"""
Audio processing utilities: VAD, chunking, format conversion
"""

try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    # Create a dummy webrtcvad module for compatibility
    class DummyVAD:
        def __init__(self, *args, **kwargs):
            pass
        def is_speech(self, *args, **kwargs):
            return True  # Always return True when VAD is not available
    webrtcvad = type('webrtcvad', (), {'Vad': DummyVAD})()
    
import numpy as np
from typing import Optional
import struct
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Handles audio chunk processing and Voice Activity Detection"""
    
    def __init__(self, sample_rate: int = 16000, vad_aggressiveness: int = 2):
        """
        Initialize audio processor
        
        Args:
            sample_rate: Audio sample rate (8000, 16000, 32000, or 48000 Hz)
            vad_aggressiveness: VAD sensitivity (0-3, higher = more aggressive)
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = 30  # 10, 20, or 30 ms frames for VAD
        
        if VAD_AVAILABLE:
            self.vad = webrtcvad.Vad(vad_aggressiveness)
            logger.info(f"AudioProcessor initialized: {sample_rate}Hz, VAD={vad_aggressiveness}")
        else:
            self.vad = None
            logger.warning("webrtcvad not available - all audio will be processed (no silence filtering)")
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Check if audio chunk contains speech using VAD
        
        Args:
            audio_chunk: Raw PCM audio bytes (16-bit)
        
        Returns:
            True if speech detected, False otherwise
        """
        # If VAD not available, assume all audio is speech
        if not VAD_AVAILABLE or self.vad is None:
            return True
        
        try:
            # Ensure chunk is correct length for VAD (10, 20, or 30ms)
            frame_size = int(self.sample_rate * self.frame_duration_ms / 1000) * 2  # 2 bytes per sample
            
            if len(audio_chunk) < frame_size:
                # Pad if too short
                audio_chunk = audio_chunk.ljust(frame_size, b'\x00')
            elif len(audio_chunk) > frame_size:
                # Truncate if too long
                audio_chunk = audio_chunk[:frame_size]
            
            return self.vad.is_speech(audio_chunk, self.sample_rate)
        
        except Exception as e:
            logger.warning(f"VAD error: {e}, assuming speech")
            return True  # Fail open to avoid dropping valid audio
    
    def convert_to_wav(self, audio_data: bytes, sample_rate: int = None) -> bytes:
        """
        Convert audio data to WAV format for Whisper API
        Handles both PCM data and WebM/Opus data
        
        Args:
            audio_data: Raw audio bytes (PCM or WebM)
            sample_rate: Sample rate (defaults to instance sample_rate)
        
        Returns:
            WAV file bytes
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        # Check if it's WebM/Opus data (starts with WebM signature)
        if audio_data.startswith(b'\x1a\x45\xdf\xa3'):
            logger.warning("WebM/Opus audio detected - using raw data as WAV (may cause issues)")
            # For now, treat WebM data as if it were PCM and create a WAV header
            # This is a temporary workaround - in production you'd use FFmpeg
            pcm_data = audio_data
        else:
            # Assume it's already PCM data
            pcm_data = audio_data
        
        # WAV header construction
        wav_buffer = BytesIO()
        
        # RIFF header
        wav_buffer.write(b'RIFF')
        wav_buffer.write(struct.pack('<I', len(pcm_data) + 36))  # File size - 8
        wav_buffer.write(b'WAVE')
        
        # fmt chunk
        wav_buffer.write(b'fmt ')
        wav_buffer.write(struct.pack('<I', 16))  # fmt chunk size
        wav_buffer.write(struct.pack('<H', 1))   # PCM format
        wav_buffer.write(struct.pack('<H', 1))   # Mono
        wav_buffer.write(struct.pack('<I', sample_rate))
        wav_buffer.write(struct.pack('<I', sample_rate * 2))  # Byte rate
        wav_buffer.write(struct.pack('<H', 2))   # Block align
        wav_buffer.write(struct.pack('<H', 16))  # Bits per sample
        
        # data chunk
        wav_buffer.write(b'data')
        wav_buffer.write(struct.pack('<I', len(pcm_data)))
        wav_buffer.write(pcm_data)
        
        return wav_buffer.getvalue()
    
    def create_overlapping_chunks(self, audio_data: bytes, chunk_size: int, overlap: float = 0.5):
        """
        Split audio into overlapping chunks for better transcription
        
        Args:
            audio_data: Audio bytes
            chunk_size: Size of each chunk in bytes
            overlap: Overlap ratio (0.0 to 1.0)
        
        Yields:
            Overlapping audio chunks
        """
        stride = int(chunk_size * (1 - overlap))
        
        for i in range(0, len(audio_data), stride):
            chunk = audio_data[i:i + chunk_size]
            if len(chunk) >= chunk_size // 2:  # Yield if at least half full
                yield chunk
    
    def normalize_audio(self, audio_data: bytes) -> bytes:
        """
        Normalize audio levels to improve transcription
        
        Args:
            audio_data: Raw PCM audio bytes
        
        Returns:
            Normalized audio bytes
        """
        try:
            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Normalize to 70% of max to avoid clipping
            max_val = np.abs(audio_array).max()
            if max_val > 0:
                normalized = (audio_array * (32767 * 0.7 / max_val)).astype(np.int16)
                return normalized.tobytes()
            
            return audio_data
        
        except Exception as e:
            logger.warning(f"Normalization error: {e}, returning original")
            return audio_data

