"""
Traditional translation pipeline: Whisper STT → GPT Translation → TTS
Fallback approach with ~3-5s latency
"""

import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import io

from services.audio_processor import AudioProcessor
from utils.logger import setup_logger

logger = setup_logger(__name__)


class TraditionalTranslator:
    """
    Sequential pipeline: Whisper → GPT → TTS
    More reliable but higher latency than Realtime API
    """
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.source_lang = "en"
        self.target_lang = "es"
        self.audio_processor = AudioProcessor()
        
        # Accumulator for better transcription (overlapping context)
        self.audio_buffer = bytearray()
        self.previous_transcript = ""
        
        logger.info("TraditionalTranslator initialized (Whisper + GPT + TTS)")
    
    def set_languages(self, source_lang: str, target_lang: str):
        """Update translation language pair"""
        self.source_lang = source_lang
        self.target_lang = target_lang
        logger.info(f"Languages set: {source_lang} → {target_lang}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def transcribe_audio_webm(self, audio_data: bytes) -> Optional[Dict]:
        """
        Transcribe WebM/Opus audio using Whisper API with retry logic
        
        Args:
            audio_data: Raw WebM audio bytes
        
        Returns:
            Transcription result with text and language
        """
        try:
            # Create file-like object with WebM audio
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.webm"
            
            # Whisper transcription with context (WebM format is supported)
            response = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=self.source_lang if self.source_lang != "auto" else None,
                prompt=self.previous_transcript[-200:] if self.previous_transcript else None,
                response_format="verbose_json"
            )
            
            return {
                "text": response.text,
                "language": response.language if hasattr(response, 'language') else self.source_lang,
                "confidence": getattr(response, 'confidence', 0.9)
            }
        
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def transcribe_audio(self, audio_data: bytes) -> Optional[Dict]:
        """
        Transcribe audio using Whisper API with retry logic
        
        Args:
            audio_data: Raw PCM audio
        
        Returns:
            Transcription result with text and language
        """
        try:
            # Convert to WAV for Whisper
            wav_data = self.audio_processor.convert_to_wav(audio_data)
            
            # Create file-like object
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "audio.wav"
            
            # Whisper transcription with context
            # Build prompt: previous transcript + Icelandic-specific vocabulary if needed
            whisper_prompt = None
            if self.previous_transcript:
                whisper_prompt = self.previous_transcript[-200:]
            
            # Add Icelandic-specific vocabulary to improve transcription accuracy
            if self.source_lang == "is":
                icelandic_vocab = "Þetta er íslenskur texti með íslenskum stöfum: ð, þ, æ, ö. Algeng orð og setningar: vandamálið, prófum, prófa, prófað, prófun, þýðing, þýðingin, þýðingar, þýða, þýðir, þýddi, spænska, spænsku, íslenska, íslensku, íslenskar, íslenskum, nokkurnvegin, nokkurn veginn, rétt, réttur, réttur, rétt, réttri, réttum, textinn, texti, texta, þarf, þarft, þurfa, þurftu, nákvæmlega, nákvæmur, nákvæmt, getur, geta, getum, getið, gettu, leiðinlegt, leiðinlegur, leiðinleg, sjáum, sjá, sér, séð, smátt, smá, smáir, smáar, smáum, hversu, hversu mikið, hversu lengi, ættir, ætti, ættum, ættuð, ættu, appið, app, appi, appin."
                if whisper_prompt:
                    whisper_prompt = f"{icelandic_vocab} {whisper_prompt}"
                else:
                    whisper_prompt = icelandic_vocab
            
            response = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=self.source_lang if self.source_lang != "auto" else None,
                prompt=whisper_prompt,
                response_format="verbose_json"
            )
            
            return {
                "text": response.text,
                "language": response.language if hasattr(response, 'language') else self.source_lang,
                "confidence": getattr(response, 'confidence', 0.9)
            }
        
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def translate_text(self, text: str, source_lang: str) -> str:
        """
        Translate text using GPT with retry logic
        
        Args:
            text: Source text
            source_lang: Detected source language
        
        Returns:
            Translated text
        """
        try:
            # Translation prompt optimized for natural conversation with Icelandic-specific instructions
            icelandic_instructions = ""
            if self.target_lang == "is" or source_lang == "is":
                icelandic_instructions = """
CRITICAL for Icelandic: Use correct spelling and grammar. Pay special attention to:
- Special characters: ð (eth), þ (thorn), æ, ö
- Correct declensions and conjugations
- Proper capitalization (Icelandic uses lowercase for most nouns)
- Natural Icelandic word order
"""
            
            system_prompt = f"""You are a professional real-time translator specializing in accurate, natural translations.
Translate the following from {source_lang} to {self.target_lang}.
{icelandic_instructions}
Maintain natural conversational tone, slang, and emotional context.
Keep translations concise and accurate. Use correct spelling, grammar, and punctuation.
Previous context: {self.previous_transcript[-150:] if self.previous_transcript else 'None'}"""

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"Translation error: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def synthesize_speech(self, text: str) -> bytes:
        """
        Generate speech using OpenAI TTS
        
        Args:
            text: Text to synthesize
        
        Returns:
            MP3 audio bytes
        """
        try:
            response = await self.client.audio.speech.create(
                model="tts-1-hd",  # High-quality TTS model
                voice="nova",  # Clear, warm voice (Options: alloy, echo, fable, onyx, nova, shimmer)
                input=text,
                response_format="mp3",
                speed=1.0
            )
            
            # Read audio bytes (compatible with openai 1.3.0)
            audio_bytes = b""
            for chunk in response.iter_bytes():
                audio_bytes += chunk
            
            return audio_bytes
        
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise
    
    async def process_audio(self, audio_chunk: bytes, timestamp: float, heartbeat_callback=None) -> Optional[Dict]:
        """
        Full pipeline: STT → Translation → TTS
        
        Args:
            audio_chunk: Raw PCM audio
            timestamp: Chunk timestamp
        
        Returns:
            Complete translation result
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"[TRANSLATOR] Processing complete WebM file: {len(audio_chunk)} bytes")
            
            # Skip very small chunks (< 2KB) - likely incomplete
            min_chunk_size = 2000
            if len(audio_chunk) < min_chunk_size:
                logger.info(f"Chunk too small ({len(audio_chunk)} bytes), skipping...")
                return None
            
            # Step 1: Transcribe complete WebM file directly (no buffering needed)
            logger.info("Sending complete WebM to Whisper...")
            if heartbeat_callback:
                await heartbeat_callback()
            transcription = await self.transcribe_audio_webm(audio_chunk)
            if not transcription or not transcription["text"].strip():
                logger.warning("No transcription result or empty text")
                return None
            
            original_text = transcription["text"]
            detected_lang = transcription["language"]
            logger.info(f"Transcription: '{original_text}' (lang: {detected_lang})")
            
            # Step 2: Translate
            logger.info("Starting translation...")
            if heartbeat_callback:
                await heartbeat_callback()
            translated_text = await self.translate_text(original_text, detected_lang)
            logger.info(f"Translation: '{translated_text}'")
            
            # Step 3: Synthesize speech
            logger.info("Starting TTS...")
            if heartbeat_callback:
                await heartbeat_callback()
            audio_data = await self.synthesize_speech(translated_text)
            logger.info(f"TTS generated {len(audio_data)} bytes")
            
            # Update context
            self.previous_transcript = original_text
            
            # Calculate total latency
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            result = {
                "original_text": original_text,
                "translated_text": translated_text,
                "source_lang": detected_lang,
                "target_lang": self.target_lang,
                "latency_ms": latency_ms,
                "audio_data": audio_data,
                "timestamp": timestamp,
                "confidence": transcription.get("confidence", 0.0)
            }
            
            logger.info(f"Pipeline completed in {latency_ms:.0f}ms: '{original_text[:50]}...' -> '{translated_text[:50]}...'")
            return result
        
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            return None

