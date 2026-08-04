from __future__ import annotations

from enum import IntEnum


class BinaryPacket(IntEnum):
    """
    Binary packet types.

    First byte identifies the payload.
    """

    AUDIO = 1

    AUDIO_END = 2

    AUDIO_INTERRUPT = 3