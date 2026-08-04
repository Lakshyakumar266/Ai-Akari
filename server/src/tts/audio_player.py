from __future__ import annotations

import os
import subprocess

from .alignment_tracker import AlignmentTracker
from .timeline_accumulator import TimelineAccumulator


MPV_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "bin",
    "mpv-windows",
    "mpv.exe",
)


class AudioPlayer:
    """
    Consumes FishStreamChunk objects.

    Responsibilities:

        • Play audio immediately
        • Track new alignments
        • Build timelines
        • Dispatch speech events
    """

    def __init__(self):

        self.tracker = AlignmentTracker()

        self.timeline = TimelineAccumulator()

    def play(
        self,
        stream,
    ):

        proc = subprocess.Popen(
            [
                MPV_PATH,
                "--no-terminal",
                "--no-cache",
                "-",
            ],
            stdin=subprocess.PIPE,
        )

        try:

            for chunk in stream:
                print(
                    "[AudioPlayer]",
                    len(chunk.audio),
                )

                if chunk.audio:

                    proc.stdin.write(
                        chunk.audio
                    )

                    proc.stdin.flush()

                yield chunk

        finally:

            proc.stdin.close()

            proc.wait()