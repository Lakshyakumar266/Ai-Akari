from __future__ import annotations

from src.bridge.audio import audio_chunk, audio_end
from src.bridge.dispatcher import dispatch


class AudioPlayer:
    """
    Consumes FishStreamChunk objects.

    Responsibilities:

        • Forward audio chunks as binary WebSocket packets to the browser
        • Yield each chunk so TimelineDispatcher can process alignment data

    MPV has been removed. The browser is now the audio output.
    """

    def play(
        self,
        stream,
    ):
        try:
            for chunk in stream:
                print(
                    "[AudioPlayer]",
                    len(chunk.audio),
                    "bytes",
                )

                if chunk.audio:
                    dispatch(
                        audio_chunk(
                            chunk.audio
                        )
                    )

                yield chunk

        finally:
            dispatch(
                audio_end()
            )