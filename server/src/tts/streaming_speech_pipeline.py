from __future__ import annotations

from collections.abc import Generator

from .sentence_accumulator import (
    SentenceAccumulator,
)

from .speech_pipeline import (
    SpeechPipeline,
)


class StreamingSpeechPipeline:
    """
    Consumes streamed LLM tokens.

    Whenever a complete sentence is produced,
    it is immediately spoken using SpeechPipeline.
    """

    def __init__(self):

        self.pipeline = SpeechPipeline()

        self.accumulator = SentenceAccumulator()

    def speak(
        self,
        token_stream: Generator[str, None, None],
    ) -> str:
        """
        Returns the complete reply while
        speaking each sentence immediately.
        """

        reply: list[str] = []

        for token in token_stream:

            reply.append(token)

            for sentence in self.accumulator.push(
                token
            ):

                self.pipeline.speak(
                    sentence
                )

        #
        # Speak remaining text
        #

        for sentence in self.accumulator.flush():

            self.pipeline.speak(
                sentence
            )

        return "".join(reply)