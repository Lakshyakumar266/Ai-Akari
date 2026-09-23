from __future__ import annotations

from src.config import LIPSYNC_START_DELAY_MS
from src.lipsync.types import SpeechTimeline
from src.bridge.broadcaster import broadcaster

#
# Thinking
#


async def thinking_start():
    await broadcaster.broadcast(
        {
            "type": "thinking_start",
        }
    )


async def thinking_end():
    await broadcaster.broadcast(
        {
            "type": "thinking_end",
        }
    )


#
# Speech
#


async def speech_start():
    await broadcaster.broadcast(
        {
            "type": "speech_start",
        }
    )


async def speech_end():
    await broadcaster.broadcast(
        {
            "type": "speech_end",
        }
    )


async def speech(
    timeline: SpeechTimeline,
):
    await broadcaster.broadcast(
        {
            "type": "speech",
            "delay_ms": LIPSYNC_START_DELAY_MS,
            "timeline": {
                "id": timeline.id,
                "text": timeline.text,
                "duration": timeline.duration,
                "frames": [
                    {
                        "t": frame.t,
                        "viseme": frame.viseme,
                        "weight": frame.weight,
                    }
                    for frame in timeline.frames
                ],
            },
        }
    )


#
# Transcript
#


async def transcript(text: str):
    await broadcaster.broadcast(
        {
            "type": "transcript",
            "text": text,
        }
    )


#
# Emotion
#


async def emotion(name: str):
    await broadcaster.broadcast(
        {
            "type": "emotion",
            "emotion": name,
        }
    )


#
# Animation
#


async def animation(name: str):
    await broadcaster.broadcast(
        {
            "type": "animation",
            "animation": name,
        }
    )


#
# Subtitle
#


async def subtitle(text: str):
    await broadcaster.broadcast(
        {
            "type": "subtitle",
            "text": text,
        }
    )
