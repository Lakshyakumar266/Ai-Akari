from __future__ import annotations

import time
import uuid

from .types import (
    SpeechTimeline,
    VisemeFrame,
)

from .phoneme_generator import (
    text_to_phonemes,
)

from .visemes import (
    phone_to_viseme,
)

#
# Temporary estimate.
# Later this will come from FishAudio timestamps.
#
AVERAGE_PHONEME_DURATION = 0.085

#
# Gives FishAudio time to buffer before
# the avatar starts moving.
#
START_DELAY = 0.25


def build_timeline(text: str) -> SpeechTimeline:
    """
    Converts text into a timed
    VRM viseme timeline.
    """

    phones = text_to_phonemes(text)

    frames: list[VisemeFrame] = []

    current_time = 0.0

    for phone in phones:
        frames.append(
            VisemeFrame(
                t=current_time,
                viseme=phone_to_viseme(phone),
            )
        )

        current_time += AVERAGE_PHONEME_DURATION

    #
    # Total duration
    #
    duration = current_time

    return SpeechTimeline(
        id=str(uuid.uuid4()),
        text=text,
        duration=duration,
        frames=frames,
    )


if __name__ == "__main__":
    timeline = build_timeline("Hello there, I am Akari.")

    print()
    print("Duration:", timeline.duration)
    print()

    for frame in timeline.frames:
        print(frame)
