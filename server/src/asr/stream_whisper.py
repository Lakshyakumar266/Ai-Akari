"""
Streaming Whisper ASR
---------------------
Dedicated single-model Whisper service for real-time WebSocket audio streaming.
Loads ONLY when chat/browser voice input is enabled.
Uses a single fast model (tiny.en, ~75MB RAM, ~0.3s on CPU) for both live interim
and final transcription to avoid choking CPU or RAM.
"""

from __future__ import annotations

import numpy as np
from faster_whisper import WhisperModel

MODEL_CACHE_DIR = "E:/HuggingFace_Cache/faster-whisper"
STREAMING_MODEL_NAME = "medium"

# Exactly ONE model instance for all streaming operations
_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        print(f"[ASR] Loading streaming Whisper model '{STREAMING_MODEL_NAME}'...")
        _model = WhisperModel(
            STREAMING_MODEL_NAME,
            device="cpu",
            compute_type="int8",
            download_root=MODEL_CACHE_DIR,
        )
        print(f"[ASR] Streaming Whisper model '{STREAMING_MODEL_NAME}' ready.")
    return _model


def transcribe_stream_interim(audio: np.ndarray) -> str:
    """Fast interim transcription during active speech (runs every ~0.5s)."""
    if audio.size == 0:
        return ""
    rms = float(np.sqrt(np.mean(audio**2)))
    if rms < 0.003:
        return ""

    model = _get_model()
    segments, _ = model.transcribe(
        audio,
        language="en",
        beam_size=1,
        best_of=1,
        temperature=0,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=250),
        without_timestamps=True,
        word_timestamps=False,
        no_speech_threshold=0.5,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


def transcribe_stream_final(audio: np.ndarray) -> str:
    """Final transcription on recording stop using the same model instance."""
    if audio.size == 0:
        return ""
    rms = float(np.sqrt(np.mean(audio**2)))
    if rms < 0.003:
        return ""

    model = _get_model()
    segments, _ = model.transcribe(
        audio,
        language="en",
        beam_size=1,
        best_of=1,
        temperature=0,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=250),
        without_timestamps=True,
        word_timestamps=False,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
        no_speech_threshold=0.5,
        repetition_penalty=1.05,
        hallucination_silence_threshold=2.0,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
