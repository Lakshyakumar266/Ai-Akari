from __future__ import annotations

import os
import asyncio
import json
import numpy as np

from websockets.asyncio.server import serve, ServerConnection

from .broadcaster import broadcaster
from .protocol import BinaryPacket
from src.asr.server_asr import unload_asr_model
from src.asr.chat_whisper import unload_stream_model
from src.llm import (
    get_provider_info,
    set_active_provider,
    set_provider_api_key,
    has_provider_api_key,
    is_tool_calling_supported,
    is_vision_supported,
)
from src.config import TOOL_CALLING_ENABLED, MAX_TOOL_CALL_ROUNDS
from src.tools import tool_registry

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8765"))

# Dynamic mode state: True = Chat Mode (client UI driven), False = Stream Mode (server mic loop driven)
_chat_input_enabled: bool = True
_tool_calling_enabled: bool = TOOL_CALLING_ENABLED
_max_tool_calls: int = MAX_TOOL_CALL_ROUNDS


def _build_config_dict() -> dict:
    """Builds the comprehensive configuration payload for connected clients."""
    provider_info = get_provider_info()
    active_prov = provider_info["active_provider"]
    active_mod = provider_info["active_model"]
    supported = is_tool_calling_supported(active_prov, active_mod)
    vision_supported = is_vision_supported(active_prov, active_mod)
    return {
        "type": "config",
        "chat_input_enabled": _chat_input_enabled,
        "llm_provider": active_prov,
        "llm_model": active_mod,
        "available_llm_providers": provider_info["providers"],
        "tool_calling_enabled": _tool_calling_enabled and supported,
        "tool_calling_supported": supported,
        "vision_supported": vision_supported,
        "max_tool_calls": _max_tool_calls,
        "available_tools": tool_registry.get_tools_summary(),
        "api_keys_configured": provider_info.get("api_keys_configured", {}),
    }



def get_chat_input_enabled() -> bool:
    return _chat_input_enabled


async def set_chat_input_enabled(enabled: bool):
    global _chat_input_enabled
    from src.voice.loop import start_voice_loop, stop_voice_loop, is_voice_loop_running

    if _chat_input_enabled == enabled and (not enabled and is_voice_loop_running()):
        return

    _chat_input_enabled = enabled
    mode_name = "Chat Mode (ENABLE_CHAT_INPUT=True)" if enabled else "Stream Mode (ENABLE_CHAT_INPUT=False)"
    print(f"[Bridge] Mode updated from client: {mode_name}")

    if enabled:
        # Chat mode: Stop server mic voice loop and unload the medium ASR model
        await stop_voice_loop()
        unload_asr_model()
    else:
        # Stream mode: Unload the streaming small.en model, then start server voice loop with medium model
        unload_stream_model()
        await start_voice_loop()

    # Broadcast updated config event to all connected clients
    await broadcaster.broadcast(_build_config_dict())

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
        from src.asr.chat_whisper import transcribe_stream_interim

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
        from src.asr.chat_whisper import transcribe_stream_final

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
    """Send feature flags and LLM provider configuration to the client on connect."""
    await websocket.send(json.dumps(_build_config_dict()))


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


MAX_IMAGE_PAYLOAD_BYTES = 7 * 1024 * 1024  # 7MB max per image Data URI
ALLOWED_IMAGE_PREFIXES = (
    "data:image/jpeg;base64,",
    "data:image/png;base64,",
    "data:image/webp;base64,",
    "data:image/gif;base64,",
)


def _validate_image_attachment(data_uri: str | None) -> str | None:
    """Validates image payload size, format, and structure on the server."""
    if not data_uri or not isinstance(data_uri, str):
        return None

    if len(data_uri) > MAX_IMAGE_PAYLOAD_BYTES:
        print(f"[Bridge] Rejected oversized image: {len(data_uri)} bytes (limit={MAX_IMAGE_PAYLOAD_BYTES})")
        return None

    if not data_uri.startswith(ALLOWED_IMAGE_PREFIXES):
        print("[Bridge] Rejected unsupported image MIME type.")
        return None

    return data_uri


async def _handle_chat_message(data: dict):
    """Process a chat_message from the UI with optional image attachment and forward-compatible attachments array."""
    text = data.get("text", "").strip()

    # Extract image from attachments array or fallback image field
    attachments = data.get("attachments") or []
    raw_image = None
    if isinstance(attachments, list) and len(attachments) > 0:
        for att in attachments:
            if isinstance(att, dict) and att.get("type") == "image":
                raw_image = att.get("data")
                break

    if not raw_image:
        raw_image = data.get("image")

    image = _validate_image_attachment(raw_image)

    if not text and not image:
        return

    if not text and image:
        text = "Look at this image. What do you think?"

    provider = data.get("provider")
    model = data.get("model")
    if provider:
        set_active_provider(provider, model)

    from src.chat.loop import (
        process_chat_message,
        stop_chat_stream,
        set_active_chat_task,
    )

    # Cancel previous stream if still generating/speaking without emitting speech_end
    await stop_chat_stream(emit_speech_end=False)

    from src.tools.builtins import set_client_timezone
    client_tz = data.get("timezone")
    if client_tz:
        set_client_timezone(client_tz)

    req_tools = data.get("tools_enabled")
    tools_enabled = _tool_calling_enabled if req_tools is None else bool(req_tools)

    task = asyncio.create_task(
        process_chat_message(
            text,
            image=image,
            tools_enabled=tools_enabled,
            max_tool_rounds=_max_tool_calls,
        )
    )
    set_active_chat_task(task)


