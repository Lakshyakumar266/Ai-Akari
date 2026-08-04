from __future__ import annotations

from .broadcaster import broadcaster
from .protocol import BinaryPacket


async def audio_chunk(
    audio: bytes,
):
    """
    Send one audio chunk.

    Packet format:

        byte[0] = packet type

        remaining = audio bytes
    """

    packet = bytes(
        [BinaryPacket.AUDIO]
    ) + audio

    await broadcaster.broadcast_binary(
        packet
    )


async def audio_end():
    packet = bytes(
        [BinaryPacket.AUDIO_END]
    )

    await broadcaster.broadcast_binary(
        packet
    )