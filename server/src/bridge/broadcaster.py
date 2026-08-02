from __future__ import annotations

import asyncio
import json
from typing import Any

from websockets.asyncio.server import ServerConnection


class Broadcaster:
    """
    Central event broadcaster.

    Every server module publishes avatar events here.

    No module knows WebSockets exist.
    """

    def __init__(self):
        self._clients: set[ServerConnection] = set()
        self._lock = asyncio.Lock()

    #
    # Client Management
    #

    async def register(self, websocket: ServerConnection):
        async with self._lock:
            self._clients.add(websocket)

        print(
            f"[Bridge] Client connected "
            f"({len(self._clients)} total)"
        )

    async def unregister(self, websocket: ServerConnection):
        async with self._lock:
            self._clients.discard(websocket)

        print(
            f"[Bridge] Client disconnected "
            f"({len(self._clients)} total)"
        )

    #
    # Broadcast
    #

    async def broadcast(self, event: Any):
        """
        Broadcast a protocol dataclass
        to every connected client.
        """

        if not self._clients:
            return

        payload = json.dumps(event)

        dead_clients: list[ServerConnection] = []

        clients = list[ServerConnection](self._clients)

        for client in clients:
            try:
                await client.send(payload)

            except Exception:
                dead_clients.append(client)

        #
        # Remove dead sockets
        #

        if dead_clients:
            async with self._lock:
                for client in dead_clients:
                    self._clients.discard(client)

    #
    # Convenience
    #

    @property
    def connected_clients(self) -> int:
        return len(self._clients)


#
# Global singleton
#

broadcaster = Broadcaster()