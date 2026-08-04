from __future__ import annotations

from .stream_models import (
    AudioAlignment,
    WordAlignment,
)


class AlignmentTracker:
    """
    Fish sends the COMPLETE alignment every event.

    We only want the NEW words.

    Example

    Event 1:
        Hello

    Event 2:
        Hello there

    Returns:
        there
    """

    def __init__(self):
        self._seen = 0

    def update(
        self,
        alignment: AudioAlignment | None,
    ) -> list[WordAlignment]:

        if alignment is None:
            return []

        words = alignment.words

        if self._seen >= len(words):
            return []

        new_words = words[self._seen :]

        self._seen = len(words)

        return new_words

    def reset(self):
        self._seen = 0