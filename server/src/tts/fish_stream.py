from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

from .sse_parser import parse_sse_line
from .stream_models import FishStreamChunk

load_dotenv()

API_KEY = os.getenv("FISH_AUDIO_API_KEY")
REFERENCE_ID = os.getenv("FISH_AUDIO_REFERENCE_ID")

MODEL = "s2.1-pro-free"

URL = (
    "https://api.fish.audio"
    "/v1/tts/stream/with-timestamp"
)


class FishStream:

    def __init__(self):
        self.client = httpx.Client(
            timeout=None,
        )

    def stream(
        self,
        text: str,
    ):

        response = self.client.post(
            URL,
            headers={
                "Authorization":
                    f"Bearer {API_KEY}",
                "Content-Type":
                    "application/json",
                "model":
                    MODEL,
            },
            json={
                "text": text,
                "reference_id":
                    REFERENCE_ID,
                "format": "wav",
                "latency": "balanced",
            },
        )

        response.raise_for_status()

        for line in response.iter_lines():

            if not line:
                continue

            chunk = parse_sse_line(line)

            if chunk is None:
                continue
            print(
                "[Fish]",
                chunk.sequence,
                len(chunk.audio),
            )
            yield chunk