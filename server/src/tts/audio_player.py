from __future__ import annotations

from src.bridge.audio import audio_chunk, audio_end
from src.bridge.dispatcher import dispatch


class AudioPlayer:
    """
    Iterates a Fish Audio stream and dispatches each audio chunk
    as a binary WebSocket packet to the browser.

    The browser handles all playback via Web Audio API + AudioQueue.
    There is no local MPV process.
    """

    def play(self, stream) -> None:
        try:
            for chunk in stream:
                if chunk.audio:
                    dispatch(audio_chunk(chunk.audio))
        finally:
            dispatch(audio_end())