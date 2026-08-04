from __future__ import annotations

import re


_SENTENCE_END = re.compile(
    r"""
    (
        .*?
        (?:
            \.\.\.          |   # ...
            [.!?]+          |   # . ! ?
            \n+                 # newline
        )
    )
    """,
    re.VERBOSE | re.DOTALL,
)


class SentenceAccumulator:
    """
    Collects streamed LLM tokens and emits
    completed sentences.

    Example:

        Tokens:
            Hello
             there
            .
             I
            am
             Akari
            .

        Emits:

            Hello there.
            I am Akari.
    """

    def __init__(self):
        self.buffer = ""

    def push(
        self,
        token: str,
    ) -> list[str]:

        self.buffer += token

        sentences: list[str] = []

        while True:

            match = _SENTENCE_END.match(
                self.buffer
            )

            if match is None:
                break

            sentence = match.group(1).strip()

            if sentence:
                sentences.append(sentence)

            self.buffer = self.buffer[
                match.end():
            ].lstrip()

        return sentences

    def flush(self) -> list[str]:

        if not self.buffer.strip():
            return []

        sentence = self.buffer.strip()

        self.buffer = ""

        return [sentence]

    def reset(self):

        self.buffer = ""