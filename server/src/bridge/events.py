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


#
# Speech Segment (Sentence-level synchronized dialogue & audio)
#


async def speech_segment(
    text: str,
    audio: str,
    is_last: bool,
    segment_index: int,
    total_segments: int,
    emotion: str = None,
):
    payload = {
        "type": "speech_segment",
        "text": text,
        "audio": audio,
        "is_last": is_last,
        "segment_index": segment_index,
        "total_segments": total_segments,
    }
    if emotion:
        payload["emotion"] = emotion
    await broadcaster.broadcast(payload)


#
# Transcription (voice-to-text result sent back to UI chat input)
#


async def transcription(text: str):
    await broadcaster.broadcast(
        {
            "type": "transcription",
            "text": text,
        }
    )

