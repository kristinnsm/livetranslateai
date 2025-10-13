"""
Buffer management for replay feature
Handles in-memory storage of translation segments with timestamps
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import io
import base64

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None

logger = logging.getLogger(__name__)


class BufferManager:
    """
    Manages translation buffers for replay functionality
    Privacy-focused: in-memory only, auto-pruning
    """
    
    def __init__(self, max_duration: int = 300):
        """
        Initialize buffer manager
        
        Args:
            max_duration: Maximum buffer duration in seconds
        """
        self.max_duration = max_duration
        self.segments: List[Dict] = []
        logger.info(f"BufferManager initialized: max {max_duration}s")
    
    def add_segment(
        self,
        timestamp: float,
        original_text: str,
        translated_text: str,
        audio_data: Optional[bytes],
        source_lang: str,
        target_lang: str
    ):
        """
        Add a translation segment to buffer
        
        Args:
            timestamp: Segment timestamp
            original_text: Original transcription
            translated_text: Translated text
            audio_data: TTS audio bytes (MP3)
            source_lang: Source language code
            target_lang: Target language code
        """
        segment = {
            "timestamp": timestamp,
            "original_text": original_text,
            "translated_text": translated_text,
            "audio_data": audio_data,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "added_at": datetime.utcnow().isoformat()
        }
        
        self.segments.append(segment)
        
        # Auto-prune old segments
        self._prune_old_segments()
        
        logger.debug(f"Segment added: {len(self.segments)} total")
    
    def _prune_old_segments(self):
        """Remove segments older than max_duration"""
        if not self.segments:
            return
        
        current_time = datetime.utcnow().timestamp()
        cutoff_time = current_time - self.max_duration
        
        # Keep only recent segments
        self.segments = [
            seg for seg in self.segments 
            if seg["timestamp"] >= cutoff_time
        ]
    
    def get_segments(self, last_n_seconds: int = None) -> List[Dict]:
        """
        Retrieve buffered segments
        
        Args:
            last_n_seconds: Get only segments from last N seconds (optional)
        
        Returns:
            List of segments
        """
        if last_n_seconds is None:
            return self.segments.copy()
        
        cutoff_time = datetime.utcnow().timestamp() - last_n_seconds
        return [
            seg for seg in self.segments 
            if seg["timestamp"] >= cutoff_time
        ]
    
    def export_replay(self, segments: List[Dict]) -> tuple[bytes, str]:
        """
        Generate replay package: concatenated audio + WebVTT subtitles
        
        Args:
            segments: Segments to include in replay
        
        Returns:
            Tuple of (audio_bytes, vtt_string)
        """
        if not segments:
            return b"", ""
        
        # Sort by timestamp
        segments = sorted(segments, key=lambda x: x["timestamp"])
        
        # Concatenate audio
        audio_data = self._concat_audio(segments)
        
        # Generate WebVTT subtitles
        vtt_data = self._generate_webvtt(segments)
        
        logger.info(f"Replay exported: {len(segments)} segments, {len(audio_data)} bytes audio")
        return audio_data, vtt_data
    
    def _concat_audio(self, segments: List[Dict]) -> bytes:
        """Concatenate MP3 audio segments using pydub"""
        if not PYDUB_AVAILABLE:
            logger.warning("pydub not available - returning first segment audio only")
            # Fallback: just return the first segment's audio
            for segment in segments:
                if segment.get("audio_data"):
                    return segment["audio_data"]
            return b""
        
        try:
            combined = AudioSegment.empty()
            
            for segment in segments:
                if segment.get("audio_data"):
                    audio_segment = AudioSegment.from_mp3(io.BytesIO(segment["audio_data"]))
                    combined += audio_segment
                else:
                    # Add silence placeholder (500ms)
                    combined += AudioSegment.silent(duration=500)
            
            # Export as MP3
            output = io.BytesIO()
            combined.export(output, format="mp3", bitrate="128k")
            return output.getvalue()
        
        except Exception as e:
            logger.error(f"Audio concatenation error: {e}")
            return b""
    
    def _generate_webvtt(self, segments: List[Dict]) -> str:
        """Generate WebVTT subtitle file from segments"""
        # Start with WebVTT header
        vtt_lines = ["WEBVTT", ""]
        
        # Normalize timestamps (start from 0)
        if segments:
            start_timestamp = segments[0]["timestamp"]
        else:
            start_timestamp = 0
        
        for i, segment in enumerate(segments):
            # Calculate relative time
            rel_time = segment["timestamp"] - start_timestamp
            
            # Format: HH:MM:SS.mmm
            start_time = self._format_timestamp(rel_time)
            
            # Estimate duration (3s per segment, or until next segment)
            if i < len(segments) - 1:
                duration = segments[i + 1]["timestamp"] - segment["timestamp"]
            else:
                duration = 3.0  # Default 3 seconds for last segment
            
            end_time = self._format_timestamp(rel_time + duration)
            
            # Add cue
            vtt_lines.append(f"{i + 1}")
            vtt_lines.append(f"{start_time} --> {end_time}")
            vtt_lines.append(segment["translated_text"])
            vtt_lines.append("")  # Blank line between cues
        
        return "\n".join(vtt_lines)
    
    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds to WebVTT timestamp (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def clear(self):
        """Clear all buffered segments (for privacy)"""
        self.segments.clear()
        logger.info("Buffer cleared")
    
    def get_stats(self) -> Dict:
        """Get buffer statistics"""
        return {
            "total_segments": len(self.segments),
            "max_duration": self.max_duration,
            "oldest_timestamp": self.segments[0]["timestamp"] if self.segments else None,
            "newest_timestamp": self.segments[-1]["timestamp"] if self.segments else None
        }

