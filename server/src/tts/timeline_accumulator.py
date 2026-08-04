from __future__ import annotations

import uuid

from src.lipsync.types import (
    SpeechTimeline,
    VisemeFrame,
)

from .stream_models import (
    WordAlignment,
)

from .viseme_builder import (
    build_word_visemes,
)


class TimelineAccumulator:
    """
    Incrementally builds a SpeechTimeline
    from Fish Audio alignments.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.id = str(uuid.uuid4())

        self.frames: list[VisemeFrame] = []

        self.text_parts: list[str] = []

        self.duration = 0.0

    def add_word(
        self,
        word: WordAlignment,
    ) -> SpeechTimeline:

        new_frames = build_word_visemes(word)

        self.frames.extend(new_frames)

        self.text_parts.append(word.text)

        self.duration = max(
            self.duration,
            word.end,
        )

        return SpeechTimeline(
            id=self.id,
            text=" ".join(self.text_parts),
            duration=self.duration,
            frames=self.frames.copy(),
        )