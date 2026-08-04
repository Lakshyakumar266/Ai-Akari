from __future__ import annotations

from .audio_player import AudioPlayer
from .fish_stream import FishStream
from .timeline_dispatcher import TimelineDispatcher


class SpeechPipeline:
    """
    High-level speech pipeline.

    Responsibilities:

        LLM text
            ↓
        Fish Audio
            ↓
        Audio playback
            ↓
        Timeline dispatch
    """

    def __init__(self):

        self.stream = FishStream()

        self.player = AudioPlayer()

        self.dispatcher = TimelineDispatcher()

    def speak(self, text: str):
        print("[Pipeline] Starting")

        stream = self.stream.stream(text)

        try:
            for chunk in self.player.play(stream):
                print("[Pipeline] Got chunk")
                self.dispatcher.process(chunk)

        finally:
            print("[Pipeline] Finished")
            self.dispatcher.reset()
