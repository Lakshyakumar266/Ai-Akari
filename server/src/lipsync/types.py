from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4
import time

VisemeName = Literal[
    "aa",
    "ih",
    "ou",
    "ee",
    "oh",
    "sil",
]


@dataclass(slots=True)
class VisemeFrame:
    """
    One viseme at one point in time.

    t:
        Seconds from speech start.
    """

    t: float

    viseme: VisemeName

    weight: float = 1.0


@dataclass(slots=True)
class SpeechTimeline:
    id: str
    text: str
    duration: float
    frames: list[VisemeFrame]