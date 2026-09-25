from __future__ import annotations

import asyncio
import json
import numpy as np

from websockets.asyncio.server import serve, ServerConnection

from .broadcaster import broadcaster
from .protocol import BinaryPacket
from src.config import ENABLE_CHAT_INPUT


HOST = "127.0.0.1"
PORT = 8765

# ─── Per-client voice recording state ────────────────────────────────────────

SAMPLE_RATE = 16000
INTERIM_INTERVAL = 0.5  # seconds between interim transcription runs


class VoiceSession:
    """Accumulates streamed PCM chunks and sends word-by-word live transcription."""

    def __init__(self, websocket: ServerConnection):
        self.websocket = websocket
        self.chunks: list[np.ndarray] = []
        self._interim_task: asyncio.Task | None = None
        self._sent_words_count = 0
        self._is_transcribing = False

    def add_chunk(self, pcm_int16: np.ndarray):
        self.chunks.append(pcm_int16)

    def get_audio(self) -> np.ndarray:
        if not self.chunks:
            return np.array([], dtype=np.float32)
        combined = np.concatenate(self.chunks)
        # int16 → float32 normalized
        return combined.astype(np.float32) / 32768.0

    def clear(self):
        self.chunks.clear()

    async def start_interim_loop(self):
        """Run Whisper frequently on accumulated audio for real-time live transcription."""
        self._interim_task = asyncio.create_task(self._interim_worker())

    async def stop_interim_loop(self):
        if self._interim_task:
            self._interim_task.cancel()
            try:
                await self._interim_task
            except asyncio.CancelledError:
                pass
            self._interim_task = None

    async def _interim_worker(self):
        from src.asr.stream_whisper import transcribe_stream_interim

        try:
            while True:
                await asyncio.sleep(INTERIM_INTERVAL)

                if self._is_transcribing:
                    continue

                audio = self.get_audio()
                if audio.size < SAMPLE_RATE * 0.4:  # skip if < 0.4s
                    continue

                self._is_transcribing = True
                try:
                    text = await asyncio.to_thread(transcribe_stream_interim, audio)
                    words = text.strip().split()
                    if len(words) > self._sent_words_count:
                        new_words = words[self._sent_words_count:]
                        self._sent_words_count = len(words)
                        for word in new_words:
                            print(f"[Voice] Word: {word}")
                            await self.websocket.send(
                                json.dumps({
                                    "type": "transcription",
                                    "text": word,
                                    "is_final": False,
                                })
                            )
                finally:
                    self._is_transcribing = False
        except asyncio.CancelledError:
            pass

    async def finalize(self):
        """Run final Whisper transcription and send any remaining words."""
        from src.asr.stream_whisper import transcribe_stream_final

        audio = self.get_audio()
        self.clear()

        if audio.size >= SAMPLE_RATE * 0.25:
            text = await asyncio.to_thread(transcribe_stream_final, audio)
            words = text.strip().split()
            if len(words) > self._sent_words_count:
                new_words = words[self._sent_words_count:]
                self._sent_words_count = len(words)
                for word in new_words:
                    print(f"[Voice] Word (final): {word}")
                    await self.websocket.send(
                        json.dumps({
                            "type": "transcription",
                            "text": word,
                            "is_final": False,
                        })
                    )

        # Notify finalization complete
        await self.websocket.send(
            json.dumps({
                "type": "transcription",
                "text": "",
                "is_final": True,
            })
        )


# Track active voice sessions per client
_voice_sessions: dict[ServerConnection, VoiceSession] = {}


# ─── Handlers ────────────────────────────────────────────────────────────────


async def _send_config(websocket: ServerConnection):
    """Send feature flags to the client on connect."""
    await websocket.send(
        json.dumps({
            "type": "config",
            "chat_input_enabled": ENABLE_CHAT_INPUT,
        })
    )


async def _handle_voice_chunk(websocket: ServerConnection, data: bytes):
    """Process a raw PCM int16 voice chunk from the browser."""
    session = _voice_sessions.get(websocket)
    if session is None:
        session = VoiceSession(websocket)
        _voice_sessions[websocket] = session
        await session.start_interim_loop()

    # Data is int16 PCM (little-endian)
    pcm = np.frombuffer(data, dtype=np.int16)
    session.add_chunk(pcm)


async def _handle_voice_end(websocket: ServerConnection):
    """Process end-of-recording signal."""
    session = _voice_sessions.pop(websocket, None)
    if session is None:
        return

    await session.stop_interim_loop()
    await session.finalize()


async def _handle_chat_message(data: dict):
    """Process a chat_message from the UI."""
    text = data.get("text", "").strip()
    if not text:
        return

    from src.chat.loop import (
        process_chat_message,
        stop_chat_stream,
        set_active_chat_task,
    )

    # Cancel previous stream if still generating/speaking
    await stop_chat_stream()

    task = asyncio.create_task(process_chat_message(text))
    set_active_chat_task(task)


async def client_handler(websocket: ServerConnection):
    """
    Handles one connected client.

    Binary frames:
      VOICE_CHUNK (0x10) + PCM_INT16_DATA  → streamed voice audio
      VOICE_END   (0x11)                    → recording stopped
      AUDIO_INTERRUPT (0x03)                → stop response/stream

    JSON frames:
      chat_message  → { type: "chat_message", text: "..." }
      interrupt     → { type: "interrupt" }
    """

    await broadcaster.register(websocket)
    await _send_config(websocket)

    try:
        async for message in websocket:
            if not ENABLE_CHAT_INPUT:
                continue

            # ── Binary path — voice audio packets ──────────────────────
            if isinstance(message, bytes):
                if len(message) < 1:
                    continue

                packet_type = message[0]

                if packet_type == BinaryPacket.VOICE_CHUNK:
                    await _handle_voice_chunk(websocket, message[1:])

                elif packet_type == BinaryPacket.VOICE_END:
                    await _handle_voice_end(websocket)

                elif packet_type == BinaryPacket.AUDIO_INTERRUPT:
                    from src.chat.loop import stop_chat_stream

                    print("[Bridge] Binary interrupt received from client.")
                    await stop_chat_stream()

                else:
                    print(f"[Bridge] Unknown binary packet from client: {packet_type}")

                continue

            # ── JSON path — text messages ──────────────────────────────
            try:
                data = json.loads(message)
                msg_type = data.get("type", "")

                if msg_type == "chat_message":
                    asyncio.create_task(_handle_chat_message(data))
                elif msg_type in ("interrupt", "stop"):
                    from src.chat.loop import stop_chat_stream

                    print("[Bridge] JSON interrupt received from client.")
                    await stop_chat_stream()
                else:
                    print(f"[Bridge] Unknown message type: {msg_type}")

            except json.JSONDecodeError:
                print(f"[Bridge] Invalid JSON: {message[:80]}")

    except Exception as e:
        print("[Bridge] Client error:", e)

    finally:
        # Clean up voice session if client disconnects mid-recording
        session = _voice_sessions.pop(websocket, None)
        if session:
            await session.stop_interim_loop()

        await broadcaster.unregister(websocket)


async def start_websocket_server():
    async with serve(
        client_handler,
        HOST,
        PORT,
        max_size=10 * 1024 * 1024,  # 10MB max message size for audio
    ):
        print(
            f"[Bridge] WebSocket running on ws://{HOST}:{PORT}"
        )

        stop_event = asyncio.Event()
        try:
            await stop_event.wait()

        except asyncio.CancelledError:
            print("[Bridge] WebSocket server stopping...")
            raise