from __future__ import annotations

from .timeline import build_timeline
from .types import SpeechTimeline


def build_speech_timeline(
    text: str,
) -> SpeechTimeline:
    """
    Public entrypoint for the lip-sync system.

    Everything outside this package should call
    this function instead of using the individual
    phoneme/viseme/timeline modules.
    """

    return build_timeline(text)


if __name__ == "__main__":
    timeline = build_speech_timeline(
        "Hello, I am Akari."
    )

    print()

    print("ID:", timeline.id)
    print("Created:", timeline.created_at)
    print("Duration:", timeline.duration)

    print()

    for frame in timeline.frames:
        print(frame)