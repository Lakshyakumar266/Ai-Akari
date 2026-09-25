from __future__ import annotations

import asyncio

from src.config import ENABLE_CHAT_INPUT
from src.bridge.dispatcher import initialize
from src.bridge.websocket_server import start_websocket_server


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
        if ENABLE_CHAT_INPUT:
            #
            # Chat input mode: the browser UI drives conversation.
            # No server-side mic loop — just keep the server alive.
            #
            print(
                "[Runtime] Chat input mode enabled. "
                "Waiting for messages from browser UI.\n"
            )
            await asyncio.Event().wait()
        else:
            #
            # Classic mode: server-side mic voice loop.
            #
            from src.voice import run_voice_loop

            await run_voice_loop()

    finally:
        websocket_task.cancel()

        await asyncio.gather(
            websocket_task,
            return_exceptions=True,
        )