from __future__ import annotations

import re

class SentenceSplitter:
    """
    Incrementally extracts complete sentences from a stream
    of LLM tokens.

    Example:

        "Hello"
        " there."
        " How"
        " are"
        " you?"

    Produces:

        "Hello there."
        "How are you?"
    """

    _PATTERN = re.compile(r"(.+?[.!?]+)(?:\s+|$)", re.DOTALL)

    def __init__(self):
        self._buffer = ""

    def push(self, token: str) -> list[str]:
        self._buffer += token

        sentences: list[str] = []

        while True:
            match = self._PATTERN.match(self._buffer)

            if not match:
                break

            sentence = match.group(1).strip()

            if sentence:
                sentences.append(sentence)

            self._buffer = self._buffer[match.end():]

        return sentences

    def flush(self) -> list[str]:
        remaining = self._buffer.strip()
        self._buffer = ""

        return [remaining] if remaining else []