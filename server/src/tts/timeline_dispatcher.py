from __future__ import annotations

from src.bridge.dispatcher import dispatch
from src.bridge.events import speech

from .alignment_tracker import AlignmentTracker
from .stream_models import FishStreamChunk
from .timeline_accumulator import TimelineAccumulator


class TimelineDispatcher:
    """
    Converts Fish Audio alignment events
    into SpeechTimeline events.
    """

    def __init__(self):
        self.tracker = AlignmentTracker()
        self.timeline = TimelineAccumulator()

    def process(
        self,
        chunk: FishStreamChunk,
    ):

        for word in self.tracker.update(
            chunk.alignment
        ):

            timeline = self.timeline.add_word(
                word
            )

            dispatch(
                speech(
                    timeline
                )
            )

    def reset(self):

        self.tracker.reset()

        self.timeline.reset()