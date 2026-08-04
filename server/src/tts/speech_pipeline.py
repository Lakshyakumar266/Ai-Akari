from __future__ import annotations

from .audio_player import AudioPlayer
from .fish_stream import FishStream


class SpeechPipeline:
    """
    High-level speech pipeline.

    LLM text
        ↓
    Fish Audio (streaming)
        ↓
    Binary WebSocket → Browser
        ↓
    Web Audio API (AudioQueue → AudioPlayer)
        ↓
    AnalyserNode → RMS → VRM mouth expressions

    No viseme timelines. No synchronization. One clock: AudioContext.currentTime.
    """

    def __init__(self):
        self.stream = FishStream()
        self.player = AudioPlayer()

    def speak(self, text: str) -> None:
        print("[Pipeline] Starting")
        stream = self.stream.stream(text)
        self.player.play(stream)
        print("[Pipeline] Finished")
