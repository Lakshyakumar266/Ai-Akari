from __future__ import annotations

import asyncio

_loop: asyncio.AbstractEventLoop | None = None


def initialize(
    loop: asyncio.AbstractEventLoop,
):
    global _loop

    _loop = loop


def dispatch(coro):
    """
    Schedule an async coroutine
    from synchronous code.
    """

    if _loop is None:
        return

    asyncio.run_coroutine_threadsafe(
        coro,
        _loop,
    )