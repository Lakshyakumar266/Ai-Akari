from __future__ import annotations

import base64
import json

from .stream_models import (
    AudioAlignment,
    FishStreamChunk,
    WordAlignment,
)


def parse_sse_line(
    line: str,
) -> FishStreamChunk | None:
    """
    Parses one Fish Audio SSE event.

    Expected format:

    data: { ...json... }

    Returns None for keep-alive events.
    """

    line = line.strip()

    if not line:
        return None

    if not line.startswith("data:"):
        return None

    payload = line[5:].strip()

    if payload == "[DONE]":
        return None

    event = json.loads(payload)

    #
    # Audio
    #

    audio = base64.b64decode(
        event.get("audio_base64", "")
    )

    #
    # Alignment
    #

    alignment_json = event.get(
        "alignment"
    )

    alignment = None

    if alignment_json:

        words = []

        for segment in alignment_json.get(
            "segments",
            [],
        ):

            words.append(
                WordAlignment(
                    text=segment["text"],
                    start=float(segment["start"]),
                    end=float(segment["end"]),
                )
            )

        alignment = AudioAlignment(
            audio_duration=float(
                alignment_json.get(
                    "audio_duration",
                    0,
                )
            ),
            words=words,
        )

    return FishStreamChunk(
        sequence=int(
            event.get(
                "chunk_seq",
                0,
            )
        ),
        audio_offset=float(
            event.get(
                "chunk_audio_offset_sec",
                0,
            )
        ),
        audio=audio,
        alignment=alignment,
    )