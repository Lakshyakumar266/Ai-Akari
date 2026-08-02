from __future__ import annotations

import asyncio
from websockets.asyncio.server import serve, ServerConnection

from .broadcaster import broadcaster


HOST = "127.0.0.1"
PORT = 8765


async def client_handler(websocket: ServerConnection):
    """
    Handles one connected client.

    Right now we only receive connections.

    Later we'll receive:
      - mouse position
      - camera position
      - interrupt speech
      - settings
      - avatar commands
    """

    await broadcaster.register(websocket)

    try:
        async for message in websocket:
            #
            # Ignore client messages for now.
            #
            print(f"[Bridge] Received: {message}")

    except Exception as e:
        print("[Bridge] Client error:", e)

    finally:
        await broadcaster.unregister(websocket)


async def start_websocket_server():
    async with serve(
        client_handler,
        HOST,
        PORT,
    ):
        print(
            f"[Bridge] WebSocket running on ws://{HOST}:{PORT}"
        )

        #
        # Keep server alive forever.
        #
        stop_event = asyncio.Event()
        try:
            await stop_event.wait()

        except asyncio.CancelledError:
            print("[Bridge] WebSocket server stopping...")
            raise