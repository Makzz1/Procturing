import numpy as np
import librosa
import torch
import noisereduce as nr
from pydub import AudioSegment
import io
import logging
from typing import Optional

# --- Params ---
SR = 16000
MIN_SPEECH_DURATION = 0.3
# ---------------

logger = logging.getLogger(__name__)

# Global variables for the model (loaded once)
_model = None
_utils = None

def initialize_speech_detection():
    """Initialize the Silero VAD model (call once at startup)"""
    global _model, _utils
    try:
        logger.info("Loading Silero VAD model...")
        _model, _utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False
        )
        logger.info("Silero VAD model loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to load Silero VAD model: {e}")
        return False

def has_voicing(segment, sr):
    """Check harmonic/voiced structure (rejects claps, bangs)."""
    try:
        f0, voiced_flag, _ = librosa.pyin(segment, fmin=50, fmax=400, sr=sr)
        if voiced_flag is None or np.isnan(voiced_flag).all():
            return False
        return np.nanmean(voiced_flag.astype(float)) > 0.15
    except Exception:
        return False

def detect_speech_from_bytes(audio_bytes: bytes, mime_type: str = "audio/webm") -> bool:
    """
    Detect if an audio chunk contains human speech.
    
    Args:
        audio_bytes: Raw audio data as bytes
        mime_type: MIME type of the audio (e.g., 'audio/webm', 'audio/wav')
    
    Returns:
        True if human speech is detected, False otherwise
    """
    global _model, _utils
    
    if _model is None or _utils is None:
        logger.error("Speech detection model not initialized")
        return False
    
    try:
        # Get the speech detection function
        get_speech_timestamps = _utils[0]
        
        # Load audio from bytes using pydub
        audio_io = io.BytesIO(audio_bytes)
        
        # Determine format from mime type
        if "webm" in mime_type.lower():
            format = "webm"
        elif "wav" in mime_type.lower():
            format = "wav"
        elif "mp3" in mime_type.lower():
            format = "mp3"
        else:
            format = "webm"  # default
        
        # Load with pydub
        audio = AudioSegment.from_file(audio_io, format=format)
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        samples /= np.iinfo(audio.array_type).max  # normalize

        if audio.channels == 2:
            samples = samples.reshape((-1, 2))
            samples = samples.mean(axis=1)  # convert to mono

        # Resample to SR
        wav = librosa.resample(samples, orig_sr=audio.frame_rate, target_sr=SR).astype(np.float32)

        # Optional denoise
        try:
            wav = nr.reduce_noise(y=wav, sr=SR)
        except:
            pass

        # Run Silero VAD
        speech_segments = get_speech_timestamps(wav, _model, sampling_rate=SR)

        for seg in speech_segments:
            start, end = seg["start"], seg["end"]
            dur = (end - start) / SR
            if dur < MIN_SPEECH_DURATION:
                continue
            segment = wav[start:end]
            if has_voicing(segment, SR):
                logger.info(f"Human speech detected in audio chunk (duration: {dur:.2f}s)")
                return True

        return False
        
    except Exception as e:
        logger.error(f"Error in speech detection: {e}")
        return False

def detect_speech_from_file(file_path: str) -> bool:
    """
    Detect if an audio file contains human speech.
    This is the original function for debugging purposes.
    """
    global _model, _utils
    
    if _model is None or _utils is None:
        logger.error("Speech detection model not initialized")
        return False
        
    try:
        get_speech_timestamps = _utils[0]
        
        # Load with pydub (handles webm, wav, mp3…)
        audio = AudioSegment.from_file(file_path)
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        samples /= np.iinfo(audio.array_type).max  # normalize

        if audio.channels == 2:
            samples = samples.reshape((-1, 2))
            samples = samples.mean(axis=1)  # convert to mono

        # Resample to SR
        wav = librosa.resample(samples, orig_sr=audio.frame_rate, target_sr=SR).astype(np.float32)

        # Optional denoise
        try:
            wav = nr.reduce_noise(y=wav, sr=SR)
        except:
            pass

        # Run Silero VAD
        speech_segments = get_speech_timestamps(wav, _model, sampling_rate=SR)

        for seg in speech_segments:
            start, end = seg["start"], seg["end"]
            dur = (end - start) / SR
            if dur < MIN_SPEECH_DURATION:
                continue
            segment = wav[start:end]
            if has_voicing(segment, SR):
                return True

        return False
        
    except Exception as e:
        logger.error(f"Error in speech detection from file: {e}")
        return False