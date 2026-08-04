from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class WordAlignment:
    text: str
    start: float
    end: float


@dataclass(slots=True)
class AudioAlignment:
    audio_duration: float
    words: list[WordAlignment] = field(default_factory=list)


@dataclass(slots=True)
class FishStreamChunk:
    """
    One SSE event received from Fish Audio.
    """

    sequence: int
    audio_offset: float

    audio: bytes

    alignment: AudioAlignment | None