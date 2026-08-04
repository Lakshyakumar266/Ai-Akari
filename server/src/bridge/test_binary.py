from src.bridge.audio import audio_chunk

import asyncio


async def main():
    print("start")
    await audio_chunk(
        b"hello"
    )
    print("done")


asyncio.run(main())