async def client_handler(websocket: ServerConnection):
    """
    Handles one connected client.

    Binary frames:
      VOICE_CHUNK (0x10) + PCM_INT16_DATA  → streamed voice audio (when in chat mode)
      VOICE_END   (0x11)                    → recording stopped
      AUDIO_INTERRUPT (0x03)                → stop response/stream

    JSON frames:
      set_mode          → { type: "set_mode", chat_input_enabled: bool, mode: "chat"|"stream" }
      set_llm_provider  → { type: "set_llm_provider", provider: "...", model: "..." }
      set_tool_calling  → { type: "set_tool_calling", enabled: bool, max_calls?: int }
      chat_message      → { type: "chat_message", text: "..." }
      interrupt         → { type: "interrupt" }
    """
    global _tool_calling_enabled, _max_tool_calls

    await broadcaster.register(websocket)
    await _send_config(websocket)

    try:
        async for message in websocket:
            # ── Binary path — voice audio packets ──────────────────────
            if isinstance(message, bytes):
                if len(message) < 1:
                    continue

                packet_type = message[0]

                if packet_type == BinaryPacket.VOICE_CHUNK:
                    if _chat_input_enabled:
                        await _handle_voice_chunk(websocket, message[1:])

                elif packet_type == BinaryPacket.VOICE_END:
                    if _chat_input_enabled:
                        await _handle_voice_end(websocket)

                elif packet_type == BinaryPacket.AUDIO_INTERRUPT:
                    from src.chat.loop import stop_chat_stream

                    print("[Bridge] Binary interrupt received from client.")
                    await stop_chat_stream()

                else:
                    print(f"[Bridge] Unknown binary packet from client: {packet_type}")

                continue

            # ── JSON path — text messages & mode control ───────────────
            try:
                data = json.loads(message)
                msg_type = data.get("type", "")

                if msg_type == "set_mode":
                    if "chat_input_enabled" in data:
                        enabled = bool(data["chat_input_enabled"])
                    elif "mode" in data:
                        enabled = (data["mode"] == "chat")
                    else:
                        enabled = True
                    if "llm_provider" in data:
                        set_active_provider(data["llm_provider"], data.get("llm_model"))
                        if _tool_calling_enabled and not is_tool_calling_supported(
                            data["llm_provider"], data.get("llm_model")
                        ):
                            _tool_calling_enabled = False
                    await set_chat_input_enabled(enabled)

                elif msg_type == "set_llm_provider":
                    provider_id = data.get("provider")
                    model_id = data.get("model")
                    if data.get("api_key"):
                        set_provider_api_key(provider_id, data["api_key"])
                    if provider_id:
                        set_active_provider(provider_id, model_id)
                        if _tool_calling_enabled and not is_tool_calling_supported(
                            provider_id, model_id
                        ):
                            print(
                                f"[Bridge] Disabling tool calling because new model '{model_id}' is unsupported."
                            )
                            _tool_calling_enabled = False
                        await broadcaster.broadcast(_build_config_dict())

                elif msg_type == "set_api_key":
                    provider_id = data.get("provider")
                    api_key = data.get("api_key", "")
                    if provider_id:
                        set_provider_api_key(provider_id, api_key)
                        await broadcaster.broadcast(_build_config_dict())

                elif msg_type == "get_config":
                    await websocket.send(json.dumps(_build_config_dict()))

                elif msg_type == "set_tool_calling":
                    enabled = bool(data.get("enabled", False))
                    if "max_calls" in data:
                        try:
                            _max_tool_calls = max(1, min(10, int(data["max_calls"])))
                        except Exception:
                            pass

                    provider_info = get_provider_info()
                    supported = is_tool_calling_supported(
                        provider_info["active_provider"], provider_info["active_model"]
                    )
                    if enabled and not supported:
                        print(
                            f"[Bridge] Tool calling not supported by '{provider_info['active_model']}', keeping disabled."
                        )
                        _tool_calling_enabled = False
                    else:
                        _tool_calling_enabled = enabled
                        print(
                            f"[Bridge] Tool calling updated: {_tool_calling_enabled} (max_calls={_max_tool_calls})"
                        )

                    await broadcaster.broadcast(_build_config_dict())

                elif msg_type == "chat_message":
                    if _chat_input_enabled:
                        asyncio.create_task(_handle_chat_message(data))
                    else:
                        print("[Bridge] Received chat_message while in stream mode, switching to chat mode.")
                        await set_chat_input_enabled(True)
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

        if broadcaster.client_count == 0:
            print("[Bridge] All clients disconnected. Halting voice loop and unloading models.")
            try:
                from src.voice.loop import stop_voice_loop
                await stop_voice_loop()
            except Exception as loop_err:
                print(f"[Bridge] Error halting voice loop: {loop_err}")
            unload_asr_model()
            unload_stream_model()


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