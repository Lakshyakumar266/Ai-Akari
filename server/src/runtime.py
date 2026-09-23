from __future__ import annotations

import asyncio

from src.bridge.dispatcher import initialize
from src.bridge.websocket_server import start_websocket_server
from src.voice import run_voice_loop


async def run():
    #
    # Give dispatcher access to the running event loop.
    #
    initialize(asyncio.get_running_loop())

    #
    # Start bridge.
    #
    websocket_task = asyncio.create_task(start_websocket_server())

    try:
        await run_voice_loop()

    finally:
        websocket_task.cancel()

        await asyncio.gather(
            websocket_task,
            return_exceptions=True,
        )