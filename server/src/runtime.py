from __future__ import annotations

import asyncio

from src.bridge.dispatcher import initialize
from src.bridge.websocket_server import start_websocket_server
from src.voice.loop import stop_voice_loop


async def run():
    #
    # Give dispatcher access to the running event loop.
    #
    initialize(asyncio.get_running_loop())

    #
    # Start bridge server.
    #
    websocket_task = asyncio.create_task(start_websocket_server())

    try:
        print(
            "[Runtime] Akari companion server ready.\n"
            "[Runtime] Mode is managed dynamically by connected client:\n"
            "          - Chat Mode:   ENABLE_CHAT_INPUT=True  (client-driven conversation)\n"
            "          - Stream Mode: ENABLE_CHAT_INPUT=False (server-side mic & TTS loop)\n"
        )
        await asyncio.Event().wait()

    finally:
        await stop_voice_loop()
        websocket_task.cancel()

        await asyncio.gather(
            websocket_task,
            return_exceptions=True,
        )